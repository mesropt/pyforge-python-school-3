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
def mock_redis(mocker):
    """Fixture for mocking the Redis client.

    Creates a MagicMock object that replaces the Redis client used in the application.
    This allows testing interactions with the Redis cache without connecting to a real Redis server.
    """
    mock_redis_client = mocker.MagicMock()
    mocker.patch("src.main.redis_client", mock_redis_client)
    return mock_redis_client


@pytest.fixture
def fastapi_client(mock_postgres, mock_redis):
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
        Molecule(id=1, name="Water", smiles="O", weight=18.015, formula="H2O"),
        Molecule(id=2, name="Ethanol", smiles="CCO", weight=46.07, formula="C2H6O"),
    ]


def test_get_molecule_by_id_with_cache(fastapi_client, mock_postgres, mock_redis, sample_molecule):

    # Mock a query to the database
    mock_postgres.query.return_value.filter.return_value.first.return_value = sample_molecule

    # Mock Redis (no cache for first call)
    mock_redis.get.return_value = None

    # First query (database access)
    response = fastapi_client.get(f"/molecule/{sample_molecule.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == sample_molecule.id
    assert data["name"] == sample_molecule.name
    assert data["smiles"] == sample_molecule.smiles
    assert data["weight"] == sample_molecule.weight
    assert data["formula"] == sample_molecule.formula

    # Checking that the data has been cached
    cache_key = f"molecule:{sample_molecule.id}"
    mock_redis.setex.assert_called_once_with(
        cache_key,
        60,  # Caching time
        '{"id": 23, "name": "Benzene", "smiles": "c1ccccc1", "weight": 78.11, "formula": "C6H6"}'
    )

    # Mock Redis (data is in cache for the second call)
    mock_redis.get.return_value = '{"id": 23, "name": "Benzene", "smiles": "c1ccccc1", "weight": 78.11, "formula": "C6H6"}'

    # Second request (data is taken from cache)
    response_cached = fastapi_client.get(f"/molecule/{sample_molecule.id}")
    assert response_cached.status_code == 200

    cached_data_from_response = response_cached.json()
    assert cached_data_from_response == data

    # Check that the second request did not cause a database call
    mock_postgres.query.return_value.filter.return_value.first.assert_called_once()


def test_get_all_molecules_with_cache(fastapi_client, mock_postgres, mock_redis, sample_molecules):
    # Mock a query to the database
    mock_postgres.query.return_value.offset.return_value.limit.return_value.all.return_value = sample_molecules

    # Mock Redis (no cache for first call)
    mock_redis.get.return_value = None

    # First query (database access)
    response = fastapi_client.get("/molecules_list?skip=0&limit=10")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 2
    for i, molecule in enumerate(sample_molecules):
        assert data[i]["id"] == molecule.id
        assert data[i]["name"] == molecule.name
        assert data[i]["smiles"] == molecule.smiles
        assert data[i]["weight"] == molecule.weight
        assert data[i]["formula"] == molecule.formula

    # Checking that the data has been cached
    cache_key = "molecules_list:skip=0:limit=10"
    mock_redis.setex.assert_called_once_with(
        cache_key,
        60,  # Caching time
        '[{"id": 1, "name": "Water", "smiles": "O", "weight": 18.015, "formula": "H2O"}, '
        '{"id": 2, "name": "Ethanol", "smiles": "CCO", "weight": 46.07, "formula": "C2H6O"}]'
    )

    # Mock Redis (data is in cache for the second call)
    mock_redis.get.return_value = '[{"id": 1, "name": "Water", "smiles": "O", "weight": 18.015, "formula": "H2O"}, ' \
                                  '{"id": 2, "name": "Ethanol", "smiles": "CCO", "weight": 46.07, "formula": "C2H6O"}]'

    # Second request (data is taken from cache)
    response_cached = fastapi_client.get("/molecules_list?skip=0&limit=10")
    assert response_cached.status_code == 200

    cached_data_from_response = response_cached.json()
    assert cached_data_from_response == data

    # Check that the second request did not cause a database call
    mock_postgres.query.return_value.offset.return_value.limit.return_value.all.assert_called_once()
