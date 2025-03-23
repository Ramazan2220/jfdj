import json
import os
import time
import shutil
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters

from config import ACCOUNTS_DIR, ADMIN_USER_IDS, MEDIA_DIR
from database.db_manager import get_session, get_instagram_accounts, bulk_add_instagram_accounts, delete_instagram_account, get_instagram_account
from database.models import InstagramAccount, PublishTask
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, BadPassword, ChallengeRequired

# Состояния для добавления аккаунта
ENTER_USERNAME, ENTER_PASSWORD, CONFIRM_ACCOUNT, ENTER_VERIFICATION_CODE = range(4)

# Состояние для ожидания файла с аккаунтами
WAITING_ACCOUNTS_FILE = 10

def is_admin(user_id):
    return user_id in ADMIN_USER_IDS

def accounts_handler(update, context):
    keyboard = [
        [InlineKeyboardButton("➕ Добавить аккаунт", callback_data='add_account')],
        [InlineKeyboardButton("📋 Список аккаунтов", callback_data='list_accounts')],
        [InlineKeyboardButton("📤 Загрузить аккаунты", callback_data='upload_accounts')],
        [InlineKeyboardButton("⚙️ Настройка профиля", callback_data='profile_setup')],
        [InlineKeyboardButton("🔙 Назад", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        "🔧 *Меню управления аккаунтами*\n\n"
        "Выберите действие из списка ниже:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

def add_account(update, context):
    if update.callback_query:
        query = update.callback_query
        query.answer()

        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data='menu_accounts')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            "Пожалуйста, введите имя пользователя (логин) аккаунта Instagram:\n\n"
            "Или нажмите 'Назад' для возврата в меню аккаунтов.",
            reply_markup=reply_markup
        )
        return ENTER_USERNAME
    else:
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data='menu_accounts')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(
            "Пожалуйста, введите имя пользователя (логин) аккаунта Instagram:\n\n"
            "Или нажмите 'Назад' для возврата в меню аккаунтов.",
            reply_markup=reply_markup
        )
        return ENTER_USERNAME

def enter_username(update, context):
    username = update.message.text.strip()

    session = get_session()
    existing_account = session.query(InstagramAccount).filter_by(username=username).first()
    session.close()

    if existing_account:
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='menu_accounts')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(
            f"Аккаунт с именем пользователя '{username}' уже существует. "
            f"Пожалуйста, используйте другое имя пользователя или вернитесь в меню аккаунтов.",
            reply_markup=reply_markup
        )
        return ConversationHandler.END

    context.user_data['instagram_username'] = username

    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='menu_accounts')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        "Теперь введите пароль для этого аккаунта Instagram.\n\n"
        "⚠️ *Важно*: Ваш пароль будет храниться в зашифрованном виде и использоваться только для авторизации в Instagram.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    return ENTER_PASSWORD

def enter_password(update, context):
    password = update.message.text.strip()

    context.user_data['instagram_password'] = password

    username = context.user_data.get('instagram_username')

    keyboard = [
        [
            InlineKeyboardButton("✅ Да, добавить", callback_data='confirm_add_account'),
            InlineKeyboardButton("❌ Нет, отменить", callback_data='cancel_add_account')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        f"Вы собираетесь добавить аккаунт Instagram:\n\n"
        f"👤 *Имя пользователя*: `{username}`\n\n"
        f"Подтверждаете добавление этого аккаунта?",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

    # Удаляем сообщение с паролем для безопасности
    update.message.delete()

    return CONFIRM_ACCOUNT

def confirm_add_account(update, context):
    query = update.callback_query
    query.answer()

    username = context.user_data.get('instagram_username')
    password = context.user_data.get('instagram_password')

    if not username or not password:
        query.edit_message_text(
            "Произошла ошибка: данные аккаунта не найдены. Пожалуйста, попробуйте снова.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='menu_accounts')]])
        )
        return ConversationHandler.END

    # Сохраняем текущий текст сообщения, чтобы не пытаться установить тот же текст
    current_text = query.message.text
    new_text = "Проверка данных аккаунта Instagram... Это может занять некоторое время."

    # Изменяем текст сообщения только если он отличается от текущего
    if current_text != new_text:
        try:
            query.edit_message_text(new_text)
        except Exception as e:
            # Игнорируем ошибку, если не удалось изменить сообщение
            pass

    try:
        # Создаем клиент Instagram
        client = Client()

        # Сохраняем клиент для последующего использования
        context.user_data['instagram_client'] = client

        try:
            # Пытаемся войти
            client.login(username, password)

            # Если дошли до этой точки без исключений, значит вход успешен
            session = get_session()
            new_account = InstagramAccount(
                username=username,
                password=password,
                is_active=True
            )
            session.add(new_account)
            session.commit()
            account_id = new_account.id
            session.close()

            # Создаем директорию для аккаунта
            account_dir = os.path.join(ACCOUNTS_DIR, str(account_id))
            os.makedirs(account_dir, exist_ok=True)

            # Сохраняем сессию
            session_data = {
                'username': username,
                'account_id': account_id,
                'created_at': str(new_account.created_at),
                'settings': client.get_settings()
            }
            with open(os.path.join(account_dir, 'session.json'), 'w') as f:
                json.dump(session_data, f)

            keyboard = [[InlineKeyboardButton("🔙 К списку аккаунтов", callback_data='list_accounts')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Отправляем новое сообщение
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"✅ Аккаунт Instagram успешно добавлен!\n\n"
                     f"👤 *Имя пользователя*: `{username}`\n"
                     f"🆔 *ID аккаунта*: `{account_id}`\n\n"
                     f"Теперь вы можете использовать этот аккаунт для публикации контента.",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

        except ChallengeRequired:
            # Если требуется код подтверждения, переходим в состояние ожидания кода
            keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data='cancel_add_account')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Отправляем новое сообщение
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"📱 Instagram запрашивает код подтверждения для аккаунта {username}.\n\n"
                     f"Пожалуйста, проверьте вашу электронную почту или SMS и введите полученный код:",
                reply_markup=reply_markup
            )

            # Запрашиваем информацию о вызове
            try:
                challenge_info = client.last_json
                if challenge_info:
                    context.user_data['challenge_info'] = challenge_info
            except:
                pass

            return ENTER_VERIFICATION_CODE

        except (BadPassword, LoginRequired) as e:
            keyboard = [[InlineKeyboardButton("🔄 Попробовать снова", callback_data='add_account')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Отправляем новое сообщение
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Не удалось войти в аккаунт Instagram. Пожалуйста, проверьте правильность имени пользователя и пароля.",
                reply_markup=reply_markup
            )

    except Exception as e:
        keyboard = [[InlineKeyboardButton("🔄 Попробовать снова", callback_data='add_account')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Отправляем новое сообщение
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❌ Произошла ошибка при добавлении аккаунта: {str(e)}",
            reply_markup=reply_markup
        )

    # Очищаем данные, если не требуется код подтверждения
    if 'instagram_username' in context.user_data and 'challenge_info' not in context.user_data:
        del context.user_data['instagram_username']
    if 'instagram_password' in context.user_data and 'challenge_info' not in context.user_data:
        del context.user_data['instagram_password']
    if 'instagram_client' in context.user_data and 'challenge_info' not in context.user_data:
        del context.user_data['instagram_client']

    return ConversationHandler.END

def enter_verification_code(update, context):
    """Обработчик ввода кода подтверждения"""
    verification_code = update.message.text.strip()

    # Получаем сохраненные данные
    username = context.user_data.get('instagram_username')
    password = context.user_data.get('instagram_password')
    client = context.user_data.get('instagram_client')

    if not client or not username or not password:
        keyboard = [[InlineKeyboardButton("🔄 Попробовать снова", callback_data='add_account')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(
            "❌ Произошла ошибка: данные сессии утеряны. Пожалуйста, начните процесс добавления аккаунта заново.",
            reply_markup=reply_markup
        )
        return ConversationHandler.END

    try:
        # Отправляем сообщение о проверке кода
        message = update.message.reply_text("🔄 Проверка кода подтверждения...")

        # Получаем информацию о вызове
        challenge_info = context.user_data.get('challenge_info', {})

        # Используем код для подтверждения
        try:
            # Пытаемся отправить код подтверждения
            client.challenge_code(verification_code)

            # Пробуем войти снова с сохраненными учетными данными
            logged_in = client.login(username, password)

            # Если дошли до этой точки без исключений, значит вход успешен
            # Сохраняем аккаунт в базу данных
            session = get_session()
            new_account = InstagramAccount(
                username=username,
                password=password,
                is_active=True
            )
            session.add(new_account)
            session.commit()
            account_id = new_account.id
            session.close()

            # Создаем директорию для аккаунта
            account_dir = os.path.join(ACCOUNTS_DIR, str(account_id))
            os.makedirs(account_dir, exist_ok=True)

            # Сохраняем сессию
            session_data = {
                'username': username,
                'account_id': account_id,
                'created_at': str(new_account.created_at),
                'settings': client.get_settings()
            }
            with open(os.path.join(account_dir, 'session.json'), 'w') as f:
                json.dump(session_data, f)

            keyboard = [[InlineKeyboardButton("🔙 К списку аккаунтов", callback_data='list_accounts')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            message.edit_text(
                f"✅ Аккаунт Instagram успешно добавлен!\n\n"
                f"👤 *Имя пользователя*: `{username}`\n"
                f"🆔 *ID аккаунта*: `{account_id}`\n\n"
                f"Теперь вы можете использовать этот аккаунт для публикации контента.",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

        except Exception as e:
            # Если произошла ошибка при отправке кода, предлагаем попробовать снова
            keyboard = [
                [InlineKeyboardButton("🔄 Ввести код снова", callback_data='retry_verification_code')],
                [InlineKeyboardButton("🔙 Отмена", callback_data='cancel_add_account')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            message.edit_text(
                f"❌ Ошибка при проверке кода: {str(e)}\n\n"
                f"Пожалуйста, проверьте код и попробуйте снова.",
                reply_markup=reply_markup
            )

            # Сохраняем данные для повторной попытки
            return ENTER_VERIFICATION_CODE

    except Exception as e:
        keyboard = [[InlineKeyboardButton("🔄 Попробовать снова", callback_data='add_account')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(
            f"❌ Произошла ошибка при подтверждении кода: {str(e)}",
            reply_markup=reply_markup
        )

    # Очищаем данные
    if 'instagram_username' in context.user_data:
        del context.user_data['instagram_username']
    if 'instagram_password' in context.user_data:
        del context.user_data['instagram_password']
    if 'instagram_client' in context.user_data:
        del context.user_data['instagram_client']
    if 'challenge_info' in context.user_data:
        del context.user_data['challenge_info']

    return ConversationHandler.END

def cancel_add_account(update, context):
    """Обработчик отмены добавления аккаунта"""
    query = update.callback_query
    query.answer()

    # Очищаем данные
    if 'instagram_username' in context.user_data:
        del context.user_data['instagram_username']
    if 'instagram_password' in context.user_data:
        del context.user_data['instagram_password']
    if 'instagram_client' in context.user_data:
        del context.user_data['instagram_client']
    if 'challenge_handler' in context.user_data:
        del context.user_data['challenge_handler']

    keyboard = [[InlineKeyboardButton("🔙 К меню аккаунтов", callback_data='menu_accounts')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query.edit_message_text(
        "❌ Добавление аккаунта отменено.",
        reply_markup=reply_markup
    )

    return ConversationHandler.END

def list_accounts_handler(update, context):
    session = get_session()
    accounts = session.query(InstagramAccount).all()
    session.close()

    if update.callback_query:
        query = update.callback_query
        query.answer()

        if not accounts:
            keyboard = [
                [InlineKeyboardButton("➕ Добавить аккаунт", callback_data='add_account')],
                [InlineKeyboardButton("🔙 К меню аккаунтов", callback_data='menu_accounts')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
                "У вас пока нет добавленных аккаунтов Instagram.",
                reply_markup=reply_markup
            )
            return

        accounts_text = "📋 *Список ваших аккаунтов Instagram:*\n\n"
        keyboard = []

        for account in accounts:
            status = "✅ Активен" if account.is_active else "❌ Неактивен"
            accounts_text += f"👤 *{account.username}*\n"
            accounts_text += f"🆔 ID: `{account.id}`\n"
            accounts_text += f"📅 Добавлен: {account.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            accounts_text += f"📊 Статус: {status}\n\n"

            # Добавляем кнопку удаления для каждого аккаунта
            keyboard.append([InlineKeyboardButton(f"🗑️ Удалить {account.username}", callback_data=f'delete_account_{account.id}')])

        # Добавляем кнопку для удаления всех аккаунтов
        if accounts:
            keyboard.append([InlineKeyboardButton("🗑️ Удалить все аккаунты", callback_data='delete_all_accounts')])

        keyboard.append([InlineKeyboardButton("🔄 Проверить валидность", callback_data='check_accounts_validity')])
        keyboard.append([InlineKeyboardButton("🔙 К меню аккаунтов", callback_data='menu_accounts')])

        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            accounts_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        if not accounts:
            keyboard = [
                [InlineKeyboardButton("➕ Добавить аккаунт", callback_data='add_account')],
                [InlineKeyboardButton("🔙 К меню аккаунтов", callback_data='menu_accounts')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            update.message.reply_text(
                "У вас пока нет добавленных аккаунтов Instagram.",
                reply_markup=reply_markup
            )
            return

        accounts_text = "📋 *Список ваших аккаунтов Instagram:*\n\n"
        keyboard = []

        for account in accounts:
            status = "✅ Активен" if account.is_active else "❌ Неактивен"
            accounts_text += f"👤 *{account.username}*\n"
            accounts_text += f"🆔 ID: `{account.id}`\n"
            accounts_text += f"📅 Добавлен: {account.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            accounts_text += f"📊 Статус: {status}\n\n"

            # Добавляем кнопку удаления для каждого аккаунта
            keyboard.append([InlineKeyboardButton(f"🗑️ Удалить {account.username}", callback_data=f'delete_account_{account.id}')])

        # Добавляем кнопку для удаления всех аккаунтов
        if accounts:
            keyboard.append([InlineKeyboardButton("🗑️ Удалить все аккаунты", callback_data='delete_all_accounts')])

        keyboard.append([InlineKeyboardButton("🔄 Проверить валидность", callback_data='check_accounts_validity')])
        keyboard.append([InlineKeyboardButton("🔙 К меню аккаунтов", callback_data='menu_accounts')])

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(
            accounts_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

def delete_account_handler(update, context):
    """Обработчик для удаления аккаунта"""
    query = update.callback_query
    query.answer()

    # Получаем ID аккаунта из callback_data
    account_id = int(query.data.split('_')[2])

    # Получаем информацию об аккаунте
    account = get_instagram_account(account_id)

    if not account:
        keyboard = [[InlineKeyboardButton("🔙 К списку аккаунтов", callback_data='list_accounts')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            "Аккаунт не найден.",
            reply_markup=reply_markup
        )
        return

    try:
        session = get_session()

        # Сначала удаляем связанные задачи
        session.query(PublishTask).filter_by(account_id=account_id).delete()

        # Затем удаляем аккаунт
        account = session.query(InstagramAccount).filter_by(id=account_id).first()
        if account:
            session.delete(account)
            session.commit()

            # Удаляем файл сессии, если он существует
            session_dir = os.path.join(ACCOUNTS_DIR, str(account_id))
            if os.path.exists(session_dir):
                shutil.rmtree(session_dir)

            keyboard = [[InlineKeyboardButton("🔙 К списку аккаунтов", callback_data='list_accounts')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
                f"✅ Аккаунт {account.username} успешно удален.",
                reply_markup=reply_markup
            )
        else:
            keyboard = [[InlineKeyboardButton("🔙 К списку аккаунтов", callback_data='list_accounts')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
                "Аккаунт не найден.",
                reply_markup=reply_markup
            )
    except Exception as e:
        session.rollback()

        keyboard = [[InlineKeyboardButton("🔙 К списку аккаунтов", callback_data='list_accounts')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            f"❌ Ошибка при удалении аккаунта: {str(e)}",
            reply_markup=reply_markup
        )
    finally:
        session.close()

def delete_all_accounts_handler(update, context):
    query = update.callback_query
    query.answer()

    keyboard = [
        [
            InlineKeyboardButton("✅ Да, удалить все", callback_data='confirm_delete_all_accounts'),
            InlineKeyboardButton("❌ Нет, отмена", callback_data='list_accounts')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query.edit_message_text(
        "⚠️ Вы уверены, что хотите удалить ВСЕ аккаунты?\n\n"
        "Это действие нельзя отменить. Все данные аккаунтов будут удалены.",
        reply_markup=reply_markup
    )

def confirm_delete_all_accounts_handler(update, context):
    query = update.callback_query
    query.answer()

    try:
        session = get_session()

        # Сначала удаляем все связанные задачи
        session.query(PublishTask).delete()
        session.commit()

        # Затем удаляем все аккаунты
        accounts = session.query(InstagramAccount).all()
        for account in accounts:
            # Удаляем файлы сессий
            session_dir = os.path.join(ACCOUNTS_DIR, str(account.id))
            if os.path.exists(session_dir):
                shutil.rmtree(session_dir)

        # Удаляем записи из базы данных
        session.query(InstagramAccount).delete()
        session.commit()

        keyboard = [[InlineKeyboardButton("🔙 К меню аккаунтов", callback_data='menu_accounts')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            "✅ Все аккаунты успешно удалены.",
            reply_markup=reply_markup
        )
    except Exception as e:
        session.rollback()

        keyboard = [[InlineKeyboardButton("🔙 К списку аккаунтов", callback_data='list_accounts')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            f"❌ Ошибка при удалении аккаунтов: {str(e)}",
            reply_markup=reply_markup
        )
    finally:
        session.close()

def check_accounts_validity_handler(update, context):
    query = update.callback_query
    query.answer()

    query.edit_message_text("🔄 Проверка валидности аккаунтов... Это может занять некоторое время.")

    session = get_session()
    accounts = session.query(InstagramAccount).all()

    if not accounts:
        keyboard = [[InlineKeyboardButton("🔙 К меню аккаунтов", callback_data='menu_accounts')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            "У вас нет добавленных аккаунтов для проверки.",
            reply_markup=reply_markup
        )
        session.close()
        return

    results = []

    for account in accounts:
        try:
            client = Client()

            # Проверяем наличие сессии
            session_file = os.path.join(ACCOUNTS_DIR, str(account.id), 'session.json')
            if os.path.exists(session_file):
                try:
                    with open(session_file, 'r') as f:
                        session_data = json.load(f)

                    if 'settings' in session_data:
                        client.set_settings(session_data['settings'])

                        # Проверяем валидность сессии
                        try:
                            client.get_timeline_feed()
                            results.append((account.username, True, "Сессия валидна"))
                            continue
                        except:
                            # Если сессия невалидна, пробуем войти с логином и паролем
                            pass
                except:
                    pass

            # Пробуем войти с логином и паролем
            try:
                client.login(account.username, account.password)

                # Сохраняем обновленную сессию
                os.makedirs(os.path.join(ACCOUNTS_DIR, str(account.id)), exist_ok=True)
                session_data = {
                    'username': account.username,
                    'account_id': account.id,
                    'updated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'settings': client.get_settings()
                }
                with open(session_file, 'w') as f:
                    json.dump(session_data, f)

                results.append((account.username, True, "Успешный вход"))
            except Exception as e:
                results.append((account.username, False, str(e)))
        except Exception as e:
            results.append((account.username, False, str(e)))

    session.close()

    # Формируем отчет
    report = "📊 *Результаты проверки аккаунтов:*\n\n"

    for username, is_valid, message in results:
        status = "✅ Валиден" if is_valid else "❌ Невалиден"
        report += f"👤 *{username}*: {status}\n"
        if not is_valid:
            report += f"📝 Причина: {message}\n"
        report += "\n"

    keyboard = [[InlineKeyboardButton("🔙 К списку аккаунтов", callback_data='list_accounts')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query.edit_message_text(
        report,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

def bulk_upload_accounts_command(update, context):
    if update.callback_query:
        query = update.callback_query
        query.answer()

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
    else:
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='menu_accounts')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(
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

def bulk_upload_accounts_file(update, context):
    # Сбрасываем флаг ожидания файла
    context.user_data['waiting_for_accounts_file'] = False

    file = update.message.document

    if not file.file_name.endswith('.txt'):
        keyboard = [[InlineKeyboardButton("🔙 К меню аккаунтов", callback_data='menu_accounts')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(
            "❌ Пожалуйста, отправьте файл в формате .txt",
            reply_markup=reply_markup
        )
        return ConversationHandler.END

    # Скачиваем файл
    file_path = os.path.join(MEDIA_DIR, file.file_name)
    file_obj = context.bot.get_file(file.file_id)
    file_obj.download(file_path)

    # Читаем файл
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        accounts = []
        for line in lines:
            line = line.strip()
            if not line or ':' not in line:
                continue

            parts = line.split(':', 1)
            if len(parts) != 2:
                continue

            username, password = parts
            accounts.append((username.strip(), password.strip()))

        if not accounts:
            keyboard = [[InlineKeyboardButton("🔙 К меню аккаунтов", callback_data='menu_accounts')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            update.message.reply_text(
                "❌ В файле не найдено аккаунтов в правильном формате.",
                reply_markup=reply_markup
            )
            return ConversationHandler.END

        # Добавляем аккаунты в базу данных
        added, skipped, errors = bulk_add_instagram_accounts(accounts)

        # Формируем отчет
        report = f"📊 *Результаты загрузки аккаунтов:*\n\n"
        report += f"✅ Успешно добавлено: {added}\n"
        report += f"⚠️ Пропущено (уже существуют): {skipped}\n"
        report += f"❌ Ошибки: {len(errors)}\n\n"

        if errors:
            report += "*Ошибки при добавлении:*\n"
            for username, error in errors:
                report += f"👤 *{username}*: {error}\n"

        keyboard = [[InlineKeyboardButton("🔙 К списку аккаунтов", callback_data='list_accounts')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(
            report,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    except Exception as e:
        keyboard = [[InlineKeyboardButton("🔙 К меню аккаунтов", callback_data='menu_accounts')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(
            f"❌ Произошла ошибка при обработке файла: {str(e)}",
            reply_markup=reply_markup
        )

    # Удаляем временный файл
    try:
        os.remove(file_path)
    except:
        pass

    return ConversationHandler.END

def profile_setup_handler(update, context):
    if update.callback_query:
        query = update.callback_query
        query.answer()

        keyboard = [[InlineKeyboardButton("🔙 К меню аккаунтов", callback_data='menu_accounts')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            "⚙️ Функция настройки профиля находится в разработке.\n\n"
            "Пожалуйста, попробуйте позже.",
            reply_markup=reply_markup
        )
    else:
        keyboard = [[InlineKeyboardButton("🔙 К меню аккаунтов", callback_data='menu_accounts')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(
            "⚙️ Функция настройки профиля находится в разработке.\n\n"
            "Пожалуйста, попробуйте позже.",
            reply_markup=reply_markup
        )

def get_account_handlers():
    """Возвращает обработчики для управления аккаунтами"""
    from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, Filters

    # Новый ConversationHandler для массовой загрузки аккаунтов
    bulk_upload_conversation = ConversationHandler(
        entry_points=[
            CommandHandler("upload_accounts", bulk_upload_accounts_command),
            CallbackQueryHandler(bulk_upload_accounts_command, pattern='^upload_accounts$')
        ],
        states={
            WAITING_ACCOUNTS_FILE: [
                MessageHandler(Filters.document.file_extension("txt"), bulk_upload_accounts_file),
                CallbackQueryHandler(lambda u, c: ConversationHandler.END, pattern='^menu_accounts$')
            ]
        },
        fallbacks=[CommandHandler("cancel", lambda update, context: ConversationHandler.END)]
    )

    return [
        CommandHandler("accounts", accounts_handler),
        # Удаляем account_conversation, так как он теперь регистрируется в bot.py
        bulk_upload_conversation,
        CommandHandler("list_accounts", list_accounts_handler),
        CommandHandler("profile_setup", profile_setup_handler),
        CallbackQueryHandler(delete_account_handler, pattern='^delete_account_\\d+$'),
        CallbackQueryHandler(delete_all_accounts_handler, pattern='^delete_all_accounts$'),
        CallbackQueryHandler(confirm_delete_all_accounts_handler, pattern='^confirm_delete_all_accounts$'),
        CallbackQueryHandler(check_accounts_validity_handler, pattern='^check_accounts_validity$')
    ]