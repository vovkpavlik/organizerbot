from telegram import Update
from telegram.ext import Application, ApplicationBuilder
from bot.handlers import handlers
from bot.keyboards import MAIN_MENU, TASK_ACTIONS
from config.config import TOKEN
from datetime import datetime
from bot.database import get_due_tasks
import asyncio
from bot.reminders import setup_reminders


def main():
    # Создание приложения с JobQueue
    app = ApplicationBuilder() \
        .token(TOKEN) \
        .build()  # Убрали .post_init(on_startup)
    
    # Добавление обработчиков
    for handler in handlers:
        app.add_handler(handler)
    
    # Настройка напоминаний из нового модуля
    setup_reminders(app)
    
    # Запуск бота
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()