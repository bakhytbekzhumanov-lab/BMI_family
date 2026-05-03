from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from app.bot.keyboards.main import household_menu_keyboard, main_menu_keyboard
from app.bot.handlers.common import is_family_member

WAIT_TASK_TITLE = 1
WAIT_TASK_ASSIGN = 2
WAIT_TASK_FREQ = 3


async def household_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_family_member(update.effective_user.id):
        return
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("🏠 *Задачи по дому*", parse_mode="Markdown",
                                      reply_markup=household_menu_keyboard())
    else:
        await update.message.reply_text("🏠 *Задачи по дому*", parse_mode="Markdown",
                                        reply_markup=household_menu_keyboard())


async def my_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    from app.modules.household.service import get_tasks_for_user
    async with context.bot_data["db_session"]() as session:
        tasks = await get_tasks_for_user(session, update.effective_user.id)

    if not tasks:
        await query.edit_message_text("✅ У тебя нет активных задач!", reply_markup=household_menu_keyboard())
        return

    lines = [f"📋 *Мои задачи ({len(tasks)}):*\n"]
    buttons = []
    for task in tasks:
        due = f" — до {task.due_date.strftime('%d.%m')}" if task.due_date else ""
        lines.append(f"• {task.title}{due}")
        buttons.append([InlineKeyboardButton(f"✅ {task.title[:30]}", callback_data=f"house:done:{task.id}")])

    buttons.append([InlineKeyboardButton("◀️ Назад", callback_data="house:menu")])
    await query.edit_message_text(
        "\n".join(lines), parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def all_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    from app.modules.household.service import get_all_pending_tasks
    from app.core.config import settings as s

    async with context.bot_data["db_session"]() as session:
        tasks = await get_all_pending_tasks(session)

    if not tasks:
        await query.edit_message_text("✅ Все задачи выполнены!", reply_markup=household_menu_keyboard())
        return

    lines = [f"📝 *Все задачи ({len(tasks)}):*\n"]
    for task in tasks:
        due = f" до {task.due_date.strftime('%d.%m')}" if task.due_date else ""
        assigned = "мне" if task.assigned_to == update.effective_user.id else "жене"
        lines.append(f"• [{assigned}]{due} {task.title}")

    await query.edit_message_text(
        "\n".join(lines), parse_mode="Markdown", reply_markup=household_menu_keyboard()
    )


async def complete_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    task_id = int(query.data.split(":")[2])

    from app.modules.household.service import mark_task_done
    from datetime import datetime
    async with context.bot_data["db_session"]() as session:
        await mark_task_done(session, task_id, update.effective_user.id, datetime.now())

    await query.edit_message_text("✅ Задача выполнена! Молодец 💪", reply_markup=household_menu_keyboard())


async def add_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("📝 Введи название задачи:")
    return WAIT_TASK_TITLE


async def add_task_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["task_title"] = update.message.text.strip()

    from app.core.config import settings as s
    owner_name = "Себе"
    wife_name = "Жене"

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"👤 {owner_name}", callback_data=f"assign:{s.owner_telegram_id}"),
            InlineKeyboardButton(f"👩 {wife_name}", callback_data=f"assign:{s.wife_telegram_id}"),
        ],
        [InlineKeyboardButton("👥 Обоим (любой)", callback_data="assign:0")],
    ])
    await update.message.reply_text("👤 Кому назначить?", reply_markup=keyboard)
    return WAIT_TASK_ASSIGN


async def add_task_assign(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    assigned_to = int(query.data.split(":")[1])
    context.user_data["task_assigned"] = assigned_to if assigned_to != 0 else None

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("1️⃣ Разово", callback_data="freq:once"),
            InlineKeyboardButton("📅 Ежедневно", callback_data="freq:daily"),
        ],
        [
            InlineKeyboardButton("📆 Еженедельно", callback_data="freq:weekly"),
            InlineKeyboardButton("🗓 Ежемесячно", callback_data="freq:monthly"),
        ],
    ])
    await query.edit_message_text("🔄 Как часто?", reply_markup=keyboard)
    return WAIT_TASK_FREQ


async def add_task_freq(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    freq = query.data.split(":")[1]

    from app.modules.household.service import create_task
    async with context.bot_data["db_session"]() as session:
        await create_task(
            session=session,
            title=context.user_data["task_title"],
            created_by=update.effective_user.id,
            assigned_to=context.user_data.get("task_assigned"),
            frequency=freq,
        )

    context.user_data.clear()
    await query.edit_message_text("✅ Задача создана!", reply_markup=household_menu_keyboard())
    return ConversationHandler.END


async def household_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    from app.modules.household.service import get_stats
    from app.core.config import settings as s

    async with context.bot_data["db_session"]() as session:
        stats = await get_stats(session)

    text = (
        f"📊 *Статистика по дому*\n\n"
        f"📋 Активных задач: *{stats['pending']}*\n"
        f"✅ Выполнено за месяц: *{stats['done_month']}*\n"
        f"👤 Моих выполнено: *{stats['done_owner']}*\n"
        f"👩 Жена выполнила: *{stats['done_wife']}*\n"
    )
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=household_menu_keyboard())


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Отменено.", reply_markup=main_menu_keyboard())
    return ConversationHandler.END


def get_household_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(add_task_start, pattern="^house:add$"),
        ],
        states={
            WAIT_TASK_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_task_title)],
            WAIT_TASK_ASSIGN: [CallbackQueryHandler(add_task_assign, pattern="^assign:")],
            WAIT_TASK_FREQ: [CallbackQueryHandler(add_task_freq, pattern="^freq:")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
    )
