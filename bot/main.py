from telegram import Update
from telegram.ext import Application
from bot.handlers import handlers
from bot.keyboards import MAIN_MENU
from config.config import TOKEN
from datetime import datetime
from bot.database import get_due_tasks
import asyncio  # Добавляем импорт asyncio

async def reminder_task(app):
    while True:
        current_time = datetime.now().replace(second=0, microsecond=0)  # Округляем до минут
        due_tasks = get_due_tasks(current_time)
        for user_id, task in due_tasks:
            try:
                if 'last_menu_message_id' in app.bot_data.get(user_id, {}):
                    try:
                        await app.bot.delete_message(
                            chat_id=user_id,
                            message_id=app.bot_data[user_id]['last_menu_message_id']
                        )
                    except Exception as e:
                        print(f"Ошибка при удалении старого меню для {user_id}: {e}")
                
                sent_message = await app.bot.send_message(
                    chat_id=user_id,
                    text=f"Напоминаю о задаче: {task}",
                    reply_markup=MAIN_MENU
                )
                if user_id not in app.bot_data:
                    app.bot_data[user_id] = {}
                app.bot_data[user_id]['last_menu_message_id'] = sent_message.message_id
            except Exception as e:
                print(f"Ошибка при отправке напоминания пользователю {user_id}: {e}")
        await asyncio.sleep(60)  # Теперь asyncio определен

async def on_startup(app):
    app.create_task(reminder_task(app))

def main():
    # Создание приложения
    app = Application.builder().token(TOKEN).post_init(on_startup).build()
    
    # Добавление обработчиков
    for handler in handlers:
        app.add_handler(handler)
    
    # Запуск бота с использованием run_polling
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()