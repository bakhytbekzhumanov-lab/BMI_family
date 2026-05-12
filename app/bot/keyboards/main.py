from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    buttons = [
        ["👶 Малыш", "📅 Календарь"],
        ["🍽 Кухня", "🏠 Дом"],
        ["❤️ Здоровье", "⚙️ Настройки"],
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


def baby_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton("🍼 Кормление", callback_data="baby:feeding"),
            InlineKeyboardButton("💤 Сон", callback_data="baby:sleep"),
        ],
        [
            InlineKeyboardButton("🚼 Подгузник", callback_data="baby:diaper"),
            InlineKeyboardButton("📏 Измерения", callback_data="baby:measure"),
        ],
        [InlineKeyboardButton("📊 Статистика сегодня", callback_data="baby:stats")],
    ]
    return InlineKeyboardMarkup(buttons)


def feeding_type_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton("◀️ Левая грудь", callback_data="feed:breast_left"),
            InlineKeyboardButton("▶️ Правая грудь", callback_data="feed:breast_right"),
        ],
        [
            InlineKeyboardButton("🍼 Бутылочка", callback_data="feed:bottle"),
            InlineKeyboardButton("🥣 Прикорм", callback_data="feed:solid"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def diaper_type_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton("💧 Мокрый", callback_data="diaper:wet"),
            InlineKeyboardButton("💩 Грязный", callback_data="diaper:dirty"),
            InlineKeyboardButton("💧💩 Оба", callback_data="diaper:both"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def sleep_action_keyboard(sleep_active: bool = False) -> InlineKeyboardMarkup:
    if sleep_active:
        buttons = [[InlineKeyboardButton("⏹ Проснулся", callback_data="sleep:end")]]
    else:
        buttons = [
            [
                InlineKeyboardButton("🌙 Ночной", callback_data="sleep:start:night"),
                InlineKeyboardButton("😴 Дневной", callback_data="sleep:start:nap"),
            ]
        ]
    return InlineKeyboardMarkup(buttons)


def kitchen_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton("📦 Запасы", callback_data="kitchen:stock"),
            InlineKeyboardButton("🛒 Список покупок", callback_data="kitchen:shopping"),
        ],
        [
            InlineKeyboardButton("🍽 План питания", callback_data="kitchen:meal_plan"),
            InlineKeyboardButton("➕ Добавить в список", callback_data="kitchen:add_shopping"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def household_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton("📋 Мои задачи", callback_data="house:my_tasks"),
            InlineKeyboardButton("📝 Все задачи", callback_data="house:all_tasks"),
        ],
        [
            InlineKeyboardButton("➕ Новая задача", callback_data="house:add"),
            InlineKeyboardButton("📊 Статистика", callback_data="house:stats"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def calendar_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton("📅 Сегодня", callback_data="cal:today"),
            InlineKeyboardButton("📆 Завтра", callback_data="cal:tomorrow"),
        ],
        [
            InlineKeyboardButton("📅 Неделя", callback_data="cal:week"),
            InlineKeyboardButton("➕ Добавить событие", callback_data="cal:add"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def health_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton("⚖️ Мой вес", callback_data="health:weight:owner"),
            InlineKeyboardButton("⚖️ Вес жены", callback_data="health:weight:wife"),
        ],
        [
            InlineKeyboardButton("👣 Шаги сегодня", callback_data="health:steps"),
            InlineKeyboardButton("❤️ Пульс", callback_data="health:heart_rate"),
        ],
        [
            InlineKeyboardButton("😴 Сон", callback_data="health:sleep"),
            InlineKeyboardButton("➕ Ввести вес", callback_data="health:add_weight"),
        ],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="health:settings")],
    ]
    return InlineKeyboardMarkup(buttons)


def health_settings_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton("📏 Мой рост", callback_data="health:set_height:owner"),
            InlineKeyboardButton("📏 Рост жены", callback_data="health:set_height:wife"),
        ],
        [InlineKeyboardButton("📱 Настройка Shortcuts", callback_data="health:shortcuts_guide")],
        [InlineKeyboardButton("◀️ Назад", callback_data="health:menu")],
    ]
    return InlineKeyboardMarkup(buttons)


def weight_who_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👤 Мой", callback_data="health:add_weight:owner"),
            InlineKeyboardButton("👩 Жены", callback_data="health:add_weight:wife"),
        ],
        [InlineKeyboardButton("◀️ Назад", callback_data="health:menu")],
    ])


def confirm_keyboard(yes_data: str, no_data: str = "cancel") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Да", callback_data=yes_data),
            InlineKeyboardButton("❌ Нет", callback_data=no_data),
        ]
    ])
