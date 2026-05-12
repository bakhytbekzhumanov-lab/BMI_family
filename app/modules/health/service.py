from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from app.db.models import HealthRecord, UserProfile
import pytz
from app.core.config import settings

# How each metric should be aggregated within a day
METRIC_AGGREGATION = {
    "weight": "latest",
    "body_fat": "latest",
    "steps": "sum",
    "active_energy": "sum",
    "heart_rate": "avg",
    "resting_heart_rate": "avg",
    "hrv": "avg",
    "sleep_hours": "sum",
    "respiratory_rate": "avg",
    "blood_oxygen": "avg",
}

BMI_CATEGORIES = [
    (18.5, "Недовес 🔵"),
    (25.0, "Норма ✅"),
    (30.0, "Избыточный вес ⚠️"),
    (float("inf"), "Ожирение 🔴"),
]

_SPARK = "▁▂▃▄▅▆▇█"


def _today_start_utc() -> datetime:
    tz = pytz.timezone(settings.timezone)
    now = datetime.now(tz)
    local_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return local_midnight.astimezone(pytz.utc).replace(tzinfo=None)


def _sparkline(values: list[float]) -> str:
    if not values:
        return ""
    mn, mx = min(values), max(values)
    if mx == mn:
        return _SPARK[4] * len(values)
    return "".join(
        _SPARK[int((v - mn) / (mx - mn) * (len(_SPARK) - 1))]
        for v in values
    )


def calc_bmi(weight_kg: float, height_cm: float) -> tuple[float, str]:
    bmi = weight_kg / (height_cm / 100) ** 2
    for threshold, label in BMI_CATEGORIES:
        if bmi < threshold:
            return round(bmi, 1), label
    return round(bmi, 1), BMI_CATEGORIES[-1][1]


async def save_health_data(session: AsyncSession, telegram_id: int, metrics: list[dict]) -> int:
    count = 0
    for m in metrics:
        recorded_at = m.get("recorded_at")
        if recorded_at is None:
            recorded_at = datetime.utcnow()
        elif isinstance(recorded_at, datetime):
            if recorded_at.tzinfo is not None:
                recorded_at = recorded_at.astimezone(timezone.utc).replace(tzinfo=None)
        record = HealthRecord(
            telegram_id=telegram_id,
            metric=m["metric"],
            value=float(m["value"]),
            unit=m.get("unit", ""),
            recorded_at=recorded_at,
            source=m.get("source"),
        )
        session.add(record)
        count += 1
    await session.commit()
    return count


async def save_single_metric(
    session: AsyncSession, telegram_id: int, metric: str, value: float, unit: str = "", source: str = "manual"
) -> HealthRecord:
    record = HealthRecord(
        telegram_id=telegram_id,
        metric=metric,
        value=value,
        unit=unit,
        recorded_at=datetime.utcnow(),
        source=source,
    )
    session.add(record)
    await session.commit()
    return record


async def get_today_metric(session: AsyncSession, telegram_id: int, metric: str) -> float | None:
    today_start = _today_start_utc()
    agg = METRIC_AGGREGATION.get(metric, "avg")

    if agg == "latest":
        result = await session.execute(
            select(HealthRecord.value)
            .where(
                and_(
                    HealthRecord.telegram_id == telegram_id,
                    HealthRecord.metric == metric,
                    HealthRecord.recorded_at >= today_start,
                )
            )
            .order_by(HealthRecord.recorded_at.desc())
            .limit(1)
        )
        return result.scalar()

    agg_fn = func.sum if agg == "sum" else func.avg
    result = await session.execute(
        select(agg_fn(HealthRecord.value))
        .where(
            and_(
                HealthRecord.telegram_id == telegram_id,
                HealthRecord.metric == metric,
                HealthRecord.recorded_at >= today_start,
            )
        )
    )
    return result.scalar()


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


async def get_or_create_profile(session: AsyncSession, telegram_id: int, name: str = "") -> UserProfile:
    result = await session.execute(
        select(UserProfile).where(UserProfile.telegram_id == telegram_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        profile = UserProfile(telegram_id=telegram_id, name=name)
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
    return profile


async def update_profile_height(session: AsyncSession, telegram_id: int, height_cm: float) -> UserProfile:
    profile = await get_or_create_profile(session, telegram_id)
    profile.height_cm = height_cm
    await session.commit()
    return profile


async def build_weight_display(session: AsyncSession, telegram_id: int, label: str) -> str:
    """Build full weight info string with trend, BMI, sparkline."""
    data = await get_weight_trend(session, telegram_id, days=90)
    profile = await get_or_create_profile(session, telegram_id)

    if not data:
        lines = [
            f"⚖️ *{label}*",
            "Данных пока нет.",
            "",
            "Введи вес через кнопку *➕ Ввести вес* или настрой Apple Shortcuts.",
        ]
        return "\n".join(lines)

    latest = data[-1]
    lines = [f"⚖️ *{label}*\n"]
    lines.append(f"Последнее: *{latest['value']:.1f} кг* ({latest['date']})")

    # BMI
    if profile.height_cm:
        bmi, bmi_label = calc_bmi(latest["value"], profile.height_cm)
        lines.append(f"ИМТ: *{bmi}* — {bmi_label}")

    # Trend vs previous
    if len(data) >= 2:
        diff = data[-1]["value"] - data[-2]["value"]
        arrow = "📈" if diff > 0.05 else "📉" if diff < -0.05 else "➡️"
        lines.append(f"Изменение: {arrow} *{diff:+.1f} кг*")

    # Week trend
    if len(data) >= 2:
        week_ago_dt = data[-1]["recorded_at"] - timedelta(days=7)
        week_data = [d for d in data if d["recorded_at"] >= week_ago_dt]
        if len(week_data) >= 2:
            week_diff = week_data[-1]["value"] - week_data[0]["value"]
            lines.append(f"За неделю: *{week_diff:+.1f} кг*")

    # Sparkline (last 10 measurements)
    if len(data) >= 3:
        spark_data = data[-10:]
        spark = _sparkline([d["value"] for d in spark_data])
        first_val = spark_data[0]["value"]
        last_val = spark_data[-1]["value"]
        lines.append(f"\n`{first_val:.1f}` {spark} `{last_val:.1f}`")

    if not profile.height_cm:
        lines.append("\n_Задай рост для расчёта ИМТ: кнопка ⚙️ Настройки_")

    return "\n".join(lines)
