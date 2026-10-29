"""
Dialer State Machines.

Enforces valid transitions for agent and call lifecycle states.
Every transition is persisted to dialer_state_logs for audit.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import update

from app.models.dialer_schema import (
    AgentState, CallState,
    DialerAgent, DialerCall, DialerStateLog,
)


class InvalidTransition(Exception):
    """Raised when a requested state transition is not permitted."""


# ---------------------------------------------------------------------------
# Agent state machine
# ---------------------------------------------------------------------------

def transition_agent(
    db: Session,
    agent_id: str,
    to_state: str,
    reason: str = "",
    worker_id: str = "",
    expected_version: Optional[int] = None,
) -> DialerAgent:
    """
    Atomically transition a DialerAgent using optimistic concurrency control.

    For SQLite the UPDATE with a WHERE clause on (state, version) is serialized by
    the write lock, so exactly one concurrent worker can succeed.

    Raises InvalidTransition if transition is not allowed.
    Raises LookupError if agent not found.
    Raises RuntimeError if the OCC version check fails (another worker won the race).
    """
    agent = db.query(DialerAgent).filter(
        DialerAgent.agent_id == agent_id
    ).first()
    if not agent:
        raise LookupError(f"DialerAgent not found: {agent_id}")

    from_state = agent.dialer_state
    _validate_agent_transition(from_state, to_state, agent_id)

    if expected_version is not None and agent.version != expected_version:
        raise RuntimeError(
            f"OCC conflict: agent {agent_id} version mismatch "
            f"(expected {expected_version}, got {agent.version})"
        )

    # Atomic update: only succeeds if state + version still match
    result = db.execute(
        update(DialerAgent)
        .where(
            DialerAgent.agent_id == agent_id,
            DialerAgent.dialer_state == from_state,
            DialerAgent.version == agent.version,
        )
        .values(
            dialer_state=to_state,
            version=DialerAgent.version + 1,
            reserved_at=(datetime.utcnow() if to_state == AgentState.RESERVED else agent.reserved_at),
            connected_at=(datetime.utcnow() if to_state == AgentState.CONNECTED else agent.connected_at),
            wrap_start_at=(datetime.utcnow() if to_state == AgentState.WRAP_UP else agent.wrap_start_at),
            updated_at=datetime.utcnow(),
        )
    )
    if result.rowcount == 0:
        raise RuntimeError(
            f"OCC conflict: agent {agent_id} was modified by another worker"
        )

    # Log the transition
    db.add(DialerStateLog(
        entity_type="agent",
        entity_id=agent_id,
        from_state=from_state,
        to_state=to_state,
        reason=reason[:255] if reason else None,
        worker_id=worker_id[:64] if worker_id else None,
        occurred_at=datetime.utcnow(),
    ))
    db.flush()
    db.refresh(agent)
    return agent


def _validate_agent_transition(from_state: str, to_state: str, agent_id: str) -> None:
    allowed = AgentState.TRANSITIONS.get(from_state)
    if allowed is None:
        raise InvalidTransition(
            f"Agent {agent_id}: unknown state '{from_state}'"
        )
    if to_state not in allowed:
        raise InvalidTransition(
            f"Agent {agent_id}: {from_state} → {to_state} is not permitted. "
            f"Allowed: {allowed}"
        )


# ---------------------------------------------------------------------------
# Call state machine
# ---------------------------------------------------------------------------

def transition_call(
    db: Session,
    call_id: str,
    to_state: str,
    reason: str = "",
    worker_id: str = "",
    expected_version: Optional[int] = None,
) -> DialerCall:
    """
    Atomically transition a DialerCall.

    Terminal states (COMPLETED, FAILED, CANCELLED) are idempotent – calling
    transition_call on an already-terminal call with the same target state
    returns the call without re-logging (prevents double-processing of duplicate
    provider events).
    """
    call = db.query(DialerCall).filter(DialerCall.call_id == call_id).first()
    if not call:
        raise LookupError(f"DialerCall not found: {call_id}")

    from_state = call.state

    # Idempotency: same terminal state → no-op
    if from_state == to_state and from_state in CallState.TERMINAL:
        return call

    _validate_call_transition(from_state, to_state, call_id)

    if expected_version is not None and call.version != expected_version:
        raise RuntimeError(
            f"OCC conflict: call {call_id} version mismatch"
        )

    now = datetime.utcnow()
    update_vals: dict = {
        "state": to_state,
        "version": DialerCall.version + 1,
        "updated_at": now,
    }
    if to_state == CallState.INITIATED:
        update_vals["initiated_at"] = now
    elif to_state == CallState.ANSWERED:
        update_vals["answered_at"] = now
    elif to_state == CallState.CONNECTED:
        update_vals["connected_at"] = now
    elif to_state in (CallState.COMPLETED, CallState.FAILED, CallState.CANCELLED):
        update_vals["completed_at"] = now
        if call.answered_at:
            update_vals["duration_sec"] = (now - call.answered_at).total_seconds()
    if to_state in (CallState.FAILED, CallState.CANCELLED):
        update_vals["failure_reason"] = reason[:255] if reason else None

    result = db.execute(
        update(DialerCall)
        .where(
            DialerCall.call_id == call_id,
            DialerCall.state == from_state,
            DialerCall.version == call.version,
        )
        .values(**update_vals)
    )
    if result.rowcount == 0:
        raise RuntimeError(
            f"OCC conflict: call {call_id} was modified by another worker"
        )

    db.add(DialerStateLog(
        entity_type="call",
        entity_id=call_id,
        from_state=from_state,
        to_state=to_state,
        reason=reason[:255] if reason else None,
        worker_id=worker_id[:64] if worker_id else None,
        occurred_at=now,
    ))
    db.flush()
    db.refresh(call)
    return call


def _validate_call_transition(from_state: str, to_state: str, call_id: str) -> None:
    if from_state in CallState.TERMINAL:
        raise InvalidTransition(
            f"Call {call_id}: already in terminal state '{from_state}', "
            f"cannot transition to '{to_state}'"
        )
    allowed = CallState.TRANSITIONS.get(from_state, set())
    if to_state not in allowed:
        raise InvalidTransition(
            f"Call {call_id}: {from_state} → {to_state} is not permitted. "
            f"Allowed: {allowed}"
        )
