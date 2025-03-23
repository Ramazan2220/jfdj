import os
import logging
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from config import DATABASE_URL
from database.models import Base, InstagramAccount, Proxy, PublishTask, TaskStatus

logger = logging.getLogger(__name__)

# Создаем директорию для базы данных, если она не существует
os.makedirs(os.path.dirname(DATABASE_URL.replace("sqlite:///", "")), exist_ok=True)

# Создаем движок SQLAlchemy
engine = create_engine(DATABASE_URL)

# Создаем фабрику сессий
Session = sessionmaker(bind=engine)

def init_db():
    """Инициализирует базу данных"""
    Base.metadata.create_all(engine)
    logger.info("База данных инициализирована")

def get_session():
    """Возвращает новую сессию базы данных"""
    return Session()

def add_instagram_account(username, password, email=None, email_password=None):
    """Добавляет новый аккаунт Instagram в базу данных"""
    try:
        session = get_session()

        # Проверяем, существует ли уже аккаунт с таким именем пользователя
        existing_account = session.query(InstagramAccount).filter_by(username=username).first()
        if existing_account:
            session.close()
            return False, "Аккаунт с таким именем пользователя уже существует"

        # Создаем новый аккаунт
        account = InstagramAccount(
            username=username,
            password=password,
            email=email,
            email_password=email_password,
            is_active=True
        )

        session.add(account)
        session.commit()
        account_id = account.id
        session.close()

        return True, account_id
    except Exception as e:
        logger.error(f"Ошибка при добавлении аккаунта: {e}")
        return False, str(e)

def get_instagram_account(account_id):
    """Получает аккаунт Instagram по ID"""
    try:
        session = get_session()
        account = session.query(InstagramAccount).filter_by(id=account_id).first()
        session.close()
        return account
    except Exception as e:
        logger.error(f"Ошибка при получении аккаунта: {e}")
        return None

def get_instagram_accounts():
    """Получает список всех аккаунтов Instagram"""
    try:
        session = get_session()
        accounts = session.query(InstagramAccount).all()
        session.close()
        return accounts
    except Exception as e:
        logger.error(f"Ошибка при получении списка аккаунтов: {e}")
        return []

def update_instagram_account(account_id, **kwargs):
    """Обновляет данные аккаунта Instagram"""
    try:
        session = get_session()
        account = session.query(InstagramAccount).filter_by(id=account_id).first()

        if not account:
            session.close()
            return False, "Аккаунт не найден"

        # Обновляем поля аккаунта
        for key, value in kwargs.items():
            if hasattr(account, key):
                setattr(account, key, value)

        session.commit()
        session.close()

        return True, None
    except Exception as e:
        logger.error(f"Ошибка при обновлении аккаунта: {e}")
        return False, str(e)

def delete_instagram_account(account_id):
    """Удаляет аккаунт Instagram"""
    try:
        session = get_session()
        account = session.query(InstagramAccount).filter_by(id=account_id).first()

        if not account:
            session.close()
            return False, "Аккаунт не найден"

        session.delete(account)
        session.commit()
        session.close()

        return True, None
    except Exception as e:
        logger.error(f"Ошибка при удалении аккаунта: {e}")
        return False, str(e)

def add_proxy(proxy_type, host, port, username=None, password=None):
    """Добавляет новый прокси в базу данных"""
    try:
        session = get_session()

        # Проверяем, существует ли уже прокси с такими параметрами
        existing_proxy = session.query(Proxy).filter_by(
            proxy_type=proxy_type,
            host=host,
            port=port
        ).first()

        if existing_proxy:
            session.close()
            return False, "Прокси с такими параметрами уже существует"

        # Создаем новый прокси
        proxy = Proxy(
            proxy_type=proxy_type,
            host=host,
            port=port,
            username=username,
            password=password,
            is_active=True
        )

        session.add(proxy)
        session.commit()
        proxy_id = proxy.id
        session.close()

        return True, proxy_id
    except Exception as e:
        logger.error(f"Ошибка при добавлении прокси: {e}")
        return False, str(e)

def get_proxy(proxy_id):
    """Получает прокси по ID"""
    try:
        session = get_session()
        proxy = session.query(Proxy).filter_by(id=proxy_id).first()
        session.close()
        return proxy
    except Exception as e:
        logger.error(f"Ошибка при получении прокси: {e}")
        return None

def get_proxies():
    """Получает список всех прокси"""
    try:
        session = get_session()
        proxies = session.query(Proxy).all()
        session.close()
        return proxies
    except Exception as e:
        logger.error(f"Ошибка при получении списка прокси: {e}")
        return []

def update_proxy(proxy_id, **kwargs):
    """Обновляет данные прокси"""
    try:
        session = get_session()
        proxy = session.query(Proxy).filter_by(id=proxy_id).first()

        if not proxy:
            session.close()
            return False, "Прокси не найден"

        # Обновляем поля прокси
        for key, value in kwargs.items():
            if hasattr(proxy, key):
                setattr(proxy, key, value)

        session.commit()
        session.close()

        return True, None
    except Exception as e:
        logger.error(f"Ошибка при обновлении прокси: {e}")
        return False, str(e)

def delete_proxy(proxy_id):
    """Удаляет прокси"""
    try:
        session = get_session()
        proxy = session.query(Proxy).filter_by(id=proxy_id).first()

        if not proxy:
            session.close()
            return False, "Прокси не найден"

        session.delete(proxy)
        session.commit()
        session.close()

        return True, None
    except Exception as e:
        logger.error(f"Ошибка при удалении прокси: {e}")
        return False, str(e)

def assign_proxy_to_account(account_id, proxy_id):
    """Назначает прокси аккаунту"""
    try:
        session = get_session()
        account = session.query(InstagramAccount).filter_by(id=account_id).first()
        proxy = session.query(Proxy).filter_by(id=proxy_id).first()

        if not account:
            session.close()
            return False, "Аккаунт не найден"

        if not proxy:
            session.close()
            return False, "Прокси не найден"

        account.proxy_id = proxy_id
        session.commit()
        session.close()

        return True, None
    except Exception as e:
        logger.error(f"Ошибка при назначении прокси аккаунту: {e}")
        return False, str(e)

def create_publish_task(account_id, task_type, media_path, caption="", scheduled_time=None):
    """Создает новую задачу на публикацию"""
    try:
        session = get_session()

        task = PublishTask(
            account_id=account_id,
            task_type=task_type,
            media_path=media_path,
            caption=caption,
            status=TaskStatus.PENDING,
            scheduled_time=scheduled_time
        )

        session.add(task)
        session.commit()
        task_id = task.id
        session.close()

        return True, task_id
    except Exception as e:
        logger.error(f"Ошибка при создании задачи: {e}")
        return False, str(e)

def update_publish_task_status(task_id, status, error_message=None, media_id=None):
    """Обновляет статус задачи на публикацию"""
    try:
        session = get_session()
        task = session.query(PublishTask).filter_by(id=task_id).first()

        if not task:
            session.close()
            return False, "Задача не найдена"

        task.status = status
        task.error_message = error_message
        task.media_id = media_id

        if status == TaskStatus.COMPLETED:
            task.completed_at = datetime.now()

        session.commit()
        session.close()

        return True, None
    except Exception as e:
        logger.error(f"Ошибка при обновлении статуса задачи: {e}")
        return False, str(e)

def update_task_status(task_id, status, error_message=None, media_id=None):
    """
    Обновляет статус задачи публикации
    Эта функция является алиасом для update_publish_task_status
    """
    return update_publish_task_status(task_id, status, error_message, media_id)

def get_publish_task(task_id):
    """Получает задачу на публикацию по ID"""
    try:
        session = get_session()
        task = session.query(PublishTask).filter_by(id=task_id).first()
        session.close()
        return task
    except Exception as e:
        logger.error(f"Ошибка при получении задачи: {e}")
        return None

def get_publish_tasks(account_id=None, status=None):
    """Получает список задач на публикацию"""
    try:
        session = get_session()
        query = session.query(PublishTask)

        if account_id:
            query = query.filter_by(account_id=account_id)

        if status:
            query = query.filter_by(status=status)

        tasks = query.all()
        session.close()
        return tasks
    except Exception as e:
        logger.error(f"Ошибка при получении списка задач: {e}")
        return []

def get_pending_tasks():
    """Получает список задач, ожидающих выполнения"""
    try:
        session = get_session()
        tasks = session.query(PublishTask).filter_by(status=TaskStatus.PENDING).all()
        session.close()
        return tasks
    except Exception as e:
        logger.error(f"Ошибка при получении списка ожидающих задач: {e}")
        return []

def get_scheduled_tasks():
    """Получает список запланированных задач, готовых к выполнению"""
    # Временно отключаем функционал запланированных задач
    return []

def delete_publish_task(task_id):
    """Удаляет задачу на публикацию"""
    try:
        session = get_session()
        task = session.query(PublishTask).filter_by(id=task_id).first()

        if not task:
            session.close()
            return False, "Задача не найдена"

        session.delete(task)
        session.commit()
        session.close()

        return True, None
    except Exception as e:
        logger.error(f"Ошибка при удалении задачи: {e}")
        return False, str(e)

def bulk_add_instagram_accounts(accounts_data):
    """
    Массовое добавление аккаунтов Instagram

    Args:
        accounts_data (list): Список словарей с данными аккаунтов
            [
                {
                    "username": "user1",
                    "password": "pass1",
                    "proxy_id": None,  # опционально
                    "description": ""  # опционально
                },
                ...
            ]

    Returns:
        tuple: (успешно_добавленные, ошибки)
    """
    session = get_session()
    success = []
    errors = []

    for data in accounts_data:
        try:
            # Проверяем, существует ли уже аккаунт
            existing = session.query(InstagramAccount).filter_by(username=data["username"]).first()
            if existing:
                errors.append((data["username"], "Аккаунт уже существует"))
                continue

            # Создаем новый аккаунт
            account = InstagramAccount(
                username=data["username"],
                password=data["password"],
                is_active=True,
                proxy_id=data.get("proxy_id"),
                email=data.get("email"),
                email_password=data.get("email_password")
            )

            session.add(account)
            session.commit()
            success.append(data["username"])

        except Exception as e:
            session.rollback()
            errors.append((data["username"], str(e)))

    session.close()
    return success, errors

def update_account_session_data(account_id, session_data):
    """Обновляет данные сессии аккаунта Instagram"""
    try:
        session = get_session()
        account = session.query(InstagramAccount).filter_by(id=account_id).first()

        if not account:
            session.close()
            return False, "Аккаунт не найден"

        account.session_data = session_data
        account.last_login = datetime.now()
        
        session.commit()
        session.close()

        return True, None
    except Exception as e:
        logger.error(f"Ошибка при обновлении данных сессии аккаунта: {e}")
        return False, str(e)

def get_active_accounts():
    """Получает список активных аккаунтов Instagram"""
    try:
        session = get_session()
        accounts = session.query(InstagramAccount).filter_by(is_active=True).all()
        session.close()
        return accounts
    except Exception as e:
        logger.error(f"Ошибка при получении списка активных аккаунтов: {e}")
        return []

def get_accounts_with_email():
    """Получает список аккаунтов с указанной электронной почтой"""
    try:
        session = get_session()
        accounts = session.query(InstagramAccount).filter(
            InstagramAccount.email != None,
            InstagramAccount.email != ""
        ).all()
        session.close()
        return accounts
    except Exception as e:
        logger.error(f"Ошибка при получении списка аккаунтов с email: {e}")
        return []


def update_account_session_data(account_id, session_data, last_login=None):
    """Обновляет данные сессии аккаунта Instagram"""
    try:
        session = get_session()
        account = session.query(InstagramAccount).filter_by(id=account_id).first()

        if not account:
            session.close()
            return False, "Аккаунт не найден"

        account.session_data = session_data
        if last_login:
            account.last_login = last_login
        else:
            account.last_login = datetime.now()

        session.commit()
        session.close()

        return True, None
    except Exception as e:
        logger.error(f"Ошибка при обновлении данных сессии аккаунта: {e}")
        return False, str(e)
