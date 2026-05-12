from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    CallbackQueryHandler, MessageHandler, filters,
)
from app.bot.keyboards.main import (
    health_menu_keyboard, health_settings_keyboard, weight_who_keyboard, main_menu_keyboard,
)
from app.bot.handlers.common import is_family_member
from app.core.config import settings

WAIT_WEIGHT_VALUE = 1
WAIT_HEIGHT_VALUE = 2


async def health_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_family_member(update.effective_user.id):
        return
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "❤️ *Здоровье*", parse_mode="Markdown", reply_markup=health_menu_keyboard()
        )
    else:
        await update.message.reply_text(
            "❤️ *Здоровье*", parse_mode="Markdown", reply_markup=health_menu_keyboard()
        )


async def show_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    who = query.data.split(":")[2]
    telegram_id = settings.owner_telegram_id if who == "owner" else settings.wife_telegram_id
    label = "Мой вес" if who == "owner" else "Вес жены"

    from app.modules.health.service import build_weight_display
    async with context.bot_data["db_session"]() as session:
        text = await build_weight_display(session, telegram_id, label)

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=health_menu_keyboard())


async def show_steps(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    from app.modules.health.service import get_today_metric
    results = []
    async with context.bot_data["db_session"]() as session:
        for who, tid in [("Я", settings.owner_telegram_id), ("Жена", settings.wife_telegram_id)]:
            val = await get_today_metric(session, tid, "steps")
            icon = "👤" if who == "Я" else "👩"
            steps_str = f"{int(val):,}".replace(",", " ") if val else "—"
            results.append(f"{icon} *{who}*: {steps_str} шагов")

    text = "👣 *Шаги сегодня:*\n\n" + "\n".join(results)
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=health_menu_keyboard())


async def show_heart_rate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    from app.modules.health.service import get_today_metric, get_latest_metric
    results = []
    async with context.bot_data["db_session"]() as session:
        for who, tid in [("Я", settings.owner_telegram_id), ("Жена", settings.wife_telegram_id)]:
            avg_val = await get_today_metric(session, tid, "heart_rate")
            resting = await get_latest_metric(session, tid, "resting_heart_rate")
            icon = "👤" if who == "Я" else "👩"
            line = f"{icon} *{who}*: {int(avg_val) if avg_val else '—'} уд/мин"
            if resting:
                line += f" (покой: {int(resting.value)})"
            results.append(line)

    text = "❤️ *Пульс:*\n\n" + "\n".join(results)
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=health_menu_keyboard())


async def show_sleep(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    from app.modules.health.service import get_today_metric
    results = []
    async with context.bot_data["db_session"]() as session:
        for who, tid in [("Я", settings.owner_telegram_id), ("Жена", settings.wife_telegram_id)]:
            val = await get_today_metric(session, tid, "sleep_hours")
            icon = "👤" if who == "Я" else "👩"
            if val:
                h = int(val)
                m = int((val - h) * 60)
                sleep_str = f"{h}ч {m}мин"
                emoji = "😴" if val >= 7 else "😵" if val < 5 else "😐"
                results.append(f"{icon} *{who}*: {sleep_str} {emoji}")
            else:
                results.append(f"{icon} *{who}*: —")

    text = "😴 *Сон:*\n\n" + "\n".join(results)
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=health_menu_keyboard())


# ─── Manual weight entry ──────────────────────────────────────────────────────

async def add_weight_who(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("⚖️ Чей вес вводим?", reply_markup=weight_who_keyboard())


async def add_weight_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    who = query.data.split(":")[3]
    context.user_data["weight_for"] = who
    label = "твой" if who == "owner" else "жены"
    await query.edit_message_text(f"⚖️ Введи {label} вес в кг (например: *75.4*):", parse_mode="Markdown")
    return WAIT_WEIGHT_VALUE


async def add_weight_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().replace(",", ".")
    try:
        value = float(text)
        if not (20 <= value <= 300):
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Некорректный вес. Введи число от 20 до 300:")
        return WAIT_WEIGHT_VALUE

    who = context.user_data.pop("weight_for", "owner")
    telegram_id = settings.owner_telegram_id if who == "owner" else settings.wife_telegram_id
    label = "Мой вес" if who == "owner" else "Вес жены"

    from app.modules.health.service import save_single_metric, build_weight_display
    async with context.bot_data["db_session"]() as session:
        await save_single_metric(session, telegram_id, "weight", value, "kg", "manual")
        display = await build_weight_display(session, telegram_id, label)

    await update.message.reply_text(
        f"✅ Вес сохранён: *{value:.1f} кг*\n\n{display}",
        parse_mode="Markdown",
        reply_markup=health_menu_keyboard(),
    )
    return ConversationHandler.END


# ─── Profile settings (height) ───────────────────────────────────────────────

async def health_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "⚙️ *Настройки здоровья*", parse_mode="Markdown",
        reply_markup=health_settings_keyboard(),
    )


async def set_height_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    who = query.data.split(":")[3]
    context.user_data["height_for"] = who
    label = "твой" if who == "owner" else "жены"
    await query.edit_message_text(f"📏 Введи {label} рост в см (например: *175*):", parse_mode="Markdown")
    return WAIT_HEIGHT_VALUE


async def set_height_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().replace(",", ".")
    try:
        value = float(text)
        if not (100 <= value <= 250):
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Некорректный рост. Введи число от 100 до 250:")
        return WAIT_HEIGHT_VALUE

    who = context.user_data.pop("height_for", "owner")
    telegram_id = settings.owner_telegram_id if who == "owner" else settings.wife_telegram_id

    from app.modules.health.service import update_profile_height
    async with context.bot_data["db_session"]() as session:
        await update_profile_height(session, telegram_id, value)

    await update.message.reply_text(
        f"✅ Рост сохранён: *{value:.0f} см*\nТеперь будет показываться ИМТ.",
        parse_mode="Markdown",
        reply_markup=health_menu_keyboard(),
    )
    return ConversationHandler.END


# ─── Apple Shortcuts setup guide ─────────────────────────────────────────────

async def shortcuts_guide(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    webhook_url = f"{settings.telegram_webhook_url.rstrip('/health')}/health/webhook" if settings.telegram_webhook_url else "https://ТВОЙ_ДОМЕН/health/webhook"
    secret = settings.health_webhook_secret or "задай в .env → HEALTH_WEBHOOK_SECRET"

    text = (
        "📱 *Настройка Apple Shortcuts*\n\n"
        "*Шаг 1.* Установи приложение **Health Auto Export** в App Store\n\n"
        "*Шаг 2.* В настройках приложения:\n"
        "  • Export URL: `" + webhook_url + "`\n"
        "  • Header: `X-Health-Secret: " + secret + "`\n"
        "  • Metrics: weight, steps, heart\\_rate, sleep\\_hours\n"
        "  • telegram\\_id: твой ID (у тебя: `" + str(settings.owner_telegram_id) + "`)\n\n"
        "*Шаг 3.* Или вручную через Shortcuts:\n"
        "  • Создай автоматизацию «Каждый день в 08:00»\n"
        "  • Добавь шаг «Получить данные здоровья»\n"
        "  • Добавь шаг «Запрос URL» (POST)\n\n"
        "*Формат JSON:*\n"
        "```\n"
        "{\n"
        '  "telegram_id": ' + str(settings.owner_telegram_id) + ',\n'
        '  "metrics": [\n'
        '    {"metric": "weight", "value": 75.5, "unit": "kg"},\n'
        '    {"metric": "steps", "value": 8432, "unit": "count"},\n'
        '    {"metric": "heart_rate", "value": 72, "unit": "bpm"},\n'
        '    {"metric": "sleep_hours", "value": 7.5, "unit": "hours"}\n'
        '  ]\n'
        "}\n"
        "```\n\n"
        "Жена использует её `telegram_id`: `" + str(settings.wife_telegram_id) + "`"
    )
    await query.edit_message_text(
        text, parse_mode="Markdown", reply_markup=health_settings_keyboard()
    )


async def health_setup_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_family_member(update.effective_user.id):
        return
    webhook_url = f"{settings.telegram_webhook_url.rstrip('/health')}/health/webhook" if settings.telegram_webhook_url else "https://ТВОЙ_ДОМЕН/health/webhook"
    text = (
        "📱 *Настройка Apple Health*\n\n"
        f"Webhook URL:\n`{webhook_url}`\n\n"
        "Открой раздел ❤️ Здоровье → ⚙️ Настройки → 📱 Настройка Shortcuts\n"
        "для полной инструкции."
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=health_menu_keyboard())


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Отменено.", reply_markup=main_menu_keyboard())
    return ConversationHandler.END


def get_health_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(add_weight_start, pattern="^health:add_weight:(owner|wife)$"),
            CallbackQueryHandler(set_height_start, pattern="^health:set_height:(owner|wife)$"),
        ],
        states={
            WAIT_WEIGHT_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_weight_value)],
            WAIT_HEIGHT_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_height_value)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
    )
