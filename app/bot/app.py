from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
)
from app.core.config import settings
from app.db.base import AsyncSessionLocal

from app.bot.handlers import common, baby, kitchen, household, calendar, health


def build_application() -> Application:
    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .build()
    )

    app.bot_data["db_session"] = AsyncSessionLocal

    _register_handlers(app)
    return app


def _register_handlers(app: Application) -> None:
    # Commands
    app.add_handler(CommandHandler("start", common.start))
    app.add_handler(CommandHandler("help", common.help_command))
    app.add_handler(CommandHandler("stats", common.daily_summary))
    app.add_handler(CommandHandler("baby", baby.baby_menu))
    app.add_handler(CommandHandler("calendar", calendar.calendar_menu))
    app.add_handler(CommandHandler("kitchen", kitchen.kitchen_menu))
    app.add_handler(CommandHandler("house", household.household_menu))
    app.add_handler(CommandHandler("health", health.health_menu))
    app.add_handler(CommandHandler("health_setup", health.health_setup_command))

    # Conversations (must be before generic callback handlers)
    app.add_handler(baby.get_baby_conversation())
    app.add_handler(kitchen.get_kitchen_conversation())
    app.add_handler(household.get_household_conversation())
    app.add_handler(calendar.get_calendar_conversation())
    app.add_handler(health.get_health_conversation())

    # Baby callbacks
    app.add_handler(CallbackQueryHandler(baby.baby_menu, pattern="^baby:menu$"))
    app.add_handler(CallbackQueryHandler(baby.baby_stats, pattern="^baby:stats$"))
    app.add_handler(CallbackQueryHandler(baby.feeding_start, pattern="^baby:feeding$"))
    app.add_handler(CallbackQueryHandler(baby.diaper_start, pattern="^baby:diaper$"))
    app.add_handler(CallbackQueryHandler(baby.diaper_type_chosen, pattern="^diaper:"))
    app.add_handler(CallbackQueryHandler(baby.sleep_start_menu, pattern="^baby:sleep$"))
    app.add_handler(CallbackQueryHandler(baby.sleep_begin, pattern="^sleep:start:"))
    app.add_handler(CallbackQueryHandler(baby.sleep_end, pattern="^sleep:end$"))

    # Calendar callbacks
    app.add_handler(CallbackQueryHandler(calendar.calendar_menu, pattern="^cal:menu$"))
    app.add_handler(CallbackQueryHandler(calendar.show_today, pattern="^cal:today$"))
    app.add_handler(CallbackQueryHandler(calendar.show_tomorrow, pattern="^cal:tomorrow$"))
    app.add_handler(CallbackQueryHandler(calendar.show_week, pattern="^cal:week$"))

    # Kitchen callbacks
    app.add_handler(CallbackQueryHandler(kitchen.kitchen_menu, pattern="^kitchen:menu$"))
    app.add_handler(CallbackQueryHandler(kitchen.show_stock, pattern="^kitchen:stock$"))
    app.add_handler(CallbackQueryHandler(kitchen.show_shopping_list, pattern="^kitchen:shopping$"))
    app.add_handler(CallbackQueryHandler(kitchen.show_meal_plan, pattern="^kitchen:meal_plan$"))

    # Household callbacks
    app.add_handler(CallbackQueryHandler(household.household_menu, pattern="^house:menu$"))
    app.add_handler(CallbackQueryHandler(household.my_tasks, pattern="^house:my_tasks$"))
    app.add_handler(CallbackQueryHandler(household.all_tasks, pattern="^house:all_tasks$"))
    app.add_handler(CallbackQueryHandler(household.complete_task, pattern="^house:done:"))
    app.add_handler(CallbackQueryHandler(household.household_stats, pattern="^house:stats$"))

    # Health callbacks
    app.add_handler(CallbackQueryHandler(health.health_menu, pattern="^health:menu$"))
    app.add_handler(CallbackQueryHandler(health.show_weight, pattern="^health:weight:(owner|wife)$"))
    app.add_handler(CallbackQueryHandler(health.show_steps, pattern="^health:steps$"))
    app.add_handler(CallbackQueryHandler(health.show_heart_rate, pattern="^health:heart_rate$"))
    app.add_handler(CallbackQueryHandler(health.show_sleep, pattern="^health:sleep$"))
    app.add_handler(CallbackQueryHandler(health.add_weight_who, pattern="^health:add_weight$"))
    app.add_handler(CallbackQueryHandler(health.health_settings, pattern="^health:settings$"))
    app.add_handler(CallbackQueryHandler(health.shortcuts_guide, pattern="^health:shortcuts_guide$"))

    # Main menu text buttons
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex("^👶 Малыш$"),
        baby.baby_menu,
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex("^📅 Календарь$"),
        calendar.calendar_menu,
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex("^🍽 Кухня$"),
        kitchen.kitchen_menu,
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex("^🏠 Дом$"),
        household.household_menu,
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex("^❤️ Здоровье$"),
        health.health_menu,
    ))

    # Fallback
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, common.unknown_message))
