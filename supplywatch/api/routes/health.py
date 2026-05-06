from datetime import datetime, timezone
from fastapi import APIRouter
from core.config import get_settings

router = APIRouter()

@router.get('/health')
async def health():
    s = get_settings()
    return {"data": {"status": "ok"}, "meta": {"timestamp": datetime.now(timezone.utc), "version": s.app_version}}
