from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from bot.database import check_user_exists, add_user, update_user_name, add_task, get_user_tasks
from bot.keyboards import MAIN_MENU, BACK_TO_MENU, REMINDER_CHOICE
from datetime import datetime
import asyncio

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    telegram_tag = update.message.from_user.username
    if telegram_tag:
        telegram_tag = f"@{telegram_tag}"
    else:
        telegram_tag = "No tag"

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
    await asyncio.sleep(300)  # Ждем 5 минут (300 секунд)
    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="Выбери действие:",
            reply_markup=MAIN_MENU
        )
    except Exception as e:
        print(f"Не удалось заменить сообщение 'Задача добавлена': {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    chat_id = update.message.chat_id
    message_id = update.message.message_id

    if context.user_data.get('waiting_for_name'):
        name = text
        update_user_name(user_id, name)
        await update.message.reply_text(
            f"Отлично, {name}! Теперь я тебя знаю. Хочешь добавить новую задачу?",
            reply_markup=MAIN_MENU
        )
        context.user_data['waiting_for_name'] = False
        return

    if context.user_data.get('waiting_for_task'):
        context.user_data['task_text'] = text
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        if 'bot_message_id' in context.user_data:
            await context.bot.delete_message(chat_id=chat_id, message_id=context.user_data['bot_message_id'])
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
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            if 'bot_message_id' in context.user_data:
                await context.bot.delete_message(chat_id=chat_id, message_id=context.user_data['bot_message_id'])
            add_task(user_id, context.user_data['task_text'], dedline)
            sent_message = await context.bot.send_message(
                chat_id=chat_id,
                text="Задача добавлена",
                reply_markup=MAIN_MENU
            )
            context.user_data['last_menu_message_id'] = sent_message.message_id
            if context.job_queue:
                context.job_queue.run_once(
                    lambda ctx: replace_task_added_message(ctx, chat_id, sent_message.message_id),
                    300,  # 5 минут в секундах
                    chat_id=chat_id
                )
            else:
                print("JobQueue не инициализирован, таймер не запущен")
            del context.user_data['task_text']
            del context.user_data['waiting_for_dedline']
            del context.user_data['bot_message_id']
        except ValueError:
            await update.message.reply_text(
                "Неверный формат! Используй: число.месяц.год час:минута (например, 31.12.2025 15:30)"
            )
        return

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    message_id = query.message.message_id
    user_id = query.from_user.id
    await query.answer()

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
                f"{i+1}) {task[1].strftime('%d.%m.%Y %H:%M') if task[1] else 'Без срока'}. {task[0]}"
                for i, task in enumerate(tasks)
            )
            await query.edit_message_text(
                f"Твои задачи:\n{tasks_text}",
                reply_markup=BACK_TO_MENU
            )
        else:
            await query.edit_message_text(
                "У тебя пока нет задач",
                reply_markup=BACK_TO_MENU
            )

    elif query.data == "back_to_menu":
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        sent_message = await context.bot.send_message(
            chat_id=chat_id,
            text="Выбери действие:",
            reply_markup=MAIN_MENU
        )
        context.user_data['last_menu_message_id'] = sent_message.message_id

    elif query.data == "no_reminder":
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        add_task(user_id, context.user_data['task_text'])
        sent_message = await context.bot.send_message(
            chat_id=chat_id,
            text="Задача добавлена",
            reply_markup=MAIN_MENU
        )
        context.user_data['last_menu_message_id'] = sent_message.message_id
        if context.job_queue:
            context.job_queue.run_once(
                lambda ctx: replace_task_added_message(ctx, chat_id, sent_message.message_id),
                300,  # 5 минут в секундах
                chat_id=chat_id
            )
        else:
            print("JobQueue не инициализирован, таймер не запущен")
        del context.user_data['task_text']
        del context.user_data['bot_message_id']

    elif query.data == "set_reminder":
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        sent_message = await context.bot.send_message(
            chat_id=chat_id,
            text="Напиши дату и время в формате: число.месяц.год час:минута (например, 31.12.2025 15:30)",
            reply_markup=BACK_TO_MENU
        )
        context.user_data['bot_message_id'] = sent_message.message_id
        context.user_data['waiting_for_dedline'] = True

handlers = [
    CommandHandler("start", start),
    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message),
    CallbackQueryHandler(handle_callback),
]