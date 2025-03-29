from telegram.ext import ApplicationBuilder
from telegram import ReplyKeyboardMarkup, KeyboardButton
from bot.handlers import setup_handlers
from config.config import TOKEN
from datetime import datetime
from bot.database import get_due_tasks
import asyncio

async def reminder_task(app):
    while True:
        current_time = datetime.now().replace(second=0, microsecond=0)
        due_tasks = get_due_tasks(current_time)
        for task_id, user_id, task in due_tasks:
            try:
                # Отправка напоминания с кнопками
                await app.bot.send_message(
                    chat_id=user_id,
                    text=f"⏰ Напоминаю о задаче:\n{task}",
                    reply_markup=ReplyKeyboardMarkup(
                        [
                            [KeyboardButton("✅ Закрыть задачу"), KeyboardButton("🔄 Перенести срок")],
                            [KeyboardButton("Мои Задачи")]
                        ],
                        resize_keyboard=True
                    )
                )
            except Exception as e:
                print(f"Ошибка при отправке напоминания: {e}")
        await asyncio.sleep(60)

async def on_startup(app):
    asyncio.create_task(reminder_task(app))

def main():
    app = ApplicationBuilder() \
        .token(TOKEN) \
        .post_init(on_startup) \
        .build()
    
    setup_handlers(app)
    
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()