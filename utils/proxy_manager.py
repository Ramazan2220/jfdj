import logging
import requests
import datetime
import concurrent.futures
from database.db_manager import get_proxies, update_instagram_account, get_instagram_accounts
from config import MAX_WORKERS

logger = logging.getLogger(__name__)

def check_proxy(proxy_id, proxy_url):
    """Проверка работоспособности прокси"""
    try:
        # Настраиваем прокси для запроса
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }

        # Делаем запрос к Google с таймаутом 10 секунд
        response = requests.get('https://www.google.com', proxies=proxies, timeout=10)

        # Если статус 200, прокси работает
        if response.status_code == 200:
            logger.info(f"Прокси {proxy_url} работает")
            return proxy_id, True, None
        else:
            logger.warning(f"Прокси {proxy_url} вернул статус {response.status_code}")
            return proxy_id, False, f"Статус {response.status_code}"
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при проверке прокси {proxy_url}: {e}")
        return proxy_id, False, str(e)

def check_all_proxies():
    """Проверка всех прокси в базе данных"""
    from database.db_manager import Session
    from database.models import Proxy

    session = Session()
    try:
        # Получаем все прокси
        proxies = get_proxies()
        results = {}

        # Проверяем прокси параллельно
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(check_proxy, proxy.id, proxy.get_url()) for proxy in proxies]

            for future in concurrent.futures.as_completed(futures):
                try:
                    proxy_id, is_working, error = future.result()

                    # Обновляем статус прокси в базе данных
                    proxy = session.query(Proxy).filter_by(id=proxy_id).first()
                    if proxy:
                        proxy.is_active = is_working
                        proxy.last_checked = datetime.datetime.utcnow()
                        session.commit()

                    results[proxy_id] = {'working': is_working, 'error': error}
                except Exception as e:
                    logger.error(f"Ошибка при обработке результата проверки прокси: {e}")

        return results
    except Exception as e:
        logger.error(f"Ошибка при проверке прокси: {e}")
        session.rollback()
        return {}
    finally:
        session.close()

def distribute_proxies():
    """Распределение прокси по аккаунтам Instagram"""
    try:
        # Получаем все активные прокси
        from database.db_manager import Session
        from database.models import Proxy

        session = Session()
        active_proxies = session.query(Proxy).filter_by(is_active=True).all()
        session.close()

        if not active_proxies:
            logger.warning("Нет активных прокси для распределения")
            return False, "Нет активных прокси"

        # Получаем все аккаунты
        accounts = get_instagram_accounts()

        if not accounts:
            logger.warning("Нет аккаунтов для назначения прокси")
            return False, "Нет аккаунтов"

        # Распределяем прокси циклически
        for i, account in enumerate(accounts):
            proxy = active_proxies[i % len(active_proxies)]
            update_instagram_account(account.id, proxy_id=proxy.id)
            logger.info(f"Аккаунту {account.username} назначен прокси {proxy.host}:{proxy.port}")

        return True, f"Прокси распределены между {len(accounts)} аккаунтами"
    except Exception as e:
        logger.error(f"Ошибка при распределении прокси: {e}")
        return False, str(e)