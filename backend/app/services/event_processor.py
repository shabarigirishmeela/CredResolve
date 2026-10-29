"""
Event Processor — idempotent provider event handling + crash recovery.

Responsibilities:
1. Deduplicate provider events using DialerEvent unique constraint.
2. Enforce call state machine on every event.
3. Release agent and borrower lock when call terminates.
4. Update answer rate and talk time in the pacing engine.
5. Crash recovery: on startup, scan stale RESERVED/INITIATED calls and recover.
"""
from __future__ import annotations
import json
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING

from sqlalchemy.orm import Session
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.models.dialer_schema import (
    AgentState, CallState,
    DialerAgent, DialerCall, DialerBorrowerLock, DialerEvent,
)
from app.services.state_machines import transition_call, transition_agent, InvalidTransition
from app.services.providers import ProviderEvent

if TYPE_CHECKING:
    from app.services.call_allocator import CallAllocator

logger = logging.getLogger(__name__)

# Map provider event_type → call state
_EVENT_TO_CALL_STATE = {
    "RINGING":   CallState.RINGING,
    "ANSWERED":  CallState.ANSWERED,
    "CONNECTED": CallState.CONNECTED,
    "COMPLETED": CallState.COMPLETED,
    "FAILED":    CallState.FAILED,
    "CANCELLED": CallState.CANCELLED,
}

# How long a reservation can sit without progressing before we consider it stale
_STALE_RESERVATION_SEC = 120


class EventProcessor:
    """
    Ingests ProviderEvent objects, deduplicates them, and drives the call
    state machine. Thread-safe: multiple provider callbacks may call process()
    concurrently.
    """

    def __init__(self, pacing_engine=None):
        self._pacing = pacing_engine
        self._lock = threading.Lock()   # coarse lock; fine-grained per call_id for production

    def process(self, evt: ProviderEvent) -> bool:
        """
        Process one provider event. Returns True if the event caused a state
        transition, False if it was a duplicate/invalid (idempotent no-op).
        """
        db = SessionLocal()
        try:
            return self._process_with_db(db, evt)
        except Exception as exc:
            logger.error("EventProcessor error for call %s: %s", evt.call_id, exc)
            db.rollback()
            return False
        finally:
            db.close()

    def _process_with_db(self, db: Session, evt: ProviderEvent) -> bool:
        target_state = _EVENT_TO_CALL_STATE.get(evt.event_type)
        if not target_state:
            logger.warning("Unknown event_type: %s", evt.event_type)
            return False

        # --- Idempotency: try to insert event record ---
        dialer_event = DialerEvent(
            call_id=evt.call_id,
            provider_name=evt.extra.get("provider") or "",
            event_type=evt.event_type,
            event_seq=evt.event_seq,
            raw_payload=json.dumps(evt.extra)[:2000],
            received_at=datetime.utcnow(),
        )
        try:
            db.add(dialer_event)
            db.flush()
        except IntegrityError:
            db.rollback()
            logger.debug(
                "Duplicate event ignored: call=%s type=%s seq=%s",
                evt.call_id, evt.event_type, evt.event_seq,
            )
            # Mark as duplicate in a new attempt
            return False

        # --- Drive state machine ---
        call = db.query(DialerCall).filter(DialerCall.call_id == evt.call_id).first()
        if not call:
            dialer_event.processed = True
            dialer_event.accepted = False
            dialer_event.reject_reason = "call not found"
            db.commit()
            return False

        try:
            transition_call(db, evt.call_id, target_state,
                            reason=f"provider event: {evt.event_type}")
            dialer_event.processed = True
            dialer_event.accepted = True
            db.commit()
        except InvalidTransition as exc:
            # Out-of-order or duplicate — don't break state
            dialer_event.processed = True
            dialer_event.accepted = False
            dialer_event.reject_reason = str(exc)[:255]
            db.commit()
            logger.debug("Invalid transition ignored: %s", exc)
            return False

        # --- Post-transition side effects ---
        db.refresh(call)
        self._handle_side_effects(db, call, evt, target_state)
        return True

    def _handle_side_effects(
        self,
        db: Session,
        call: DialerCall,
        evt: ProviderEvent,
        new_state: str,
    ) -> None:
        if new_state == CallState.ANSWERED:
            # Move agent from DIALING → CONNECTED
            self._safe_agent_transition(db, call.agent_id, AgentState.CONNECTED,
                                        reason=f"call {call.call_id} answered")
            # Update pacing engine
            if self._pacing:
                self._pacing.record_outcome(answered=True)

        elif new_state in (CallState.COMPLETED, CallState.FAILED, CallState.CANCELLED):
            # Calculate duration if answered
            answered = new_state == CallState.COMPLETED and call.answered_at
            if self._pacing:
                if answered and call.duration_sec:
                    self._pacing.record_outcome(
                        answered=True,
                        talk_time_sec=call.duration_sec,
                    )
                elif new_state == CallState.FAILED:
                    self._pacing.record_outcome(answered=False)

            # Release agent → WRAP_UP (if was connected) or AVAILABLE (if never answered)
            agent = db.query(DialerAgent).filter(
                DialerAgent.agent_id == call.agent_id
            ).first()
            if agent:
                if agent.dialer_state in (AgentState.CONNECTED, AgentState.DIALING):
                    target = AgentState.WRAP_UP if new_state == CallState.COMPLETED else AgentState.AVAILABLE
                    self._safe_agent_transition(db, call.agent_id, target,
                                                reason=f"call {call.call_id} {new_state}")

            # Release borrower lock
            db.query(DialerBorrowerLock).filter(
                DialerBorrowerLock.borrower_id == call.borrower_id
            ).delete()
            db.commit()

    def _safe_agent_transition(
        self,
        db: Session,
        agent_id: str,
        to_state: str,
        reason: str = "",
    ) -> None:
        try:
            transition_agent(db, agent_id, to_state, reason=reason)
            db.commit()
        except (InvalidTransition, RuntimeError, LookupError) as exc:
            db.rollback()
            logger.debug("Agent transition skipped: %s", exc)


# ---------------------------------------------------------------------------
# Crash recovery
# ---------------------------------------------------------------------------

def recover_stale_state(db: Session, session_id: Optional[str] = None) -> dict:
    """
    Called on application startup. Finds calls stuck in non-terminal states
    due to a previous worker crash and reconciles them.

    Strategy (conservative):
    - RESERVED / INITIATED / RINGING with no update in STALE_RESERVATION_SEC
      → mark FAILED, release agent to AVAILABLE, release borrower lock
    - ANSWERED / CONNECTED → mark COMPLETED (assume call completed while we were down)
    """
    cutoff = datetime.utcnow() - timedelta(seconds=_STALE_RESERVATION_SEC)
    q = db.query(DialerCall).filter(
        DialerCall.state.notin_(list(CallState.TERMINAL)),
        DialerCall.updated_at < cutoff,
    )
    if session_id:
        q = q.filter(DialerCall.session_id == session_id)

    stale_calls = q.all()
    recovered = {"failed": 0, "completed": 0, "agents_released": 0}

    for call in stale_calls:
        try:
            if call.state in (CallState.RESERVED, CallState.INITIATED, CallState.RINGING):
                db.execute(
                    update(DialerCall)
                    .where(DialerCall.call_id == call.call_id)
                    .values(
                        state=CallState.FAILED,
                        failure_reason="crash_recovery: stale reservation",
                        completed_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                )
                recovered["failed"] += 1
                # Release agent
                db.execute(
                    update(DialerAgent)
                    .where(DialerAgent.agent_id == call.agent_id)
                    .values(
                        dialer_state=AgentState.AVAILABLE,
                        version=DialerAgent.version + 1,
                        updated_at=datetime.utcnow(),
                    )
                )
                recovered["agents_released"] += 1

            elif call.state in (CallState.ANSWERED, CallState.CONNECTED):
                db.execute(
                    update(DialerCall)
                    .where(DialerCall.call_id == call.call_id)
                    .values(
                        state=CallState.COMPLETED,
                        completed_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                )
                recovered["completed"] += 1
                db.execute(
                    update(DialerAgent)
                    .where(DialerAgent.agent_id == call.agent_id)
                    .values(
                        dialer_state=AgentState.WRAP_UP,
                        version=DialerAgent.version + 1,
                        updated_at=datetime.utcnow(),
                    )
                )
                recovered["agents_released"] += 1

            # Release borrower lock
            db.query(DialerBorrowerLock).filter(
                DialerBorrowerLock.borrower_id == call.borrower_id
            ).delete()

        except Exception as exc:
            logger.error("Recovery failed for call %s: %s", call.call_id, exc)

    # Also expire stale borrower locks (orphaned without matching stale call)
    db.query(DialerBorrowerLock).filter(
        DialerBorrowerLock.expires_at < datetime.utcnow()
    ).delete()

    db.commit()
    logger.info("Crash recovery complete: %s", recovered)
    return recovered
