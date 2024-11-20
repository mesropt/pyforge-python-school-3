import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from src.main import app, redis_client, get_cached_result, set_cache
from src.database import get_db
from src.models import Molecule


TEST_DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(TEST_DATABASE_URL)  # объект подключения к базе данных
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)  # создаёт фабрику сессий для взаимодействия с базой


@pytest.fixture
def test_db():
    connection = engine.connect()  # создаёт прямое соединение с базой
    transaction = connection.begin()  # открывает транзакцию, чтобы откатить все изменения после тестов
    session = TestingSessionLocal(bind=connection)  # создаёт объект сессии для взаимодействия с базой

    try:
        yield session  # возвращает сессию тесту
    finally:
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(test_db):
    def override_get_db():  # заменяет зависимость get_db на фикстуру test_db для тестирования
        try:
            yield test_db
        finally:
            test_db.close()

    app.dependency_overrides[get_db] = override_get_db  # переопределяет зависимости в приложении
    return TestClient(app)  # клиент для отправки HTTP-запросов


@pytest.fixture
def clear_redis():
    redis_client.flushdb()  # очищает Redis перед каждым тестом
    yield # отдать контроль управления пайтесту
    redis_client.flushdb()  # очищает Redis после каждого теста


def test_get_molecule_by_id_with_cache(client, test_db, clear_redis):
    # Очистка таблицы Molecule
    test_db.query(Molecule).delete()
    test_db.commit()

    # Создание тестового молекулы
    test_molecule = Molecule(
        name="Water", smiles="O", weight=18.015, formula="H2O"
    )
    test_db.add(test_molecule)
    test_db.commit()

    # Получаем ID молекулы
    molecule_id = test_molecule.id

    # Проверяем первый запрос (должен попасть в базу и сохранить результат в кеш)
    response = client.get(f"/molecule/{molecule_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == molecule_id
    assert data["name"] == "Water"
    assert data["smiles"] == "O"
    assert data["weight"] == 18.015
    assert data["formula"] == "H2O"

    # Проверяем, что данные закешировались
    cache_key = f"molecule:{molecule_id}"
    cached_data = get_cached_result(cache_key)
    assert cached_data is not None
    assert cached_data["id"] == molecule_id
    assert cached_data["name"] == "Water"
    assert cached_data["smiles"] == "O"
    assert cached_data["weight"] == 18.015
    assert cached_data["formula"] == "H2O"

    # Проверяем второй запрос (должен использовать кеш)
    response_cached = client.get(f"/molecule/{molecule_id}")
    assert response_cached.status_code == 200

    cached_data_from_response = response_cached.json()
    assert cached_data_from_response == cached_data


def test_get_all_molecules_with_cache(client, test_db, clear_redis):
    # Очистка таблицы Molecule
    test_db.query(Molecule).delete()
    test_db.commit()

    # Создание тестовых данных
    test_molecules = [
        Molecule(name="Water", smiles="O", weight=18.015, formula="H2O"),
        Molecule(name="Ethanol", smiles="CCO", weight=46.07, formula="C2H6O"),
    ]
    test_db.add_all(test_molecules)
    test_db.commit()

    # Проверяем первый запрос (должен попасть в базу и сохранить результат в кеш)
    response = client.get("/molecules_list?skip=0&limit=10")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 2
    for molecule in data:
        assert "id" in molecule
        assert "name" in molecule
        assert "smiles" in molecule
        assert "weight" in molecule
        assert "formula" in molecule

    # Проверяем, что данные закешировались
    cache_key = "molecules_list:skip=0:limit=10"
    cached_data = get_cached_result(cache_key)
    assert cached_data is not None
    assert len(cached_data) == 2

    # Проверяем второй запрос (должен использовать кеш)
    response_cached = client.get("/molecules_list?skip=0&limit=10")
    assert response_cached.status_code == 200

    cached_data_from_response = response_cached.json()
    assert cached_data_from_response == cached_data
