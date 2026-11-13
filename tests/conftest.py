import pytest
from fastapi.testclient import TestClient

from backend import db
from backend.main import app


@pytest.fixture(autouse=True)
def database(tmp_path, monkeypatch):
    """Give every test a freshly seeded database of its own."""
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "undercover.db"))
    db.seed()


@pytest.fixture
def client():
    return TestClient(app)
