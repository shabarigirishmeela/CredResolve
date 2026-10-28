from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from app.core.database import get_db
from app.models.schema import Campaign, DailyTargeting, Call

router = APIRouter(prefix="/campaigns", tags=["Campaign Analytics"])

@router.get("")
def list_campaigns(
    channel: Optional[str] = Query(None),
    strategy_version: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    q = db.query(Campaign)
    if channel:
        q = q.filter(Campaign.channel == channel)
    if strategy_version:
        q = q.filter(Campaign.strategy_version == strategy_version)

    total = q.count()
    items = q.order_by(Campaign.start_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    cmp_ids = [c.campaign_id for c in items]

    # Target count per campaign
    targets = db.query(
        DailyTargeting.campaign_id,
        func.count(DailyTargeting.target_id)
    ).filter(DailyTargeting.campaign_id.in_(cmp_ids)).group_by(DailyTargeting.campaign_id).all()
    target_map = {t[0]: t[1] for t in targets}

    # Calls generated per campaign
    call_counts = db.query(
        Call.campaign_id,
        func.count(Call.call_id)
    ).filter(Call.campaign_id.in_(cmp_ids)).group_by(Call.campaign_id).all()
    call_map = {c[0]: c[1] for c in call_counts}

    result = []
    for c in items:
        tgt_cnt = target_map.get(c.campaign_id, 0)
        call_cnt = call_map.get(c.campaign_id, 0)
        result.append({
            "campaign_id": c.campaign_id,
            "campaign_name": c.campaign_name,
            "channel": c.channel,
            "strategy_version": c.strategy_version,
            "start_at": c.start_at,
            "end_at": c.end_at,
            "target_definition": c.target_definition,
            "targeted_accounts": tgt_cnt,
            "outreach_events": call_cnt,
            "engagement_rate_pct": round((call_cnt / max(1, tgt_cnt) * 100), 1) if tgt_cnt > 0 else 0.0
        })

    return {
        "items": result,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }

@router.get("/summary")
def get_campaign_summary(db: Session = Depends(get_db)):
    total_campaigns = db.query(Campaign).count()

    channel_distribution = db.query(
        Campaign.channel,
        func.count(Campaign.campaign_id)
    ).group_by(Campaign.channel).all()

    strategy_distribution = db.query(
        Campaign.strategy_version,
        func.count(Campaign.campaign_id)
    ).group_by(Campaign.strategy_version).all()

    return {
        "total_campaigns": total_campaigns,
        "by_channel": [{"channel": c[0], "count": c[1]} for c in channel_distribution],
        "by_strategy": [{"strategy": s[0], "count": s[1]} for s in strategy_distribution]
    }
