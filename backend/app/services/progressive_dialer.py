"""
Progressive Dialer — main dialing loop.

Orchestrates:
  Pacing Engine → Safety Controller → Call Allocator

The pacing engine recommends how many calls to start.
The Safety Controller approves/reduces/rejects that count.
The Call Allocator executes only the approved count.

The Progressive Dialer can be run as a background thread or
stepped manually (for testing and simulation).
"""
from __future__ import annotations
import logging
import threading
import time
import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import update, func

from app.core.database import SessionLocal
from app.models.dialer_schema import (
    AgentState, CallState, SessionState, DialingMode,
    DialerAgent, DialerCall, DialerSession, DialerBorrowerLock,
)
from app.services.pacing_engine import PacingEngine, PacingInput
from app.services.safety_controller import SafetyController, SafetyVerdict
from app.services.call_allocator import CallAllocator
from app.services.providers import TelecomProvider

logger = logging.getLogger(__name__)


class ProgressiveDialer:
    """
    The main dialing loop.

    Implements both Progressive and Predictive modes.  The mode is
    determined by the DialerSession configuration and passed through to
    both the PacingEngine and the SafetyController.
    """

    TICK_INTERVAL_SEC = 1.0   # how often the loop recalculates

    def __init__(
        self,
        session_id: str,
        providers: List[TelecomProvider],
        event_processor=None,
    ):
        self.session_id = session_id
        self._pacing    = PacingEngine()
        self._safety    = SafetyController()
        self._allocator = CallAllocator(providers)
        if event_processor:
            self._allocator.register_event_callbacks(event_processor)

        self._running   = False
        self._thread: Optional[threading.Thread] = None
        self._lock      = threading.Lock()

    # ------------------------------------------------------------------
    # Control
    # ------------------------------------------------------------------

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
        self._thread = threading.Thread(
            target=self._loop,
            name=f"dialer-{self.session_id[:8]}",
            daemon=True,
        )
        self._thread.start()
        logger.info("ProgressiveDialer started: session=%s", self.session_id)

    def stop(self) -> None:
        with self._lock:
            self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("ProgressiveDialer stopped: session=%s", self.session_id)

    @property
    def is_running(self) -> bool:
        return self._running

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        while self._running:
            try:
                self._tick()
            except Exception as exc:
                logger.error("Dialer tick error: %s", exc, exc_info=True)
            time.sleep(self.TICK_INTERVAL_SEC)

    def _tick(self) -> dict:
        """Single dialing tick. Returns metrics dict (for testing)."""
        db = SessionLocal()
        try:
            return self._tick_with_db(db)
        finally:
            db.close()

    def _tick_with_db(self, db: Session) -> dict:
        # Check session state
        session = db.query(DialerSession).filter(
            DialerSession.session_id == self.session_id
        ).first()
        if not session or session.state != SessionState.RUNNING:
            self._running = False
            return {"skipped": "session not running"}

        mode = session.mode

        # Gather live metrics
        snap = self._gather_snapshot(db, session)

        # Step 1: Pacing recommendation
        pacing_input = PacingInput(
            available_agents=snap["available"],
            reserved_agents=snap["reserved"],
            dialing_agents=snap["dialing"],
            connected_agents=snap["connected"],
            wrap_up_agents=snap["wrap_up"],
            calls_initiated=snap["initiated"] + snap["ringing"],
            calls_connected=snap["answered"] + snap["connected_calls"],
            provider_health=snap["provider_health"],
            avg_setup_latency_ms=self._pacing.rolling_avg_latency_ms,
            avg_talk_time_sec=self._pacing.rolling_avg_talk_sec,
            answer_rate=self._pacing.rolling_answer_rate,
            mode=mode,
        )
        pacing_decision = self._pacing.recommend(pacing_input)

        # Step 2: Safety Controller (reads DB independently — cannot be bypassed)
        safety_decision = self._safety.evaluate(
            db, pacing_decision, self.session_id, mode
        )

        metrics = {
            "session_id": self.session_id,
            "mode": mode,
            "proposed_dials": pacing_decision.proposed_dials,
            "pacing_explanation": pacing_decision.explanation,
            "safety_verdict": safety_decision.verdict,
            "approved_dials": safety_decision.approved_dials,
            "safety_reason": safety_decision.reason,
            "snap": snap,
        }

        if safety_decision.verdict == SafetyVerdict.REJECTED:
            logger.debug("Safety REJECTED: %s", safety_decision.reason)
            return metrics

        if safety_decision.approved_dials == 0:
            return metrics

        # Step 3: Select eligible borrowers
        borrower_ids = self._get_eligible_borrowers(db, safety_decision.approved_dials)
        if not borrower_ids:
            return metrics

        # Step 4: Allocate (agent + borrower + provider call)
        created = self._allocator.allocate_batch(
            db, safety_decision, self.session_id, borrower_ids
        )
        metrics["calls_created"] = len(created)
        logger.debug("Tick: created %d calls, verdict=%s", len(created), safety_decision.verdict)
        return metrics

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _gather_snapshot(self, db: Session, session: DialerSession) -> dict:
        agent_counts = dict(
            db.query(DialerAgent.dialer_state, func.count(DialerAgent.id))
            .filter(DialerAgent.session_id == self.session_id)
            .group_by(DialerAgent.dialer_state)
            .all()
        )
        call_counts = dict(
            db.query(DialerCall.state, func.count(DialerCall.id))
            .filter(
                DialerCall.session_id == self.session_id,
                DialerCall.state.notin_(list(CallState.TERMINAL)),
            )
            .group_by(DialerCall.state)
            .all()
        )
        provider_health = {}
        from app.services.call_allocator import CircuitBreaker
        for name in self._allocator._providers:
            h = self._allocator._providers[name].get_health()
            cb = CircuitBreaker(name)
            from app.core.database import SessionLocal
            _db = SessionLocal()
            try:
                h["circuit_state"] = cb.get_state(_db)
                h["healthy"] = cb.get_state(_db) != "OPEN" and h.get("healthy", True)
            finally:
                _db.close()
            provider_health[name] = h

        return {
            "available":       agent_counts.get(AgentState.AVAILABLE, 0),
            "reserved":        agent_counts.get(AgentState.RESERVED, 0),
            "dialing":         agent_counts.get(AgentState.DIALING, 0),
            "connected":       agent_counts.get(AgentState.CONNECTED, 0),
            "wrap_up":         agent_counts.get(AgentState.WRAP_UP, 0),
            "initiated":       call_counts.get(CallState.INITIATED, 0),
            "ringing":         call_counts.get(CallState.RINGING, 0),
            "answered":        call_counts.get(CallState.ANSWERED, 0),
            "connected_calls": call_counts.get(CallState.CONNECTED, 0),
            "provider_health": provider_health,
        }

    def _get_eligible_borrowers(self, db: Session, limit: int) -> list[str]:
        """
        Get borrower IDs eligible for dialing:
        - Not currently locked (in DialerBorrowerLock)
        - Ordered by existing prioritization engine score if available
        """
        locked_ids = [
            row[0] for row in
            db.query(DialerBorrowerLock.borrower_id)
            .filter(DialerBorrowerLock.session_id == self.session_id)
            .all()
        ]

        # Use the existing prioritization engine's scored queue
        # Fallback: query Borrower table directly ordered by borrower_id
        try:
            from app.models.schema import Account
            q = (
                db.query(Account.borrower_id)
                .filter(
                    Account.compliance_hold == 0,
                    Account.dpd > 0,
                )
                .order_by(Account.dpd.desc(), Account.outstanding_amount.desc())
            )
            if locked_ids:
                q = q.filter(Account.borrower_id.notin_(locked_ids))
            rows = q.limit(limit).all()
            return [r[0] for r in rows if r[0]]
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Step method for testing and simulation
    # ------------------------------------------------------------------

    def step(self) -> dict:
        """Execute exactly one tick. For simulation and testing."""
        db = SessionLocal()
        try:
            return self._tick_with_db(db)
        finally:
            db.close()
