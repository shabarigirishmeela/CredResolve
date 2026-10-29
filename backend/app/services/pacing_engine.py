"""
Predictive Pacing Engine.

Rule-based algorithm that estimates how many additional calls can be safely
initiated right now.  It NEVER places calls directly — it only produces a
recommendation that the Safety Controller must approve.

Formula (Erlang-inspired occupancy model):
    expected_new_connections = proposed_dials * answer_rate
    agents_needed_now       = connected_calls + calls_ringing * answer_rate
    headroom                = available_agents - agents_needed_now
    safe_dials              = headroom / max(answer_rate, 0.01)

Adjusted for:
    - Provider health (reduce when circuit is OPEN or degraded)
    - Setup latency (slower providers → dial earlier / fewer)
    - Recency bias on answer rate (rolling 50-call window)
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime, timedelta
from typing import Deque, Optional


@dataclass
class PacingInput:
    """Live snapshot fed to the engine each tick."""
    available_agents: int          # AVAILABLE state
    reserved_agents: int           # RESERVED (allocated but not yet dialing)
    dialing_agents: int            # DIALING state
    connected_agents: int          # CONNECTED state
    wrap_up_agents: int            # WRAP_UP state

    calls_initiated: int           # INITIATED + RINGING (in-flight, answer unknown)
    calls_connected: int           # ANSWERED + CONNECTED (agent busy)

    provider_health: dict          # {provider_name: {"healthy": bool, "failure_rate": float}}
    avg_setup_latency_ms: float    # observed provider setup time
    avg_talk_time_sec: float       # rolling average call duration
    answer_rate: float             # rolling answer rate (0.0–1.0)

    mode: str = "PREDICTIVE"       # "PROGRESSIVE" | "PREDICTIVE"


@dataclass
class PacingDecision:
    """Output of the pacing engine — forwarded to the Safety Controller."""
    proposed_dials: int
    explanation: str
    inputs_snapshot: dict = field(default_factory=dict)
    computed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class AnswerRateTracker:
    """Rolling-window answer rate tracker (thread-safe enough for single-writer use)."""

    def __init__(self, window: int = 50):
        self._window = window
        self._outcomes: Deque[bool] = deque(maxlen=window)

    def record(self, answered: bool) -> None:
        self._outcomes.append(answered)

    @property
    def rate(self) -> float:
        if not self._outcomes:
            return 0.5   # neutral prior when no data
        return sum(self._outcomes) / len(self._outcomes)

    @property
    def sample_count(self) -> int:
        return len(self._outcomes)


class PacingEngine:
    """
    Stateless core computation + stateful tracker.

    The engine is intentionally separated from the Safety Controller so that
    the Controller can override any recommendation without the engine being
    able to circumvent it.
    """

    # Overhang cap as a fraction of total agents (predictive mode)
    # MUST match Safety Controller's _MAX_OVERHANG_RATIO (0.25) to avoid
    # proposing dials that safety will reject
    MAX_OVERHANG_RATIO = 0.25

    def __init__(self) -> None:
        self._answer_tracker = AnswerRateTracker(window=50)
        self._setup_latency_samples: Deque[float] = deque(maxlen=20)
        self._talk_time_samples: Deque[float] = deque(maxlen=50)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def recommend(self, inp: PacingInput) -> PacingDecision:
        """Compute how many additional calls to propose."""
        if inp.mode == "PROGRESSIVE":
            return self._progressive(inp)
        return self._predictive(inp)

    def record_outcome(
        self,
        answered: bool,
        setup_latency_ms: float = 0.0,
        talk_time_sec: float = 0.0,
    ) -> None:
        self._answer_tracker.record(answered)
        if setup_latency_ms > 0:
            self._setup_latency_samples.append(setup_latency_ms)
        if talk_time_sec > 0:
            self._talk_time_samples.append(talk_time_sec)

    @property
    def rolling_answer_rate(self) -> float:
        return self._answer_tracker.rate

    @property
    def rolling_avg_talk_sec(self) -> float:
        if not self._talk_time_samples:
            return 120.0
        return sum(self._talk_time_samples) / len(self._talk_time_samples)

    @property
    def rolling_avg_latency_ms(self) -> float:
        if not self._setup_latency_samples:
            return 300.0
        return sum(self._setup_latency_samples) / len(self._setup_latency_samples)

    # ------------------------------------------------------------------
    # Progressive mode: 1 available agent → 1 outbound call
    # ------------------------------------------------------------------

    def _progressive(self, inp: PacingInput) -> PacingDecision:
        dials = inp.available_agents  # strict 1:1 mapping
        explanation = (
            f"PROGRESSIVE: {inp.available_agents} available agents → "
            f"propose {dials} dials (1:1 mapping, no overhang)"
        )
        return PacingDecision(
            proposed_dials=max(0, dials),
            explanation=explanation,
            inputs_snapshot=self._snap(inp),
        )

    # ------------------------------------------------------------------
    # Predictive mode: Erlang occupancy model
    # ------------------------------------------------------------------

    def _predictive(self, inp: PacingInput) -> PacingDecision:
        answer_rate = max(inp.answer_rate, 0.01)
        total_agents = (
            inp.available_agents + inp.reserved_agents +
            inp.dialing_agents + inp.connected_agents + inp.wrap_up_agents
        )

        # Agents currently occupied or earmarked
        agents_committed = (
            inp.reserved_agents +
            inp.dialing_agents +
            inp.connected_agents +
            # wrap-up will soon be available, discount at 50%
            math.ceil(inp.wrap_up_agents * 0.5)
        )

        # Expected additional connections from in-flight calls
        expected_connections = inp.calls_initiated * answer_rate

        # Free headroom: agents available minus expected occupancy
        free_headroom = inp.available_agents - expected_connections

        if free_headroom <= 0:
            return PacingDecision(
                proposed_dials=0,
                explanation=(
                    f"PREDICTIVE: headroom={free_headroom:.1f} ≤ 0 "
                    f"(in-flight={inp.calls_initiated}, answer_rate={answer_rate:.0%}); "
                    f"proposing 0 dials"
                ),
                inputs_snapshot=self._snap(inp),
            )

        # How many additional dials can we absorb?
        # If answer_rate is 30%, dialing 10 will yield ~3 connections.
        # We want to fill headroom fully → safe_dials = headroom / answer_rate
        raw_dials = free_headroom / answer_rate

        # Cap overhang: never propose more than MAX_OVERHANG_RATIO of total agents
        # Use floor to match Safety Controller's calculation (not ceil)
        max_overhang = math.floor(total_agents * self.MAX_OVERHANG_RATIO)
        current_inflight = inp.calls_initiated + inp.reserved_agents
        headroom_cap = max(0, max_overhang - current_inflight)
        dials = min(raw_dials, headroom_cap)

        # Provider health penalty: reduce if any provider is degraded
        health_factor = self._provider_health_factor(inp.provider_health)
        dials = math.floor(dials * health_factor)

        # No minimum floor: respect headroom_cap and safety limits
        # The Safety Controller is the authoritative check and will enforce
        # the real capacity constraints. Pacing should not force a minimum
        # that could exceed what safety allows.

        explanation = (
            f"PREDICTIVE: available={inp.available_agents}, "
            f"in-flight={inp.calls_initiated}, answer_rate={answer_rate:.0%}, "
            f"headroom={free_headroom:.1f}, raw_dials={raw_dials:.1f}, "
            f"overhang_cap={headroom_cap}, health_factor={health_factor:.2f} "
            f"→ propose {dials} dials"
        )
        return PacingDecision(
            proposed_dials=max(0, dials),
            explanation=explanation,
            inputs_snapshot=self._snap(inp),
        )

    def _provider_health_factor(self, health: dict) -> float:
        """Return 0.0–1.0 scalar. All-healthy → 1.0. Any OPEN circuit → 0.0."""
        if not health:
            return 1.0
        factors = []
        for _, h in health.items():
            if not h.get("healthy", True):
                fr = h.get("failure_rate", 0.5)
                factors.append(max(0.0, 1.0 - fr * 2))
            else:
                factors.append(1.0)
        return min(factors) if factors else 1.0

    def _snap(self, inp: PacingInput) -> dict:
        return {
            "available_agents": inp.available_agents,
            "reserved_agents": inp.reserved_agents,
            "dialing_agents": inp.dialing_agents,
            "connected_agents": inp.connected_agents,
            "calls_initiated": inp.calls_initiated,
            "calls_connected": inp.calls_connected,
            "answer_rate": inp.answer_rate,
            "avg_setup_latency_ms": inp.avg_setup_latency_ms,
            "avg_talk_time_sec": inp.avg_talk_time_sec,
            "mode": inp.mode,
        }
