"""
Independent Safety Controller.

Mandatory firewall between the Pacing Engine and the Call Allocator.
The pacing engine cannot bypass this component.

Responsibilities:
- Query the database for the true authoritative state of agents (not a cache).
- Validate the pacing recommendation against hard capacity limits.
- Approve, reduce, or reject the proposed dial count.
- Fall back to progressive mode (1 available agent = 1 call) when unsafe.
- Fail CLOSED when safety cannot be established.
- Track abandoned-call risk (connected borrowers without free agents).
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.dialer_schema import (
    AgentState, CallState, CircuitState,
    DialerAgent, DialerCall, DialerProviderHealth,
)
from app.services.pacing_engine import PacingDecision


class SafetyVerdict(str, Enum):
    APPROVED    = "APPROVED"
    REDUCED     = "REDUCED"
    REJECTED    = "REJECTED"
    FALLBACK    = "FALLBACK"    # fell back to progressive (1:1)


@dataclass
class SafetyDecision:
    verdict: SafetyVerdict
    approved_dials: int          # number the allocator is allowed to initiate
    original_proposed: int
    reason: str
    checked_at: str = ""

    def __post_init__(self):
        if not self.checked_at:
            self.checked_at = datetime.utcnow().isoformat()


# Hard limits – the pacing engine has NO access to these constants.
_MAX_OVERHANG_RATIO = 0.25   # max (in-flight calls) / (total agents)
_MIN_FREE_AGENTS_RATIO = 0.10  # keep at least 10% agents free for incoming answers
_MAX_ABANDON_RISK = 0.05      # max fraction of ringing calls that may be abandoned


class SafetyController:
    """
    The Safety Controller queries the database directly for the authoritative
    picture of agent states.  It does NOT trust values passed in by the pacing
    engine or any other caller.

    The pacing engine is given no reference to this class; it only sees
    PacingDecision objects it produces.  The allocator is given SafetyDecision
    objects it receives from this class.

    Architectural invariant: the pacing engine's `recommend()` method has no
    parameters that can increase the approved_dials above what the Safety
    Controller computes independently.
    """

    def evaluate(
        self,
        db: Session,
        pacing: PacingDecision,
        session_id: str,
        mode: str = "PREDICTIVE",
    ) -> SafetyDecision:
        """
        Evaluate the pacing engine's recommendation.
        Reads agent/call counts DIRECTLY from the database (authoritative state).
        """
        try:
            return self._evaluate_inner(db, pacing, session_id, mode)
        except Exception as exc:
            # Fail CLOSED: any error → reject to prevent unsafe allocation
            return SafetyDecision(
                verdict=SafetyVerdict.REJECTED,
                approved_dials=0,
                original_proposed=pacing.proposed_dials,
                reason=f"Safety Controller error (fail-closed): {exc}",
            )

    # ------------------------------------------------------------------
    # Internal evaluation
    # ------------------------------------------------------------------

    def _evaluate_inner(
        self,
        db: Session,
        pacing: PacingDecision,
        session_id: str,
        mode: str,
    ) -> SafetyDecision:
        proposed = pacing.proposed_dials

        if proposed < 0:
            return SafetyDecision(
                verdict=SafetyVerdict.REJECTED,
                approved_dials=0,
                original_proposed=proposed,
                reason="Proposed dial count is negative",
            )

        # --- Read authoritative state from DB ---
        agent_counts = self._count_agents(db, session_id)
        call_counts  = self._count_calls(db, session_id)
        any_circuit_open = self._any_circuit_open(db)

        available  = agent_counts.get(AgentState.AVAILABLE, 0)
        total_agents = sum(agent_counts.values())

        in_flight  = (
            call_counts.get(CallState.INITIATED, 0) +
            call_counts.get(CallState.RINGING, 0) +
            call_counts.get(CallState.RESERVED, 0)
        )
        connected  = (
            call_counts.get(CallState.ANSWERED, 0) +
            call_counts.get(CallState.CONNECTED, 0)
        )

        # --- Progressive mode: hard 1:1 cap ---
        if mode == "PROGRESSIVE":
            cap = available
            if proposed > cap:
                return SafetyDecision(
                    verdict=SafetyVerdict.REDUCED,
                    approved_dials=cap,
                    original_proposed=proposed,
                    reason=(
                        f"PROGRESSIVE: capped at {cap} available agents "
                        f"(proposed {proposed})"
                    ),
                )
            return SafetyDecision(
                verdict=SafetyVerdict.APPROVED,
                approved_dials=proposed,
                original_proposed=proposed,
                reason=f"PROGRESSIVE: {proposed} ≤ {available} available agents",
            )

        # --- Circuit breaker: fail closed ---
        if any_circuit_open:
            # Allow at most progressive (1:1) when a provider is down
            cap = available
            if proposed > cap:
                return SafetyDecision(
                    verdict=SafetyVerdict.FALLBACK,
                    approved_dials=cap,
                    original_proposed=proposed,
                    reason=(
                        f"Provider circuit OPEN: falling back to progressive cap "
                        f"of {cap} (proposed {proposed})"
                    ),
                )

        # --- Hard capacity checks ---
        # 1. Cannot exceed available agents in any mode (no free agent = abandoned call risk)
        if available == 0:
            return SafetyDecision(
                verdict=SafetyVerdict.REJECTED,
                approved_dials=0,
                original_proposed=proposed,
                reason="No available agents — all dials would risk abandonment",
            )

        # 2. Keep at least MIN_FREE_AGENTS_RATIO agents free
        min_free = max(1, math.ceil(total_agents * _MIN_FREE_AGENTS_RATIO))
        headroom_after = available - proposed
        if headroom_after < min_free:
            adjusted = max(0, available - min_free)
            if adjusted == 0:
                return SafetyDecision(
                    verdict=SafetyVerdict.REJECTED,
                    approved_dials=0,
                    original_proposed=proposed,
                    reason=(
                        f"Insufficient headroom: need {min_free} free agents, "
                        f"only {available} available"
                    ),
                )
            return SafetyDecision(
                verdict=SafetyVerdict.REDUCED,
                approved_dials=adjusted,
                original_proposed=proposed,
                reason=(
                    f"Reduced from {proposed} to {adjusted}: maintaining "
                    f"{min_free}-agent safety buffer"
                ),
            )

        # 3. Overhang limit: (in_flight + proposed) / total_agents ≤ MAX_OVERHANG_RATIO
        if total_agents > 0:
            projected_overhang = (in_flight + proposed) / total_agents
            if projected_overhang > _MAX_OVERHANG_RATIO:
                allowed_inflight = math.floor(total_agents * _MAX_OVERHANG_RATIO)
                adjusted = max(0, allowed_inflight - in_flight)
                if adjusted <= 0:
                    return SafetyDecision(
                        verdict=SafetyVerdict.REJECTED,
                        approved_dials=0,
                        original_proposed=proposed,
                        reason=(
                            f"Overhang limit: {in_flight} calls already in-flight "
                            f"(limit {allowed_inflight} for {total_agents} agents)"
                        ),
                    )
                return SafetyDecision(
                    verdict=SafetyVerdict.REDUCED,
                    approved_dials=adjusted,
                    original_proposed=proposed,
                    reason=(
                        f"Overhang limit: reduced from {proposed} to {adjusted} "
                        f"(in-flight={in_flight}, total_agents={total_agents})"
                    ),
                )

        return SafetyDecision(
            verdict=SafetyVerdict.APPROVED,
            approved_dials=proposed,
            original_proposed=proposed,
            reason=(
                f"Approved: available={available}, in_flight={in_flight}, "
                f"connected={connected}"
            ),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _count_agents(self, db: Session, session_id: str) -> dict:
        rows = (
            db.query(DialerAgent.dialer_state, func.count(DialerAgent.id))
            .filter(DialerAgent.session_id == session_id)
            .group_by(DialerAgent.dialer_state)
            .all()
        )
        return {state: count for state, count in rows}

    def _count_calls(self, db: Session, session_id: str) -> dict:
        rows = (
            db.query(DialerCall.state, func.count(DialerCall.id))
            .filter(
                DialerCall.session_id == session_id,
                DialerCall.state.notin_(list(CallState.TERMINAL)),
            )
            .group_by(DialerCall.state)
            .all()
        )
        return {state: count for state, count in rows}

    def _any_circuit_open(self, db: Session) -> bool:
        return (
            db.query(DialerProviderHealth)
            .filter(DialerProviderHealth.circuit_state == CircuitState.OPEN)
            .count()
        ) > 0
