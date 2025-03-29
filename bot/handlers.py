from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from bot.database import check_user_exists, add_user, update_user_name, add_task, get_user_tasks
from bot.keyboards import MAIN_MENU, BACK_TO_MENU, REMINDER_CHOICE
from datetime import datetime
import asyncio

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    telegram_tag = update.message.from_user.username
    telegram_tag = f"@{telegram_tag}" if telegram_tag else "No tag"

    if not check_user_exists(user_id):
        add_user(user_id, telegram_tag)
        await update.message.reply_text("Привет! Как тебя зовут?")
        context.user_data['waiting_for_name'] = True
    else:
        await update.message.reply_text(
            "Привет! Ты уже зарегистрирован. Хочешь добавить новую задачу?",
            reply_markup=MAIN_MENU
        )

async def replace_task_added_message(context: ContextTypes.DEFAULT_TYPE, chat_id, message_id):
    await asyncio.sleep(300)
    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="Выбери действие:",
            reply_markup=MAIN_MENU
        )
    except Exception as e:
        print(f"Не удалось обновить сообщение: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    chat_id = update.message.chat_id

    if context.user_data.get('waiting_for_name'):
        name = text.strip()
        update_user_name(user_id, name)
        await update.message.reply_text(
            f"Отлично, {name}! Теперь я тебя знаю. Хочешь добавить новую задачу?",
            reply_markup=MAIN_MENU
        )
        context.user_data['waiting_for_name'] = False
        return

    if context.user_data.get('waiting_for_task'):
        context.user_data['task_text'] = text
        await update.message.delete()
        if 'bot_message_id' in context.user_data:
            try:
                await context.bot.delete_message(chat_id, context.user_data['bot_message_id'])
            except Exception as e:
                print(f"Не удалось удалить сообщение: {e}")
        
        sent_message = await context.bot.send_message(
            chat_id=chat_id,
            text="Нужно ли поставить напоминание?",
            reply_markup=REMINDER_CHOICE
        )
        context.user_data['bot_message_id'] = sent_message.message_id
        context.user_data['waiting_for_task'] = False
        return

    if context.user_data.get('waiting_for_dedline'):
        try:
            dedline = datetime.strptime(text, "%d.%m.%Y %H:%M")
            await update.message.delete()
            if 'bot_message_id' in context.user_data:
                try:
                    await context.bot.delete_message(chat_id, context.user_data['bot_message_id'])
                except Exception as e:
                    print(f"Не удалось удалить сообщение: {e}")
            
            add_task(user_id, context.user_data['task_text'], dedline)
            sent_message = await context.bot.send_message(
                chat_id=chat_id,
                text="✅ Задача добавлена",
                reply_markup=MAIN_MENU
            )
            context.user_data['last_menu_message_id'] = sent_message.message_id
            
            # Запускаем таймер для замены сообщения
            if hasattr(context, 'job_queue') and context.job_queue:
                context.job_queue.run_once(
                    lambda ctx: asyncio.create_task(replace_task_added_message(ctx, chat_id, sent_message.message_id)),
                    300
                )
            
            # Очищаем временные данные
            for key in ['task_text', 'waiting_for_dedline', 'bot_message_id']:
                context.user_data.pop(key, None)
                
        except ValueError:
            await update.message.reply_text(
                "Неверный формат! Используй: ДД.ММ.ГГГГ ЧЧ:ММ (например, 31.12.2025 15:30)"
            )
        return

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    user_id = query.from_user.id
    message_id = query.message.message_id

    try:
        if query.data == "add_task":
            context.user_data['bot_message_id'] = message_id
            await query.edit_message_text(
                "Напиши задачу, которую хочешь добавить",
                reply_markup=BACK_TO_MENU
            )
            context.user_data['waiting_for_task'] = True

        elif query.data == "my_tasks":
            tasks = get_user_tasks(user_id)
            if tasks:
                tasks_text = "\n".join(
                    f"{i+1}) {task[0]} - {task[1].strftime('%d.%m.%Y %H:%M') if task[1] else 'Без срока'}"
                    for i, task in enumerate(tasks)
                )
                await query.edit_message_text(
                    f"📝 Твои задачи:\n{tasks_text}",
                    reply_markup=BACK_TO_MENU
                )
            else:
                await query.edit_message_text(
                    "У тебя пока нет задач",
                    reply_markup=BACK_TO_MENU
                )

        elif query.data == "back_to_menu":
            await query.edit_message_text(
                "Выбери действие:",
                reply_markup=MAIN_MENU
            )

        elif query.data == "no_reminder":
            add_task(user_id, context.user_data['task_text'])
            await query.edit_message_text(
                "✅ Задача добавлена",
                reply_markup=MAIN_MENU
            )
            context.user_data['last_menu_message_id'] = message_id
            
            if hasattr(context, 'job_queue') and context.job_queue:
                context.job_queue.run_once(
                    lambda ctx: asyncio.create_task(replace_task_added_message(ctx, chat_id, message_id)),
                    300
                )
            
            context.user_data.pop('task_text', None)
            context.user_data.pop('bot_message_id', None)

        elif query.data == "set_reminder":
            await query.edit_message_text(
                "Напиши дату и время в формате: ДД.ММ.ГГГГ ЧЧ:ММ (например, 31.12.2025 15:30)",
                reply_markup=BACK_TO_MENU
            )
            context.user_data['waiting_for_dedline'] = True
            context.user_data['bot_message_id'] = message_id
            
    except Exception as e:
        print(f"Ошибка в обработчике callback: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="Произошла ошибка. Попробуй еще раз.",
            reply_markup=MAIN_MENU
        )

handlers = [
    CommandHandler("start", start),
    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message),
    CallbackQueryHandler(handle_callback),
]