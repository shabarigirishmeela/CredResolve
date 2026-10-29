"""
SmartDialer ORM models.

Separate from the collections-platform schema to avoid polluting existing tables.
Uses the same SQLAlchemy engine declared in app.core.database.
"""
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Boolean,
    Text, Index, UniqueConstraint, ForeignKey
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


# ---------------------------------------------------------------------------
# Enumerations (plain strings – avoids SQLite enum dialect issues)
# ---------------------------------------------------------------------------

class AgentState:
    OFFLINE    = "OFFLINE"
    AVAILABLE  = "AVAILABLE"
    RESERVED   = "RESERVED"
    DIALING    = "DIALING"
    CONNECTED  = "CONNECTED"
    WRAP_UP    = "WRAP_UP"
    PAUSED     = "PAUSED"

    ALL = {OFFLINE, AVAILABLE, RESERVED, DIALING, CONNECTED, WRAP_UP, PAUSED}

    # Valid forward transitions
    TRANSITIONS: dict[str, set[str]] = {
        OFFLINE:   {AVAILABLE},
        AVAILABLE: {RESERVED, OFFLINE, PAUSED},
        RESERVED:  {DIALING, AVAILABLE, OFFLINE},   # AVAILABLE = reservation released
        DIALING:   {CONNECTED, AVAILABLE, OFFLINE},  # AVAILABLE = call not answered
        CONNECTED: {WRAP_UP, OFFLINE},
        WRAP_UP:   {AVAILABLE, OFFLINE, PAUSED},
        PAUSED:    {AVAILABLE, OFFLINE},
    }


class CallState:
    QUEUED     = "QUEUED"
    RESERVED   = "RESERVED"
    INITIATED  = "INITIATED"
    RINGING    = "RINGING"
    ANSWERED   = "ANSWERED"
    CONNECTED  = "CONNECTED"
    COMPLETED  = "COMPLETED"
    FAILED     = "FAILED"
    CANCELLED  = "CANCELLED"

    ALL = {QUEUED, RESERVED, INITIATED, RINGING, ANSWERED, CONNECTED,
           COMPLETED, FAILED, CANCELLED}

    TERMINAL = {COMPLETED, FAILED, CANCELLED}

    TRANSITIONS: dict[str, set[str]] = {
        QUEUED:    {RESERVED, CANCELLED},
        RESERVED:  {INITIATED, CANCELLED},
        INITIATED: {RINGING, FAILED, CANCELLED},
        RINGING:   {ANSWERED, FAILED, CANCELLED},
        ANSWERED:  {CONNECTED, FAILED},
        CONNECTED: {COMPLETED, FAILED},
        COMPLETED: set(),
        FAILED:    set(),
        CANCELLED: set(),
    }


class CircuitState:
    CLOSED     = "CLOSED"      # normal
    OPEN       = "OPEN"        # failing – reject all
    HALF_OPEN  = "HALF_OPEN"   # probe one call


class SessionState:
    IDLE     = "IDLE"
    RUNNING  = "RUNNING"
    PAUSED   = "PAUSED"
    STOPPED  = "STOPPED"


class DialingMode:
    PROGRESSIVE = "PROGRESSIVE"
    PREDICTIVE  = "PREDICTIVE"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class DialerSession(Base):
    """A campaign dialing run (maps 1:1 to a campaign in the existing platform)."""
    __tablename__ = "dialer_sessions"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    session_id    = Column(String(64), unique=True, nullable=False, index=True)
    campaign_id   = Column(String(64), nullable=True, index=True)   # link to existing campaigns table
    mode          = Column(String(20), nullable=False, default=DialingMode.PROGRESSIVE)
    state         = Column(String(20), nullable=False, default=SessionState.IDLE, index=True)
    max_dial_rate = Column(Float, default=1.0)   # calls per available agent
    started_at    = Column(DateTime, nullable=True)
    stopped_at    = Column(DateTime, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    # Snapshot stats
    total_initiated  = Column(Integer, default=0)
    total_answered   = Column(Integer, default=0)
    total_completed  = Column(Integer, default=0)
    total_failed     = Column(Integer, default=0)
    total_abandoned  = Column(Integer, default=0)


class DialerAgent(Base):
    """
    SmartDialer view of an agent.  Separate from the collections `agents` table
    so existing functionality is not disturbed.  References `agents.agent_id`
    for metadata lookups but owns its own lifecycle state.

    An agent can exist in multiple sessions with different states per session.
    The uniqueness constraint is per-session (agent_id + session_id).
    """
    __tablename__ = "dialer_agents"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    agent_id      = Column(String(64), nullable=False, index=True)
    agent_name    = Column(String(150), nullable=True)
    dialer_state  = Column(String(20), nullable=False, default=AgentState.OFFLINE, index=True)
    version       = Column(Integer, nullable=False, default=0)   # OCC version
    session_id    = Column(String(64), nullable=False, index=True)
    reserved_at   = Column(DateTime, nullable=True)
    connected_at  = Column(DateTime, nullable=True)
    wrap_start_at = Column(DateTime, nullable=True)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        # Unique per session: same agent_id can exist in different sessions
        UniqueConstraint("agent_id", "session_id", name="uq_dialer_agent_session"),
        Index("ix_dialer_agents_state_session", "dialer_state", "session_id"),
    )


class DialerCall(Base):
    """Lifecycle of a single dialer call attempt."""
    __tablename__ = "dialer_calls"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    call_id          = Column(String(64), unique=True, nullable=False, index=True)
    session_id       = Column(String(64), nullable=False, index=True)
    agent_id         = Column(String(64), nullable=False, index=True)
    borrower_id      = Column(String(64), nullable=False, index=True)
    account_id       = Column(String(64), nullable=True, index=True)
    provider_name    = Column(String(50), nullable=True)
    provider_call_id = Column(String(100), nullable=True, index=True)  # external reference
    state            = Column(String(20), nullable=False, default=CallState.QUEUED, index=True)
    version          = Column(Integer, nullable=False, default=0)   # OCC version for state
    idempotency_key  = Column(String(100), unique=True, nullable=True)  # prevents duplicate provider calls
    initiated_at     = Column(DateTime, nullable=True)
    answered_at      = Column(DateTime, nullable=True)
    connected_at     = Column(DateTime, nullable=True)
    completed_at     = Column(DateTime, nullable=True)
    duration_sec     = Column(Float, nullable=True)
    failure_reason   = Column(String(255), nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_dialer_calls_state_session", "state", "session_id"),
        # Prevent same borrower being dialed twice simultaneously in same session
        Index("ix_dialer_calls_borrower_session", "borrower_id", "session_id"),
    )


class DialerBorrowerLock(Base):
    """
    Prevents the same borrower being allocated to two concurrent calls.
    Row exists while a call is in-progress; deleted when call reaches a terminal state.
    Uniqueness constraint enforces exclusivity.
    """
    __tablename__ = "dialer_borrower_locks"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    borrower_id  = Column(String(64), unique=True, nullable=False, index=True)
    call_id      = Column(String(64), nullable=False)
    session_id   = Column(String(64), nullable=False)
    locked_at    = Column(DateTime, default=datetime.utcnow)
    expires_at   = Column(DateTime, nullable=True)   # for crash recovery TTL


class DialerEvent(Base):
    """
    Idempotent log of provider webhook events.
    Unique constraint on (call_id, event_type, event_seq) prevents re-processing.
    """
    __tablename__ = "dialer_events"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    call_id       = Column(String(64), nullable=False, index=True)
    provider_name = Column(String(50), nullable=True)
    event_type    = Column(String(50), nullable=False)   # e.g., RINGING, ANSWERED, COMPLETED
    event_seq     = Column(Integer, nullable=True)       # provider sequence number if available
    raw_payload   = Column(Text, nullable=True)
    processed     = Column(Boolean, default=False)
    accepted      = Column(Boolean, default=False)       # False if duplicate/invalid transition
    reject_reason = Column(String(255), nullable=True)
    received_at   = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        # Prevent processing same event twice (idempotency)
        UniqueConstraint("call_id", "event_type", "event_seq", name="uq_dialer_event_dedup"),
        Index("ix_dialer_events_call_processed", "call_id", "processed"),
    )


class DialerProviderHealth(Base):
    """Circuit-breaker state per provider."""
    __tablename__ = "dialer_provider_health"

    id                   = Column(Integer, primary_key=True, autoincrement=True)
    provider_name        = Column(String(50), unique=True, nullable=False, index=True)
    circuit_state        = Column(String(20), nullable=False, default=CircuitState.CLOSED)
    failure_count        = Column(Integer, default=0)
    success_count        = Column(Integer, default=0)
    consecutive_failures = Column(Integer, default=0)
    last_failure_at      = Column(DateTime, nullable=True)
    half_open_at         = Column(DateTime, nullable=True)  # when to attempt probe
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DialerStateLog(Base):
    """Audit log of every state transition for both agents and calls."""
    __tablename__ = "dialer_state_logs"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String(20), nullable=False)   # "agent" | "call"
    entity_id   = Column(String(64), nullable=False, index=True)
    from_state  = Column(String(20), nullable=True)
    to_state    = Column(String(20), nullable=False)
    reason      = Column(String(255), nullable=True)
    worker_id   = Column(String(64), nullable=True)
    occurred_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_dialer_state_log_entity", "entity_type", "entity_id"),
    )
