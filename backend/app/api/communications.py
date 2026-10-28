from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import Optional
from app.core.database import get_db
from app.models.schema import Call, SmsEvent, WhatsappEvent

router = APIRouter(prefix="/communications", tags=["Communication Analytics"])

@router.get("/summary")
def get_communications_summary(db: Session = Depends(get_db)):
    # 1. Calls Overview
    total_calls = db.query(Call).count()
    call_statuses = db.query(Call.call_status, func.count(Call.call_id)).group_by(Call.call_status).all()
    call_status_map = {c[0]: c[1] for c in call_statuses}
    answered = call_status_map.get("ANSWERED", 0)
    contact_rate = round((answered / total_calls * 100), 2) if total_calls > 0 else 0.0

    # 2. SMS Overview
    total_sms = db.query(SmsEvent).count()
    sms_types = db.query(SmsEvent.event_type, func.count(SmsEvent.sms_event_id)).group_by(SmsEvent.event_type).all()
    sms_type_map = {s[0]: s[1] for s in sms_types}
    sms_delivered = sms_type_map.get("DELIVERED", 0) + sms_type_map.get("CLICKED", 0)
    sms_clicked = sms_type_map.get("CLICKED", 0)
    sms_failed = sms_type_map.get("FAILED", 0)

    # 3. WhatsApp Overview
    total_wa = db.query(WhatsappEvent).count()
    wa_types = db.query(WhatsappEvent.event_type, func.count(WhatsappEvent.whatsapp_event_id)).group_by(WhatsappEvent.event_type).all()
    wa_type_map = {w[0]: w[1] for w in wa_types}
    wa_delivered = wa_type_map.get("DELIVERED", 0) + wa_type_map.get("READ", 0) + wa_type_map.get("REPLIED", 0) + wa_type_map.get("PAYMENT_CLICK", 0)
    wa_clicks = wa_type_map.get("PAYMENT_CLICK", 0)
    wa_replies = wa_type_map.get("REPLIED", 0)
    wa_failed = wa_type_map.get("FAILED", 0)

    return {
        "calls": {
            "total": total_calls,
            "answered": answered,
            "contact_rate_pct": contact_rate,
            "status_breakdown": call_status_map
        },
        "sms": {
            "total": total_sms,
            "delivered": sms_delivered,
            "clicked": sms_clicked,
            "failed": sms_failed,
            "delivery_rate_pct": round((sms_delivered / total_sms * 100), 2) if total_sms > 0 else 0.0,
            "click_rate_pct": round((sms_clicked / max(1, sms_delivered) * 100), 2) if sms_delivered > 0 else 0.0,
            "status_breakdown": sms_type_map
        },
        "whatsapp": {
            "total": total_wa,
            "delivered": wa_delivered,
            "payment_clicks": wa_clicks,
            "replies": wa_replies,
            "failed": wa_failed,
            "delivery_rate_pct": round((wa_delivered / total_wa * 100), 2) if total_wa > 0 else 0.0,
            "payment_intent_rate_pct": round((wa_clicks / max(1, wa_delivered) * 100), 2) if wa_delivered > 0 else 0.0,
            "status_breakdown": wa_type_map
        }
    }

@router.get("/calls")
def list_calls(
    status: Optional[str] = Query(None),
    direction: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    q = db.query(Call)
    if status:
        q = q.filter(Call.call_status == status)
    if direction:
        q = q.filter(Call.direction == direction)
    if search:
        s = f"%{search.strip()}%"
        q = q.filter(or_(Call.call_id.ilike(s), Call.account_id.ilike(s), Call.agent_id.ilike(s)))

    total = q.count()
    items = q.order_by(Call.event_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [
            {
                "call_id": c.call_id,
                "account_id": c.account_id,
                "borrower_id": c.borrower_id,
                "agent_id": c.agent_id or "IVR Dialer",
                "campaign_id": c.campaign_id,
                "direction": c.direction,
                "call_status": c.call_status,
                "duration_sec": c.duration_sec,
                "event_at": c.event_at,
                "timezone": c.timezone
            } for c in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }

@router.get("/sms")
def list_sms(
    event_type: Optional[str] = Query(None),
    template_code: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    q = db.query(SmsEvent)
    if event_type:
        q = q.filter(SmsEvent.event_type == event_type)
    if template_code:
        q = q.filter(SmsEvent.template_code == template_code)

    total = q.count()
    items = q.order_by(SmsEvent.event_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [
            {
                "sms_event_id": s.sms_event_id,
                "account_id": s.account_id,
                "borrower_id": s.borrower_id,
                "message_id": s.message_id,
                "event_type": s.event_type,
                "template_code": s.template_code,
                "event_at": s.event_at
            } for s in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }

@router.get("/whatsapp")
def list_whatsapp(
    event_type: Optional[str] = Query(None),
    template_code: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    q = db.query(WhatsappEvent)
    if event_type:
        q = q.filter(WhatsappEvent.event_type == event_type)
    if template_code:
        q = q.filter(WhatsappEvent.template_code == template_code)

    total = q.count()
    items = q.order_by(WhatsappEvent.event_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [
            {
                "whatsapp_event_id": w.whatsapp_event_id,
                "account_id": w.account_id,
                "borrower_id": w.borrower_id,
                "message_id": w.message_id,
                "event_type": w.event_type,
                "template_code": w.template_code,
                "event_at": w.event_at
            } for w in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }
