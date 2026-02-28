"""Shared test configuration and fixtures.

API tests that require the database must use the `test_client` fixture,
which triggers the FastAPI lifespan (DB schema creation) and uses an
isolated in-memory SQLite database.
"""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="function")
def test_client():
    """Provide a TestClient that triggers the app lifespan (DB init).

    Each test function gets a fresh in-memory database via a temp file
    to prevent state leakage between tests.
    """
    # Use a temp file so aiosqlite can open it (aiosqlite doesn't support :memory: well)
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # Override the DB path before importing the app
    os.environ["DB_PATH"] = db_path

    # Re-apply settings after overriding env var
    from app.config import settings
    settings.DB_PATH = db_path

    from app.main import app
    # Use TestClient as context manager to trigger lifespan (init_db)
    with TestClient(app) as client:
        yield client

    # Cleanup
    try:
        os.unlink(db_path)
    except Exception:
        pass
