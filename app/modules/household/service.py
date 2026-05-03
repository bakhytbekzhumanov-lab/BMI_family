from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from app.db.models import HouseholdTask, TaskStatus, TaskFrequency
from app.core.config import settings


async def get_tasks_for_user(session: AsyncSession, telegram_id: int) -> list[HouseholdTask]:
    result = await session.execute(
        select(HouseholdTask)
        .where(
            and_(
                HouseholdTask.assigned_to == telegram_id,
                HouseholdTask.status == TaskStatus.pending,
            )
        )
        .order_by(HouseholdTask.due_date.asc().nullslast(), HouseholdTask.created_at)
    )
    return result.scalars().all()


async def get_all_pending_tasks(session: AsyncSession) -> list[HouseholdTask]:
    result = await session.execute(
        select(HouseholdTask)
        .where(HouseholdTask.status == TaskStatus.pending)
        .order_by(HouseholdTask.due_date.asc().nullslast(), HouseholdTask.assigned_to)
    )
    return result.scalars().all()


async def get_pending_tasks(session: AsyncSession) -> list[HouseholdTask]:
    return await get_all_pending_tasks(session)


async def create_task(
    session: AsyncSession,
    title: str,
    created_by: int,
    assigned_to: int | None = None,
    frequency: str = "once",
    due_date: datetime | None = None,
    description: str | None = None,
) -> HouseholdTask:
    task = HouseholdTask(
        title=title,
        description=description,
        created_by=created_by,
        assigned_to=assigned_to,
        frequency=TaskFrequency(frequency),
        due_date=due_date,
        status=TaskStatus.pending,
    )
    session.add(task)
    await session.commit()
    return task


async def mark_task_done(
    session: AsyncSession, task_id: int, completed_by: int, completed_at: datetime
) -> HouseholdTask | None:
    result = await session.execute(select(HouseholdTask).where(HouseholdTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        return None

    task.status = TaskStatus.done
    task.completed_by = completed_by
    task.completed_at = completed_at

    if task.frequency != TaskFrequency.once:
        next_due = _calc_next_due(completed_at, task.frequency)
        new_task = HouseholdTask(
            title=task.title,
            description=task.description,
            created_by=task.created_by,
            assigned_to=task.assigned_to,
            frequency=task.frequency,
            due_date=next_due,
            next_due=next_due,
            status=TaskStatus.pending,
        )
        session.add(new_task)

    await session.commit()
    return task


def _calc_next_due(from_dt: datetime, frequency: TaskFrequency) -> datetime:
    if frequency == TaskFrequency.daily:
        return from_dt + timedelta(days=1)
    elif frequency == TaskFrequency.weekly:
        return from_dt + timedelta(weeks=1)
    elif frequency == TaskFrequency.monthly:
        return from_dt + timedelta(days=30)
    return from_dt


async def get_stats(session: AsyncSession) -> dict:
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    pending_count = await session.execute(
        select(func.count(HouseholdTask.id)).where(HouseholdTask.status == TaskStatus.pending)
    )

    done_month = await session.execute(
        select(func.count(HouseholdTask.id)).where(
            and_(
                HouseholdTask.status == TaskStatus.done,
                HouseholdTask.completed_at >= month_start,
            )
        )
    )

    done_owner = await session.execute(
        select(func.count(HouseholdTask.id)).where(
            and_(
                HouseholdTask.status == TaskStatus.done,
                HouseholdTask.completed_by == settings.owner_telegram_id,
                HouseholdTask.completed_at >= month_start,
            )
        )
    )

    done_wife = await session.execute(
        select(func.count(HouseholdTask.id)).where(
            and_(
                HouseholdTask.status == TaskStatus.done,
                HouseholdTask.completed_by == settings.wife_telegram_id,
                HouseholdTask.completed_at >= month_start,
            )
        )
    )

    return {
        "pending": pending_count.scalar() or 0,
        "done_month": done_month.scalar() or 0,
        "done_owner": done_owner.scalar() or 0,
        "done_wife": done_wife.scalar() or 0,
    }
