from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from app.core.database import get_db
from app.models.schema import Account, Borrower, Payment, AccountStatusHistory, Complaint, PromiseToPay, Call
from app.services.prioritization_engine import evaluate_account_priority

router = APIRouter(prefix="/accounts", tags=["Account Management"])

@router.get("")
def list_accounts(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    loan_type: Optional[str] = Query(None),
    risk_segment: Optional[str] = Query(None),
    priority_tier: Optional[str] = Query(None),
    dpd_min: Optional[int] = Query(None),
    dpd_max: Optional[int] = Query(None),
    compliance_hold: Optional[bool] = Query(None),
    sort_by: str = Query("priority_score", pattern="^(priority_score|dpd|outstanding_amount|opened_at)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    q = db.query(Account)
    if search:
        s = f"%{search.strip()}%"
        q = q.filter(or_(Account.account_id.ilike(s), Account.borrower_id.ilike(s)))
    if status:
        q = q.filter(Account.status == status)
    if loan_type:
        q = q.filter(Account.loan_type == loan_type)
    if risk_segment:
        q = q.filter(Account.risk_segment == risk_segment)
    if priority_tier:
        q = q.filter(Account.priority_tier == priority_tier)
    if dpd_min is not None:
        q = q.filter(Account.dpd >= dpd_min)
    if dpd_max is not None:
        q = q.filter(Account.dpd <= dpd_max)
    if compliance_hold is not None:
        q = q.filter(Account.compliance_hold == (1 if compliance_hold else 0))

    # Sorting
    col = getattr(Account, sort_by)
    if sort_order == "desc":
        q = q.order_by(col.desc())
    else:
        q = q.order_by(col.asc())

    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()

    # Get borrower names
    b_ids = [a.borrower_id for a in items if a.borrower_id]
    borrowers = {b.borrower_id: b for b in db.query(Borrower).filter(Borrower.borrower_id.in_(b_ids)).all()}

    result = []
    for a in items:
        b = borrowers.get(a.borrower_id)
        result.append({
            "account_id": a.account_id,
            "borrower_id": a.borrower_id,
            "borrower_name": b.name if b else "Unknown Borrower",
            "borrower_city": b.city if b else None,
            "borrower_state": b.state if b else None,
            "loan_type": a.loan_type,
            "principal_amount": a.principal_amount,
            "outstanding_amount": a.outstanding_amount,
            "dpd": a.dpd,
            "risk_segment": a.risk_segment,
            "status": a.status,
            "opened_at": a.opened_at,
            "timezone": a.timezone,
            "priority_score": a.priority_score,
            "priority_tier": a.priority_tier,
            "recommended_action": a.recommended_action,
            "compliance_hold": bool(a.compliance_hold),
            "compliance_reason": a.compliance_reason
        })

    return {
        "items": result,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }

@router.get("/{account_id}")
def get_account_detail(account_id: str, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.account_id == account_id).first()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    borrower = db.query(Borrower).filter(Borrower.borrower_id == account.borrower_id).first() if account.borrower_id else None
    status_history = db.query(AccountStatusHistory).filter(AccountStatusHistory.account_id == account_id).order_by(AccountStatusHistory.event_at.desc()).all()
    payments = db.query(Payment).filter(Payment.account_id == account_id).order_by(Payment.event_at.desc()).all()
    ptps = db.query(PromiseToPay).filter(PromiseToPay.account_id == account_id).order_by(PromiseToPay.event_at.desc()).all()
    complaints = db.query(Complaint).filter(Complaint.account_id == account_id).order_by(Complaint.event_at.desc()).all()
    calls = db.query(Call).filter(Call.account_id == account_id).order_by(Call.event_at.desc()).all()

    # Dynamic explainability evaluation
    explainability = evaluate_account_priority(
        account={
            "dpd": account.dpd,
            "outstanding_amount": account.outstanding_amount,
            "risk_segment": account.risk_segment,
            "status": account.status,
            "timezone": account.timezone
        },
        recent_complaints=[{"complaint_type": c.complaint_type, "severity": c.severity, "status": c.status} for c in complaints],
        recent_ptps=[{"status": p.status} for p in ptps],
        recent_payments=[{"payment_status": p.payment_status} for p in payments],
        recent_contacts=[]
    )

    return {
        "account_id": account.account_id,
        "borrower_id": account.borrower_id,
        "borrower_name": borrower.name if borrower else "Unknown",
        "borrower_city": borrower.city if borrower else "Unknown",
        "borrower_state": borrower.state if borrower else "Unknown",
        "loan_type": account.loan_type,
        "principal_amount": account.principal_amount,
        "outstanding_amount": account.outstanding_amount,
        "dpd": account.dpd,
        "risk_segment": account.risk_segment,
        "status": account.status,
        "opened_at": account.opened_at,
        "timezone": account.timezone,
        "priority_score": account.priority_score,
        "priority_tier": account.priority_tier,
        "recommended_action": account.recommended_action,
        "compliance_hold": bool(account.compliance_hold),
        "compliance_reason": account.compliance_reason,
        "explainability": explainability,
        "status_history": [
            {
                "history_id": sh.history_id,
                "status": sh.status,
                "event_at": sh.event_at,
                "recorded_at": sh.recorded_at,
                "changed_by": sh.changed_by,
                "source": sh.source
            } for sh in status_history
        ],
        "payments": [
            {
                "payment_id": p.payment_id,
                "amount": p.amount,
                "event_at": p.event_at,
                "payment_status": p.payment_status,
                "payment_method": p.payment_method,
                "payment_reference": p.payment_reference,
                "is_duplicate_ref": bool(p.is_duplicate_ref)
            } for p in payments
        ],
        "ptps": [
            {
                "ptp_id": pt.ptp_id,
                "promised_amount": pt.promised_amount,
                "promised_date": pt.promised_date,
                "status": pt.status,
                "source": pt.source
            } for pt in ptps
        ],
        "complaints": [
            {
                "complaint_id": cm.complaint_id,
                "complaint_type": cm.complaint_type,
                "severity": cm.severity,
                "status": cm.status,
                "event_at": cm.event_at
            } for cm in complaints
        ],
        "calls": [
            {
                "call_id": c.call_id,
                "call_status": c.call_status,
                "direction": c.direction,
                "duration_sec": c.duration_sec,
                "event_at": c.event_at,
                "agent_id": c.agent_id
            } for c in calls
        ]
    }
