import io
import csv
from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.schema import Account, Payment, Complaint, PromiseToPay

router = APIRouter(prefix="/reports", tags=["Reports & Settings"])

@router.get("/export-csv")
def export_csv_report(
    report_type: str = Query("accounts", pattern="^(accounts|payments|queue|complaints|ptp)$"),
    db: Session = Depends(get_db)
):
    output = io.StringIO()
    writer = csv.writer(output)

    if report_type == "accounts":
        writer.writerow(["account_id", "borrower_id", "loan_type", "principal_amount", "outstanding_amount", "dpd", "risk_segment", "status", "priority_score", "priority_tier", "recommended_action"])
        accounts = db.query(Account).limit(5000).all()
        for a in accounts:
            writer.writerow([a.account_id, a.borrower_id, a.loan_type, a.principal_amount, a.outstanding_amount, a.dpd, a.risk_segment, a.status, a.priority_score, a.priority_tier, a.recommended_action])
        filename = "credresolve_accounts_export.csv"

    elif report_type == "payments":
        writer.writerow(["payment_id", "account_id", "borrower_id", "event_at", "amount", "payment_status", "payment_method", "payment_reference", "is_duplicate_ref"])
        payments = db.query(Payment).limit(5000).all()
        for p in payments:
            writer.writerow([p.payment_id, p.account_id, p.borrower_id, p.event_at, p.amount, p.payment_status, p.payment_method, p.payment_reference, p.is_duplicate_ref])
        filename = "credresolve_payments_export.csv"

    elif report_type == "queue":
        writer.writerow(["account_id", "borrower_id", "priority_score", "priority_tier", "recommended_action", "compliance_hold", "dpd", "outstanding_amount", "risk_segment"])
        queue_accs = db.query(Account).filter(~Account.status.in_(["CLOSED", "PAID"])).order_by(Account.priority_score.desc()).limit(5000).all()
        for q in queue_accs:
            writer.writerow([q.account_id, q.borrower_id, q.priority_score, q.priority_tier, q.recommended_action, q.compliance_hold, q.dpd, q.outstanding_amount, q.risk_segment])
        filename = "credresolve_work_queue_export.csv"

    elif report_type == "complaints":
        writer.writerow(["complaint_id", "account_id", "borrower_id", "complaint_type", "severity", "status", "source", "event_at", "resolution_at"])
        complaints = db.query(Complaint).limit(5000).all()
        for c in complaints:
            writer.writerow([c.complaint_id, c.account_id, c.borrower_id, c.complaint_type, c.severity, c.status, c.source, c.event_at, c.resolution_at])
        filename = "credresolve_complaints_export.csv"

    else:
        writer.writerow(["ptp_id", "account_id", "borrower_id", "agent_id", "promised_amount", "promised_date", "status", "source"])
        ptps = db.query(PromiseToPay).limit(5000).all()
        for pt in ptps:
            writer.writerow([pt.ptp_id, pt.account_id, pt.borrower_id, pt.agent_id, pt.promised_amount, pt.promised_date, pt.status, pt.source])
        filename = "credresolve_ptp_export.csv"

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/definitions")
def get_metric_definitions():
    return {
        "kpi_metrics": [
            {
                "metric": "Total Accounts & Outstanding Balance",
                "definition": "Count of all loan accounts in the core registry, and the aggregate current outstanding sum across all loan products (Consumer, Auto, BNPL, Credit Card, Personal).",
                "formula": "SUM(outstanding_amount) across active/delinquent accounts"
            },
            {
                "metric": "Overdue Accounts & Overdue Balance",
                "definition": "Accounts with Days Past Due (DPD) > 0 excluding accounts marked as CLOSED or PAID.",
                "formula": "COUNT(*) and SUM(outstanding_amount) WHERE dpd > 0 AND status NOT IN ('CLOSED', 'PAID')"
            },
            {
                "metric": "Collection Rate",
                "definition": "The proportion of overdue balances successfully recovered through collections.",
                "formula": "Successful Collections / (Overdue Balance + Successful Collections) * 100"
            },
            {
                "metric": "PTP Fulfillment Rate",
                "definition": "The percentage of resolved commitments where the borrower paid as promised.",
                "formula": "Kept Promises / (Kept Promises + Broken Promises) * 100"
            },
            {
                "metric": "Complaint Resolution Rate",
                "definition": "The proportion of borrower grievances that have been investigated and closed.",
                "formula": "Resolved Complaints / Total Complaints * 100"
            }
        ],
        "prioritization_engine_weights": [
            {"factor": "Days Past Due (DPD)", "weight": "25%", "logic": "DPD >= 90 (25 pts), DPD >= 60 (20 pts), DPD >= 30 (14 pts), DPD > 0 (7 pts)"},
            {"factor": "Outstanding Exposure", "weight": "25%", "logic": ">= 500k (25 pts), >= 250k (18 pts), >= 100k (12 pts), < 100k (5 pts)"},
            {"factor": "Credit Risk Segment", "weight": "15%", "logic": "NPA (15 pts), HIGH (12 pts), MEDIUM (8 pts), LOW (3 pts)"},
            {"factor": "Promise-to-Pay History", "weight": "15%", "logic": "Broken PTP (15 pts), No PTP (7 pts), Kept PTP (5 pts), Open PTP (4 pts)"},
            {"factor": "Contact Responsiveness", "weight": "20%", "logic": "Dispute/Refused (18 pts), No Contact (14 pts), Standard (10 pts), Recent Payment (6 pts)"}
        ],
        "compliance_guardrails": [
            {
                "guardrail": "Active Grievance & Dispute Pause",
                "standard": "RBI Fair Practices Code & Consumer Protection Act 2019",
                "enforcement": "Accounts with open CRITICAL or HIGH severity complaints or active disputes automatically lock with compliance_hold = True. Automated calls/SMS are paused."
            },
            {
                "guardrail": "Permissible Calling Window (08:00 - 19:00)",
                "standard": "Indian Banking / RBI Recovery Agent Guidelines",
                "enforcement": "Dynamic timezone conversion ensures no borrower is contacted outside 8:00 AM to 7:00 PM local time. Outside hours, queue shifts to morning scheduling."
            },
            {
                "guardrail": "Data Privacy & PII Masking",
                "standard": "Fintech Data Protection Standards",
                "enforcement": "Phone numbers and emails are masked in all standard dashboard views (+91-XXXXX-1234) and excluded from analytics logs."
            }
        ],
        "data_cleaning_decisions": [
            {
                "dataset": "agents.csv",
                "issue": "30,000 rows for only 1,000 unique agent IDs due to repeated historical state snapshots.",
                "cleaning_rule": "Deduplicated by canonical agent_id, preserving the latest updated_at record. Result: 1,000 clean agents."
            },
            {
                "dataset": "borrowers.csv",
                "issue": "19,585 duplicate rows and 2,913 account references with missing borrower master records.",
                "cleaning_rule": "Deduplicated by borrower_id keeping latest updated_at. Synthesized 2,913 placeholder profiles flagged as is_enriched=False to ensure 100% referential integrity."
            },
            {
                "dataset": "payments.csv",
                "issue": "500 duplicate payment_id entries and 8,042 cross-account duplicate transaction references.",
                "cleaning_rule": "Purged 500 duplicate event rows. Added is_duplicate_ref flag to isolate retry/webhook duplicates and prevent balance inflation."
            },
            {
                "dataset": "call_dispositions.csv",
                "issue": "Inconsistent legacy disposition codes (e.g., PROMISE_TO_PAY vs PTP).",
                "cleaning_rule": "Standardized all legacy PROMISE_TO_PAY entries to canonical PTP."
            }
        ]
    }

@router.get("/settings")
def get_system_settings():
    return {
        "platform_name": "CredResolve Intelligence",
        "version": "2.4.0-enterprise",
        "environment": "Production Ready",
        "database_backend": "SQLite (Local Embedded) / PostgreSQL Compatible",
        "active_compliance_mode": "Strict (RBI Fair Practices Code & GDPR PII Masking)",
        "contact_window_start": "08:00:00",
        "contact_window_end": "19:00:00",
        "prioritization_model": "Explainable Rule-Based Multi-Factor Scoring Engine",
        "supported_channels": ["VOICE", "WHATSAPP", "SMS", "FIELD_VISIT"],
        "max_daily_attempts_per_borrower": 3
    }
