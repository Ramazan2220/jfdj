import logging
import os
from pathlib import Path
import concurrent.futures

from instagram.client import InstagramClient
from database.db_manager import update_task_status, get_instagram_accounts
from config import MAX_WORKERS

logger = logging.getLogger(__name__)

class ReelsManager:
    def __init__(self, account_id):
        self.instagram = InstagramClient(account_id)

    def publish_reel(self, video_path, caption=None, thumbnail_path=None):
        """Публикация видео в Reels"""
        try:
            # Проверяем статус входа
            if not self.instagram.check_login():
                logger.error(f"Не удалось войти в аккаунт для публикации Reels")
                return False, "Ошибка входа в аккаунт"

            # Проверяем существование файла
            if not os.path.exists(video_path):
                logger.error(f"Файл {video_path} не найден")
                return False, f"Файл не найден: {video_path}"

            # Публикуем Reels
            media = self.instagram.client.clip_upload(
                Path(video_path),
                caption=caption or "",
                thumbnail=Path(thumbnail_path) if thumbnail_path and os.path.exists(thumbnail_path) else None
            )

            logger.info(f"Reels успешно опубликован: {media.pk}")
            return True, media.pk
        except Exception as e:
            logger.error(f"Ошибка при публикации Reels: {e}")
            return False, str(e)

    def execute_reel_task(self, task):
        """Выполнение задачи по публикации Reels"""
        try:
            # Обновляем статус задачи
            update_task_status(task.id, 'processing')

            # Публикуем Reels
            success, result = self.publish_reel(task.media_path, task.caption)

            if success:
                update_task_status(task.id, 'completed')
                logger.info(f"Задача {task.id} по публикации Reels выполнена успешно")
                return True, None
            else:
                update_task_status(task.id, 'failed', error_message=result)
                logger.error(f"Задача {task.id} по публикации Reels не выполнена: {result}")
                return False, result
        except Exception as e:
            update_task_status(task.id, 'failed', error_message=str(e))
            logger.error(f"Ошибка при выполнении задачи {task.id} по публикации Reels: {e}")
            return False, str(e)

def publish_reels_in_parallel(video_path, caption, account_ids):
    """Публикация Reels в несколько аккаунтов параллельно"""
    results = {}

    def publish_to_account(account_id):
        manager = ReelsManager(account_id)
        success, result = manager.publish_reel(video_path, caption)
        return account_id, success, result

    # Используем ThreadPoolExecutor для параллельной публикации
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(publish_to_account, account_id) for account_id in account_ids]

        for future in concurrent.futures.as_completed(futures):
            try:
                account_id, success, result = future.result()
                results[account_id] = {'success': success, 'result': result}
            except Exception as e:
                logger.error(f"Ошибка при параллельной публикации: {e}")

    return results