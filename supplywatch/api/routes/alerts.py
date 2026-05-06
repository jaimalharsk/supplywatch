from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import require_api_key
from api.schemas import AlertSubscribeRequest
from core.config import get_settings
from core.database import AlertHistory, AlertSubscription, ApiKey, get_db
from scheduler.jobs import generate_digest

router = APIRouter(tags=["alerts"], dependencies=[Depends(require_api_key)])

@router.post('/alerts/subscribe')
async def subscribe(payload: AlertSubscribeRequest, api_key: ApiKey = Depends(require_api_key), db: AsyncSession = Depends(get_db)):
    sub = AlertSubscription(api_key_id=api_key.id, material_id=payload.material_id, threshold=payload.threshold, email=payload.email, webhook_url=payload.webhook_url)
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return {"data": {"id": sub.id, "material_id": sub.material_id, "threshold": sub.threshold}, "meta": {"timestamp": datetime.now(timezone.utc), "version": get_settings().app_version}}

@router.get('/alerts/history')
async def alert_history(api_key: ApiKey = Depends(require_api_key), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(AlertHistory).join(AlertSubscription, AlertSubscription.id == AlertHistory.subscription_id).where(AlertSubscription.api_key_id == api_key.id).order_by(desc(AlertHistory.sent_at)))).scalars().all()
    return {"data": [{"id": r.id, "score_at_trigger": r.score_at_trigger, "message": r.message, "sent_at": r.sent_at} for r in rows], "meta": {"timestamp": datetime.now(timezone.utc), "version": get_settings().app_version}}

@router.post('/digest/trigger')
async def digest_trigger(api_key: ApiKey = Depends(require_api_key), db: AsyncSession = Depends(get_db)):
    digest = await generate_digest(db, api_key.id)
    return {"data": digest, "meta": {"timestamp": datetime.now(timezone.utc), "version": get_settings().app_version}}
