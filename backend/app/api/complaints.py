from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.core.database import get_db
from app.models.schema import Complaint, Account

router = APIRouter(prefix="/complaints", tags=["Complaints & Compliance"])

class ResolveComplaintRequest(BaseModel):
    resolution_notes: Optional[str] = "Grievance resolved following borrower review"

@router.get("")
def list_complaints(
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    complaint_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    q = db.query(Complaint)
    if severity:
        q = q.filter(Complaint.severity == severity)
    if status:
        q = q.filter(Complaint.status == status)
    if complaint_type:
        q = q.filter(Complaint.complaint_type == complaint_type)
    if search:
        s = f"%{search.strip()}%"
        q = q.filter(or_(Complaint.complaint_id.ilike(s), Complaint.account_id.ilike(s), Complaint.borrower_id.ilike(s)))

    total = q.count()
    items = q.order_by(Complaint.event_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [
            {
                "complaint_id": c.complaint_id,
                "account_id": c.account_id,
                "borrower_id": c.borrower_id,
                "complaint_type": c.complaint_type,
                "severity": c.severity,
                "status": c.status,
                "source": c.source,
                "event_at": c.event_at,
                "resolution_at": c.resolution_at
            } for c in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }

@router.get("/summary")
def get_complaints_summary(db: Session = Depends(get_db)):
    total = db.query(Complaint).count()
    open_count = db.query(Complaint).filter(Complaint.status.in_(["OPEN", "INVESTIGATING"])).count()
    resolved_count = db.query(Complaint).filter(Complaint.status.in_(["RESOLVED", "CLOSED"])).count()
    resolution_rate = round((resolved_count / total * 100), 2) if total > 0 else 0.0

    by_severity = db.query(Complaint.severity, func.count(Complaint.complaint_id)).group_by(Complaint.severity).all()
    by_type = db.query(Complaint.complaint_type, func.count(Complaint.complaint_id)).group_by(Complaint.complaint_type).all()
    by_status = db.query(Complaint.status, func.count(Complaint.complaint_id)).group_by(Complaint.status).all()

    return {
        "total_complaints": total,
        "open_unresolved": open_count,
        "resolved_closed": resolved_count,
        "resolution_rate_pct": resolution_rate,
        "by_severity": [{"severity": s[0], "count": s[1]} for s in by_severity],
        "by_type": [{"type": t[0], "count": t[1]} for t in by_type],
        "by_status": [{"status": st[0], "count": st[1]} for st in by_status]
    }

@router.post("/{complaint_id}/resolve")
def resolve_complaint(complaint_id: str, body: ResolveComplaintRequest, db: Session = Depends(get_db)):
    complaint = db.query(Complaint).filter(Complaint.complaint_id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")

    complaint.status = "RESOLVED"
    complaint.resolution_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    db.commit()

    # Check if account has other open critical complaints
    account = db.query(Account).filter(Account.account_id == complaint.account_id).first()
    compliance_cleared = False
    if account:
        other_open = db.query(Complaint).filter(
            Complaint.account_id == account.account_id,
            Complaint.status.in_(["OPEN", "INVESTIGATING"]),
            Complaint.severity.in_(["CRITICAL", "HIGH"])
        ).count()
        if other_open == 0:
            account.compliance_hold = 0
            account.compliance_reason = None
            account.recommended_action = "Outreach Resumed — Dispute Resolved"
            compliance_cleared = True
            db.commit()

    return {
        "status": "success",
        "message": f"Complaint {complaint_id} resolved successfully.",
        "compliance_hold_cleared": compliance_cleared,
        "account_id": complaint.account_id
    }
