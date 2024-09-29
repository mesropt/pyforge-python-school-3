from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_add_molecule():
    molecule_data = {
        "id": 77771,
        "name": "Test Molecule 77771",
        "smiles": "CKDOD",
        "weight": 49.20,
        "formula": "C26H40"
    }
    response = client.post("/add", json=molecule_data)
    assert response.status_code == 200
    assert response.json() == {"message": "Molecule added successfully."}


def test_get_molecule_by_id():
    response = client.get("/molecule/77771")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Molecule 77771"
    assert data["smiles"] == "CKDOD"


def test_update_molecule_by_id():
    molecule_data_updated = {
        "id": 77771,
        "name": "Test Molecule 77771 Updated",
        "smiles": "CKDODF",
        "weight": 49.201,
        "formula": "C26H40"
    }
    response = client.put("/update/molecule/77771", json=molecule_data_updated)
    assert response.status_code == 200
    assert response.json() == {"message": "Molecule updated successfully."}

    response = client.get("/molecule/77771")
    data = response.json()
    assert data["name"] == "Test Molecule 77771 Updated"
    assert data["weight"] == 49.201


def test_delete_molecule_by_id():
    molecule_data = {
        "id": 66660,
        "name": "Test Molecule 66660",
        "smiles": "MDDOD",
        "weight": 56.20,
        "formula": "CDS26H40"
    }
    response = client.post("/add", json=molecule_data)
    assert response.status_code == 200
    assert response.json() == {"message": "Molecule added successfully."}

    response = client.delete("/delete/molecule/66660")
    assert response.status_code == 200
    assert response.json() == {"message": "Molecule deleted successfully."}

    response = client.get("/molecule/66660")
    assert response.status_code == 404
    assert response.json() == {"detail": "Molecule not found."}


def test_list_molecules():
    response = client.get("/list")
    assert response.status_code == 200

    data = response.json()
    assert "molecules" in data
    assert len(data["molecules"]) > 0


def test_substructure_search():
    response = client.get("/search?substructure=c1ccccc1")
    assert response.status_code == 200

    data = response.json()
    assert len(data) > 0
    assert data[0]["name"] == "Benzene"


def test_upload_image():
    with open("tests/test_image.png", "rb") as image_file:
        response = client.post("/upload_image", files={"file": image_file})
        assert response.status_code == 200
        data = response.json()
        assert "file_path" in data
        assert data["message"] == "Image uploaded successfully."


def test_get_server():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()

    assert "server_id" in data
    assert data["server_id"] == "1"
