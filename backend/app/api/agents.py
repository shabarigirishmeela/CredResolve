from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, case
from typing import Optional
from app.core.database import get_db
from app.models.schema import Agent, AgentSession, Call, PromiseToPay, FieldVisit

router = APIRouter(prefix="/agents", tags=["Agent Performance"])

@router.get("")
def list_agents(
    team: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    q = db.query(Agent)
    if team:
        q = q.filter(Agent.team == team)
    if status:
        q = q.filter(Agent.status == status)
    if search:
        s = f"%{search.strip()}%"
        q = q.filter(or_(Agent.agent_name.ilike(s), Agent.agent_id.ilike(s), Agent.employee_code.ilike(s)))

    total = q.count()
    items = q.order_by(Agent.agent_name).offset((page - 1) * page_size).limit(page_size).all()
    agent_ids = [a.agent_id for a in items]

    # Call stats per agent
    call_stats = db.query(
        Call.agent_id,
        func.count(Call.call_id).label("total_calls"),
        func.sum(case((Call.call_status == "ANSWERED", 1), else_=0)).label("answered_calls"),
        func.sum(Call.duration_sec).label("total_duration")
    ).filter(Call.agent_id.in_(agent_ids)).group_by(Call.agent_id).all()

    call_map = {
        c[0]: {
            "total_calls": c[1] or 0,
            "answered_calls": c[2] or 0,
            "avg_duration_sec": round(float(c[3] or 0) / max(1, c[1] or 1), 1),
            "contact_rate": round(float(c[2] or 0) / max(1, c[1] or 1) * 100, 1)
        } for c in call_stats
    }

    # PTP stats per agent
    ptp_stats = db.query(
        PromiseToPay.agent_id,
        func.count(PromiseToPay.ptp_id).label("total_ptp"),
        func.sum(case((PromiseToPay.status == "KEPT", 1), else_=0)).label("kept_ptp"),
        func.sum(PromiseToPay.promised_amount).label("promised_amount")
    ).filter(PromiseToPay.agent_id.in_(agent_ids)).group_by(PromiseToPay.agent_id).all()

    ptp_map = {
        p[0]: {
            "total_ptp": p[1] or 0,
            "kept_ptp": p[2] or 0,
            "conversion_rate": round(float(p[2] or 0) / max(1, p[1] or 1) * 100, 1),
            "promised_amount": round(float(p[3] or 0.0), 2)
        } for p in ptp_stats
    }

    result = []
    for a in items:
        cm = call_map.get(a.agent_id, {"total_calls": 0, "answered_calls": 0, "avg_duration_sec": 0, "contact_rate": 0.0})
        pm = ptp_map.get(a.agent_id, {"total_ptp": 0, "kept_ptp": 0, "conversion_rate": 0.0, "promised_amount": 0.0})
        result.append({
            "agent_id": a.agent_id,
            "employee_code": a.employee_code,
            "agent_name": a.agent_name,
            "team": a.team,
            "vendor_id": a.vendor_id,
            "status": a.status,
            "joined_at": a.joined_at,
            "total_calls": cm["total_calls"],
            "answered_calls": cm["answered_calls"],
            "contact_rate_pct": cm["contact_rate"],
            "avg_call_duration_sec": cm["avg_duration_sec"],
            "total_ptp_secured": pm["total_ptp"],
            "kept_ptp": pm["kept_ptp"],
            "ptp_conversion_rate_pct": pm["conversion_rate"],
            "total_promised_amount": pm["promised_amount"]
        })

    return {
        "items": result,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }

@router.get("/{agent_id}")
def get_agent_detail(agent_id: str, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    sessions = db.query(AgentSession).filter(AgentSession.agent_id == agent_id).order_by(AgentSession.login_at.desc()).limit(10).all()
    recent_calls = db.query(Call).filter(Call.agent_id == agent_id).order_by(Call.event_at.desc()).limit(15).all()
    recent_ptps = db.query(PromiseToPay).filter(PromiseToPay.agent_id == agent_id).order_by(PromiseToPay.event_at.desc()).limit(10).all()
    recent_visits = db.query(FieldVisit).filter(FieldVisit.agent_id == agent_id).order_by(FieldVisit.event_at.desc()).limit(10).all()

    return {
        "agent_id": agent.agent_id,
        "employee_code": agent.employee_code,
        "agent_name": agent.agent_name,
        "team": agent.team,
        "vendor_id": agent.vendor_id,
        "status": agent.status,
        "joined_at": agent.joined_at,
        "sessions": [
            {
                "session_id": s.session_id,
                "login_at": s.login_at,
                "logout_at": s.logout_at,
                "channel": s.channel,
                "device_id": s.device_id,
                "timezone": s.timezone
            } for s in sessions
        ],
        "recent_calls": [
            {
                "call_id": c.call_id,
                "account_id": c.account_id,
                "call_status": c.call_status,
                "direction": c.direction,
                "duration_sec": c.duration_sec,
                "event_at": c.event_at
            } for c in recent_calls
        ],
        "recent_ptps": [
            {
                "ptp_id": p.ptp_id,
                "account_id": p.account_id,
                "promised_amount": p.promised_amount,
                "promised_date": p.promised_date,
                "status": p.status,
                "source": p.source
            } for p in recent_ptps
        ],
        "recent_visits": [
            {
                "visit_id": v.visit_id,
                "account_id": v.account_id,
                "visit_type": v.visit_type,
                "outcome": v.outcome,
                "event_at": v.event_at
            } for v in recent_visits
        ]
    }
