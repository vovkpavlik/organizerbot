from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Основное меню
MAIN_MENU = InlineKeyboardMarkup([
    [InlineKeyboardButton("Добавить задачу", callback_data="add_task")],
    [InlineKeyboardButton("Мои задачи", callback_data="my_tasks")]
])

# Кнопка "Обратно в меню"
BACK_TO_MENU = InlineKeyboardMarkup([
    [InlineKeyboardButton("Обратно в меню", callback_data="back_to_menu")]
])

# Кнопки для выбора напоминания
REMINDER_CHOICE = InlineKeyboardMarkup([
    [InlineKeyboardButton("Установить время и дату", callback_data="set_reminder")],
    [InlineKeyboardButton("Напоминание не нужно", callback_data="no_reminder")]
])

# Кнопки для управления напоминанием
TASK_ACTIONS = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("✅ Закрыть задачу", callback_data="close_task"),
        InlineKeyboardButton("🔄 Перенести срок", callback_data="reschedule_task")
    ],
    [InlineKeyboardButton("Обратно в меню", callback_data="back_to_menu")]
])

# Кнопка только для переноса срока (используется после выбора "Перенести срок")
RESCHEDULE_CONFIRM = InlineKeyboardMarkup([
    [InlineKeyboardButton("Обратно в меню", callback_data="back_to_menu")]
])