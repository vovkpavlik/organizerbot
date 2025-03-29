from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Основное меню с двумя кнопками
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