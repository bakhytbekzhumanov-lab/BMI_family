import re
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.db.models import KitchenItem, ShoppingList, MealPlan
import pytz
from app.core.config import settings


def _parse_shopping_item(raw: str) -> tuple[str, float | None, str | None]:
    """Parse 'молоко 2л' → ('молоко', 2.0, 'л')"""
    pattern = r"^(.+?)\s+([\d.]+)\s*([а-яёa-z]+)?$"
    match = re.match(pattern, raw.strip(), re.IGNORECASE)
    if match:
        name = match.group(1).strip()
        qty = float(match.group(2))
        unit = match.group(3)
        return name, qty, unit
    return raw.strip(), None, None


async def get_stock(session: AsyncSession) -> list[KitchenItem]:
    result = await session.execute(
        select(KitchenItem).where(KitchenItem.is_active == True).order_by(KitchenItem.category, KitchenItem.name)
    )
    return result.scalars().all()


async def get_shopping_list(session: AsyncSession) -> list[ShoppingList]:
    result = await session.execute(
        select(ShoppingList).order_by(ShoppingList.is_bought, ShoppingList.created_at.desc())
    )
    return result.scalars().all()


async def add_shopping_items(session: AsyncSession, items_raw: list[str], added_by: int) -> list[ShoppingList]:
    created = []
    for raw in items_raw:
        name, qty, unit = _parse_shopping_item(raw)
        item = ShoppingList(
            name=name,
            quantity=qty,
            unit=unit,
            added_by=added_by,
        )
        session.add(item)
        created.append(item)
    await session.commit()
    return created


async def mark_shopping_item_bought(session: AsyncSession, item_id: int, bought_by: int) -> ShoppingList | None:
    result = await session.execute(select(ShoppingList).where(ShoppingList.id == item_id))
    item = result.scalar_one_or_none()
    if item:
        item.is_bought = True
        item.bought_by = bought_by
        await session.commit()
    return item


async def clear_bought_items(session: AsyncSession) -> int:
    result = await session.execute(select(ShoppingList).where(ShoppingList.is_bought == True))
    items = result.scalars().all()
    count = len(items)
    for item in items:
        await session.delete(item)
    await session.commit()
    return count


async def get_week_meal_plan(session: AsyncSession) -> dict:
    tz = pytz.timezone(settings.timezone)
    today = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)
    week_end = today + timedelta(days=7)

    result = await session.execute(
        select(MealPlan)
        .where(and_(MealPlan.date >= today, MealPlan.date < week_end))
        .order_by(MealPlan.date, MealPlan.meal_type)
    )
    plans = result.scalars().all()

    meal_type_labels = {
        "breakfast": "🌅 Завтрак",
        "lunch": "☀️ Обед",
        "dinner": "🌙 Ужин",
        "snack": "🍎 Перекус",
    }

    by_day: dict[str, list] = {}
    for plan in plans:
        day_key = plan.date.strftime("%a %d.%m")
        if day_key not in by_day:
            by_day[day_key] = []
        by_day[day_key].append({
            "type": meal_type_labels.get(plan.meal_type, plan.meal_type),
            "desc": plan.description,
        })

    return by_day


async def add_meal_plan(
    session: AsyncSession, date: datetime, meal_type: str, description: str, added_by: int
) -> MealPlan:
    plan = MealPlan(date=date, meal_type=meal_type, description=description, added_by=added_by)
    session.add(plan)
    await session.commit()
    return plan


async def update_stock_item(
    session: AsyncSession, name: str, quantity: float, unit: str, category: str | None = None,
    min_quantity: float | None = None,
) -> KitchenItem:
    result = await session.execute(
        select(KitchenItem).where(KitchenItem.name.ilike(name))
    )
    item = result.scalar_one_or_none()
    if item:
        item.quantity = quantity
        item.unit = unit
    else:
        item = KitchenItem(
            name=name, quantity=quantity, unit=unit,
            category=category, min_quantity=min_quantity,
        )
        session.add(item)
    await session.commit()
    return item
