import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from src.main import app

client = TestClient(app)


@pytest.fixture
def mock_add_molecule():
    with patch('src.crud.add_molecule') as mock_add:
        yield mock_add


@pytest.fixture
def mock_get_molecule_by_id():
    with patch('src.crud.get_molecule_by_id') as mock_get:
        yield mock_get


@pytest.fixture
def mock_get_molecule_by_name():
    with patch('src.crud.get_molecule_by_name') as mock_get:
        yield mock_get


@pytest.fixture
def mock_get_all_molecules():
    with patch('src.crud.get_all_molecules') as mock_get:
        yield mock_get


@pytest.fixture
def mock_update_molecule():
    with patch('src.crud.update_molecule') as mock_update:
        yield mock_update


@pytest.fixture
def mock_delete_molecule():
    with patch('src.crud.delete_molecule') as mock_delete:
        yield mock_delete


def test_add_molecule(mock_add_molecule, mock_get_molecule_by_name):
    molecule_data = {
        "name": "Ethanol",
        "smiles": "CCO",
        "weight": 46.07,
        "formula": "C2H6O",
    }
    mock_get_molecule_by_name.return_value = None
    mock_add_molecule.return_value = {**molecule_data, "id": 1}

    response = client.post("/add/molecule", json=molecule_data)

    assert response.status_code == 200
    assert response.json()["message"] == "Molecule added successfully."
    assert response.json()["molecule"]["name"] == molecule_data["name"]


def test_get_molecule_by_id(mock_get_molecule_by_id):
    molecule_data = {
        "id": 1,
        "name": "Ethanol",
        "smiles": "CCO",
        "weight": 46.07,
        "formula": "C2H6O",
    }
    mock_get_molecule_by_id.return_value = molecule_data

    response = client.get("/molecule/1")

    assert response.status_code == 200
    assert response.json()["id"] == molecule_data["id"]


def test_get_all_molecules(mock_get_all_molecules):
    molecule_data = [
        {
            "id": 1,
            "name": "Ethanol",
            "smiles": "CCO",
            "weight": 46.07,
            "formula": "C2H6O",
        },
        {
            "id": 2,
            "name": "Methanol",
            "smiles": "CO",
            "weight": 32.04,
            "formula": "CH4O",
        },
        {
            "id": 3,
            "name": "Water",
            "smiles": "O",
            "weight": 18.02,
            "formula": "H2O",
        }
    ]
    mock_get_all_molecules.return_value = molecule_data

    response = client.get("/molecules_list")

    assert response.status_code == 200
    assert response.json() == molecule_data
