"""
Apple Health webhook endpoint.

Setup in iPhone — see /health_setup command in the bot or GET /health/setup-guide.

Payload format:
  POST /health/webhook
  Headers: X-Health-Secret: <HEALTH_WEBHOOK_SECRET>
  Body: {
    "telegram_id": 123456789,
    "metrics": [
      {"metric": "weight", "value": 75.5, "unit": "kg", "recorded_at": "2024-01-15T08:00:00"},
      {"metric": "steps", "value": 8432, "unit": "count"},
      {"metric": "heart_rate", "value": 72, "unit": "bpm"},
      {"metric": "sleep_hours", "value": 7.5, "unit": "hours"}
    ]
  }
"""
from datetime import datetime
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, field_validator, model_validator
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import get_db
from app.core.config import settings
from app.modules.health.service import save_health_data, METRIC_AGGREGATION

router = APIRouter(prefix="/health", tags=["health"])

# Validation bounds per metric
METRIC_BOUNDS: dict[str, tuple[float, float]] = {
    "weight": (20, 300),
    "body_fat": (1, 70),
    "steps": (0, 100_000),
    "active_energy": (0, 10_000),
    "heart_rate": (30, 250),
    "resting_heart_rate": (30, 150),
    "hrv": (0, 200),
    "sleep_hours": (0, 24),
    "respiratory_rate": (5, 50),
    "blood_oxygen": (70, 100),
}

SUPPORTED_METRICS = set(METRIC_AGGREGATION.keys())


class HealthMetric(BaseModel):
    metric: str
    value: float
    unit: str = ""
    recorded_at: datetime | None = None
    source: str | None = None

    @field_validator("metric")
    @classmethod
    def validate_metric(cls, v: str) -> str:
        normalized = v.lower().replace("-", "_").replace(" ", "_")
        return normalized

    @model_validator(mode="after")
    def validate_value_bounds(self) -> "HealthMetric":
        bounds = METRIC_BOUNDS.get(self.metric)
        if bounds:
            lo, hi = bounds
            if not (lo <= self.value <= hi):
                raise ValueError(
                    f"Value {self.value} out of range [{lo}, {hi}] for metric '{self.metric}'"
                )
        return self


class HealthPayload(BaseModel):
    telegram_id: int
    metrics: list[HealthMetric]

    @field_validator("metrics")
    @classmethod
    def limit_batch_size(cls, v: list) -> list:
        if len(v) > 100:
            raise ValueError("Too many metrics in one request (max 100)")
        return v


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

    return {"saved": count, "total": len(metrics)}


@router.get("/status/{telegram_id}")
async def health_status(
    telegram_id: int,
    x_health_secret: str = Header(default=""),
    session: AsyncSession = Depends(get_db),
):
    if settings.health_webhook_secret and x_health_secret != settings.health_webhook_secret:
        raise HTTPException(status_code=403, detail="Invalid secret")

    if telegram_id not in settings.family_member_ids:
        raise HTTPException(status_code=403, detail="Unknown family member")

    from app.modules.health.service import get_latest_metric
    result = {}
    for metric in ["weight", "steps", "heart_rate", "sleep_hours", "resting_heart_rate"]:
        record = await get_latest_metric(session, telegram_id, metric)
        if record:
            result[metric] = {
                "value": record.value,
                "unit": record.unit,
                "at": record.recorded_at.isoformat(),
                "source": record.source,
            }

    return result


@router.get("/setup-guide")
async def setup_guide():
    """Returns setup instructions as JSON for reference."""
    return {
        "webhook_url": "POST /health/webhook",
        "headers": {"X-Health-Secret": "<HEALTH_WEBHOOK_SECRET from .env>"},
        "supported_metrics": list(SUPPORTED_METRICS),
        "metric_bounds": METRIC_BOUNDS,
        "example_payload": {
            "telegram_id": settings.owner_telegram_id,
            "metrics": [
                {"metric": "weight", "value": 75.5, "unit": "kg"},
                {"metric": "steps", "value": 8432, "unit": "count"},
                {"metric": "heart_rate", "value": 72, "unit": "bpm"},
                {"metric": "sleep_hours", "value": 7.5, "unit": "hours"},
            ],
        },
    }
