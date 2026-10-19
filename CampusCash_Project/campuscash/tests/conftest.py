import pytest
from database import initialize_database

@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "test.db"
    initialize_database(path)
    return path
