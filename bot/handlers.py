from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from bot.database import (
    check_user_exists, add_user, update_user_name, add_task, get_user_tasks,
    close_task, update_task_deadline
)
from datetime import datetime
import asyncio
from bot.keyboards import MAIN_REPLY_MARKUP, ADD_TASK_REMINDER_MARKUP, INPUT_TASK_MARKUP

async def delete_message_safe(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int):
    """Безопасное удаление сообщения"""
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        return True
    except Exception:
        return False

async def send_with_main_keyboard(context, chat_id, text):
    """Отправка сообщения с основной клавиатурой"""
    return await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=MAIN_REPLY_MARKUP
    )

async def delete_message_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int):
    """Удаление сообщения с задержкой"""
    await asyncio.sleep(delay)
    await delete_message_safe(context, chat_id, message_id)

async def show_tasks_list(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int):
    """Показать список задач с автоматическим удалением и возможностью обновления"""
    # Удаляем предыдущее сообщение с задачами, если оно есть
    if 'last_tasks_message_id' in context.user_data:
        await delete_message_safe(context, chat_id, context.user_data['last_tasks_message_id'])
        context.user_data.pop('last_tasks_message_id', None)
    
    # Отменяем предыдущий таймер удаления, если он был
    if 'delete_task_timer' in context.user_data:
        context.user_data['delete_task_timer'].cancel()
    
    tasks = get_user_tasks(user_id)
    if tasks:
        tasks_text = "\n".join(
            f"{i+1}) {task[1]} - {task[2].strftime('%d.%m.%Y %H:%M') if task[2] else 'Без срока'}"
            for i, task in enumerate(tasks)
        )
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=f"📝 Твои задачи:\n{tasks_text}",
            reply_markup=MAIN_REPLY_MARKUP
        )
    else:
        msg = await send_with_main_keyboard(context, chat_id, "Нет текущих задач")
    
    # Сохраняем ID сообщения
    context.user_data['last_tasks_message_id'] = msg.message_id
    
    # Создаем задачу для удаления через 2 минуты
    delete_task = asyncio.create_task(
        delete_message_after_delay(context, chat_id, msg.message_id, 120)
    )
    
    # Сохраняем ссылку на задачу, чтобы можно было отменить
    context.user_data['delete_task_timer'] = delete_task

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user_id = update.message.from_user.id
    telegram_tag = update.message.from_user.username or "No tag"
    
    if not check_user_exists(user_id):
        add_user(user_id, f"@{telegram_tag}" if telegram_tag != "No tag" else telegram_tag)
        await update.message.reply_text(
            "Привет! Как тебя зовут?",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Отмена")]], resize_keyboard=True)
        )
        context.user_data['waiting_for_name'] = True
    else:
        await send_with_main_keyboard(context, update.message.chat_id, "Привет! Ты уже зарегистрирован.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    user_id = update.message.from_user.id
    text = update.message.text
    chat_id = update.message.chat_id

    # Обработка имени пользователя
    if context.user_data.get('waiting_for_name'):
        if text == "Отмена":
            await send_with_main_keyboard(context, chat_id, "Регистрация отменена")
            context.user_data.pop('waiting_for_name', None)
            return
            
        name = text.strip()
        update_user_name(user_id, name)
        await send_with_main_keyboard(context, chat_id, f"Отлично, {name}! Теперь я тебя знаю.")
        context.user_data.pop('waiting_for_name', None)
        return

    # Обработка кнопки "Мои Задачи"
    if text == "Мои Задачи":
        await show_tasks_list(context, chat_id, user_id)
        return

    # Обработка кнопки "Отмена" в главном меню
    if text == "Отмена" and not context.user_data.get('waiting_for_task'):
        await send_with_main_keyboard(context, chat_id, "Действие отменено")
        return

    # Обработка кнопки "Добавить задачу"
    if text == "Добавить задачу":
        context.user_data['waiting_for_task'] = True
        await context.bot.send_message(
            chat_id=chat_id,
            text="Напиши задачу, которую хочешь добавить",
            reply_markup=INPUT_TASK_MARKUP
        )
        return

    # Обработка отмены при добавлении задачи
    if text == "Отмена" and context.user_data.get('waiting_for_task'):
        context.user_data.pop('waiting_for_task', None)
        await send_with_main_keyboard(context, chat_id, "Добавление задачи отменено")
        return

    # Обработка текста задачи
    if context.user_data.get('waiting_for_task'):
        context.user_data['task_text'] = text
        context.user_data.pop('waiting_for_task', None)
        
        await context.bot.send_message(
            chat_id=chat_id,
            text="Нужно ли поставить напоминание?",
            reply_markup=ADD_TASK_REMINDER_MARKUP
        )
        context.user_data['waiting_for_reminder_choice'] = True
        return

    # Обработка выбора "Без напоминания"
    if text == "Без напоминания" and context.user_data.get('waiting_for_reminder_choice'):
        add_task(user_id, context.user_data['task_text'])
        
        msg = await send_with_main_keyboard(context, chat_id, "✅ Задача добавлена без напоминания")
        asyncio.create_task(delete_message_after_delay(context, chat_id, msg.message_id, 3))
        
        # Очищаем временные данные
        context.user_data.pop('task_text', None)
        context.user_data.pop('waiting_for_reminder_choice', None)
        return

    # Обработка выбора "Установить время и дату"
    if text == "Установить время и дату" and context.user_data.get('waiting_for_reminder_choice'):
        await context.bot.send_message(
            chat_id=chat_id,
            text="Введите дату и время в формате ДД.ММ.ГГГГ ЧЧ:ММ (например, 31.12.2025 15:30)",
            reply_markup=INPUT_TASK_MARKUP
        )
        context.user_data.pop('waiting_for_reminder_choice', None)
        context.user_data['waiting_for_dedline'] = True
        return

    # Обработка дедлайна для новой задачи
    if context.user_data.get('waiting_for_dedline'):
        if text == "Отмена":
            await send_with_main_keyboard(context, chat_id, "Добавление задачи отменено")
            context.user_data.pop('waiting_for_dedline', None)
            context.user_data.pop('task_text', None)
            return
            
        try:
            dedline = datetime.strptime(text, "%d.%m.%Y %H:%M")
            add_task(user_id, context.user_data['task_text'], dedline)
            
            msg = await send_with_main_keyboard(context, chat_id, "✅ Задача добавлена")
            asyncio.create_task(delete_message_after_delay(context, chat_id, msg.message_id, 3))
            
            # Очищаем временные данные
            context.user_data.pop('task_text', None)
            context.user_data.pop('waiting_for_dedline', None)
                
        except ValueError:
            await context.bot.send_message(
                chat_id=chat_id,
                text="Неверный формат! Используй: ДД.ММ.ГГГГ ЧЧ:ММ (например, 31.12.2025 15:30)",
                reply_markup=INPUT_TASK_MARKUP
            )
        return

    # Обработка нового срока для переноса задачи
    if context.user_data.get('waiting_for_reschedule'):
        if text == "Отмена":
            await send_with_main_keyboard(context, chat_id, "Перенос срока отменен")
            context.user_data.pop('waiting_for_reschedule', None)
            context.user_data.pop('current_task_id', None)
            return
            
        try:
            task_id = context.user_data.get('current_task_id')
            new_deadline = datetime.strptime(text, "%d.%m.%Y %H:%M")
            
            if task_id and update_task_deadline(task_id, new_deadline):
                msg = await send_with_main_keyboard(
                    context, chat_id, 
                    f"✅ Срок задачи перенесен на {new_deadline.strftime('%d.%m.%Y %H:%M')}"
                )
                asyncio.create_task(delete_message_after_delay(context, chat_id, msg.message_id, 3))
            
            # Очищаем временные данные
            context.user_data.pop('current_task_id', None)
            context.user_data.pop('waiting_for_reschedule', None)
                
        except ValueError:
            await context.bot.send_message(
                chat_id=chat_id,
                text="Неверный формат! Используй: ДД.ММ.ГГГГ ЧЧ:ММ (например, 31.12.2025 15:30)",
                reply_markup=INPUT_TASK_MARKUP
            )
        return

    # Если сообщение не обработано, показываем главное меню
    await send_with_main_keyboard(context, chat_id, "Выберите действие:")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback-запросов"""
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    user_id = query.from_user.id
    message_id = query.message.message_id

    try:
        context.user_data['bot_message_id'] = message_id

        # Добавление без напоминания (из inline-кнопки)
        if query.data == "no_reminder":
            add_task(user_id, context.user_data['task_text'])
            await query.edit_message_text("✅ Задача добавлена без напоминания")
            await send_with_main_keyboard(context, chat_id, "Главное меню:")
            
            # Очищаем временные данные
            for key in ['task_text', 'waiting_for_reminder_choice', 'bot_message_id']:
                context.user_data.pop(key, None)

        # Закрытие задачи
        elif query.data == "close_task":
            task_id = context.user_data.get('current_task_id')
            if task_id and close_task(task_id):
                await query.edit_message_text("✅ Задача закрыта")
                await send_with_main_keyboard(context, chat_id, "Главное меню:")
            context.user_data.pop('current_task_id', None)

        # Перенос срока задачи
        elif query.data == "reschedule_task":
            await query.edit_message_text("Введите новую дату и время в формате ДД.ММ.ГГГГ ЧЧ:ММ")
            context.user_data['waiting_for_reschedule'] = True
            
    except Exception as e:
        print(f"Ошибка в обработчике callback: {e}")
        await send_with_main_keyboard(context, chat_id, "Произошла ошибка. Попробуй еще раз.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    print(f"Ошибка при обработке обновления: {context.error}")
    if update and update.message:
        await send_with_main_keyboard(context, update.message.chat_id, "Произошла ошибка. Пожалуйста, попробуйте еще раз.")

def setup_handlers(application):
    """Регистрация всех обработчиков"""
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_error_handler(error_handler)