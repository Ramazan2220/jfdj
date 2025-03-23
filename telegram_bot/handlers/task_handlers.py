from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import ConversationHandler

def tasks_handler(update, context):
    keyboard = [
        [
            InlineKeyboardButton("📤 Опубликовать сейчас", callback_data='publish_now'),
            InlineKeyboardButton("⏰ Запланировать публикацию", callback_data='schedule_publish')
        ],
        [
            InlineKeyboardButton("📊 Статистика публикаций", callback_data='publication_stats'),
            InlineKeyboardButton("🔙 Назад", callback_data='back_to_main')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        "📝 *Меню управления задачами*\n\n"
        "Выберите действие из списка ниже:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

def schedule_publish_handler(update, context):
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='menu_tasks')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        "Функция планирования публикации в разработке",
        reply_markup=reply_markup
    )
    return ConversationHandler.END

def get_task_handlers():
    """Возвращает обработчики для управления задачами"""
    from telegram.ext import CommandHandler

    return [
        CommandHandler("tasks", tasks_handler),
        CommandHandler("schedule_publish", schedule_publish_handler)
    ]