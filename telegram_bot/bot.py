import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, ConversationHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode

from config import TELEGRAM_TOKEN, ADMIN_USER_IDS
from telegram_bot.handlers import get_all_handlers
from telegram_bot.handlers.account_handlers import (
    bulk_upload_accounts_file, list_accounts_handler, WAITING_ACCOUNTS_FILE,
    add_account, enter_username, enter_password, confirm_add_account,
    enter_verification_code, cancel_add_account,
    ENTER_USERNAME, ENTER_PASSWORD, CONFIRM_ACCOUNT, ENTER_VERIFICATION_CODE
)

logger = logging.getLogger(__name__)

def is_admin(user_id):
    return user_id in ADMIN_USER_IDS

def start_handler(update, context):
    user = update.effective_user

    keyboard = [
    [InlineKeyboardButton("👤 Аккаунты", callback_data='menu_accounts')],
    [InlineKeyboardButton("📝 Задачи", callback_data='menu_tasks')],
    [InlineKeyboardButton("🔄 Прокси", callback_data='menu_proxy')],
    [InlineKeyboardButton("ℹ️ Помощь", callback_data='menu_help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
    f"Привет, {user.first_name}! Я бот для автоматической загрузки контента в Instagram.\n\n"
    f"Выберите раздел из меню ниже или используйте /help для получения списка доступных команд.",
    reply_markup=reply_markup
    )

def help_handler(update, context):
    help_text = """
*Доступные команды:*

*Аккаунты:*
/accounts - Меню управления аккаунтами
/add_account - Добавить новый аккаунт Instagram
/upload_accounts - Загрузить несколько аккаунтов из файла
/list_accounts - Показать список аккаунтов
/profile_setup - Настроить профиль аккаунта

*Задачи:*
/tasks - Меню управления задачами
/publish_now - Опубликовать контент сейчас
/schedule_publish - Запланировать публикацию

*Прокси:*
/proxy - Меню управления прокси
/add_proxy - Добавить новый прокси
/distribute_proxies - Распределить прокси по аккаунтам
/list_proxies - Показать список прокси

/cancel - Отменить текущую операцию
    """

    keyboard = [
    [InlineKeyboardButton("👤 Аккаунты", callback_data='menu_accounts')],
    [InlineKeyboardButton("📝 Задачи", callback_data='menu_tasks')],
    [InlineKeyboardButton("🔄 Прокси", callback_data='menu_proxy')],
    [InlineKeyboardButton("🔙 Главное меню", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

def cancel_handler(update, context):
    keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
    "Операция отменена.",
    reply_markup=reply_markup
    )
    return ConversationHandler.END

def callback_handler(update, context):
    query = update.callback_query
    query.answer()

    if query.data == 'menu_accounts':
        keyboard = [
        [InlineKeyboardButton("➕ Добавить аккаунт", callback_data='add_account')],
        [InlineKeyboardButton("📋 Список аккаунтов", callback_data='list_accounts')],
        [InlineKeyboardButton("📤 Загрузить аккаунты", callback_data='upload_accounts')],
        [InlineKeyboardButton("⚙️ Настройка профиля", callback_data='profile_setup')],
        [InlineKeyboardButton("🔙 Назад", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
        text="🔧 *Меню управления аккаунтами*\n\n"
        "Выберите действие из списка ниже:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
        )

    elif query.data == 'menu_tasks':
        keyboard = [
        [InlineKeyboardButton("📤 Опубликовать сейчас", callback_data='publish_now')],
        [InlineKeyboardButton("⏰ Запланировать публикацию", callback_data='schedule_publish')],
        [InlineKeyboardButton("📊 Статистика публикаций", callback_data='publication_stats')],
        [InlineKeyboardButton("🔙 Назад", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
        text="📝 *Меню управления задачами*\n\n"
        "Выберите действие из списка ниже:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
        )

    elif query.data == 'menu_proxy':
        keyboard = [
        [InlineKeyboardButton("➕ Добавить прокси", callback_data='add_proxy')],
        [InlineKeyboardButton("📋 Список прокси", callback_data='list_proxies')],
        [InlineKeyboardButton("🔄 Распределить прокси", callback_data='distribute_proxies')],
        [InlineKeyboardButton("🔙 Назад", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
        text="🔄 *Меню управления прокси*\n\n"
        "Выберите действие из списка ниже:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
        )

    elif query.data == 'menu_help':
        help_text = """
*Доступные команды:*

*Аккаунты:*
/accounts - Меню управления аккаунтами
/add_account - Добавить новый аккаунт Instagram
/upload_accounts - Загрузить несколько аккаунтов из файла
/list_accounts - Показать список аккаунтов
/profile_setup - Настроить профиль аккаунта

*Задачи:*
/tasks - Меню управления задачами
/publish_now - Опубликовать контент сейчас
/schedule_publish - Запланировать публикацию

*Прокси:*
/proxy - Меню управления прокси
/add_proxy - Добавить новый прокси
/distribute_proxies - Распределить прокси по аккаунтам
/list_proxies - Показать список прокси

/cancel - Отменить текущую операцию
        """

        keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
        text=help_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
        )

    elif query.data == 'back_to_main':
        keyboard = [
        [InlineKeyboardButton("👤 Аккаунты", callback_data='menu_accounts')],
        [InlineKeyboardButton("📝 Задачи", callback_data='menu_tasks')],
        [InlineKeyboardButton("🔄 Прокси", callback_data='menu_proxy')],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data='menu_help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
        text="Главное меню бота для автоматической загрузки контента в Instagram.\n\n"
        "Выберите раздел из меню ниже или используйте /help для получения списка доступных команд.",
        reply_markup=reply_markup
        )

    elif query.data == 'upload_accounts':
        # Отправляем новое сообщение вместо редактирования текущего
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='menu_accounts')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
        "Отправьте TXT файл с аккаунтами Instagram.\n\n"
        "Формат файла:\n"
        "username:password\n"
        "username:password\n"
        "...\n\n"
        "Каждый аккаунт должен быть на новой строке в формате username:password",
        reply_markup=reply_markup
        )

        # Устанавливаем состояние для ожидания файла
        context.user_data['waiting_for_accounts_file'] = True
        return WAITING_ACCOUNTS_FILE

    elif query.data == 'list_accounts':
        # Вызываем обработчик списка аккаунтов
        list_accounts_handler(update, context)

    elif query.data in ['profile_setup', 'publication_stats', 'add_proxy', 'list_proxies',
    'distribute_proxies']:
        query.edit_message_text(
        text=f"Функция '{query.data}' находится в разработке.\n\n"
        "Пожалуйста, попробуйте позже.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='back_to_main')]])
        )

    else:
        # Другие callback_data обрабатываются в соответствующих обработчиках
        pass

def text_handler(update, context):
    keyboard = [
    [InlineKeyboardButton("👤 Аккаунты", callback_data='menu_accounts')],
    [InlineKeyboardButton("📝 Задачи", callback_data='menu_tasks')],
    [InlineKeyboardButton("🔄 Прокси", callback_data='menu_proxy')],
    [InlineKeyboardButton("ℹ️ Помощь", callback_data='menu_help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
    "Я понимаю только команды. Используйте /help для получения списка доступных команд или выберите раздел из меню ниже:",
    reply_markup=reply_markup
    )

def error_handler(update, context):
    logger.error(f"Ошибка при обработке обновления {update}: {context.error}")

    if update.effective_chat:
        context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз.",
        parse_mode=ParseMode.MARKDOWN
        )

def setup_bot(updater):
    dp = updater.dispatcher

    # Основные обработчики
    dp.add_handler(CommandHandler("start", start_handler))
    dp.add_handler(CommandHandler("help", help_handler))
    dp.add_handler(CommandHandler("cancel", cancel_handler))

    # Регистрируем ConversationHandler для добавления аккаунта
    add_account_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("add_account", add_account),
            CallbackQueryHandler(add_account, pattern='^add_account$')
        ],
        states={
            ENTER_USERNAME: [MessageHandler(Filters.text & ~Filters.command, enter_username)],
            ENTER_PASSWORD: [MessageHandler(Filters.text & ~Filters.command, enter_password)],
            CONFIRM_ACCOUNT: [CallbackQueryHandler(confirm_add_account, pattern='^confirm_add_account$')],
            ENTER_VERIFICATION_CODE: [MessageHandler(Filters.text & ~Filters.command, enter_verification_code)]
        },
        fallbacks=[
            CallbackQueryHandler(cancel_add_account, pattern='^cancel_add_account$'),
            CallbackQueryHandler(lambda u, c: ConversationHandler.END, pattern='^menu_accounts$'),
            CommandHandler("cancel", cancel_handler)
        ]
    )

    dp.add_handler(add_account_conv_handler)

    # Добавляем все обработчики из модулей
    for handler in get_all_handlers():
        dp.add_handler(handler)

    # Добавляем обработчик для файлов с аккаунтами
    dp.add_handler(MessageHandler(
        Filters.document.file_extension("txt"),
        lambda update, context: bulk_upload_accounts_file(update, context) if context.user_data.get('waiting_for_accounts_file', False) else None
    ))

    # Обработчик callback-запросов
    dp.add_handler(CallbackQueryHandler(callback_handler))

    # Обработчик текстовых сообщений
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text_handler))

    # Обработчик ошибок
    dp.add_error_handler(error_handler)

    logger.info("Бот настроен и готов к работе")