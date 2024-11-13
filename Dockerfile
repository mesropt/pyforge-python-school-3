# 1. Используем базовый образ с Miniconda
FROM continuumio/miniconda3

# 2. Устанавливаем рабочую директорию в контейнере
WORKDIR /cont_prj_folder

# 3. Копируем всё приложение в контейнер
COPY . /cont_prj_folder

# 4. Копируем упакованное виртуальное окружение
COPY my-rdkit-env.tar.gz /opt/conda/envs/

# 5. Распаковываем окружение в нужную директорию
RUN mkdir /opt/conda/envs/my-rdkit-env && tar -xzf /opt/conda/envs/my-rdkit-env.tar.gz -C /opt/conda/envs/my-rdkit-env

# 6. Опционально делаем окружение перемещаемым
RUN /opt/conda/envs/my-rdkit-env/bin/conda-unpack

# 7. Автоматически активируем виртуальное окружение при запуске контейнера
RUN echo "conda activate /opt/conda/envs/my-rdkit-env" >> ~/.bashrc

# 8. Устанавливаем клиент PostgreSQL
RUN apt-get update && apt-get install -y postgresql-client

# 9. Открываем порт приложения
EXPOSE 8010

# 10. Запускаем FastAPI с Uvicorn, используя conda run и указав путь к окружению
CMD ["conda", "run", "--no-capture-output", "-p", "/opt/conda/envs/my-rdkit-env", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8010", "--reload"]
