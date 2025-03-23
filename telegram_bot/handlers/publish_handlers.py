import os
import tempfile
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import ConversationHandler

from database.db_manager import get_instagram_account, get_instagram_accounts, create_publish_task
from instagram_api.publisher import publish_video

# Состояния для публикации видео
CHOOSE_ACCOUNT, ENTER_CAPTION, CONFIRM_PUBLISH, CHOOSE_SCHEDULE = range(10, 14)

def is_admin(user_id):
    from telegram_bot.bot import is_admin
    return is_admin(user_id)

def publish_now_handler(update, context):
    """Обработчик команды публикации контента"""
    user_id = update.effective_user.id

    if not is_admin(user_id):
        update.message.reply_text("У вас нет прав для выполнения этой команды.")
        return ConversationHandler.END

    # Получаем список аккаунтов
    accounts = get_instagram_accounts()

    if not accounts:
        keyboard = [[InlineKeyboardButton("➕ Добавить аккаунт", callback_data='add_account')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(
            "У вас нет добавленных аккаунтов Instagram. Сначала добавьте аккаунт.",
            reply_markup=reply_markup
        )
        return ConversationHandler.END

    # Создаем клавиатуру с аккаунтами
    keyboard = []
    for account in accounts:
        if account.is_active:
            keyboard.append([InlineKeyboardButton(f"👤 {account.username}", callback_data=f"publish_account_{account.id}")])

    keyboard.append([InlineKeyboardButton("🔙 Отмена", callback_data='cancel_publish')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        query = update.callback_query
        query.answer()
        query.edit_message_text(
            "Выберите аккаунт для публикации:",
            reply_markup=reply_markup
        )
    else:
        update.message.reply_text(
            "Выберите аккаунт для публикации:",
            reply_markup=reply_markup
        )

    return CHOOSE_ACCOUNT

def choose_account_callback(update, context):
    """Обработчик выбора аккаунта для публикации"""
    query = update.callback_query
    query.answer()

    # Получаем ID аккаунта из callback_data
    account_id = int(query.data.split('_')[-1])
    context.user_data['publish_account_id'] = account_id

    # Получаем аккаунт
    account = get_instagram_account(account_id)
    context.user_data['publish_account_username'] = account.username

    # Проверяем, есть ли уже медиафайл
    if 'publish_media_path' in context.user_data:
        # Если медиафайл уже загружен, переходим к вводу подписи
        query.edit_message_text(
            f"Выбран аккаунт: *{account.username}*\n\n"
            f"Теперь введите подпись к публикации (или отправьте /skip для публикации без подписи):",
            parse_mode=ParseMode.MARKDOWN
        )
        return ENTER_CAPTION
    else:
        # Если медиафайла нет, просим загрузить
        query.edit_message_text(
            f"Выбран аккаунт: *{account.username}*\n\n"
            f"Теперь отправьте видео для публикации:",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END

def video_upload_handler(update, context):
    """Обработчик загрузки видео"""
    user_id = update.effective_user.id

    if not is_admin(user_id):
        update.message.reply_text("У вас нет прав для выполнения этой команды.")
        return

    # Проверяем, выбран ли аккаунт
    if 'publish_account_id' not in context.user_data:
        # Если аккаунт не выбран, запускаем процесс выбора аккаунта
        # Store the video file information for later use
        context.user_data['pending_video'] = update.message.video or update.message.document
        return publish_now_handler(update, context)

    # Получаем информацию о видео
    video_file = update.message.video or update.message.document
    file_id = video_file.file_id

    # Скачиваем видео
    video = context.bot.get_file(file_id)

    # Создаем временный файл для сохранения видео
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
        video_path = temp_file.name

    # Скачиваем видео во временный файл
    video.download(video_path)

    # Сохраняем путь к видео
    context.user_data['publish_media_path'] = video_path
    context.user_data['publish_media_type'] = 'video'

    # Запрашиваем подпись
    update.message.reply_text(
        "Видео успешно загружено!\n\n"
        "Теперь введите подпись к публикации (или отправьте /skip для публикации без подписи):"
    )

    return ENTER_CAPTION

def enter_caption(update, context):
    """Обработчик ввода подписи к публикации"""
    if update.message.text == '/skip':
        context.user_data['publish_caption'] = ""
    else:
        context.user_data['publish_caption'] = update.message.text

    # Получаем данные для публикации
    account_id = context.user_data.get('publish_account_id')
    account_username = context.user_data.get('publish_account_username')
    media_type = context.user_data.get('publish_media_type')
    caption = context.user_data.get('publish_caption')

    # Создаем клавиатуру для подтверждения
    keyboard = [
        [
            InlineKeyboardButton("✅ Опубликовать сейчас", callback_data='confirm_publish_now'),
            InlineKeyboardButton("⏰ Запланировать", callback_data='schedule_publish')
        ],
        [InlineKeyboardButton("❌ Отмена", callback_data='cancel_publish')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        f"*Данные для публикации:*\n\n"
        f"👤 *Аккаунт:* {account_username}\n"
        f"📝 *Тип:* {media_type}\n"
        f"✏️ *Подпись:* {caption or '(без подписи)'}\n\n"
        f"Что вы хотите сделать?",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

    return CONFIRM_PUBLISH

def confirm_publish_now(update, context):
    """Обработчик подтверждения немедленной публикации"""
    query = update.callback_query
    query.answer()

    # Получаем данные для публикации
    account_id = context.user_data.get('publish_account_id')
    media_path = context.user_data.get('publish_media_path')
    media_type = context.user_data.get('publish_media_type')
    caption = context.user_data.get('publish_caption', '')

    query.edit_message_text("⏳ Публикация контента... Это может занять некоторое время.")

    # Создаем задачу на публикацию
    success, task_id = create_publish_task(
        account_id=account_id,
        task_type=media_type,
        media_path=media_path,
        caption=caption
    )

    if not success:
        query.edit_message_text(f"❌ Ошибка при создании задачи: {task_id}")
        return ConversationHandler.END

    # Публикуем видео
    if media_type == 'video':
        success, result = publish_video(task_id)

        if success:
            keyboard = [[InlineKeyboardButton("🔙 К меню задач", callback_data='menu_tasks')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
                "✅ Видео успешно опубликовано!",
                reply_markup=reply_markup
            )
        else:
            keyboard = [[InlineKeyboardButton("🔙 К меню задач", callback_data='menu_tasks')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
                f"❌ Ошибка при публикации видео: {result}",
                reply_markup=reply_markup
            )
    else:
        query.edit_message_text("❌ Неподдерживаемый тип медиа")

    # Очищаем данные
    if 'publish_account_id' in context.user_data:
        del context.user_data['publish_account_id']
    if 'publish_account_username' in context.user_data:
        del context.user_data['publish_account_username']
    if 'publish_media_path' in context.user_data:
        del context.user_data['publish_media_path']
    if 'publish_media_type' in context.user_data:
        del context.user_data['publish_media_type']
    if 'publish_caption' in context.user_data:
        del context.user_data['publish_caption']

    return ConversationHandler.END

def schedule_publish_callback(update, context):
    """Обработчик запланированной публикации"""
    query = update.callback_query
    query.answer()

    query.edit_message_text(
        "Введите дату и время публикации в формате ДД.ММ.ГГГГ ЧЧ:ММ\n"
        "Например: 25.12.2023 15:30"
    )

    return CHOOSE_SCHEDULE

def choose_schedule(update, context):
    """Обработчик выбора времени для запланированной публикации"""
    try:
        # Парсим дату и время
        scheduled_time = datetime.strptime(update.message.text, "%d.%m.%Y %H:%M")

        # Получаем данные для публикации
        account_id = context.user_data.get('publish_account_id')
        media_path = context.user_data.get('publish_media_path')
        media_type = context.user_data.get('publish_media_type')
        caption = context.user_data.get('publish_caption', '')

        # Создаем задачу на публикацию
        success, task_id = create_publish_task(
            account_id=account_id,
            task_type=media_type,
            media_path=media_path,
            caption=caption,
            scheduled_time=scheduled_time
        )

        if not success:
            update.message.reply_text(f"❌ Ошибка при создании задачи: {task_id}")
            return ConversationHandler.END

        keyboard = [[InlineKeyboardButton("🔙 К меню задач", callback_data='menu_tasks')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(
            f"✅ Публикация успешно запланирована на {scheduled_time.strftime('%d.%m.%Y %H:%M')}",
            reply_markup=reply_markup
        )

        # Очищаем данные
        if 'publish_account_id' in context.user_data:
            del context.user_data['publish_account_id']
        if 'publish_account_username' in context.user_data:
            del context.user_data['publish_account_username']
        if 'publish_media_path' in context.user_data:
            del context.user_data['publish_media_path']
        if 'publish_media_type' in context.user_data:
            del context.user_data['publish_media_type']
        if 'publish_caption' in context.user_data:
            del context.user_data['publish_caption']

    except ValueError:
        update.message.reply_text(
            "❌ Неверный формат даты и времени. Пожалуйста, используйте формат ДД.ММ.ГГГГ ЧЧ:ММ\n"
            "Например: 25.12.2023 15:30"
        )
        return CHOOSE_SCHEDULE

    return ConversationHandler.END

def cancel_publish(update, context):
    """Обработчик отмены публикации"""
    query = update.callback_query
    query.answer()

    # Очищаем данные
    if 'publish_account_id' in context.user_data:
        del context.user_data['publish_account_id']
    if 'publish_account_username' in context.user_data:
        del context.user_data['publish_account_username']
    if 'publish_media_path' in context.user_data:
        # Удаляем временный файл
        try:
            os.remove(context.user_data['publish_media_path'])
        except:
            pass
        del context.user_data['publish_media_path']
    if 'publish_media_type' in context.user_data:
        del context.user_data['publish_media_type']
    if 'publish_caption' in context.user_data:
        del context.user_data['publish_caption']

    keyboard = [[InlineKeyboardButton("🔙 К меню задач", callback_data='menu_tasks')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query.edit_message_text(
        "❌ Публикация отменена.",
        reply_markup=reply_markup
    )

    return ConversationHandler.END

def get_publish_handlers():
    """Возвращает обработчики для публикации контента"""
    from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, Filters

    publish_conversation = ConversationHandler(
        entry_points=[
            CommandHandler("publish_now", publish_now_handler),
            CallbackQueryHandler(publish_now_handler, pattern='^publish_now$')
        ],
        states={
            CHOOSE_ACCOUNT: [
                CallbackQueryHandler(choose_account_callback, pattern='^publish_account_\d+$'),
                CallbackQueryHandler(cancel_publish, pattern='^cancel_publish$')
            ],
            ENTER_CAPTION: [
                MessageHandler(Filters.text & ~Filters.command, enter_caption),
                CommandHandler("skip", enter_caption)
            ],
            CONFIRM_PUBLISH: [
                CallbackQueryHandler(confirm_publish_now, pattern='^confirm_publish_now$'),
                CallbackQueryHandler(schedule_publish_callback, pattern='^schedule_publish$'),
                CallbackQueryHandler(cancel_publish, pattern='^cancel_publish$')
            ],
            CHOOSE_SCHEDULE: [
                MessageHandler(Filters.text & ~Filters.command, choose_schedule)
            ]
        },
        fallbacks=[CommandHandler("cancel", lambda update, context: ConversationHandler.END)]
    )

    video_handler = MessageHandler(Filters.video | Filters.document.video, video_upload_handler)

    return [publish_conversation, video_handler]