from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from pydantic import BaseModel
from app.core.database import get_db
from app.models.schema import Account, Borrower, Complaint, PromiseToPay, Payment, Call
from app.services.prioritization_engine import evaluate_account_priority

router = APIRouter(prefix="/queue", tags=["Intelligent Collection Work Queue"])

class QueueActionRequest(BaseModel):
    action_type: str  # LOG_CALL, SEND_WHATSAPP, SCHEDULE_FIELD_VISIT, SUBMIT_PTP, COMPLIANCE_REVIEW
    notes: Optional[str] = None
    outcome: Optional[str] = None
    agent_id: Optional[str] = "AGT0000001"

@router.get("")
def get_work_queue(
    tier: Optional[str] = Query(None),
    compliance_hold: Optional[bool] = Query(None),
    recommended_action: Optional[str] = Query(None),
    loan_type: Optional[str] = Query(None),
    risk_segment: Optional[str] = Query(None),
    dpd_min: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    # Only show active/delinquent accounts needing collection
    q = db.query(Account).filter(~Account.status.in_(["CLOSED", "PAID"]))
    
    if tier:
        q = q.filter(Account.priority_tier == tier)
    if compliance_hold is not None:
        q = q.filter(Account.compliance_hold == (1 if compliance_hold else 0))
    if recommended_action:
        q = q.filter(Account.recommended_action.ilike(f"%{recommended_action}%"))
    if loan_type:
        q = q.filter(Account.loan_type == loan_type)
    if risk_segment:
        q = q.filter(Account.risk_segment == risk_segment)
    if dpd_min is not None:
        q = q.filter(Account.dpd >= dpd_min)

    # Prioritized order: Highest score first, then highest outstanding amount
    q = q.order_by(Account.priority_score.desc(), Account.outstanding_amount.desc())

    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()

    # Pre-fetch borrower records
    b_ids = [a.borrower_id for a in items if a.borrower_id]
    borrowers = {b.borrower_id: b for b in db.query(Borrower).filter(Borrower.borrower_id.in_(b_ids)).all()}

    # Compute quick queue items
    result = []
    for a in items:
        b = borrowers.get(a.borrower_id)
        result.append({
            "account_id": a.account_id,
            "borrower_id": a.borrower_id,
            "borrower_name": b.name if b else "Unknown Borrower",
            "borrower_city": b.city if b else None,
            "borrower_state": b.state if b else None,
            "phone_masked": f"+91-XXXXX-{str(b.phone)[-4:]}" if (b and b.phone) else "Not Provided",
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
            "compliance_reason": a.compliance_reason,
            "timezone": a.timezone
        })

    return {
        "items": result,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }

@router.get("/{account_id}/explain")
def explain_priority(account_id: str, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.account_id == account_id).first()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    complaints = db.query(Complaint).filter(Complaint.account_id == account_id).all()
    ptps = db.query(PromiseToPay).filter(PromiseToPay.account_id == account_id).all()
    payments = db.query(Payment).filter(Payment.account_id == account_id).all()
    calls = db.query(Call).filter(Call.account_id == account_id).order_by(Call.event_at.desc()).limit(5).all()

    report = evaluate_account_priority(
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
        recent_contacts=[{"disposition_code": c.call_status} for c in calls]
    )
    return report

@router.post("/{account_id}/action")
def log_action(account_id: str, body: QueueActionRequest, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.account_id == account_id).first()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    # In a real environment, this inserts into an audit/action table and updates status
    if body.action_type == "COMPLIANCE_REVIEW":
        account.compliance_hold = 1
        account.compliance_reason = f"Manual Compliance Review Requested: {body.notes or 'Suspected grievance'}"
        account.recommended_action = "Compliance Pause — Grievance Officer Review"
    elif body.action_type == "SUBMIT_PTP":
        account.recommended_action = "PTP Scheduled — Await Payment Window"
    elif body.action_type in ["LOG_CALL", "SEND_WHATSAPP"]:
        account.recommended_action = f"Follow-up Scheduled ({body.outcome or 'Contact Logged'})"

    db.commit()
    return {
        "status": "success",
        "message": f"Action '{body.action_type}' recorded successfully for account {account_id}",
        "new_recommended_action": account.recommended_action,
        "compliance_hold": bool(account.compliance_hold)
    }
