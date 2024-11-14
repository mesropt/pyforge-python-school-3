# 1. Используем базовый образ с Python 3.12
FROM python:3.12

# 2. Устанавливаем зависимости для PostgreSQL клиента и RDKit
RUN apt-get update && \
    apt-get install -y \
    libpq-dev \
    build-essential \
    cmake \
    libboost-dev \
    libboost-system-dev \
    libboost-iostreams-dev \
    libeigen3-dev \
    wget && \
    rm -rf /var/lib/apt/lists/*

# 3. Создаем рабочую директорию
WORKDIR /cont_prj_folder

# 4. Копируем requirements.txt и устанавливаем зависимости через pip, включая RDKit
COPY requirements.txt /cont_prj_folder/
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 5. Копируем код приложения в контейнер
COPY . /cont_prj_folder

# 6. Открываем порт для приложения
EXPOSE 8010

# 7. Запускаем сервер FastAPI с Uvicorn, доступный на порту 8010, с автоматической перезагрузкой
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8010", "--reload"]
