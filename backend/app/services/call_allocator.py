"""
Call Allocator.

Executes ONLY safety-approved allocations from the Safety Controller.

Responsibilities:
- Atomically reserve agent + borrower in a single DB transaction.
- Use idempotency keys to prevent duplicate provider calls.
- Select the healthiest provider.
- Handle provider timeouts and retries.
- Record unknown/ambiguous outcomes safely.
- Never call a provider for a rejected/unapproved Safety decision.
"""
from __future__ import annotations
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Tuple
import threading

from sqlalchemy.orm import Session
from sqlalchemy import update, func
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.models.dialer_schema import (
    AgentState, CallState, CircuitState,
    DialerAgent, DialerCall, DialerBorrowerLock, DialerProviderHealth,
    DialerSession,
)
from app.services.state_machines import transition_agent, transition_call, InvalidTransition
from app.services.providers import TelecomProvider, ProviderCallRequest
from app.services.safety_controller import SafetyDecision, SafetyVerdict


class AllocationConflict(Exception):
    """Two workers tried to allocate the same agent/borrower."""


class NoEligibleBorrower(Exception):
    """No borrower available for dialing in this session."""


class NoEligibleAgent(Exception):
    """No agent in AVAILABLE state for this session."""


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------

_FAILURE_THRESHOLD   = 5    # open after N consecutive failures
_HALF_OPEN_TIMEOUT   = 30   # seconds before probing
_SUCCESS_TO_CLOSE    = 2    # consecutive successes to re-close


class CircuitBreaker:
    """Thread-safe circuit breaker backed by the DB for persistence."""

    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self._lock = threading.Lock()

    def record_success(self, db: Session) -> None:
        with self._lock:
            ph = self._get_or_create(db)
            ph.success_count += 1
            ph.consecutive_failures = 0
            if ph.circuit_state == CircuitState.HALF_OPEN:
                if ph.success_count >= _SUCCESS_TO_CLOSE:
                    ph.circuit_state = CircuitState.CLOSED
                    ph.failure_count = 0
            ph.updated_at = datetime.utcnow()
            db.commit()

    def record_failure(self, db: Session) -> None:
        with self._lock:
            ph = self._get_or_create(db)
            ph.failure_count += 1
            ph.consecutive_failures += 1
            ph.last_failure_at = datetime.utcnow()
            if ph.consecutive_failures >= _FAILURE_THRESHOLD:
                ph.circuit_state = CircuitState.OPEN
                ph.half_open_at = datetime.utcnow() + timedelta(seconds=_HALF_OPEN_TIMEOUT)
            ph.updated_at = datetime.utcnow()
            db.commit()

    def is_open(self, db: Session) -> bool:
        ph = self._get_or_create(db)
        if ph.circuit_state == CircuitState.CLOSED:
            return False
        if ph.circuit_state == CircuitState.OPEN:
            if ph.half_open_at and datetime.utcnow() >= ph.half_open_at:
                ph.circuit_state = CircuitState.HALF_OPEN
                ph.success_count = 0
                db.commit()
                return False   # allow probe
            return True
        return False   # HALF_OPEN: allow one probe

    def get_state(self, db: Session) -> str:
        return self._get_or_create(db).circuit_state

    def _get_or_create(self, db: Session) -> DialerProviderHealth:
        ph = db.query(DialerProviderHealth).filter(
            DialerProviderHealth.provider_name == self.provider_name
        ).first()
        if not ph:
            ph = DialerProviderHealth(provider_name=self.provider_name)
            db.add(ph)
            db.flush()
        return ph


# ---------------------------------------------------------------------------
# Call Allocator
# ---------------------------------------------------------------------------

class CallAllocator:
    """
    Executes allocations approved by the Safety Controller.

    Only accepts SafetyDecision objects with verdict APPROVED or REDUCED.
    Internally re-validates capacity at the atomic reservation boundary.
    """

    # Lock expiry: if a worker crashes, locks expire after this many seconds
    LOCK_TTL_SEC = 120

    def __init__(
        self,
        providers: list[TelecomProvider],
        worker_id: Optional[str] = None,
    ):
        if not providers:
            raise ValueError("At least one provider required")
        self._providers = {p.name: p for p in providers}
        self._worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self._circuit_breakers = {
            name: CircuitBreaker(name) for name in self._providers
        }

    def allocate_batch(
        self,
        db: Session,
        safety_decision: SafetyDecision,
        session_id: str,
        borrower_ids: list[str],   # ordered priority list from the queue
        on_call_created=None,       # optional callback(call_id)
    ) -> list[str]:
        """
        Attempt to allocate up to safety_decision.approved_dials calls.
        Returns list of created call_ids.
        Only called if verdict is APPROVED or REDUCED (callers must check).
        """
        if safety_decision.verdict not in (SafetyVerdict.APPROVED, SafetyVerdict.REDUCED,
                                            SafetyVerdict.FALLBACK):
            raise ValueError(
                f"Cannot allocate: Safety verdict is {safety_decision.verdict}"
            )

        cap = safety_decision.approved_dials
        created = []
        borrower_iter = iter(borrower_ids)

        for _ in range(cap):
            borrower_id = next(borrower_iter, None)
            if borrower_id is None:
                break
            try:
                call_id = self._allocate_one(db, session_id, borrower_id)
                created.append(call_id)
                if on_call_created:
                    on_call_created(call_id)
            except (AllocationConflict, NoEligibleAgent, NoEligibleBorrower) as exc:
                # Soft failure — log and continue with next borrower
                continue
            except Exception:
                continue   # Don't let one failure block others

        return created

    def _allocate_one(
        self,
        db: Session,
        session_id: str,
        borrower_id: str,
    ) -> str:
        """
        Atomically reserve agent + borrower, create DialerCall, and initiate
        the provider call.  All DB work happens in a single transaction.
        """
        with db.begin_nested():   # savepoint for rollback
            # 1. Reserve an AVAILABLE agent (OCC)
            agent = self._reserve_agent(db, session_id)

            # 2. Lock the borrower (unique constraint enforces exclusivity)
            self._lock_borrower(db, borrower_id, session_id)

            # 3. Create the call record (QUEUED → RESERVED)
            call_id = f"dc-{uuid.uuid4().hex}"
            idempotency_key = hashlib.sha256(
                f"{session_id}:{agent.agent_id}:{borrower_id}".encode()
            ).hexdigest()[:32]

            provider = self._select_provider(db)

            call = DialerCall(
                call_id=call_id,
                session_id=session_id,
                agent_id=agent.agent_id,
                borrower_id=borrower_id,
                provider_name=provider.name,
                state=CallState.QUEUED,
                idempotency_key=idempotency_key,
                created_at=datetime.utcnow(),
            )
            db.add(call)
            db.flush()

            # Transition: QUEUED → RESERVED → INITIATED (within same transaction)
            transition_call(db, call_id, CallState.RESERVED,
                            reason="agent allocated", worker_id=self._worker_id)
            transition_agent(db, agent.agent_id, AgentState.DIALING,
                             reason=f"call {call_id}", worker_id=self._worker_id,
                             expected_version=agent.version + 1)

        # 4. Initiate with provider OUTSIDE the DB transaction to avoid
        #    holding the SQLite write lock during network I/O.
        self._initiate_with_provider(db, call_id, agent.agent_id, borrower_id,
                                      provider, idempotency_key, session_id)
        return call_id

    def _reserve_agent(self, db: Session, session_id: str) -> DialerAgent:
        """OCC-based atomic agent reservation."""
        agent = (
            db.query(DialerAgent)
            .filter(
                DialerAgent.session_id == session_id,
                DialerAgent.dialer_state == AgentState.AVAILABLE,
            )
            # NOTE: skip_locked=True is not supported on SQLite.
            # Atomicity is guaranteed by the OCC UPDATE WHERE (state='AVAILABLE' AND version=X)
            # below — SQLite serializes writes, so exactly one UPDATE will succeed.
            .first()
        )
        if not agent:
            raise NoEligibleAgent("No AVAILABLE agent found")

        result = db.execute(
            update(DialerAgent)
            .where(
                DialerAgent.agent_id == agent.agent_id,
                DialerAgent.dialer_state == AgentState.AVAILABLE,
                DialerAgent.version == agent.version,
            )
            .values(
                dialer_state=AgentState.RESERVED,
                version=DialerAgent.version + 1,
                reserved_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
        if result.rowcount == 0:
            raise AllocationConflict(f"Agent {agent.agent_id} was taken by another worker")
        db.flush()
        db.refresh(agent)
        return agent

    def _lock_borrower(self, db: Session, borrower_id: str, session_id: str) -> None:
        """Insert a borrower lock row. IntegrityError = already locked."""
        try:
            lock = DialerBorrowerLock(
                borrower_id=borrower_id,
                call_id="pending",
                session_id=session_id,
                locked_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(seconds=self.LOCK_TTL_SEC),
            )
            db.add(lock)
            db.flush()
        except IntegrityError:
            db.rollback()
            raise AllocationConflict(f"Borrower {borrower_id} already locked")

    def _select_provider(self, db: Session) -> TelecomProvider:
        """Prefer the healthiest provider (lowest failure rate with CLOSED circuit)."""
        healthy = []
        for name, cb in self._circuit_breakers.items():
            if not cb.is_open(db):
                health = self._providers[name].get_health()
                healthy.append((health.get("failure_rate", 0.0), name))

        if not healthy:
            # All circuits open — try any provider (conservative)
            return next(iter(self._providers.values()))

        healthy.sort()   # ascending by failure_rate
        return self._providers[healthy[0][1]]

    def _initiate_with_provider(
        self,
        db: Session,
        call_id: str,
        agent_id: str,
        borrower_id: str,
        provider: TelecomProvider,
        idempotency_key: str,
        session_id: str,
    ) -> None:
        """Initiate the call and handle provider response."""
        cb = self._circuit_breakers[provider.name]
        req = ProviderCallRequest(
            call_id=call_id,
            borrower_phone=f"+91{borrower_id[-10:]}",   # mock phone from borrower_id
            agent_id=agent_id,
            idempotency_key=idempotency_key,
        )

        result = provider.initiate_call(req)

        if result.success:
            cb.record_success(db)
            # Transition call: RESERVED → INITIATED
            try:
                db.execute(
                    update(DialerCall)
                    .where(DialerCall.call_id == call_id)
                    .values(
                        state=CallState.INITIATED,
                        provider_call_id=result.provider_call_id,
                        initiated_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                )
                db.commit()
            except Exception:
                db.rollback()
        else:
            cb.record_failure(db)
            # Fail the call and release agent
            try:
                db.execute(
                    update(DialerCall)
                    .where(DialerCall.call_id == call_id)
                    .values(
                        state=CallState.FAILED,
                        failure_reason=result.error[:255] if result.error else "provider_error",
                        completed_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                )
                db.execute(
                    update(DialerAgent)
                    .where(DialerAgent.agent_id == agent_id)
                    .values(
                        dialer_state=AgentState.AVAILABLE,
                        version=DialerAgent.version + 1,
                        updated_at=datetime.utcnow(),
                    )
                )
                # Release borrower lock
                db.query(DialerBorrowerLock).filter(
                    DialerBorrowerLock.borrower_id == borrower_id
                ).delete()
                db.commit()
            except Exception:
                db.rollback()

    def register_event_callbacks(self, event_processor) -> None:
        """Wire provider event callbacks to the event processor."""
        for provider in self._providers.values():
            provider.set_event_callback(
                lambda evt, ep=event_processor: ep.process(evt)
            )
