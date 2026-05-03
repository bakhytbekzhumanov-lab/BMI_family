from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from app.bot.keyboards.main import calendar_menu_keyboard, main_menu_keyboard
from app.bot.handlers.common import is_family_member

WAIT_EVENT_TITLE = 1
WAIT_EVENT_DATETIME = 2
WAIT_EVENT_CALENDAR = 3


async def calendar_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_family_member(update.effective_user.id):
        return
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("📅 *Календарь*", parse_mode="Markdown",
                                      reply_markup=calendar_menu_keyboard())
    else:
        await update.message.reply_text("📅 *Календарь*", parse_mode="Markdown",
                                        reply_markup=calendar_menu_keyboard())


async def show_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    from app.modules.calendar.service import get_today_events
    events = await get_today_events()
    await _send_events(query, events, "Сегодня")


async def show_tomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    from app.modules.calendar.service import get_tomorrow_events
    events = await get_tomorrow_events()
    await _send_events(query, events, "Завтра")


async def show_week(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    from app.modules.calendar.service import get_week_events
    events = await get_week_events()
    await _send_events(query, events, "На неделю")


async def _send_events(query, events: list, label: str) -> None:
    if not events:
        await query.edit_message_text(
            f"📅 *{label}:* нет событий", parse_mode="Markdown",
            reply_markup=calendar_menu_keyboard(),
        )
        return

    lines = [f"📅 *{label}:*\n"]
    for e in events:
        owner_icon = "👤" if e.get("calendar") == "owner" else "👩" if e.get("calendar") == "wife" else "👨‍👩‍👧"
        lines.append(f"{owner_icon} *{e['time']}* — {e['title']}")
        if e.get("location"):
            lines.append(f"  📍 {e['location']}")

    await query.edit_message_text(
        "\n".join(lines), parse_mode="Markdown", reply_markup=calendar_menu_keyboard()
    )


async def add_event_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("📝 Введи название события:")
    return WAIT_EVENT_TITLE


async def add_event_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["event_title"] = update.message.text.strip()
    await update.message.reply_text(
        "📅 Введи дату и время:\n"
        "Формат: *ДД.ММ ЧЧ:ММ* или *ДД.ММ.ГГГГ ЧЧ:ММ*\n"
        "Например: *15.06 14:30*",
        parse_mode="Markdown",
    )
    return WAIT_EVENT_DATETIME


async def add_event_datetime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    from datetime import datetime
    import pytz
    from app.core.config import settings

    text = update.message.text.strip()
    tz = pytz.timezone(settings.timezone)

    parsed = None
    for fmt in ("%d.%m %H:%M", "%d.%m.%Y %H:%M"):
        try:
            parsed = datetime.strptime(text, fmt)
            if parsed.year == 1900:
                parsed = parsed.replace(year=datetime.now().year)
            break
        except ValueError:
            continue

    if not parsed:
        await update.message.reply_text("❌ Неверный формат. Попробуй: *15.06 14:30*", parse_mode="Markdown")
        return WAIT_EVENT_DATETIME

    context.user_data["event_dt"] = tz.localize(parsed)

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👤 Мой", callback_data="cal_target:owner"),
            InlineKeyboardButton("👩 Жены", callback_data="cal_target:wife"),
        ],
        [InlineKeyboardButton("👨‍👩‍👧 Семейный", callback_data="cal_target:family")],
    ])
    await update.message.reply_text("📅 В какой календарь добавить?", reply_markup=keyboard)
    return WAIT_EVENT_CALENDAR


async def add_event_calendar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    target = query.data.split(":")[1]

    from app.modules.calendar.service import create_event
    event = await create_event(
        title=context.user_data["event_title"],
        start_dt=context.user_data["event_dt"],
        calendar_target=target,
    )

    context.user_data.clear()
    labels = {"owner": "👤 Мой", "wife": "👩 Жены", "family": "👨‍👩‍👧 Семейный"}
    await query.edit_message_text(
        f"✅ Событие добавлено в *{labels[target]}* календарь!",
        parse_mode="Markdown",
        reply_markup=calendar_menu_keyboard(),
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Отменено.", reply_markup=main_menu_keyboard())
    return ConversationHandler.END


def get_calendar_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(add_event_start, pattern="^cal:add$"),
        ],
        states={
            WAIT_EVENT_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_event_title)],
            WAIT_EVENT_DATETIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_event_datetime)],
            WAIT_EVENT_CALENDAR: [CallbackQueryHandler(add_event_calendar, pattern="^cal_target:")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
    )
