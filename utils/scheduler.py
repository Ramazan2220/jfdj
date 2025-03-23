import logging
import time
import threading
import schedule
import datetime

from database.db_manager import get_pending_tasks, update_publish_task_status
from instagram.profile_manager import ProfileManager
from instagram.post_manager import PostManager
from instagram.reels_manager import ReelsManager
from database.db_manager import get_scheduled_tasks

logger = logging.getLogger(__name__)

def execute_task(task):
    """Выполнение запланированной задачи"""
    try:
        logger.info(f"Выполнение запланированной задачи {task.id} типа {task.task_type}")

        # Выбираем менеджер в зависимости от типа задачи
        if task.task_type == 'profile':
            manager = ProfileManager(task.account_id)
            success, error = manager.execute_profile_task(task)
        elif task.task_type in ['post', 'mosaic']:
            manager = PostManager(task.account_id)
            success, error = manager.execute_post_task(task)
        elif task.task_type == 'reel':
            manager = ReelsManager(task.account_id)
            success, error = manager.execute_reel_task(task)
        else:
            logger.error(f"Неизвестный тип задачи: {task.task_type}")
            update_task_status(task.id, 'failed', error_message=f"Неизвестный тип задачи: {task.task_type}")
            return

        if success:
            logger.info(f"Задача {task.id} выполнена успешно")
        else:
            logger.error(f"Задача {task.id} не выполнена: {error}")
    except Exception as e:
        logger.error(f"Ошибка при выполнении задачи {task.id}: {e}")
        update_task_status(task.id, 'failed', error_message=str(e))

def check_scheduled_tasks():
    """Проверка и выполнение запланированных задач"""
    try:
        # Получаем текущее время
        now = datetime.datetime.utcnow()

        # Получаем все запланированные задачи
        tasks = get_scheduled_tasks()

        for task in tasks:
            # Если время выполнения задачи наступило или прошло
            if task.scheduled_time and task.scheduled_time <= now:
                # Запускаем выполнение задачи в отдельном потоке
                threading.Thread(target=execute_task, args=(task,)).start()
    except Exception as e:
        logger.error(f"Ошибка при проверке запланированных задач: {e}")

def start_scheduler():
    """Запуск планировщика задач"""
    try:
        # Проверяем запланированные задачи каждую минуту
        schedule.every(1).minutes.do(check_scheduled_tasks)

        logger.info("Планировщик задач запущен")

        # Бесконечный цикл для выполнения запланированных задач
        while True:
            schedule.run_pending()
            time.sleep(10)  # Пауза между проверками
    except Exception as e:
        logger.error(f"Ошибка в планировщике задач: {e}")