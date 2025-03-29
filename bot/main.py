from telegram import Update
from telegram.ext import Application, ApplicationBuilder
from bot.handlers import handlers
from bot.keyboards import MAIN_MENU
from config.config import TOKEN
from datetime import datetime
from bot.database import get_due_tasks
import asyncio

async def reminder_task(app):
    while True:
        current_time = datetime.now().replace(second=0, microsecond=0)
        due_tasks = get_due_tasks(current_time)
        for user_id, task in due_tasks:
            try:
                # Удаляем старое меню, если оно есть и доступно
                user_data = app.user_data.get(user_id, {})
                if 'last_menu_message_id' in user_data:
                    try:
                        await app.bot.delete_message(
                            chat_id=user_id,
                            message_id=user_data['last_menu_message_id']
                        )
                    except Exception as e:
                        print(f"Не удалось удалить старое меню: {e}")
                
                # Отправляем напоминание
                sent_message = await app.bot.send_message(
                    chat_id=user_id,
                    text=f"⏰ Напоминаю о задаче: {task}",
                    reply_markup=MAIN_MENU
                )
                
                # Обновляем данные пользователя
                if user_id not in app.user_data:
                    app.user_data[user_id] = {}
                app.user_data[user_id]['last_menu_message_id'] = sent_message.message_id
            except Exception as e:
                print(f"Ошибка при отправке напоминания пользователю {user_id}: {e}")
        await asyncio.sleep(60)

async def on_startup(app):
    asyncio.create_task(reminder_task(app))

def main():
    # Создание приложения с JobQueue
    app = ApplicationBuilder() \
        .token(TOKEN) \
        .post_init(on_startup) \
        .build()
    
    # Добавление обработчиков
    for handler in handlers:
        app.add_handler(handler)
    
    # Запуск бота
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()