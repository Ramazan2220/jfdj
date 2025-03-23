import logging
import os
from pathlib import Path

from instagram.client import InstagramClient
from database.db_manager import update_task_status

logger = logging.getLogger(__name__)

class ProfileManager:
    def __init__(self, account_id):
        self.instagram = InstagramClient(account_id)

    def update_profile(self, biography=None, avatar_path=None):
        """Обновление профиля Instagram"""
        try:
            # Проверяем статус входа
            if not self.instagram.check_login():
                logger.error(f"Не удалось войти в аккаунт для обновления профиля")
                return False, "Ошибка входа в аккаунт"

            # Обновляем биографию, если указана
            if biography:
                self.instagram.client.account_edit(biography=biography)
                logger.info(f"Биография обновлена для {self.instagram.account.username}")

            # Обновляем аватар, если указан
            if avatar_path and os.path.exists(avatar_path):
                self.instagram.client.account_change_picture(Path(avatar_path))
                logger.info(f"Аватар обновлен для {self.instagram.account.username}")

            return True, None
        except Exception as e:
            logger.error(f"Ошибка при обновлении профиля: {e}")
            return False, str(e)

    def execute_profile_task(self, task):
        """Выполнение задачи по обновлению профиля"""
        try:
            # Обновляем статус задачи
            update_task_status(task.id, 'processing')

            # Получаем путь к аватару, если есть
            avatar_path = task.media_path if task.media_path else None

            # Получаем описание профиля, если есть
            biography = task.caption if task.caption else None

            # Обновляем профиль
            success, error = self.update_profile(biography=biography, avatar_path=avatar_path)

            if success:
                update_task_status(task.id, 'completed')
                logger.info(f"Задача {task.id} по обновлению профиля выполнена успешно")
                return True, None
            else:
                update_task_status(task.id, 'failed', error_message=error)
                logger.error(f"Задача {task.id} по обновлению профиля не выполнена: {error}")
                return False, error
        except Exception as e:
            update_task_status(task.id, 'failed', error_message=str(e))
            logger.error(f"Ошибка при выполнении задачи {task.id} по обновлению профиля: {e}")
            return False, str(e)