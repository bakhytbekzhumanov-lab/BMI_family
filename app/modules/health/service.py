from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from app.db.models import HealthRecord
import pytz
from app.core.config import settings


def _today_start() -> datetime:
    tz = pytz.timezone(settings.timezone)
    now = datetime.now(tz)
    return now.replace(hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)


async def save_health_data(session: AsyncSession, telegram_id: int, metrics: list[dict]) -> int:
    """Save batch of health metrics from Apple Health / Shortcuts webhook."""
    count = 0
    for m in metrics:
        record = HealthRecord(
            telegram_id=telegram_id,
            metric=m["metric"],
            value=float(m["value"]),
            unit=m.get("unit", ""),
            recorded_at=m.get("recorded_at", datetime.utcnow()),
            source=m.get("source"),
        )
        session.add(record)
        count += 1
    await session.commit()
    return count


async def get_weight_trend(session: AsyncSession, telegram_id: int, days: int = 30) -> list[dict]:
    since = datetime.utcnow() - timedelta(days=days)
    result = await session.execute(
        select(HealthRecord)
        .where(
            and_(
                HealthRecord.telegram_id == telegram_id,
                HealthRecord.metric == "weight",
                HealthRecord.recorded_at >= since,
            )
        )
        .order_by(HealthRecord.recorded_at)
    )
    records = result.scalars().all()
    tz = pytz.timezone(settings.timezone)
    return [
        {
            "value": r.value,
            "date": r.recorded_at.strftime("%d.%m"),
            "recorded_at": r.recorded_at,
        }
        for r in records
    ]


async def get_today_metric(session: AsyncSession, telegram_id: int, metric: str) -> float | None:
    today_start = _today_start()
    result = await session.execute(
        select(func.avg(HealthRecord.value))
        .where(
            and_(
                HealthRecord.telegram_id == telegram_id,
                HealthRecord.metric == metric,
                HealthRecord.recorded_at >= today_start,
            )
        )
    )
    return result.scalar()


async def get_latest_metric(session: AsyncSession, telegram_id: int, metric: str) -> HealthRecord | None:
    result = await session.execute(
        select(HealthRecord)
        .where(
            and_(
                HealthRecord.telegram_id == telegram_id,
                HealthRecord.metric == metric,
            )
        )
        .order_by(HealthRecord.recorded_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
