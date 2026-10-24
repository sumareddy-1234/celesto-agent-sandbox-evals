"""
tests/conftest.py — Session-wide patches for unit testing without PostgreSQL.

Patches app.main.init_db to an AsyncMock before any test runs.
This prevents the FastAPI lifespan from attempting a real database connection.
"""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True, scope="session")
def mock_init_db():
    """Replace init_db with an AsyncMock for the entire test session."""
    with patch("app.main.init_db", new_callable=AsyncMock) as mock:
        yield mock
