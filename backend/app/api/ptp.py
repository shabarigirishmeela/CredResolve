from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import Optional
from app.core.database import get_db
from app.models.schema import PromiseToPay

router = APIRouter(prefix="/ptp", tags=["Promise-to-Pay Management"])

@router.get("")
def list_ptps(
    status: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    q = db.query(PromiseToPay)
    if status:
        q = q.filter(PromiseToPay.status == status)
    if source:
        q = q.filter(PromiseToPay.source == source)
    if search:
        s = f"%{search.strip()}%"
        q = q.filter(or_(PromiseToPay.ptp_id.ilike(s), PromiseToPay.account_id.ilike(s), PromiseToPay.agent_id.ilike(s)))
    if from_date:
        q = q.filter(PromiseToPay.promised_date >= from_date)
    if to_date:
        q = q.filter(PromiseToPay.promised_date <= to_date)

    total = q.count()
    items = q.order_by(PromiseToPay.event_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    result = [
        {
            "ptp_id": p.ptp_id,
            "account_id": p.account_id,
            "borrower_id": p.borrower_id,
            "agent_id": p.agent_id,
            "promised_amount": p.promised_amount,
            "promised_date": p.promised_date,
            "event_at": p.event_at,
            "status": p.status,
            "source": p.source
        } for p in items
    ]

    return {
        "items": result,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }

@router.get("/summary")
def get_ptp_summary(db: Session = Depends(get_db)):
    total_count = db.query(PromiseToPay).count()
    total_amount = db.query(func.sum(PromiseToPay.promised_amount)).scalar() or 0.0

    status_counts = db.query(
        PromiseToPay.status,
        func.count(PromiseToPay.ptp_id),
        func.sum(PromiseToPay.promised_amount)
    ).group_by(PromiseToPay.status).all()

    status_data = {}
    for st, cnt, sm in status_counts:
        status_data[st] = {
            "count": cnt,
            "amount": round(float(sm or 0.0), 2)
        }

    kept = status_data.get("KEPT", {}).get("count", 0)
    broken = status_data.get("BROKEN", {}).get("count", 0)
    resolved = kept + broken
    fulfillment_rate = round((kept / resolved * 100), 2) if resolved > 0 else 0.0

    # Channel conversion
    channels = db.query(
        PromiseToPay.source,
        func.count(PromiseToPay.ptp_id),
        func.sum(PromiseToPay.promised_amount)
    ).group_by(PromiseToPay.source).all()

    channel_stats = [
        {
            "channel": c[0] or "Unknown",
            "count": c[1],
            "total_promised": round(float(c[2] or 0.0), 2)
        } for c in channels
    ]

    return {
        "total_promises": total_count,
        "total_promised_amount": round(float(total_amount), 2),
        "fulfillment_rate_pct": fulfillment_rate,
        "by_status": status_data,
        "by_channel": channel_stats
    }
