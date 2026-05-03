from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from app.bot.keyboards.main import health_menu_keyboard
from app.bot.handlers.common import is_family_member
from app.core.config import settings


async def health_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_family_member(update.effective_user.id):
        return
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("❤️ *Здоровье*", parse_mode="Markdown",
                                      reply_markup=health_menu_keyboard())
    else:
        await update.message.reply_text("❤️ *Здоровье*", parse_mode="Markdown",
                                        reply_markup=health_menu_keyboard())


async def show_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    parts = query.data.split(":")
    who = parts[2]  # owner or wife

    telegram_id = settings.owner_telegram_id if who == "owner" else settings.wife_telegram_id
    label = "Мой вес" if who == "owner" else "Вес жены"

    from app.modules.health.service import get_weight_trend
    async with context.bot_data["db_session"]() as session:
        data = await get_weight_trend(session, telegram_id)

    if not data:
        await query.edit_message_text(
            f"⚖️ *{label}*\nДанных пока нет.\n\n"
            "Для синхронизации используй Apple Shortcuts → Health Auto Export",
            parse_mode="Markdown",
            reply_markup=health_menu_keyboard(),
        )
        return

    latest = data[-1]
    lines = [f"⚖️ *{label}*\n"]
    lines.append(f"Последнее: *{latest['value']:.1f} кг* ({latest['date']})")

    if len(data) >= 2:
        diff = data[-1]["value"] - data[-2]["value"]
        arrow = "📈" if diff > 0 else "📉" if diff < 0 else "➡️"
        lines.append(f"Изменение: {arrow} {diff:+.1f} кг")

    if len(data) >= 7:
        week_data = data[-7:]
        avg = sum(d["value"] for d in week_data) / len(week_data)
        lines.append(f"Среднее за неделю: *{avg:.1f} кг*")

    await query.edit_message_text(
        "\n".join(lines), parse_mode="Markdown", reply_markup=health_menu_keyboard()
    )


async def show_steps(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    from app.modules.health.service import get_today_metric

    results = []
    async with context.bot_data["db_session"]() as session:
        for who, tid in [("Я", settings.owner_telegram_id), ("Жена", settings.wife_telegram_id)]:
            val = await get_today_metric(session, tid, "steps")
            results.append(f"{'👤' if who == 'Я' else '👩'} *{who}*: {int(val) if val else '—'} шагов")

    text = "👣 *Шаги сегодня:*\n\n" + "\n".join(results)
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=health_menu_keyboard())


async def show_heart_rate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    from app.modules.health.service import get_today_metric

    results = []
    async with context.bot_data["db_session"]() as session:
        for who, tid in [("Я", settings.owner_telegram_id), ("Жена", settings.wife_telegram_id)]:
            val = await get_today_metric(session, tid, "heart_rate")
            results.append(f"{'👤' if who == 'Я' else '👩'} *{who}*: {int(val) if val else '—'} уд/мин")

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
            results.append(f"{'👤' if who == 'Я' else '👩'} *{who}*: {f'{val:.1f} ч' if val else '—'}")

    text = "😴 *Сон:*\n\n" + "\n".join(results)
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=health_menu_keyboard())
