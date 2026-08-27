"""
Pytest configuration and shared test fixtures.
"""

import tempfile
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.store.context_store import ContextStore, get_context_store


@pytest.fixture
def temp_db_store():
    """Create an isolated temporary SQLite ContextStore for each test."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        store = ContextStore(db_path=tmp.name)
        yield store
        store.clear()


@pytest.fixture
def client(temp_db_store):
    """FastAPI TestClient with isolated database dependency override."""
    app.dependency_overrides[get_context_store] = lambda: temp_db_store
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
