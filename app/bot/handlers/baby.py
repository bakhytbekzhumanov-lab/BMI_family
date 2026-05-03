from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from app.bot.keyboards.main import (
    baby_menu_keyboard, feeding_type_keyboard,
    diaper_type_keyboard, sleep_action_keyboard, main_menu_keyboard,
)
from app.bot.handlers.common import is_family_member
from app.core.config import settings
import pytz

WAIT_FEEDING_DURATION = 1
WAIT_BOTTLE_AMOUNT = 2
WAIT_MEASURE_WEIGHT = 3
WAIT_MEASURE_HEIGHT = 4

tz = pytz.timezone(settings.timezone)


def now_local() -> datetime:
    return datetime.now(tz).replace(tzinfo=None)


async def baby_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_family_member(update.effective_user.id):
        return

    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("👶 *Трекер малыша*", parse_mode="Markdown",
                                      reply_markup=baby_menu_keyboard())
    else:
        await update.message.reply_text("👶 *Трекер малыша*", parse_mode="Markdown",
                                        reply_markup=baby_menu_keyboard())


async def baby_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    from app.modules.baby.service import get_today_stats
    async with context.bot_data["db_session"]() as session:
        stats = await get_today_stats(session)

    if not stats:
        await query.edit_message_text("Нет данных за сегодня.", reply_markup=baby_menu_keyboard())
        return

    last_feed = stats.get("last_feeding_ago", "?")
    text = (
        f"📊 *Статистика за сегодня*\n\n"
        f"🍼 Кормлений: *{stats['feedings']}*\n"
        f"🚼 Подгузников: *{stats['diapers']}*\n"
        f"💤 Сон: *{stats['sleep_hours']:.1f} ч*\n"
        f"⏱ Последнее кормление: *{last_feed} мин назад*\n"
    )
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=baby_menu_keyboard())


async def feeding_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🍼 Выбери тип кормления:", reply_markup=feeding_type_keyboard())


async def feeding_type_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    feed_type = query.data.split(":")[1]
    context.user_data["feeding_type"] = feed_type
    context.user_data["feeding_start"] = now_local()

    if feed_type == "bottle":
        await query.edit_message_text("🍼 Сколько мл выпил? (введи число)")
        return WAIT_BOTTLE_AMOUNT

    await query.edit_message_text("⏱ Сколько минут кормил? (введи число или 0)")
    return WAIT_FEEDING_DURATION


async def feeding_bottle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        amount = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Введи число, например: 120")
        return WAIT_BOTTLE_AMOUNT

    context.user_data["bottle_amount"] = amount
    await update.message.reply_text("⏱ Сколько минут длилось кормление? (введи 0 если не знаешь)")
    return WAIT_FEEDING_DURATION


async def feeding_duration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        minutes = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Введи число минут, например: 15")
        return WAIT_FEEDING_DURATION

    from app.modules.baby.service import record_feeding
    async with context.bot_data["db_session"]() as session:
        await record_feeding(
            session=session,
            telegram_id=update.effective_user.id,
            feeding_type=context.user_data["feeding_type"],
            started_at=context.user_data["feeding_start"],
            duration_minutes=minutes if minutes > 0 else None,
            amount_ml=context.user_data.pop("bottle_amount", None),
        )

    await update.message.reply_text(
        "✅ Кормление записано!",
        reply_markup=baby_menu_keyboard(),
    )
    context.user_data.clear()
    return ConversationHandler.END


async def diaper_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🚼 Какой подгузник?", reply_markup=diaper_type_keyboard())


async def diaper_type_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    diaper_type = query.data.split(":")[1]

    from app.modules.baby.service import record_diaper
    async with context.bot_data["db_session"]() as session:
        await record_diaper(
            session=session,
            telegram_id=update.effective_user.id,
            diaper_type=diaper_type,
            changed_at=now_local(),
        )

    type_labels = {"wet": "💧 Мокрый", "dirty": "💩 Грязный", "both": "💧💩 Оба"}
    await query.edit_message_text(
        f"✅ Подгузник записан: {type_labels.get(diaper_type, diaper_type)}",
        reply_markup=baby_menu_keyboard(),
    )


async def sleep_start_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    from app.modules.baby.service import get_active_sleep
    async with context.bot_data["db_session"]() as session:
        active = await get_active_sleep(session)

    await query.edit_message_text(
        "💤 Управление сном:",
        reply_markup=sleep_action_keyboard(sleep_active=active is not None),
    )


async def sleep_begin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    sleep_type = query.data.split(":")[2]

    from app.modules.baby.service import start_sleep
    async with context.bot_data["db_session"]() as session:
        await start_sleep(
            session=session,
            telegram_id=update.effective_user.id,
            sleep_type=sleep_type,
            started_at=now_local(),
        )

    label = "🌙 Ночной" if sleep_type == "night" else "😴 Дневной"
    await query.edit_message_text(f"✅ {label} сон начат!", reply_markup=baby_menu_keyboard())


async def sleep_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    from app.modules.baby.service import end_sleep
    async with context.bot_data["db_session"]() as session:
        sleep = await end_sleep(session=session, ended_at=now_local())

    if sleep and sleep.duration_minutes:
        h, m = divmod(sleep.duration_minutes, 60)
        await query.edit_message_text(
            f"✅ Сон завершён. Длительность: *{h}ч {m}мин*",
            parse_mode="Markdown",
            reply_markup=baby_menu_keyboard(),
        )
    else:
        await query.edit_message_text("✅ Сон завершён.", reply_markup=baby_menu_keyboard())


async def measure_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("⚖️ Введи вес малыша в кг (например: 6.2) или 0 чтобы пропустить:")
    return WAIT_MEASURE_WEIGHT


async def measure_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        weight = float(update.message.text.strip())
        context.user_data["measure_weight"] = weight if weight > 0 else None
    except ValueError:
        await update.message.reply_text("Введи число, например: 6.2")
        return WAIT_MEASURE_WEIGHT

    await update.message.reply_text("📏 Введи рост в см (например: 62.5) или 0 чтобы пропустить:")
    return WAIT_MEASURE_HEIGHT


async def measure_height(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        height = float(update.message.text.strip())
        context.user_data["measure_height"] = height if height > 0 else None
    except ValueError:
        await update.message.reply_text("Введи число, например: 62.5")
        return WAIT_MEASURE_HEIGHT

    from app.modules.baby.service import record_measurement
    async with context.bot_data["db_session"]() as session:
        await record_measurement(
            session=session,
            telegram_id=update.effective_user.id,
            measured_at=now_local(),
            weight_kg=context.user_data.pop("measure_weight", None),
            height_cm=context.user_data.pop("measure_height", None),
        )

    await update.message.reply_text("✅ Измерения записаны!", reply_markup=baby_menu_keyboard())
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Отменено.", reply_markup=main_menu_keyboard())
    return ConversationHandler.END


def get_baby_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(feeding_type_chosen, pattern="^feed:"),
            CallbackQueryHandler(measure_start, pattern="^baby:measure$"),
        ],
        states={
            WAIT_FEEDING_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, feeding_duration)],
            WAIT_BOTTLE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, feeding_bottle_amount)],
            WAIT_MEASURE_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, measure_weight)],
            WAIT_MEASURE_HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, measure_height)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
    )
