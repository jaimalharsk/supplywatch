import hashlib
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.database import ApiKey, ApiUsageCounter, get_db


async def require_api_key(request: Request, db: AsyncSession = Depends(get_db)) -> ApiKey:
    raw_key = request.headers.get("X-API-Key")
    if not raw_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-API-Key is required")

    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    result = await db.execute(select(ApiKey).where(ApiKey.key_hash == key_hash))
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    if api_key.tier == "free":
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        usage = (await db.execute(select(ApiUsageCounter).where(ApiUsageCounter.api_key_id == api_key.id, ApiUsageCounter.day == day))).scalar_one_or_none()
        if usage and usage.count >= get_settings().default_rate_limit_free:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Daily request limit reached")
        if not usage:
            usage = ApiUsageCounter(api_key_id=api_key.id, day=day, count=0)
            db.add(usage)
        usage.count += 1

    api_key.last_used_at = datetime.now(timezone.utc)
    await db.commit()
    return api_key
