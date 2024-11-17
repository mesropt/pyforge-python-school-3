import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from dotenv import load_dotenv

from src.main import app
from src.database import Base, get_db
from src.models import Molecule

# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Путь к корню проекта. С ним формируем
# load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env.local"))

# Подключение к тестовой базе данных
# TEST_DATABASE_URL = os.getenv("DATABASE_URL")
TEST_DATABASE_URL="postgresql+psycopg2://chemuser:password@postgres:5432/chemdb"
print(TEST_DATABASE_URL)

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создаем фикстуру для базы данных
@pytest.fixture(scope="function")
def test_db():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    try:
        yield session
    finally:
        transaction.rollback()
        connection.close()


# Заменяем зависимость get_db на фикстуру test_db
@pytest.fixture(scope="function")
def client(test_db):
    def override_get_db():
        try:
            yield test_db
        finally:
            test_db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_get_all_molecules(client, test_db):
    test_db.query(Molecule).delete()
    test_db.commit()

    test_molecules = [
        Molecule(name="Water", smiles="O", weight=18.015, formula="H2O"),
        Molecule(name="Ethanol", smiles="CCO", weight=46.07, formula="C2H6O"),
    ]
    test_db.add_all(test_molecules)
    test_db.commit()

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


def test_add_molecule(client, test_db):
    molecule_data = {
        "name": "Benzene",
        "smiles": "c1ccccc1",
        "weight": 78.11,
        "formula": "C6H6"
    }

    response = client.post("/add/molecule", json=molecule_data)
    assert response.status_code == 200

    data = response.json()
    assert data["molecule"]["name"] == molecule_data["name"]
    assert data["molecule"]["smiles"] == molecule_data["smiles"]


def test_get_molecule_by_id(client, test_db):
    molecule = Molecule(name="Methane", smiles="C", weight=16.04, formula="CH4")
    test_db.add(molecule)
    test_db.commit()

    response = client.get(f"/molecule/{molecule.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == molecule.name
    assert data["smiles"] == molecule.smiles


def test_update_molecule(client, test_db):
    molecule = Molecule(name="Propane", smiles="CCC", weight=44.10, formula="C3H8")
    test_db.add(molecule)
    test_db.commit()

    updated_data = {
        "name": "Propene",
        "smiles": "C=CC",
        "weight": 42.08,
        "formula": "C3H6"
    }

    response = client.put(f"/update/molecule/{molecule.id}", json=updated_data)
    assert response.status_code == 200

    data = response.json()
    assert data["molecule"]["name"] == updated_data["name"]
    assert data["molecule"]["smiles"] == updated_data["smiles"]


def test_delete_molecule(client, test_db):
    molecule = Molecule(name="Butane", smiles="CCCC", weight=58.12, formula="C4H10")
    test_db.add(molecule)
    test_db.commit()

    response = client.delete(f"/delete/molecule/{molecule.id}")
    assert response.status_code == 200

    data = response.json()
    assert f"Molecule with id {molecule.id} deleted successfully." in data["detail"]

    # Проверяем, что молекула действительно удалена
    deleted_molecule = test_db.query(Molecule).filter(Molecule.id == molecule.id).first()
    assert deleted_molecule is None


def test_substructure_search(client, test_db):
    test_molecules = [
        Molecule(name="Phenol", smiles="c1ccccc1O", weight=94.11, formula="C6H6O"),
        Molecule(name="Cyclohexane", smiles="C1CCCCC1", weight=84.16, formula="C6H12"),
    ]
    test_db.add_all(test_molecules)
    test_db.commit()

    substructure = "c1ccccc1"  # Benzene ring
    response = client.get(f"/substructure_search?substructure={substructure}")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Phenol"
    assert data[0]["smiles"] == "c1ccccc1O"
