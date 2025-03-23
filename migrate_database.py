
import os
import sys
import logging
from sqlalchemy import create_engine, Column, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from alembic import op
import sqlalchemy as sa

# Настраиваем логирование
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Путь к корневой директории проекта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

# Импортируем конфигурацию
from config import DATABASE_URL

# Создаем движок SQLAlchemy
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def upgrade_database():
    """Обновляет структуру базы данных"""
    try:
        # Подключаемся к базе данных
        connection = engine.connect()
        
        # Проверяем, существуют ли уже новые колонки
        inspector = sa.inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('instagram_accounts')]
        
        # Добавляем новые колонки, если их нет
        if 'email' not in columns:
            logger.info("Добавление колонки 'email'")
            connection.execute('ALTER TABLE instagram_accounts ADD COLUMN email VARCHAR(255)')
        
        if 'email_password' not in columns:
            logger.info("Добавление колонки 'email_password'")
            connection.execute('ALTER TABLE instagram_accounts ADD COLUMN email_password VARCHAR(255)')
        
        if 'session_data' not in columns:
            logger.info("Добавление колонки 'session_data'")
            connection.execute('ALTER TABLE instagram_accounts ADD COLUMN session_data TEXT')
        
        if 'last_login' not in columns:
            logger.info("Добавление колонки 'last_login'")
            connection.execute('ALTER TABLE instagram_accounts ADD COLUMN last_login DATETIME')
        
        connection.close()
        logger.info("Миграция базы данных успешно завершена")
        return True
    except Exception as e:
        logger.error(f"Ошибка при миграции базы данных: {e}")
        return False

if __name__ == "__main__":
    logger.info("Запуск миграции базы данных...")
    success = upgrade_database()
    if success:
        logger.info("Миграция успешно завершена")
    else:
        logger.error("Миграция завершилась с ошибками")
