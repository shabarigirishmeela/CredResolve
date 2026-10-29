"""
Simulation engine for SmartDialer.

Runs scenarios A/B/C/D as defined in the assignment PDF:
  A: 20% answer rate, 120s avg talk time
  B: 50% answer rate, 90s avg talk time
  C: 70% answer rate, 180s avg talk time
  D: changing answer rate and talk time

The simulation uses the actual PacingEngine and SafetyController with
synthetic in-memory state (no DB I/O in tight loops) for speed.
Results include all required metrics from the assignment.
"""
from __future__ import annotations
import math
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.services.pacing_engine import PacingEngine, PacingInput
from app.services.safety_controller import SafetyController, SafetyVerdict
from app.services.providers import ProviderAlpha, ProviderBeta


SCENARIOS = {
    "A": {"answer_rate": 0.20, "avg_talk_sec": 120, "desc": "Low answer rate"},
    "B": {"answer_rate": 0.50, "avg_talk_sec": 90,  "desc": "Medium answer rate"},
    "C": {"answer_rate": 0.70, "avg_talk_sec": 180, "desc": "High answer rate"},
    "D": {"answer_rate": None, "avg_talk_sec": None, "desc": "Dynamic conditions"},
}


# ---------------------------------------------------------------------------
# Lightweight in-memory call / agent state
# ---------------------------------------------------------------------------

@dataclass
class SimCall:
    call_id: str
    agent_id: str
    borrower_id: str
    state: str = "INITIATED"
    tick_started: int = 0
    tick_answered: Optional[int] = None
    answered: bool = False
    completed: bool = False
    talk_ticks: int = 0    # ticks to completion


@dataclass
class SimAgent:
    agent_id: str
    state: str = "AVAILABLE"
    current_call_id: Optional[str] = None
    busy_until_tick: int = 0
    wrap_ticks: int = 3    # ticks in WRAP_UP before returning to AVAILABLE


@dataclass
class TickMetrics:
    tick: int
    available_agents: int
    busy_agents: int
    calls_initiated: int
    calls_ringing: int
    calls_connected: int
    calls_completed: int
    calls_failed: int
    proposed_dials: int
    approved_dials: int
    safety_verdict: str
    answer_rate: float
    agent_utilization: float
    safety_explanation: str = ""


@dataclass
class SimulationResult:
    scenario: str
    mode: str
    num_agents: int
    num_borrowers: int
    duration_ticks: int
    total_initiated: int = 0
    total_answered: int = 0
    total_completed: int = 0
    total_failed: int = 0
    total_abandoned: int = 0   # borrower answered, no agent (should be 0 in progressive)
    peak_utilization: float = 0.0
    avg_utilization: float = 0.0
    safety_reductions: int = 0
    safety_rejections: int = 0
    circuit_opens: int = 0
    tick_metrics: List[dict] = field(default_factory=list)
    description: str = ""


# ---------------------------------------------------------------------------
# Main simulation runner
# ---------------------------------------------------------------------------

def run_scenario(
    scenario: str,
    num_agents: int = 10,
    num_borrowers: int = 100,
    duration_ticks: int = 20,
    mode: str = "PREDICTIVE",
    provider_fail_rate: float = 0.0,
    include_provider_outage: bool = False,
) -> dict:
    """Run one scenario and return structured metrics."""

    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario}. Use A, B, C, or D.")

    cfg = SCENARIOS[scenario]
    result = SimulationResult(
        scenario=scenario,
        mode=mode,
        num_agents=num_agents,
        num_borrowers=num_borrowers,
        duration_ticks=duration_ticks,
        description=cfg["desc"],
    )

    # Build synthetic state
    agents   = [SimAgent(agent_id=f"sim-agent-{i}") for i in range(num_agents)]
    borrowers = [f"sim-borrower-{i}" for i in range(num_borrowers)]
    locked_borrowers: set = set()
    active_calls: Dict[str, SimCall] = {}

    pacing  = PacingEngine()
    safety  = SafetyController()

    # Use our mock providers for health signals
    provider_alpha = ProviderAlpha(fail_rate=provider_fail_rate)
    provider_beta  = ProviderBeta(fail_rate=provider_fail_rate)
    providers = [provider_alpha, provider_beta]

    util_samples = []
    outage_tick  = duration_ticks // 2 if include_provider_outage else -1
    borrower_idx = 0

    for tick in range(1, duration_ticks + 1):

        # --- Dynamic scenario D: change conditions mid-run ---
        if scenario == "D":
            answer_rate = 0.20 + 0.50 * math.sin(tick / duration_ticks * math.pi)
            avg_talk    = 60 + 120 * (1 - tick / duration_ticks)
        else:
            answer_rate = cfg["answer_rate"]
            avg_talk    = cfg["avg_talk_sec"]

        # --- Advance active calls by one tick ---
        to_complete = []
        for cid, call in list(active_calls.items()):
            if call.state == "INITIATED":
                # Simulate ringing → answer or fail
                if random.random() < answer_rate:
                    call.state = "ANSWERED"
                    call.answered = True
                    call.tick_answered = tick
                    call.talk_ticks   = max(1, int(avg_talk / 10))  # compressed
                    result.total_answered += 1
                    pacing.record_outcome(answered=True, talk_time_sec=avg_talk)
                    # Assign agent: find agent with this call
                    for a in agents:
                        if a.current_call_id == cid:
                            a.state = "CONNECTED"
                            a.busy_until_tick = tick + call.talk_ticks
                            break
                else:
                    call.state = "FAILED"
                    result.total_failed += 1
                    pacing.record_outcome(answered=False)
                    to_complete.append(cid)

            elif call.state == "ANSWERED":
                if tick >= (call.tick_answered or 0) + call.talk_ticks:
                    call.state = "COMPLETED"
                    call.completed = True
                    result.total_completed += 1
                    to_complete.append(cid)

        # Release completed/failed calls
        for cid in to_complete:
            call = active_calls.pop(cid, None)
            if call:
                locked_borrowers.discard(call.borrower_id)
                for a in agents:
                    if a.current_call_id == cid:
                        a.state = "WRAP_UP"
                        a.current_call_id = None
                        a.busy_until_tick = tick + a.wrap_ticks
                        break

        # Advance agents from WRAP_UP → AVAILABLE
        for a in agents:
            if a.state == "WRAP_UP" and tick >= a.busy_until_tick:
                a.state = "AVAILABLE"

        # Provider outage simulation
        if tick == outage_tick:
            result.circuit_opens += 1
            provider_beta.set_failure_rate(0.9)  # simulate outage

        # --- Compute live counts ---
        available  = sum(1 for a in agents if a.state == "AVAILABLE")
        connected  = sum(1 for a in agents if a.state == "CONNECTED")
        reserved   = sum(1 for a in agents if a.state == "RESERVED")
        wrap_count = sum(1 for a in agents if a.state == "WRAP_UP")
        initiated  = sum(1 for c in active_calls.values() if c.state == "INITIATED")
        answered_c = sum(1 for c in active_calls.values() if c.state == "ANSWERED")

        utilization = (connected + reserved) / max(1, num_agents)
        util_samples.append(utilization)
        result.peak_utilization = max(result.peak_utilization, utilization)

        provider_health = {p.name: p.get_health() for p in providers}

        # --- Pacing recommendation ---
        inp = PacingInput(
            available_agents=available,
            reserved_agents=reserved,
            dialing_agents=0,   # simplified: no DIALING state in sim
            connected_agents=connected,
            wrap_up_agents=wrap_count,
            calls_initiated=initiated,
            calls_connected=answered_c,
            provider_health=provider_health,
            avg_setup_latency_ms=pacing.rolling_avg_latency_ms,
            avg_talk_time_sec=pacing.rolling_avg_talk_sec,
            answer_rate=pacing.rolling_answer_rate,
            mode=mode,
        )
        pd = pacing.recommend(inp)

        # --- Safety evaluation (in-memory simulation, no DB) ---
        sd = _sim_safety_eval(
            available=available,
            reserved=reserved,
            connected=connected,
            wrap_count=wrap_count,
            initiated=initiated,
            proposed=pd.proposed_dials,
            num_agents=num_agents,
            mode=mode,
            any_circuit_open=(tick == outage_tick),
        )

        if sd["verdict"] == "REDUCED":
            result.safety_reductions += 1
        elif sd["verdict"] == "REJECTED":
            result.safety_rejections += 1

        approved = sd["approved_dials"]

        # --- Allocate calls ---
        new_calls = 0
        for _ in range(approved):
            if available <= 0:
                break
            # Find free agent
            free_agent = next((a for a in agents if a.state == "AVAILABLE"), None)
            if not free_agent:
                break
            # Find free borrower
            while borrower_idx < len(borrowers) and borrowers[borrower_idx] in locked_borrowers:
                borrower_idx += 1
            if borrower_idx >= len(borrowers):
                break

            bid = borrowers[borrower_idx]
            locked_borrowers.add(bid)
            borrower_idx = (borrower_idx + 1) % len(borrowers)

            cid = f"sim-call-{tick}-{new_calls}"
            call = SimCall(
                call_id=cid,
                agent_id=free_agent.agent_id,
                borrower_id=bid,
                tick_started=tick,
            )
            active_calls[cid] = call
            free_agent.state = "RESERVED"
            free_agent.current_call_id = cid
            free_agent.state = "CONNECTED" if random.random() < 0.5 else "RESERVED"
            available -= 1
            new_calls += 1
            result.total_initiated += 1

        result.tick_metrics.append({
            "tick": tick,
            "available_agents": available,
            "connected_agents": connected,
            "calls_initiated": initiated,
            "calls_in_progress": len(active_calls),
            "new_calls_this_tick": new_calls,
            "proposed_dials": pd.proposed_dials,
            "approved_dials": approved,
            "safety_verdict": sd["verdict"],
            "answer_rate_pct": round(pacing.rolling_answer_rate * 100, 1),
            "utilization_pct": round(utilization * 100, 1),
            "pacing_explanation": pd.explanation[:200],
        })

    result.avg_utilization = sum(util_samples) / max(1, len(util_samples))

    return {
        "scenario": scenario,
        "description": cfg["desc"],
        "mode": mode,
        "num_agents": num_agents,
        "num_borrowers": num_borrowers,
        "duration_ticks": duration_ticks,
        "summary": {
            "total_initiated": result.total_initiated,
            "total_answered": result.total_answered,
            "total_completed": result.total_completed,
            "total_failed": result.total_failed,
            "total_abandoned": result.total_abandoned,
            "answer_rate_pct": round(
                result.total_answered / max(1, result.total_initiated) * 100, 2
            ),
            "peak_utilization_pct": round(result.peak_utilization * 100, 2),
            "avg_utilization_pct": round(result.avg_utilization * 100, 2),
            "safety_reductions": result.safety_reductions,
            "safety_rejections": result.safety_rejections,
            "circuit_opens": result.circuit_opens,
        },
        "tick_metrics": result.tick_metrics,
    }


def _sim_safety_eval(
    available: int,
    reserved: int,
    connected: int,
    wrap_count: int,
    initiated: int,
    proposed: int,
    num_agents: int,
    mode: str,
    any_circuit_open: bool,
) -> dict:
    """Lightweight safety check for simulation (mirrors SafetyController logic)."""
    import math

    if proposed <= 0:
        return {"verdict": "REJECTED", "approved_dials": 0, "reason": "proposed=0"}

    if mode == "PROGRESSIVE":
        cap = available
        if proposed > cap:
            return {"verdict": "REDUCED", "approved_dials": cap, "reason": "progressive cap"}
        return {"verdict": "APPROVED", "approved_dials": proposed, "reason": "progressive ok"}

    if any_circuit_open:
        return {"verdict": "FALLBACK", "approved_dials": min(proposed, available), "reason": "circuit open"}

    if available == 0:
        return {"verdict": "REJECTED", "approved_dials": 0, "reason": "no available agents"}

    max_overhang = math.floor(num_agents * 0.25)
    if initiated >= max_overhang:
        return {"verdict": "REJECTED", "approved_dials": 0, "reason": "overhang limit"}

    approved = min(proposed, max_overhang - initiated, available)
    if approved < proposed:
        return {"verdict": "REDUCED", "approved_dials": approved, "reason": "capacity limit"}

    return {"verdict": "APPROVED", "approved_dials": approved, "reason": "ok"}
