import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.main import app

client = TestClient(app)


@pytest.fixture
def mock_get_all_molecules():
    with patch('src.crud.get_all_molecules') as mock_get:
        yield mock_get


@pytest.fixture
def mock_redis():
    with patch('src.main.redis_client') as mock_redis:
        mock_instance = MagicMock()
        mock_redis.return_value = mock_instance
        yield mock_instance