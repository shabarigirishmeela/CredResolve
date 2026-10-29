"""
SmartDialer REST API router.

Endpoints:
  Sessions (campaigns):  POST/GET/PATCH /dialer/sessions
  Agents:                POST/GET        /dialer/sessions/{id}/agents
  Calls:                 GET             /dialer/sessions/{id}/calls
  Control:               POST            /dialer/sessions/{id}/start|stop
  Pacing:                GET             /dialer/sessions/{id}/pacing
  Provider events:        POST            /dialer/events (webhook)
  Provider health:        GET             /dialer/providers/health
  Metrics:               GET             /dialer/sessions/{id}/metrics
  Simulation:            POST/GET        /dialer/simulate
"""
from __future__ import annotations
import uuid
import threading
import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func, update, text
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.core.security import get_current_user_payload
from app.models.dialer_schema import (
    AgentState, CallState, SessionState, DialingMode, CircuitState,
    DialerSession, DialerAgent, DialerCall, DialerEvent,
    DialerProviderHealth, DialerStateLog,
)
from app.services.pacing_engine import PacingEngine, PacingInput
from app.services.safety_controller import SafetyController
from app.services.event_processor import EventProcessor, recover_stale_state
from app.services.providers import ProviderAlpha, ProviderBeta, ProviderEvent


def _migrate_agent_table(db: Session):
    """
    Ensure dialer_agents table has the composite unique constraint (agent_id, session_id).
    This is a one-time migration for existing databases that may have had a single-column
    unique constraint on agent_id.
    """
    try:
        # Check if the table exists
        db.execute(text("SELECT agent_id, session_id FROM dialer_agents LIMIT 1"))
        
        # Check if the composite unique index already exists
        result = db.execute(text("SELECT name FROM sqlite_master WHERE type='index' AND name='uq_dialer_agent_session'"))
        if result.fetchone() is None:
            # Composite unique index doesn't exist
            logger.info("Checking dialer_agents schema for migration")
            
            # Get the current table schema
            schema_result = db.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name='dialer_agents'"))
            schema_row = schema_result.fetchone()
            
            if schema_row and schema_row[0]:
                schema_sql = schema_row[0]
                # Check if there's a column-level unique constraint on agent_id
                # This would look like: agent_id VARCHAR(64) NOT NULL UNIQUE
                if "agent_id" in schema_sql and "UNIQUE" in schema_sql and "uq_dialer_agent_session" not in schema_sql:
                    # Old schema detected - need to recreate table
                    logger.info("Old schema detected, recreating dialer_agents table")
                    
                    # Create new table with correct schema
                    db.execute(text("""
                        CREATE TABLE dialer_agents_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            agent_id VARCHAR(64) NOT NULL,
                            agent_name VARCHAR(150),
                            dialer_state VARCHAR(20) NOT NULL,
                            version INTEGER NOT NULL,
                            session_id VARCHAR(64) NOT NULL,
                            reserved_at DATETIME,
                            connected_at DATETIME,
                            wrap_start_at DATETIME,
                            updated_at DATETIME
                        )
                    """))
                    
                    # Copy data
                    db.execute(text("""
                        INSERT INTO dialer_agents_new
                        SELECT id, agent_id, agent_name, dialer_state, version, session_id,
                               reserved_at, connected_at, wrap_start_at, updated_at
                        FROM dialer_agents
                    """))
                    
                    # Drop old table and rename new one
                    db.execute(text("DROP TABLE dialer_agents"))
                    db.execute(text("ALTER TABLE dialer_agents_new RENAME TO dialer_agents"))
                    
                    # Create indexes
                    db.execute(text("CREATE INDEX ix_dialer_agents_agent_id ON dialer_agents(agent_id)"))
                    db.execute(text("CREATE INDEX ix_dialer_agents_session_id ON dialer_agents(session_id)"))
                    db.execute(text("CREATE INDEX ix_dialer_agents_state_session ON dialer_agents(dialer_state, session_id)"))
                    db.execute(text("CREATE UNIQUE INDEX uq_dialer_agent_session ON dialer_agents(agent_id, session_id)"))
                    
                    db.commit()
                    logger.info("Table migration completed successfully")
                else:
                    # No column-level unique constraint, just add the composite index
                    logger.info("Adding composite unique index")
                    db.execute(text("""
                        CREATE UNIQUE INDEX uq_dialer_agent_session ON dialer_agents(agent_id, session_id)
                    """))
                    db.commit()
                    logger.info("Composite unique index added successfully")
            else:
                # No schema found, just try to add the index
                logger.info("Adding composite unique index (no schema check)")
                db.execute(text("""
                    CREATE UNIQUE INDEX uq_dialer_agent_session ON dialer_agents(agent_id, session_id)
                """))
                db.commit()
                logger.info("Composite unique index added successfully")
        else:
            logger.debug("Composite unique index already exists")
    except Exception as exc:
        # Table doesn't exist or other error - will be created by Base.metadata.create_all
        logger.debug("Migration check skipped or failed: %s", exc)
        pass

router = APIRouter(prefix="/dialer", tags=["SmartDialer"])

# ---------------------------------------------------------------------------
# Shared singletons (process-scoped)
# ---------------------------------------------------------------------------
_pacing_engine   = PacingEngine()
_safety_ctrl     = SafetyController()
_event_processor = EventProcessor(pacing_engine=_pacing_engine)

_provider_alpha  = ProviderAlpha()
_provider_beta   = ProviderBeta()
_providers       = [_provider_alpha, _provider_beta]

# Wire callbacks
for _p in _providers:
    _p.set_event_callback(lambda evt: _event_processor.process(evt))

# Active dialer threads keyed by session_id
_dialer_threads: dict[str, object] = {}
_dialers_lock   = threading.Lock()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class CreateSessionRequest(BaseModel):
    campaign_id: Optional[str] = None
    mode: str = Field(default="PROGRESSIVE", pattern="^(PROGRESSIVE|PREDICTIVE)$")
    max_dial_rate: float = Field(default=1.0, ge=0.1, le=5.0)


class AddAgentsRequest(BaseModel):
    agent_ids: List[str]


class ProviderEventRequest(BaseModel):
    call_id: str
    provider_call_id: str
    event_type: str
    event_seq: int = 0
    extra: dict = {}


class SimulateRequest(BaseModel):
    scenario: str = Field(pattern="^[ABCD]$", description="A=20%, B=50%, C=70%, D=changing")
    num_agents: int = Field(default=10, ge=1, le=500)
    num_borrowers: int = Field(default=100, ge=10, le=5000)
    duration_ticks: int = Field(default=20, ge=1, le=200)
    mode: str = Field(default="PREDICTIVE", pattern="^(PROGRESSIVE|PREDICTIVE)$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_tables(db: Session) -> None:
    """Create SmartDialer tables if they don't exist (idempotent)."""
    from app.core.database import engine
    from app.models.dialer_schema import (
        DialerSession, DialerAgent, DialerCall, DialerBorrowerLock,
        DialerEvent, DialerProviderHealth, DialerStateLog,
    )
    from app.core.database import Base
    # Migrate existing tables if needed
    _migrate_agent_table(db)
    Base.metadata.create_all(bind=engine)


def _get_session_or_404(session_id: str, db: Session) -> DialerSession:
    s = db.query(DialerSession).filter(DialerSession.session_id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return s


def _build_pacing_input(db: Session, session_id: str, mode: str) -> PacingInput:
    agent_counts = dict(
        db.query(DialerAgent.dialer_state, func.count(DialerAgent.id))
        .filter(DialerAgent.session_id == session_id)
        .group_by(DialerAgent.dialer_state)
        .all()
    )
    call_counts = dict(
        db.query(DialerCall.state, func.count(DialerCall.id))
        .filter(
            DialerCall.session_id == session_id,
            DialerCall.state.notin_(list(CallState.TERMINAL)),
        )
        .group_by(DialerCall.state)
        .all()
    )
    provider_health = {p.name: p.get_health() for p in _providers}
    return PacingInput(
        available_agents=agent_counts.get(AgentState.AVAILABLE, 0),
        reserved_agents=agent_counts.get(AgentState.RESERVED, 0),
        dialing_agents=agent_counts.get(AgentState.DIALING, 0),
        connected_agents=agent_counts.get(AgentState.CONNECTED, 0),
        wrap_up_agents=agent_counts.get(AgentState.WRAP_UP, 0),
        calls_initiated=call_counts.get(CallState.INITIATED, 0) + call_counts.get(CallState.RINGING, 0),
        calls_connected=call_counts.get(CallState.ANSWERED, 0) + call_counts.get(CallState.CONNECTED, 0),
        provider_health=provider_health,
        avg_setup_latency_ms=_pacing_engine.rolling_avg_latency_ms,
        avg_talk_time_sec=_pacing_engine.rolling_avg_talk_sec,
        answer_rate=_pacing_engine.rolling_answer_rate,
        mode=mode,
    )


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

@router.post("/sessions", status_code=201)
def create_session(
    body: CreateSessionRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user_payload),
):
    _ensure_tables(db)
    session_id = f"ds-{uuid.uuid4().hex[:16]}"
    s = DialerSession(
        session_id=session_id,
        campaign_id=body.campaign_id,
        mode=body.mode,
        max_dial_rate=body.max_dial_rate,
        state=SessionState.IDLE,
        created_at=datetime.utcnow(),
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return {
        "session_id": s.session_id,
        "mode": s.mode,
        "state": s.state,
        "created_at": s.created_at,
    }


@router.get("/sessions")
def list_sessions(
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user_payload),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    _ensure_tables(db)
    total = db.query(DialerSession).count()
    items = (
        db.query(DialerSession)
        .order_by(DialerSession.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [
            {
                "session_id": s.session_id,
                "mode": s.mode,
                "state": s.state,
                "campaign_id": s.campaign_id,
                "total_initiated": s.total_initiated,
                "total_answered": s.total_answered,
                "total_completed": s.total_completed,
                "total_failed": s.total_failed,
                "started_at": s.started_at,
                "stopped_at": s.stopped_at,
            }
            for s in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/sessions/{session_id}")
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user_payload),
):
    _ensure_tables(db)
    s = _get_session_or_404(session_id, db)
    agent_counts = dict(
        db.query(DialerAgent.dialer_state, func.count(DialerAgent.id))
        .filter(DialerAgent.session_id == session_id)
        .group_by(DialerAgent.dialer_state)
        .all()
    )
    call_counts = dict(
        db.query(DialerCall.state, func.count(DialerCall.id))
        .filter(DialerCall.session_id == session_id)
        .group_by(DialerCall.state)
        .all()
    )
    return {
        "session_id": s.session_id,
        "mode": s.mode,
        "state": s.state,
        "campaign_id": s.campaign_id,
        "max_dial_rate": s.max_dial_rate,
        "started_at": s.started_at,
        "stopped_at": s.stopped_at,
        "total_initiated": s.total_initiated,
        "total_answered": s.total_answered,
        "total_completed": s.total_completed,
        "total_failed": s.total_failed,
        "agent_states": agent_counts,
        "call_states": call_counts,
        "is_running": session_id in _dialer_threads,
    }


# ---------------------------------------------------------------------------
# Session control
# ---------------------------------------------------------------------------

@router.post("/sessions/{session_id}/start")
def start_session(
    session_id: str,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user_payload),
):
    _ensure_tables(db)
    s = _get_session_or_404(session_id, db)
    if s.state == SessionState.RUNNING:
        raise HTTPException(400, "Session already running")

    # Run crash recovery first
    recover_stale_state(db, session_id)

    s.state = SessionState.RUNNING
    s.started_at = datetime.utcnow()
    db.commit()

    from app.services.progressive_dialer import ProgressiveDialer
    with _dialers_lock:
        if session_id not in _dialer_threads:
            dialer = ProgressiveDialer(session_id, _providers, _event_processor)
            dialer.start()
            _dialer_threads[session_id] = dialer

    return {"status": "started", "session_id": session_id}


@router.post("/sessions/{session_id}/stop")
def stop_session(
    session_id: str,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user_payload),
):
    _ensure_tables(db)
    s = _get_session_or_404(session_id, db)
    s.state = SessionState.STOPPED
    s.stopped_at = datetime.utcnow()
    db.commit()

    with _dialers_lock:
        dialer = _dialer_threads.pop(session_id, None)
        if dialer:
            dialer.stop()

    return {"status": "stopped", "session_id": session_id}


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

@router.post("/sessions/{session_id}/agents", status_code=201)
def add_agents(
    session_id: str,
    body: AddAgentsRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user_payload),
):
    logger.info("add_agents called for session %s with agent_ids: %s", session_id, body.agent_ids)
    try:
        _ensure_tables(db)
        logger.debug("Tables ensured")
        _get_session_or_404(session_id, db)
        logger.debug("Session validated")
        added = []
        skipped = []
        for aid in body.agent_ids:
            existing = db.query(DialerAgent).filter(
                DialerAgent.agent_id == aid,
                DialerAgent.session_id == session_id,
            ).first()
            if not existing:
                logger.debug("Adding new agent %s to session %s", aid, session_id)
                agent = DialerAgent(
                    agent_id=aid,
                    dialer_state=AgentState.AVAILABLE,
                    session_id=session_id,
                    version=0,
                )
                db.add(agent)
                added.append(aid)
            else:
                logger.debug("Agent %s already exists in session %s, skipping", aid, session_id)
                skipped.append(aid)
        logger.debug("Committing %d new agents, %d skipped", len(added), len(skipped))
        db.commit()
        logger.info("Successfully added %d agents to session %s", len(added), session_id)
        return {"added": len(added), "agent_ids": added, "skipped": len(skipped), "skipped_ids": skipped}
    except HTTPException:
        raise  # Re-raise FastAPI HTTP exceptions as-is
    except IntegrityError as exc:
        # Race condition: another thread added an agent between our check and commit
        # Rollback and retry with fresh check
        logger.exception("IntegrityError in add_agents for session %s, retrying", session_id)
        db.rollback()
        added = []
        skipped = []
        for aid in body.agent_ids:
            existing = db.query(DialerAgent).filter(
                DialerAgent.agent_id == aid,
                DialerAgent.session_id == session_id,
            ).first()
            if not existing:
                agent = DialerAgent(
                    agent_id=aid,
                    dialer_state=AgentState.AVAILABLE,
                    session_id=session_id,
                    version=0,
                )
                db.add(agent)
                added.append(aid)
            else:
                skipped.append(aid)
        db.commit()
        logger.info("Retry successful: added %d agents to session %s", len(added), session_id)
        return {"added": len(added), "agent_ids": added, "skipped": len(skipped), "skipped_ids": skipped}
    except Exception as exc:
        logger.exception("Unexpected error in add_agents for session %s", session_id)
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add agents: {exc}"
        )


@router.get("/sessions/{session_id}/agents")
def list_agents(
    session_id: str,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user_payload),
):
    _ensure_tables(db)
    agents = (
        db.query(DialerAgent)
        .filter(DialerAgent.session_id == session_id)
        .order_by(DialerAgent.agent_id)
        .all()
    )
    return {
        "agents": [
            {
                "agent_id": a.agent_id,
                "dialer_state": a.dialer_state,
                "version": a.version,
                "reserved_at": a.reserved_at,
                "connected_at": a.connected_at,
            }
            for a in agents
        ]
    }


# ---------------------------------------------------------------------------
# Calls
# ---------------------------------------------------------------------------

@router.get("/sessions/{session_id}/calls")
def list_calls(
    session_id: str,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user_payload),
    state: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    _ensure_tables(db)
    q = db.query(DialerCall).filter(DialerCall.session_id == session_id)
    if state:
        q = q.filter(DialerCall.state == state)
    total = q.count()
    items = q.order_by(DialerCall.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [
            {
                "call_id": c.call_id,
                "agent_id": c.agent_id,
                "borrower_id": c.borrower_id,
                "state": c.state,
                "provider_name": c.provider_name,
                "initiated_at": c.initiated_at,
                "answered_at": c.answered_at,
                "completed_at": c.completed_at,
                "duration_sec": c.duration_sec,
                "failure_reason": c.failure_reason,
            }
            for c in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ---------------------------------------------------------------------------
# Pacing recommendation
# ---------------------------------------------------------------------------

@router.get("/sessions/{session_id}/pacing")
def get_pacing(
    session_id: str,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user_payload),
):
    _ensure_tables(db)
    s = _get_session_or_404(session_id, db)
    inp = _build_pacing_input(db, session_id, s.mode)
    pacing_decision = _pacing_engine.recommend(inp)
    safety_decision = _safety_ctrl.evaluate(db, pacing_decision, session_id, s.mode)
    return {
        "session_id": session_id,
        "mode": s.mode,
        "pacing": {
            "proposed_dials": pacing_decision.proposed_dials,
            "explanation": pacing_decision.explanation,
            "inputs": pacing_decision.inputs_snapshot,
        },
        "safety": {
            "verdict": safety_decision.verdict,
            "approved_dials": safety_decision.approved_dials,
            "reason": safety_decision.reason,
        },
        "rolling_answer_rate": _pacing_engine.rolling_answer_rate,
        "rolling_avg_talk_sec": _pacing_engine.rolling_avg_talk_sec,
    }


# ---------------------------------------------------------------------------
# Provider events (webhook)
# ---------------------------------------------------------------------------

@router.post("/events")
def receive_provider_event(body: ProviderEventRequest):
    """
    Accepts inbound webhook events from telecom providers.
    No auth required (providers authenticate via signed payload in production;
    here we keep it simple since providers are mocks).
    """
    evt = ProviderEvent(
        call_id=body.call_id,
        provider_call_id=body.provider_call_id,
        event_type=body.event_type,
        event_seq=body.event_seq,
        extra=body.extra,
    )
    accepted = _event_processor.process(evt)
    return {"accepted": accepted, "call_id": body.call_id, "event_type": body.event_type}


# ---------------------------------------------------------------------------
# Provider health
# ---------------------------------------------------------------------------

@router.get("/providers/health")
def get_provider_health(db: Session = Depends(get_db)):
    _ensure_tables(db)
    result = []
    for p in _providers:
        health = p.get_health()
        ph = db.query(DialerProviderHealth).filter(
            DialerProviderHealth.provider_name == p.name
        ).first()
        health["circuit_state"] = ph.circuit_state if ph else CircuitState.CLOSED
        health["consecutive_failures"] = ph.consecutive_failures if ph else 0
        result.append(health)
    return {"providers": result}


# ---------------------------------------------------------------------------
# Session metrics
# ---------------------------------------------------------------------------

@router.get("/sessions/{session_id}/metrics")
def get_metrics(
    session_id: str,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user_payload),
):
    _ensure_tables(db)
    s = _get_session_or_404(session_id, db)
    call_stats = dict(
        db.query(DialerCall.state, func.count(DialerCall.id))
        .filter(DialerCall.session_id == session_id)
        .group_by(DialerCall.state)
        .all()
    )
    total_calls = sum(call_stats.values())
    answered    = call_stats.get(CallState.ANSWERED, 0) + call_stats.get(CallState.CONNECTED, 0) + call_stats.get(CallState.COMPLETED, 0)
    total_initiated = sum(call_stats.get(st, 0) for st in [
        CallState.INITIATED, CallState.RINGING, CallState.ANSWERED,
        CallState.CONNECTED, CallState.COMPLETED, CallState.FAILED,
    ])
    answer_rate = answered / max(1, total_initiated)

    avg_dur = db.query(func.avg(DialerCall.duration_sec)).filter(
        DialerCall.session_id == session_id,
        DialerCall.duration_sec.isnot(None),
    ).scalar() or 0.0

    agent_counts = dict(
        db.query(DialerAgent.dialer_state, func.count(DialerAgent.id))
        .filter(DialerAgent.session_id == session_id)
        .group_by(DialerAgent.dialer_state)
        .all()
    )
    total_agents = sum(agent_counts.values())
    busy_agents  = agent_counts.get(AgentState.CONNECTED, 0) + agent_counts.get(AgentState.DIALING, 0)
    utilization  = busy_agents / max(1, total_agents)

    return {
        "session_id": session_id,
        "mode": s.mode,
        "state": s.state,
        "total_calls": total_calls,
        "call_states": call_stats,
        "total_initiated": total_initiated,
        "total_answered": answered,
        "total_completed": call_stats.get(CallState.COMPLETED, 0),
        "total_failed": call_stats.get(CallState.FAILED, 0),
        "answer_rate_pct": round(answer_rate * 100, 2),
        "avg_talk_time_sec": round(avg_dur, 2),
        "agent_utilization_pct": round(utilization * 100, 2),
        "agent_states": agent_counts,
        "rolling_answer_rate": round(_pacing_engine.rolling_answer_rate * 100, 2),
    }


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

@router.post("/simulate")
def run_simulation(
    body: SimulateRequest,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user_payload),
):
    """
    Run a reproducible simulation scenario.
    Executes synchronously and returns metrics without modifying production data.
    """
    from app.services.simulation import run_scenario
    _ensure_tables(db)
    result = run_scenario(
        scenario=body.scenario,
        num_agents=body.num_agents,
        num_borrowers=body.num_borrowers,
        duration_ticks=body.duration_ticks,
        mode=body.mode,
    )
    return result


# ---------------------------------------------------------------------------
# Crash recovery endpoint (for ops)
# ---------------------------------------------------------------------------

@router.post("/recover")
def trigger_recovery(
    session_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user_payload),
):
    _ensure_tables(db)
    result = recover_stale_state(db, session_id)
    return {"recovered": result}

