from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import require_api_key
from core.config import get_settings
from core.database import DisruptionScore, Material, RawSignal, get_db

router = APIRouter(prefix="/materials", tags=["materials"], dependencies=[Depends(require_api_key)])

@router.get('')
async def list_materials(db: AsyncSession = Depends(get_db)):
    mats = (await db.execute(select(Material))).scalars().all()
    payload = []
    for m in mats:
        latest = (await db.execute(select(DisruptionScore).where(DisruptionScore.material_id == m.id).order_by(desc(DisruptionScore.computed_at)).limit(1))).scalar_one_or_none()
        payload.append({"id": m.id, "name": m.name, "symbol": m.symbol, "latest_score": latest.score if latest else 0})
    return {"data": payload, "meta": {"timestamp": datetime.now(timezone.utc), "version": get_settings().app_version}}

@router.get('/{material_id}/signal')
async def get_signal(material_id: int, db: AsyncSession = Depends(get_db)):
    score = (await db.execute(select(DisruptionScore).where(DisruptionScore.material_id == material_id).order_by(desc(DisruptionScore.computed_at)).limit(1))).scalar_one_or_none()
    if not score:
        raise HTTPException(status_code=404, detail='signal not found')
    raws = (await db.execute(select(RawSignal).where(RawSignal.material_id == material_id).order_by(desc(RawSignal.fetched_at)).limit(10))).scalars().all()
    return {"data": {"score": score.score, "factors": score.factors, "raw_signals": [{"source": r.source, "raw_data": r.raw_data} for r in raws]}, "meta": {"timestamp": datetime.now(timezone.utc), "version": get_settings().app_version}}

@router.get('/{material_id}/history')
async def history(material_id: int, db: AsyncSession = Depends(get_db)):
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    rows = (await db.execute(select(DisruptionScore).where(DisruptionScore.material_id == material_id, DisruptionScore.computed_at >= cutoff).order_by(DisruptionScore.computed_at))).scalars().all()
    return {"data": [{"score": r.score, "computed_at": r.computed_at} for r in rows], "meta": {"timestamp": datetime.now(timezone.utc), "version": get_settings().app_version}}
