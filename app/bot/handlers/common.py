from telegram import Update
from telegram.ext import ContextTypes
from app.bot.keyboards.main import main_menu_keyboard
from app.core.config import settings


def is_family_member(telegram_id: int) -> bool:
    return telegram_id in settings.family_member_ids


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_family_member(update.effective_user.id):
        await update.message.reply_text("❌ Доступ запрещён.")
        return

    name = update.effective_user.first_name
    await update.message.reply_text(
        f"Привет, {name}! 👋\n\nДобро пожаловать в семейный помощник.\nВыбери раздел:",
        reply_markup=main_menu_keyboard(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_family_member(update.effective_user.id):
        return

    text = (
        "📖 *Команды:*\n\n"
        "👶 *Малыш* — кормления, сон, подгузники, измерения\n"
        "📅 *Календарь* — события в Google Calendar\n"
        "🍽 *Кухня* — запасы, список покупок, план питания\n"
        "🏠 *Дом* — задачи по дому\n"
        "❤️ *Здоровье* — данные Apple Health\n\n"
        "/start — главное меню\n"
        "/stats — сводка за день\n"
        "/baby — трекер малыша\n"
        "/calendar — календарь\n"
        "/kitchen — кухня\n"
        "/house — задачи по дому\n"
        "/health — здоровье\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def daily_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_family_member(update.effective_user.id):
        return

    from app.modules.baby.service import get_today_stats
    from app.modules.calendar.service import get_today_events
    from app.modules.household.service import get_pending_tasks

    async with context.bot_data["db_session"]() as session:
        baby_stats = await get_today_stats(session)
        events = await get_today_events()
        tasks = await get_pending_tasks(session)

    lines = ["📊 *Сводка на сегодня*\n"]

    if baby_stats:
        lines.append(
            f"👶 *Малыш*\n"
            f"  Кормлений: {baby_stats['feedings']}\n"
            f"  Подгузников: {baby_stats['diapers']}\n"
            f"  Сон: {baby_stats['sleep_hours']:.1f} ч\n"
        )

    if events:
        lines.append("📅 *События:*")
        for e in events[:5]:
            lines.append(f"  • {e['time']} — {e['title']}")
        lines.append("")

    if tasks:
        lines.append(f"🏠 *Задачи* ({len(tasks)} ожидает)")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_family_member(update.effective_user.id):
        return
    await update.message.reply_text(
        "Не понял 🤔 Используй меню или /help",
        reply_markup=main_menu_keyboard(),
    )
