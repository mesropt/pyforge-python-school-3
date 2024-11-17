# 1. Используем базовый образ с Python 3.12
FROM python:3.12

# 2. Создаем рабочую директорию
WORKDIR /cont_prj_folder

# 3. Копируем requirements.txt и устанавливаем зависимости через pip, включая RDKit
COPY requirements.txt /cont_prj_folder/
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    rm -rf /root/.cache/pip # явное удаление кеша пакетов после установки, чтобы уменьшить размер образа

# 4. Копируем код приложения в контейнер
COPY . /cont_prj_folder

# 5. Открываем порт для приложения
EXPOSE 8010

# 6. Запускаем сервер FastAPI с Uvicorn, доступный на порту 8010, с автоматической перезагрузкой
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8010", "--reload"]
