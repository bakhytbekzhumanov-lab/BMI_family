"""
Apple Health webhook endpoint.

Setup in iPhone:
1. Install "Health Auto Export" app OR use Apple Shortcuts
2. Configure to POST to: https://yourdomain.com/health/webhook
3. Include header: X-Health-Secret: <HEALTH_WEBHOOK_SECRET>
4. Payload format:
   {
     "telegram_id": 123456789,
     "metrics": [
       {"metric": "weight", "value": 75.5, "unit": "kg", "recorded_at": "2024-01-15T08:00:00"},
       {"metric": "steps", "value": 8432, "unit": "count", "recorded_at": "2024-01-15T23:59:00"},
       {"metric": "heart_rate", "value": 72, "unit": "bpm", "recorded_at": "2024-01-15T10:00:00"},
       {"metric": "sleep_hours", "value": 7.5, "unit": "hours", "recorded_at": "2024-01-15T07:00:00"}
     ]
   }
"""
from datetime import datetime
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import get_db
from app.core.config import settings
from app.modules.health.service import save_health_data

router = APIRouter(prefix="/health", tags=["health"])


class HealthMetric(BaseModel):
    metric: str
    value: float
    unit: str = ""
    recorded_at: datetime | None = None
    source: str | None = None


class HealthPayload(BaseModel):
    telegram_id: int
    metrics: list[HealthMetric]


@router.post("/webhook")
async def health_webhook(
    payload: HealthPayload,
    x_health_secret: str = Header(default=""),
    session: AsyncSession = Depends(get_db),
):
    if settings.health_webhook_secret and x_health_secret != settings.health_webhook_secret:
        raise HTTPException(status_code=403, detail="Invalid secret")

    if payload.telegram_id not in settings.family_member_ids:
        raise HTTPException(status_code=403, detail="Unknown family member")

    metrics = [m.model_dump() for m in payload.metrics]
    count = await save_health_data(session, payload.telegram_id, metrics)

    return {"saved": count}


@router.get("/status/{telegram_id}")
async def health_status(
    telegram_id: int,
    x_health_secret: str = Header(default=""),
    session: AsyncSession = Depends(get_db),
):
    """Quick check endpoint — returns latest metrics for a family member."""
    if settings.health_webhook_secret and x_health_secret != settings.health_webhook_secret:
        raise HTTPException(status_code=403, detail="Invalid secret")

    from app.modules.health.service import get_latest_metric
    result = {}
    for metric in ["weight", "steps", "heart_rate", "sleep_hours"]:
        record = await get_latest_metric(session, telegram_id, metric)
        if record:
            result[metric] = {"value": record.value, "unit": record.unit, "at": record.recorded_at}

    return result
