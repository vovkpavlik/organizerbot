from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

# Основные кнопки под чатом
MAIN_REPLY_MARKUP = ReplyKeyboardMarkup(
    [
        [KeyboardButton("Добавить задачу"), KeyboardButton("Мои Задачи")],
        [KeyboardButton("Отмена")]
    ],
    resize_keyboard=True
)

# Кнопки для добавления задачи (без напоминания)
ADD_TASK_REMINDER_MARKUP = ReplyKeyboardMarkup(
    [
        [KeyboardButton("Установить время и дату"), KeyboardButton("Без напоминания")],
        [KeyboardButton("Отмена")]
    ],
    resize_keyboard=True
)

# Кнопки для ввода задачи
INPUT_TASK_MARKUP = ReplyKeyboardMarkup(
    [[KeyboardButton("Отмена")]],
    resize_keyboard=True
)