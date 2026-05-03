from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from app.bot.keyboards.main import kitchen_menu_keyboard, main_menu_keyboard
from app.bot.handlers.common import is_family_member

WAIT_SHOPPING_ITEM = 1
WAIT_MEAL_PLAN_DATE = 2
WAIT_MEAL_PLAN_DESC = 3


async def kitchen_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_family_member(update.effective_user.id):
        return
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("🍽 *Кухня*", parse_mode="Markdown",
                                      reply_markup=kitchen_menu_keyboard())
    else:
        await update.message.reply_text("🍽 *Кухня*", parse_mode="Markdown",
                                        reply_markup=kitchen_menu_keyboard())


async def show_stock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    from app.modules.kitchen.service import get_stock
    async with context.bot_data["db_session"]() as session:
        items = await get_stock(session)

    if not items:
        await query.edit_message_text("📦 Запасы пусты.", reply_markup=kitchen_menu_keyboard())
        return

    lines = ["📦 *Запасы на кухне:*\n"]
    for item in items:
        status = "⚠️" if item.min_quantity and item.quantity <= item.min_quantity else "✅"
        lines.append(f"{status} {item.name}: *{item.quantity} {item.unit}*")

    await query.edit_message_text(
        "\n".join(lines), parse_mode="Markdown", reply_markup=kitchen_menu_keyboard()
    )


async def show_shopping_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    from app.modules.kitchen.service import get_shopping_list
    async with context.bot_data["db_session"]() as session:
        items = await get_shopping_list(session)

    pending = [i for i in items if not i.is_bought]
    bought = [i for i in items if i.is_bought]

    if not pending and not bought:
        await query.edit_message_text("🛒 Список покупок пуст.", reply_markup=kitchen_menu_keyboard())
        return

    lines = ["🛒 *Список покупок:*\n"]
    for item in pending:
        qty = f" — {item.quantity} {item.unit}" if item.quantity else ""
        lines.append(f"☐ {item.name}{qty}")

    if bought:
        lines.append(f"\n✅ Куплено: {len(bought)} позиций")

    await query.edit_message_text(
        "\n".join(lines), parse_mode="Markdown", reply_markup=kitchen_menu_keyboard()
    )


async def add_shopping_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🛒 Напиши что купить (можно несколько через запятую):\n"
        "Например: *молоко 2л, хлеб, яблоки 1кг*",
        parse_mode="Markdown",
    )
    return WAIT_SHOPPING_ITEM


async def add_shopping_items(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    items_raw = [i.strip() for i in text.split(",") if i.strip()]

    from app.modules.kitchen.service import add_shopping_items as save_items
    async with context.bot_data["db_session"]() as session:
        await save_items(session, items_raw, update.effective_user.id)

    await update.message.reply_text(
        f"✅ Добавлено в список: {len(items_raw)} позиций",
        reply_markup=kitchen_menu_keyboard(),
    )
    return ConversationHandler.END


async def show_meal_plan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    from app.modules.kitchen.service import get_week_meal_plan
    async with context.bot_data["db_session"]() as session:
        plans = await get_week_meal_plan(session)

    if not plans:
        await query.edit_message_text("🍽 План питания на неделю пуст.", reply_markup=kitchen_menu_keyboard())
        return

    lines = ["🍽 *План питания на неделю:*\n"]
    for day, meals in plans.items():
        lines.append(f"*{day}*")
        for meal in meals:
            lines.append(f"  {meal['type']}: {meal['desc']}")

    await query.edit_message_text(
        "\n".join(lines), parse_mode="Markdown", reply_markup=kitchen_menu_keyboard()
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Отменено.", reply_markup=main_menu_keyboard())
    return ConversationHandler.END


def get_kitchen_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(add_shopping_start, pattern="^kitchen:add_shopping$"),
        ],
        states={
            WAIT_SHOPPING_ITEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_shopping_items)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
    )
