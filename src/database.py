import os
from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

###
# Определяем, какое окружение используется (по умолчанию - локальное)
environment = os.getenv("ENVIRONMENT", "local")

# Загружаем соответствующий файл окружения
env_file = f".env.{environment}"
if os.path.exists(env_file):
    load_dotenv(env_file)
else:
    load_dotenv(".env.local")  # Файл по умолчанию, если ENVIRONMENT не указан

# Получаем строку подключения из переменных окружения
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("DATABASE_URL is not set. Check your .env configuration.")
###

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Логирование текущей конфигурации (для отладки)
if __name__ == "__main__":
    print(f"Loaded environment: {environment}")
    print(f"Database URL: {SQLALCHEMY_DATABASE_URL}")