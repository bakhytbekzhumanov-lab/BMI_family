from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from app.db.models import Baby, Feeding, Diaper, Sleep, BabyMeasurement, FeedingType, DiaperType, SleepType
import pytz
from app.core.config import settings


def _today_start() -> datetime:
    tz = pytz.timezone(settings.timezone)
    now = datetime.now(tz)
    return now.replace(hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)


async def _get_or_create_baby(session: AsyncSession) -> Baby:
    result = await session.execute(select(Baby).limit(1))
    baby = result.scalar_one_or_none()
    if not baby:
        baby = Baby(name="Малыш", birth_date=datetime.now())
        session.add(baby)
        await session.commit()
        await session.refresh(baby)
    return baby


async def record_feeding(
    session: AsyncSession,
    telegram_id: int,
    feeding_type: str,
    started_at: datetime,
    duration_minutes: int | None = None,
    amount_ml: float | None = None,
    notes: str | None = None,
) -> Feeding:
    baby = await _get_or_create_baby(session)
    feeding = Feeding(
        baby_id=baby.id,
        recorded_by=telegram_id,
        feeding_type=FeedingType(feeding_type),
        started_at=started_at,
        duration_minutes=duration_minutes,
        amount_ml=amount_ml,
        notes=notes,
    )
    session.add(feeding)
    await session.commit()
    return feeding


async def record_diaper(
    session: AsyncSession,
    telegram_id: int,
    diaper_type: str,
    changed_at: datetime,
    notes: str | None = None,
) -> Diaper:
    baby = await _get_or_create_baby(session)
    diaper = Diaper(
        baby_id=baby.id,
        recorded_by=telegram_id,
        diaper_type=DiaperType(diaper_type),
        changed_at=changed_at,
        notes=notes,
    )
    session.add(diaper)
    await session.commit()
    return diaper


async def start_sleep(
    session: AsyncSession,
    telegram_id: int,
    sleep_type: str,
    started_at: datetime,
) -> Sleep:
    baby = await _get_or_create_baby(session)
    sleep = Sleep(
        baby_id=baby.id,
        recorded_by=telegram_id,
        sleep_type=SleepType(sleep_type),
        started_at=started_at,
    )
    session.add(sleep)
    await session.commit()
    return sleep


async def get_active_sleep(session: AsyncSession) -> Sleep | None:
    result = await session.execute(
        select(Sleep).where(Sleep.ended_at.is_(None)).order_by(Sleep.started_at.desc()).limit(1)
    )
    return result.scalar_one_or_none()


async def end_sleep(session: AsyncSession, ended_at: datetime) -> Sleep | None:
    sleep = await get_active_sleep(session)
    if not sleep:
        return None
    sleep.ended_at = ended_at
    await session.commit()
    await session.refresh(sleep)
    return sleep


async def record_measurement(
    session: AsyncSession,
    telegram_id: int,
    measured_at: datetime,
    weight_kg: float | None = None,
    height_cm: float | None = None,
    head_cm: float | None = None,
) -> BabyMeasurement:
    baby = await _get_or_create_baby(session)
    m = BabyMeasurement(
        baby_id=baby.id,
        recorded_by=telegram_id,
        measured_at=measured_at,
        weight_kg=weight_kg,
        height_cm=height_cm,
        head_cm=head_cm,
    )
    session.add(m)
    await session.commit()
    return m


async def get_today_stats(session: AsyncSession) -> dict | None:
    baby = await _get_or_create_baby(session)
    today = _today_start()

    feeding_count = await session.execute(
        select(func.count(Feeding.id)).where(
            and_(Feeding.baby_id == baby.id, Feeding.started_at >= today)
        )
    )
    feedings = feeding_count.scalar() or 0

    diaper_count = await session.execute(
        select(func.count(Diaper.id)).where(
            and_(Diaper.baby_id == baby.id, Diaper.changed_at >= today)
        )
    )
    diapers = diaper_count.scalar() or 0

    sleeps_result = await session.execute(
        select(Sleep).where(
            and_(Sleep.baby_id == baby.id, Sleep.started_at >= today, Sleep.ended_at.is_not(None))
        )
    )
    sleeps = sleeps_result.scalars().all()
    sleep_minutes = sum(s.duration_minutes or 0 for s in sleeps)

    last_feeding_result = await session.execute(
        select(Feeding)
        .where(Feeding.baby_id == baby.id)
        .order_by(Feeding.started_at.desc())
        .limit(1)
    )
    last_feeding = last_feeding_result.scalar_one_or_none()
    last_feeding_ago = None
    if last_feeding:
        delta = datetime.now() - last_feeding.started_at
        last_feeding_ago = int(delta.total_seconds() / 60)

    return {
        "feedings": feedings,
        "diapers": diapers,
        "sleep_hours": sleep_minutes / 60,
        "last_feeding_ago": last_feeding_ago,
    }
