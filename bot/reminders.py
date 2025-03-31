from telegram.ext import ContextTypes
from bot.database import get_due_tasks
from bot.keyboards import TASK_ACTIONS
from datetime import datetime
import logging

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_due_tasks(context: ContextTypes.DEFAULT_TYPE):
    """Проверка просроченных задач и отправка напоминаний"""
    current_time = datetime.now().replace(second=0, microsecond=0)
    due_tasks = get_due_tasks(current_time)
    
    for task_id, user_id, task in due_tasks:
        try:
            # Получаем или создаем user_data для пользователя
            user_data = context.application.user_data.get(user_id, {})
            if user_id not in context.application.user_data:
                context.application.user_data[user_id] = {}

            # Удаляем старое сообщение, если оно есть
            if 'last_menu_message_id' in user_data:
                try:
                    await context.bot.delete_message(
                        chat_id=user_id,
                        message_id=user_data['last_menu_message_id']
                    )
                except Exception as e:
                    logger.warning(f"Не удалось удалить сообщение для пользователя {user_id}: {e}")

            # Сохраняем ID текущей задачи
            context.application.user_data[user_id]['current_task_id'] = task_id
            
            # Отправляем напоминание
            sent_message = await context.bot.send_message(
                chat_id=user_id,
                text=f"⏰ Напоминаю о задаче:\n{task}",
                reply_markup=TASK_ACTIONS
            )
            context.application.user_data[user_id]['last_menu_message_id'] = sent_message.message_id
            logger.info(f"Напоминание отправлено пользователю {user_id} для задачи {task_id}")
        
        except Exception as e:
            logger.error(f"Ошибка при отправке напоминания пользователю {user_id}: {e}")

def setup_reminders(application):
    """Настройка периодической проверки напоминаний"""
    if hasattr(application, 'job_queue') and application.job_queue:
        application.job_queue.run_repeating(
            check_due_tasks,
            interval=60,  # Проверка каждую минуту
            first=10      # Первая проверка через 10 секунд после запуска
        )
        logger.info("Напоминания успешно настроены с интервалом 60 секунд")