from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import Optional
from app.core.database import get_db
from app.models.schema import Payment, Account, Borrower

router = APIRouter(prefix="/payments", tags=["Payment Management"])

@router.get("")
def list_payments(
    status: Optional[str] = Query(None),
    method: Optional[str] = Query(None),
    is_duplicate: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    q = db.query(Payment)
    if status:
        q = q.filter(Payment.payment_status == status)
    if method:
        q = q.filter(Payment.payment_method == method)
    if is_duplicate is not None:
        q = q.filter(Payment.is_duplicate_ref == (1 if is_duplicate else 0))
    if search:
        s = f"%{search.strip()}%"
        q = q.filter(or_(Payment.payment_id.ilike(s), Payment.payment_reference.ilike(s), Payment.account_id.ilike(s)))
    if from_date:
        q = q.filter(Payment.event_at >= from_date)
    if to_date:
        q = q.filter(Payment.event_at <= to_date)

    total = q.count()
    items = q.order_by(Payment.event_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    result = [
        {
            "payment_id": p.payment_id,
            "account_id": p.account_id,
            "borrower_id": p.borrower_id,
            "amount": p.amount,
            "event_at": p.event_at,
            "payment_status": p.payment_status,
            "payment_method": p.payment_method,
            "payment_reference": p.payment_reference,
            "provider_id": p.provider_id,
            "is_duplicate_ref": bool(p.is_duplicate_ref)
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
def get_payment_summary(db: Session = Depends(get_db)):
    total_count = db.query(Payment).count()
    
    # Status totals
    status_counts = db.query(
        Payment.payment_status,
        func.count(Payment.payment_id),
        func.sum(Payment.amount)
    ).group_by(Payment.payment_status).all()

    status_data = {}
    for st, cnt, sm in status_counts:
        status_data[st] = {
            "count": cnt,
            "amount": round(float(sm or 0.0), 2)
        }

    # Method breakdown
    methods = db.query(
        Payment.payment_method,
        func.count(Payment.payment_id),
        func.sum(Payment.amount)
    ).filter(Payment.payment_status == "SUCCESS").group_by(Payment.payment_method).all()

    method_breakdown = [
        {
            "method": m[0] or "Unknown",
            "count": m[1],
            "amount": round(float(m[2] or 0.0), 2)
        } for m in methods
    ]

    duplicate_refs = db.query(Payment).filter(Payment.is_duplicate_ref == 1).count()
    success_amount = status_data.get("SUCCESS", {}).get("amount", 0.0)
    success_count = status_data.get("SUCCESS", {}).get("count", 0)
    success_rate = round((success_count / total_count * 100), 2) if total_count > 0 else 0.0

    return {
        "total_payments_recorded": total_count,
        "total_successful_amount": success_amount,
        "success_rate_pct": success_rate,
        "duplicate_reference_count": duplicate_refs,
        "by_status": status_data,
        "by_method": method_breakdown
    }
