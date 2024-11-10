# 1. Use base image to install RDKit
FROM continuumio/miniconda3

# 2. Create venv
# (Здесь устанавливаю rdkit. Подумать)
RUN conda create -c conda-forge -n my-rdkit-env rdkit=2024.03.4 python=3.12 -y

# 3. Make working directory in the container
WORKDIR /app

# 4. Copy app code from local to the container
COPY . /app

# 5. Activate venv
# 5.1. ДОБАВИТЬ ИНСТРУКЦИЮ. Добавить команду активации виртуальной среды my-rdkit-env в файл .bashrc,
# чтобы она автоматически активировалась при запуске новой оболочки:
RUN echo "conda activate my-rdkit-env" >> ~/.bashrc
# Old version: RUN "conda activate my-rdkit-env"

# 5.2. ИСПОЛНИТЬ ИНСТРУКЦИЮ. Выполнить все команды (через оболочку /bin/bash),
# которые идут после этой строки в Dockerfile, внутри активированной my-rdkit-env с помощью conda (т.е. изменяем оболочку):
SHELL ["conda", "run", "-n", "my-rdkit-env", "/bin/bash", "-c"]

# Install FastAPI, Uvicorn and Redis into my-rdkit-env
RUN conda install -c conda-forge redis-py fastapi uvicorn -y
# redis-py is the Python client for Redis. Сам redis уже установлен в своём контейнере, то есть мне надо только
# подключиться к нему из приложения, для чего и нужен redis-py.

#(Optional) Install PostgreSQL client for connecting to the database from inside the container
RUN apt-get update && apt-get install -y postgresql-client

# Open the port for our app
# (Не обязательно, больше для явности, так как маппинг происходит в docker-compose.yaml)
EXPOSE 8010

# Run FastAPI server with Uvicorn
# (Запустить app в окружении my-rdkit-env через Uvicorn, сделав его доступным на порту 8010 и автоматически перезагружать при изменениях кода:)
CMD ["conda", "run", "--no-capture-output", "-n", "my-rdkit-env", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8010", "--reload"]
