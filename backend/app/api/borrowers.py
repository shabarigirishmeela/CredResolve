from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Optional
from app.core.database import get_db
from app.models.schema import Borrower, Account, Payment, Call, PromiseToPay, Complaint, FieldVisit

router = APIRouter(prefix="/borrowers", tags=["Borrower Management"])

@router.get("")
def list_borrowers(
    search: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    q = db.query(Borrower)
    if search:
        s = f"%{search.strip()}%"
        q = q.filter(
            or_(
                Borrower.borrower_id.ilike(s),
                Borrower.name.ilike(s),
                Borrower.phone.ilike(s),
                Borrower.email.ilike(s),
                Borrower.city.ilike(s)
            )
        )
    if city:
        q = q.filter(Borrower.city == city)
    if state:
        q = q.filter(Borrower.state == state)

    total = q.count()
    items = q.order_by(Borrower.borrower_id).offset((page - 1) * page_size).limit(page_size).all()

    # Enrich with summary stats per borrower
    borrower_ids = [b.borrower_id for b in items]
    acc_stats = db.query(
        Account.borrower_id,
        func.count(Account.account_id).label("acc_count"),
        func.sum(Account.outstanding_amount).label("total_outstanding"),
        func.max(Account.dpd).label("max_dpd"),
        func.max(Account.priority_score).label("max_score")
    ).filter(Account.borrower_id.in_(borrower_ids)).group_by(Account.borrower_id).all()

    stats_map = {
        r[0]: {
            "account_count": r[1],
            "total_outstanding": round(float(r[2] or 0.0), 2),
            "max_dpd": r[3] or 0,
            "max_score": round(float(r[4] or 0.0), 1)
        } for r in acc_stats
    }

    result = []
    for b in items:
        st = stats_map.get(b.borrower_id, {"account_count": 0, "total_outstanding": 0.0, "max_dpd": 0, "max_score": 0.0})
        result.append({
            "borrower_id": b.borrower_id,
            "name": b.name,
            # Mask phone & email for GDPR/Fintech borrower privacy compliance
            "phone_masked": f"+91-XXXXX-{str(b.phone)[-4:]}" if b.phone else "Not Provided",
            "email_masked": f"{b.email[:3]}***@{b.email.split('@')[-1]}" if b.email and '@' in b.email else "Not Provided",
            "city": b.city or "Unknown",
            "state": b.state or "Unknown",
            "created_at": b.created_at,
            "is_enriched": b.is_enriched,
            "account_count": st["account_count"],
            "total_outstanding": st["total_outstanding"],
            "max_dpd": st["max_dpd"],
            "max_score": st["max_score"]
        })

    return {
        "items": result,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }

@router.get("/{borrower_id}")
def get_borrower_detail(borrower_id: str, db: Session = Depends(get_db)):
    borrower = db.query(Borrower).filter(Borrower.borrower_id == borrower_id).first()
    if not borrower:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Borrower record not found")

    accounts = db.query(Account).filter(Account.borrower_id == borrower_id).all()
    acc_ids = [a.account_id for a in accounts]

    payments = db.query(Payment).filter(Payment.borrower_id == borrower_id).order_by(Payment.event_at.desc()).limit(20).all()
    calls = db.query(Call).filter(Call.borrower_id == borrower_id).order_by(Call.event_at.desc()).limit(20).all()
    ptps = db.query(PromiseToPay).filter(PromiseToPay.borrower_id == borrower_id).order_by(PromiseToPay.event_at.desc()).limit(15).all()
    complaints = db.query(Complaint).filter(Complaint.borrower_id == borrower_id).order_by(Complaint.event_at.desc()).all()
    field_visits = db.query(FieldVisit).filter(FieldVisit.borrower_id == borrower_id).order_by(FieldVisit.event_at.desc()).all()

    return {
        "borrower_id": borrower.borrower_id,
        "name": borrower.name,
        "phone_masked": f"+91-XXXXX-{str(borrower.phone)[-4:]}" if borrower.phone else "Not Provided",
        "email_masked": f"{borrower.email[:3]}***@{borrower.email.split('@')[-1]}" if borrower.email and '@' in borrower.email else "Not Provided",
        "city": borrower.city,
        "state": borrower.state,
        "created_at": borrower.created_at,
        "is_enriched": borrower.is_enriched,
        "accounts": [
            {
                "account_id": a.account_id,
                "loan_type": a.loan_type,
                "principal_amount": a.principal_amount,
                "outstanding_amount": a.outstanding_amount,
                "dpd": a.dpd,
                "risk_segment": a.risk_segment,
                "status": a.status,
                "priority_score": a.priority_score,
                "priority_tier": a.priority_tier,
                "recommended_action": a.recommended_action,
                "compliance_hold": bool(a.compliance_hold),
                "compliance_reason": a.compliance_reason
            } for a in accounts
        ],
        "payments": [
            {
                "payment_id": p.payment_id,
                "account_id": p.account_id,
                "amount": p.amount,
                "event_at": p.event_at,
                "payment_status": p.payment_status,
                "payment_method": p.payment_method,
                "payment_reference": p.payment_reference,
                "is_duplicate_ref": bool(p.is_duplicate_ref)
            } for p in payments
        ],
        "calls": [
            {
                "call_id": c.call_id,
                "account_id": c.account_id,
                "event_at": c.event_at,
                "direction": c.direction,
                "call_status": c.call_status,
                "duration_sec": c.duration_sec,
                "agent_id": c.agent_id
            } for c in calls
        ],
        "ptps": [
            {
                "ptp_id": pt.ptp_id,
                "account_id": pt.account_id,
                "promised_amount": pt.promised_amount,
                "promised_date": pt.promised_date,
                "status": pt.status,
                "source": pt.source
            } for pt in ptps
        ],
        "complaints": [
            {
                "complaint_id": cm.complaint_id,
                "account_id": cm.account_id,
                "complaint_type": cm.complaint_type,
                "severity": cm.severity,
                "status": cm.status,
                "source": cm.source,
                "event_at": cm.event_at,
                "resolution_at": cm.resolution_at
            } for cm in complaints
        ],
        "field_visits": [
            {
                "visit_id": fv.visit_id,
                "account_id": fv.account_id,
                "visit_type": fv.visit_type,
                "outcome": fv.outcome,
                "event_at": fv.event_at,
                "scheduled_at": fv.scheduled_at,
                "latitude": fv.latitude,
                "longitude": fv.longitude
            } for fv in field_visits
        ]
    }
