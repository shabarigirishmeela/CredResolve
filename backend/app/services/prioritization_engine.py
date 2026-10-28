import json
from datetime import datetime, timezone
import zoneinfo
from typing import Dict, Any, List, Tuple

def evaluate_account_priority(
    account: Dict[str, Any],
    recent_complaints: List[Dict[str, Any]] = None,
    recent_ptps: List[Dict[str, Any]] = None,
    recent_payments: List[Dict[str, Any]] = None,
    recent_contacts: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Transparent, explainable rule-based collection prioritization engine.
    Produces a 0-100 score, priority tier, explainability factors,
    compliance guardrails, and recommended next actions.
    """
    recent_complaints = recent_complaints or []
    recent_ptps = recent_ptps or []
    recent_payments = recent_payments or []
    recent_contacts = recent_contacts or []

    dpd = int(account.get("dpd", 0))
    outstanding = float(account.get("outstanding_amount", 0.0))
    risk_segment = str(account.get("risk_segment", "MEDIUM")).upper()
    status = str(account.get("status", "ACTIVE")).upper()
    acc_timezone = str(account.get("timezone", "Asia/Kolkata"))

    factors: List[Dict[str, Any]] = []
    total_score = 0.0

    # 1. DPD Factor (Max 25 pts)
    dpd_points = 0.0
    dpd_rationale = ""
    if dpd >= 90:
        dpd_points = 25.0
        dpd_rationale = f"Severe delinquency (DPD {dpd} >= 90): Imminent NPA classification and balance loss."
    elif dpd >= 60:
        dpd_points = 20.0
        dpd_rationale = f"Late-stage delinquency (DPD {dpd}): Roll-forward risk into late buckets."
    elif dpd >= 30:
        dpd_points = 14.0
        dpd_rationale = f"Mid-stage delinquency (DPD {dpd}): High probability of cure if contacted promptly."
    elif dpd > 0:
        dpd_points = 7.0
        dpd_rationale = f"Early delinquency (DPD {dpd}): Early warning buffer stage."
    else:
        dpd_points = 0.0
        dpd_rationale = "Account is current (0 DPD)."
    
    total_score += dpd_points
    factors.append({
        "factor_name": "Days Past Due (DPD)",
        "raw_value": dpd,
        "weight": 0.25,
        "points_awarded": dpd_points,
        "rationale": dpd_rationale
    })

    # 2. Outstanding Balance Factor (Max 25 pts)
    bal_points = 0.0
    bal_rationale = ""
    if outstanding >= 500000:
        bal_points = 25.0
        bal_rationale = f"Very high financial exposure (₹{outstanding:,.2f} >= ₹500k): High recovery priority."
    elif outstanding >= 250000:
        bal_points = 18.0
        bal_rationale = f"Substantial exposure (₹{outstanding:,.2f}): Significant impact on portfolio recovery."
    elif outstanding >= 100000:
        bal_points = 12.0
        bal_rationale = f"Moderate exposure (₹{outstanding:,.2f}): Standard tiered recovery priority."
    else:
        bal_points = 5.0
        bal_rationale = f"Low exposure (₹{outstanding:,.2f}): Best served via automated digital channels."

    total_score += bal_points
    factors.append({
        "factor_name": "Outstanding Exposure",
        "raw_value": round(outstanding, 2),
        "weight": 0.25,
        "points_awarded": bal_points,
        "rationale": bal_rationale
    })

    # 3. Risk Segment Factor (Max 15 pts)
    risk_points = 0.0
    risk_rationale = ""
    if risk_segment == "NPA":
        risk_points = 15.0
        risk_rationale = "Non-Performing Asset: Maximum recovery intervention required."
    elif risk_segment == "HIGH":
        risk_points = 12.0
        risk_rationale = "High Risk profile: Significant historical default propensity."
    elif risk_segment == "MEDIUM":
        risk_points = 8.0
        risk_rationale = "Medium Risk profile: Moderate responsiveness expected."
    else:
        risk_points = 3.0
        risk_rationale = "Low Risk profile: High self-cure probability."

    total_score += risk_points
    factors.append({
        "factor_name": "Credit Risk Segment",
        "raw_value": risk_segment,
        "weight": 0.15,
        "points_awarded": risk_points,
        "rationale": risk_rationale
    })

    # 4. PTP History Factor (Max 15 pts)
    ptp_points = 7.0
    ptp_rationale = "No active promise to pay recorded."
    has_broken_ptp = any(str(p.get("status", "")).upper() == "BROKEN" for p in recent_ptps)
    has_open_ptp = any(str(p.get("status", "")).upper() == "OPEN" for p in recent_ptps)
    has_kept_ptp = any(str(p.get("status", "")).upper() == "KEPT" for p in recent_ptps)

    if has_broken_ptp:
        ptp_points = 15.0
        ptp_rationale = "Broken Promise to Pay: High breach risk requiring urgent cure notice."
    elif has_open_ptp:
        ptp_points = 4.0
        ptp_rationale = "Active Open PTP: Awaiting promised payment date before escalation."
    elif has_kept_ptp:
        ptp_points = 5.0
        ptp_rationale = "History of Kept PTP: Demonstrated willingness and ability to repay."

    total_score += ptp_points
    factors.append({
        "factor_name": "Promise-to-Pay Status",
        "raw_value": "BROKEN" if has_broken_ptp else ("OPEN" if has_open_ptp else ("KEPT" if has_kept_ptp else "NONE")),
        "weight": 0.15,
        "points_awarded": ptp_points,
        "rationale": ptp_rationale
    })

    # 5. Behavioral & Contact Responsiveness (Max 20 pts)
    resp_points = 10.0
    resp_rationale = "Standard outreach channel responsiveness."
    has_successful_payment = any(str(p.get("payment_status", "")).upper() == "SUCCESS" for p in recent_payments)
    
    last_disposition = ""
    if recent_contacts:
        last_disposition = str(recent_contacts[0].get("disposition_code", "")).upper()

    if last_disposition in ["REFUSED", "DISPUTE"]:
        resp_points = 18.0
        resp_rationale = f"Last contact resulted in '{last_disposition}': Needs senior supervisor engagement."
    elif last_disposition in ["NO_CONTACT", "NO_ANSWER", "WRONG_NUMBER"]:
        resp_points = 14.0
        resp_rationale = f"Repeated non-contact on voice: Channel shift recommended."
    elif has_successful_payment:
        resp_points = 6.0
        resp_rationale = "Recent successful collection detected: Maintain gentle reminder cadence."

    total_score += resp_points
    factors.append({
        "factor_name": "Contact & Payment Responsiveness",
        "raw_value": last_disposition or ("PAID_RECENTLY" if has_successful_payment else "UNCONTACTED"),
        "weight": 0.20,
        "points_awarded": resp_points,
        "rationale": resp_rationale
    })

    final_score = min(100.0, max(0.0, round(total_score, 1)))

    # Determine Priority Tier
    if final_score >= 75:
        tier = "CRITICAL"
    elif final_score >= 55:
        tier = "HIGH"
    elif final_score >= 35:
        tier = "MEDIUM"
    else:
        tier = "LOW"

    # --- Compliance Guardrails ---
    compliance_hold = False
    compliance_reason = None

    # Check for active severe complaints
    open_disputes = [
        c for c in recent_complaints 
        if str(c.get("status", "")).upper() in ["OPEN", "INVESTIGATING"]
    ]
    critical_complaints = [
        c for c in open_disputes 
        if str(c.get("severity", "")).upper() in ["CRITICAL", "HIGH"] or str(c.get("complaint_type", "")).upper() in ["HARASSMENT", "DISPUTE", "PRIVACY"]
    ]

    if critical_complaints:
        compliance_hold = True
        c_type = critical_complaints[0].get("complaint_type", "DISPUTE")
        c_sev = critical_complaints[0].get("severity", "HIGH")
        compliance_reason = f"Compliance Hold: Active {c_sev} severity {c_type} complaint under review. Fair Collections Code prohibits automated/aggressive outreach."

    # Contact Time Restrictions (Fair Practices Code: 08:00 to 19:00 in borrower timezone)
    contact_window_open = True
    local_time_str = "Unknown"
    try:
        # Map timezone
        tz_name = "UTC"
        if "kolkata" in acc_timezone.lower():
            tz_name = "Asia/Kolkata"
        elif "dubai" in acc_timezone.lower():
            tz_name = "Asia/Dubai"
        
        now_utc = datetime.now(timezone.utc)
        tz = zoneinfo.ZoneInfo(tz_name)
        borrower_local_dt = now_utc.astimezone(tz)
        local_time_str = borrower_local_dt.strftime("%Y-%m-%d %H:%M:%S %Z")
        current_hour = borrower_local_dt.hour
        if current_hour < 8 or current_hour >= 19:
            contact_window_open = False
    except Exception:
        contact_window_open = True
        local_time_str = "UTC / Standard"

    # Action Recommendation Formulation
    recommended_action = "Standard Digital Outreach"
    if compliance_hold:
        recommended_action = "Compliance Pause — Grievance Officer Review"
    elif status in ["CLOSED", "PAID"]:
        recommended_action = "Account Settled — No Action Required"
    elif status == "WRITEOFF":
        recommended_action = "Legal Recovery & Write-off Asset Recovery"
    elif not contact_window_open:
        recommended_action = f"Hold Call (Outside 08:00-19:00) — Queue for Morning Batch"
    elif has_broken_ptp:
        recommended_action = "Priority Voice Call — Broken PTP Cure Notice"
    elif dpd >= 90 and outstanding >= 200000:
        recommended_action = "Field Visit & Address Verification"
    elif dpd >= 60:
        recommended_action = "Senior Agent Outbound Call — Restructuring Offer"
    elif dpd >= 30:
        recommended_action = "WhatsApp Interactive Payment Link & SMS Notice"
    elif dpd > 0:
        recommended_action = "Automated IVR & Digital Due Reminder"
    else:
        recommended_action = "Courtesy Pre-Due Notification"

    return {
        "score": final_score,
        "tier": tier,
        "recommended_action": recommended_action,
        "compliance_hold": compliance_hold,
        "compliance_reason": compliance_reason,
        "factors": factors,
        "contact_window_open": contact_window_open,
        "borrower_local_time": local_time_str,
        "timezone": acc_timezone
    }
