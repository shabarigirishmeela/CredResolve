from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import Optional
from app.core.database import get_db
from app.models.schema import FieldVisit, Agent

router = APIRouter(prefix="/field-visits", tags=["Field Visit Management"])

@router.get("")
def list_field_visits(
    outcome: Optional[str] = Query(None),
    visit_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    q = db.query(FieldVisit)
    if outcome:
        q = q.filter(FieldVisit.outcome == outcome)
    if visit_type:
        q = q.filter(FieldVisit.visit_type == visit_type)
    if search:
        s = f"%{search.strip()}%"
        q = q.filter(or_(FieldVisit.visit_id.ilike(s), FieldVisit.account_id.ilike(s), FieldVisit.agent_id.ilike(s)))

    total = q.count()
    items = q.order_by(FieldVisit.event_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    # Fetch agent names
    agt_ids = [v.agent_id for v in items if v.agent_id]
    agents = {a.agent_id: a.agent_name for a in db.query(Agent).filter(Agent.agent_id.in_(agt_ids)).all()}

    return {
        "items": [
            {
                "visit_id": v.visit_id,
                "account_id": v.account_id,
                "borrower_id": v.borrower_id,
                "agent_id": v.agent_id,
                "agent_name": agents.get(v.agent_id, "Field Officer"),
                "visit_type": v.visit_type,
                "outcome": v.outcome,
                "latitude": round(v.latitude, 4) if v.latitude else None,
                "longitude": round(v.longitude, 4) if v.longitude else None,
                "scheduled_at": v.scheduled_at,
                "event_at": v.event_at
            } for v in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }

@router.get("/summary")
def get_field_visit_summary(db: Session = Depends(get_db)):
    total_visits = db.query(FieldVisit).count()

    outcomes = db.query(
        FieldVisit.outcome,
        func.count(FieldVisit.visit_id)
    ).group_by(FieldVisit.outcome).all()

    types = db.query(
        FieldVisit.visit_type,
        func.count(FieldVisit.visit_id)
    ).group_by(FieldVisit.visit_type).all()

    outcome_map = {o[0]: o[1] for o in outcomes}
    contacted_count = outcome_map.get("CONTACTED", 0) + outcome_map.get("PTP", 0) + outcome_map.get("PAID", 0)
    contact_success_rate = round((contacted_count / total_visits * 100), 2) if total_visits > 0 else 0.0

    return {
        "total_visits": total_visits,
        "contact_success_rate_pct": contact_success_rate,
        "by_outcome": [{"outcome": o[0], "count": o[1]} for o in outcomes],
        "by_type": [{"type": t[0], "count": t[1]} for t in types]
    }
