from datetime import datetime
from sqlalchemy import (
    BigInteger, Boolean, DateTime, Enum, Float, ForeignKey,
    Integer, String, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
import enum


# ─── Enums ────────────────────────────────────────────────────────────────────

class FamilyRole(str, enum.Enum):
    owner = "owner"
    wife = "wife"


class FeedingType(str, enum.Enum):
    breast_left = "breast_left"
    breast_right = "breast_right"
    bottle = "bottle"
    solid = "solid"


class DiaperType(str, enum.Enum):
    wet = "wet"
    dirty = "dirty"
    both = "both"


class SleepType(str, enum.Enum):
    night = "night"
    nap = "nap"


class TaskStatus(str, enum.Enum):
    pending = "pending"
    done = "done"
    skipped = "skipped"


class TaskFrequency(str, enum.Enum):
    once = "once"
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


# ─── Family Members ───────────────────────────────────────────────────────────

class FamilyMember(Base):
    __tablename__ = "family_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100))
    role: Mapped[FamilyRole] = mapped_column(Enum(FamilyRole))
    google_calendar_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ─── Baby Tracker ─────────────────────────────────────────────────────────────

class Baby(Base):
    __tablename__ = "babies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    birth_date: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    feedings: Mapped[list["Feeding"]] = relationship(back_populates="baby")
    diapers: Mapped[list["Diaper"]] = relationship(back_populates="baby")
    sleeps: Mapped[list["Sleep"]] = relationship(back_populates="baby")
    measurements: Mapped[list["BabyMeasurement"]] = relationship(back_populates="baby")


class Feeding(Base):
    __tablename__ = "feedings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    baby_id: Mapped[int] = mapped_column(ForeignKey("babies.id"))
    recorded_by: Mapped[int] = mapped_column(BigInteger)  # telegram_id
    feeding_type: Mapped[FeedingType] = mapped_column(Enum(FeedingType))
    started_at: Mapped[datetime] = mapped_column(DateTime)
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    amount_ml: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    baby: Mapped["Baby"] = relationship(back_populates="feedings")


class Diaper(Base):
    __tablename__ = "diapers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    baby_id: Mapped[int] = mapped_column(ForeignKey("babies.id"))
    recorded_by: Mapped[int] = mapped_column(BigInteger)
    diaper_type: Mapped[DiaperType] = mapped_column(Enum(DiaperType))
    changed_at: Mapped[datetime] = mapped_column(DateTime)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    baby: Mapped["Baby"] = relationship(back_populates="diapers")


class Sleep(Base):
    __tablename__ = "sleeps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    baby_id: Mapped[int] = mapped_column(ForeignKey("babies.id"))
    recorded_by: Mapped[int] = mapped_column(BigInteger)
    sleep_type: Mapped[SleepType] = mapped_column(Enum(SleepType))
    started_at: Mapped[datetime] = mapped_column(DateTime)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    baby: Mapped["Baby"] = relationship(back_populates="sleeps")

    @property
    def duration_minutes(self) -> int | None:
        if self.ended_at:
            delta = self.ended_at - self.started_at
            return int(delta.total_seconds() / 60)
        return None


class BabyMeasurement(Base):
    __tablename__ = "baby_measurements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    baby_id: Mapped[int] = mapped_column(ForeignKey("babies.id"))
    recorded_by: Mapped[int] = mapped_column(BigInteger)
    measured_at: Mapped[datetime] = mapped_column(DateTime)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    height_cm: Mapped[float | None] = mapped_column(Float)
    head_cm: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    baby: Mapped["Baby"] = relationship(back_populates="measurements")


# ─── Apple Health ─────────────────────────────────────────────────────────────

class HealthRecord(Base):
    __tablename__ = "health_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger)
    metric: Mapped[str] = mapped_column(String(100))  # weight, steps, heart_rate, sleep, etc.
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(50))
    recorded_at: Mapped[datetime] = mapped_column(DateTime)
    source: Mapped[str | None] = mapped_column(String(100))  # Apple Watch, iPhone
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ─── Kitchen Tracker ──────────────────────────────────────────────────────────

class KitchenItem(Base):
    __tablename__ = "kitchen_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str | None] = mapped_column(String(100))
    quantity: Mapped[float] = mapped_column(Float, default=0)
    unit: Mapped[str] = mapped_column(String(50))  # kg, шт, л
    min_quantity: Mapped[float | None] = mapped_column(Float)  # alert threshold
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ShoppingList(Base):
    __tablename__ = "shopping_list"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    quantity: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(50))
    added_by: Mapped[int] = mapped_column(BigInteger)
    is_bought: Mapped[bool] = mapped_column(Boolean, default=False)
    bought_by: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MealPlan(Base):
    __tablename__ = "meal_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[datetime] = mapped_column(DateTime)
    meal_type: Mapped[str] = mapped_column(String(50))  # breakfast, lunch, dinner, snack
    description: Mapped[str] = mapped_column(Text)
    added_by: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ─── Household Tracker ────────────────────────────────────────────────────────

class HouseholdTask(Base):
    __tablename__ = "household_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    assigned_to: Mapped[int | None] = mapped_column(BigInteger)
    created_by: Mapped[int] = mapped_column(BigInteger)
    frequency: Mapped[TaskFrequency] = mapped_column(Enum(TaskFrequency), default=TaskFrequency.once)
    due_date: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.pending)
    completed_by: Mapped[int | None] = mapped_column(BigInteger)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    next_due: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
