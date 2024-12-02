import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.database import get_db
from src.models import Molecule


@pytest.fixture
def mock_postgres(mocker):
    """Fixture for mocking an SQLAlchemy session.

    Creates a MagicMock object that replaces the real database session
    for testing interactions with SQLAlchemy without accessing the actual database.
    """
    mock_session = mocker.MagicMock()
    return mock_session


@pytest.fixture
def fastapi_client(mock_postgres):
    """Fixture for creating a FastAPI client.

    Creates a FastAPI client (TestClient) with mocked dependencies:
    - The SQLAlchemy session is replaced by mock_postgres.
    - The Redis client is replaced by mock_redis.

    This allows testing endpoints without interacting with real external services.
    """
    def override_get_db(): # Replaces the get_db dependency with the test mock database
        yield mock_postgres

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.fixture
def sample_molecule():
    sample_molecule = Molecule(
        id=23,
        name="Benzene",
        smiles="c1ccccc1",
        weight=78.11,
        formula="C6H6"
    )
    return sample_molecule


@pytest.fixture
def sample_molecules():
    return [
        Molecule(id=219, name="Water", smiles="O", weight=18.015, formula="H2O"),
        Molecule(id=220, name="Methane", smiles="C", weight=16.04, formula="CH4"),
        Molecule(id=221, name="Ethanol", smiles="CCO", weight=46.07, formula="C2H6O"),
        Molecule(id=222, name="Glucose", smiles="C(C1C(C(C(C(O1)O)O)O)O)O", weight=180.16, formula="C6H12O6"),
        Molecule(id=223, name="Carbon Dioxide", smiles="O=C=O", weight=44.01, formula="CO2"),
        Molecule(id=224, name="Ammonia", smiles="N", weight=17.03, formula="NH3"),
        Molecule(id=225, name="Acetic Acid", smiles="CC(=O)O", weight=60.05, formula="C2H4O2"),
        Molecule(id=226, name="Acetone", smiles="CC(=O)C", weight=58.08, formula="C3H6O"),
        Molecule(id=227, name="Citric Acid", smiles="C(C(=O)O)C(CC(=O)O)(C(=O)O)O", weight=192.13, formula="C6H8O7"),
        Molecule(id=228, name="Caffeine", smiles="Cn1cnc2c1c(=O)n(c(=O)n2C)C", weight=194.19, formula="C8H10N4O2"),
        Molecule(id=229, name="Toluene", smiles="Cc1ccccc1", weight=92.14, formula="C7H8"),
        Molecule(id=230, name="Phenol", smiles="c1ccc(cc1)O", weight=94.11, formula="C6H6O"),
        Molecule(id=231, name="Formaldehyde", smiles="C=O", weight=30.03, formula="CH2O"),
        Molecule(id=232, name="Sucrose", smiles="C12C(C(C(O1)O)O)OC(C(C(C2O)O)O)CO", weight=342.3, formula="C12H22O11"),
        Molecule(id=233, name="Sulfuric Acid", smiles="OS(=O)(=O)O", weight=98.08, formula="H2SO4"),
        Molecule(id=234, name="Sodium Chloride", smiles="[Na+].[Cl-]", weight=58.44, formula="NaCl"),
        Molecule(id=235, name="Urea", smiles="C(=O)(N)N", weight=60.06, formula="CH4N2O"),
        Molecule(id=236, name="Hydrogen Peroxide", smiles="OO", weight=34.01, formula="H2O2"),
    ]


# Test retrieving all molecules
def test_get_all_molecules(fastapi_client, mock_postgres, sample_molecules):
    # Mock database query to return a list of molecules
    mock_postgres.query.return_value.offset.return_value.limit.return_value.all.return_value = sample_molecules

    response = fastapi_client.get(f"/molecules_list?skip=0&limit=100")
    assert response.status_code == 200

    data = response.json()

    assert len(data) == 18


def test_add_molecule(fastapi_client, mock_postgres):
    # Mock database query for checking molecule existence
    mock_postgres.query.return_value.filter.return_value.first.return_value = None

    # Mock method for refreshing the molecule
    mock_postgres.refresh.side_effect = lambda obj: setattr(obj, "id", 1)

    molecule_data = {
        "name": "Benzene",
        "smiles": "c1ccccc1",
        "weight": 78.11,
        "formula": "C6H6"
    }

    response = fastapi_client.post("/add/molecule", json=molecule_data)
    assert response.status_code == 200

    data = response.json()
    assert data["molecule"]["id"] == 1
    assert data["molecule"]["name"] == molecule_data["name"]
    assert data["molecule"]["smiles"] == molecule_data["smiles"]
    assert data["molecule"]["weight"] == molecule_data["weight"]
    assert data["molecule"]["formula"] == molecule_data["formula"]
    assert data["message"] == "Molecule added successfully."


def test_get_molecule_by_id(fastapi_client, mock_postgres, sample_molecule):
    mock_postgres.query.return_value.filter.return_value.first.return_value = sample_molecule

    response = fastapi_client.get(f"/molecule/{sample_molecule.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == sample_molecule.id
    assert data["name"] == sample_molecule.name
    assert data["smiles"] == sample_molecule.smiles
    assert data["weight"] == sample_molecule.weight
    assert data["formula"] == sample_molecule.formula


def test_update_molecule(fastapi_client, mock_postgres, sample_molecule):
    original_molecule = sample_molecule
    mock_postgres.query.return_value.filter.return_value.first.return_value = original_molecule

    updated_molecule = {
        "name": "Benzene Updated",
        "smiles": "c1ccccc1",
        "weight": 78.11,
        "formula": "C6H6"
    }

    response = fastapi_client.put(f"/update/molecule/{original_molecule.id}", json=updated_molecule)
    assert response.status_code == 200

    data = response.json()
    assert data["molecule"]["name"] == updated_molecule["name"]
    assert data["molecule"]["smiles"] == updated_molecule["smiles"]


def test_delete_molecule(fastapi_client, mock_postgres, sample_molecule):
    # Mock database query to return an existing molecule
    mock_postgres.query.return_value.filter.return_value.first.return_value = sample_molecule

    response = fastapi_client.delete(f"/delete/molecule/{sample_molecule.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["detail"] == f"Molecule with id {sample_molecule.id} deleted successfully."


# def test_sync_substructure_search(client, mock_db, sample_molecules):
#     mock_db.query.return_value.all.return_value = sample_molecules
#
#     substructure = "c1ccccc1"  # Benzene ring
#
#     response = client.get(f"/sync_substructure_search?substructure={substructure}")
#
#     assert response.status_code == 200
#
#     data = response.json()
#     assert len(data) == 2
