"""
tests/test_api.py — Unit tests for the FastAPI Run Ledger API.

Label: MOCKED — database init and sessions are mocked; PostgreSQL NOT required.
These tests verify HTTP routing, request validation, response codes, and schema.
"""
import re
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SANDBOX_RE = re.compile(r"^sbx-[a-z0-9]{8,}$")

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _make_mock_run(**overrides):
    """Return a RunModel-like MagicMock with sensible defaults."""
    from app.database import RunModel
    defaults = {
        "run_id": "test-run-001",
        "sandbox_name": "sbx-testrun01",
        "problem_id": "problem-001",
        "state": "created",
        "execution_target": "celesto_sandbox",
        "created_at": None,
    }
    defaults.update(overrides)
    obj = MagicMock(spec=RunModel)
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_db_session(rows=None):
    rows = rows or []
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = rows
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result_mock)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


def _get_client(rows=None):
    """
    Return a TestClient with init_db patched to no-op and get_db returning a
    mock session.
    """
    from app.main import app
    from app.database import get_db

    mock_db = _make_db_session(rows)

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db

    # Patch init_db so startup doesn't require a real DB
    with patch("app.main.init_db", new_callable=AsyncMock):
        client = TestClient(app, raise_server_exceptions=True)

    app.dependency_overrides.clear()
    return client, mock_db


# ─────────────────────────────────────────────
# /health
# ─────────────────────────────────────────────

class TestHealth:
    def test_health_returns_200(self):
        from app.main import app
        # Patch the internal create_all so lifespan doesn't need a live DB
        with patch("app.database.Base.metadata.create_all"), \
             patch("app.database.engine") as mock_eng:
            mock_eng.begin = MagicMock(return_value=AsyncMock().__aenter__.return_value)
            with patch("app.main.init_db", new_callable=AsyncMock):
                client = TestClient(app)
                r = client.get("/health")
        assert r.status_code == 200

    def test_health_body(self):
        from app.main import app
        with patch("app.main.init_db", new_callable=AsyncMock):
            client = TestClient(app)
            r = client.get("/health")
        assert r.json() == {"status": "ok"}


# ─────────────────────────────────────────────
# GET /api/runs
# ─────────────────────────────────────────────

class TestListRuns:
    def test_list_runs_returns_200(self):
        from app.main import app
        from app.database import get_db
        mock_db = _make_db_session([])

        async def _ov():
            yield mock_db

        app.dependency_overrides[get_db] = _ov
        with patch("app.main.init_db", new_callable=AsyncMock):
            with TestClient(app) as c:
                r = c.get("/api/runs")
        app.dependency_overrides.clear()
        assert r.status_code == 200

    def test_list_runs_returns_list(self):
        from app.main import app
        from app.database import get_db
        mock_db = _make_db_session([])

        async def _ov():
            yield mock_db

        app.dependency_overrides[get_db] = _ov
        with patch("app.main.init_db", new_callable=AsyncMock):
            with TestClient(app) as c:
                r = c.get("/api/runs")
        app.dependency_overrides.clear()
        assert isinstance(r.json(), list)


# ─────────────────────────────────────────────
# POST /api/runs — valid requests
# ─────────────────────────────────────────────

VALID_PAYLOAD = {
    "run_id": "run-abc123",
    "sandbox_name": "sbx-abcdef01",
    "problem_id": "prob-001",
    "state": "created",
    "execution_target": "celesto_sandbox",
}


class TestCreateRunValid:
    def _post(self, payload):
        from app.main import app
        from app.database import get_db
        mock_run = _make_mock_run(**payload)
        mock_db = _make_db_session()

        async def _ov():
            yield mock_db

        app.dependency_overrides[get_db] = _ov
        with patch("app.main.init_db", new_callable=AsyncMock):
            with TestClient(app) as c:
                r = c.post("/api/runs", json=payload)
        app.dependency_overrides.clear()
        return r

    def test_valid_post_returns_201(self):
        r = self._post(VALID_PAYLOAD)
        assert r.status_code == 201

    def test_all_states_accepted(self):
        states = ["created", "ready", "running", "succeeded", "failed", "deleted"]
        for state in states:
            payload = {**VALID_PAYLOAD, "state": state, "run_id": f"run-{state}"}
            r = self._post(payload)
            assert r.status_code == 201, f"Expected 201 for state={state!r}, got {r.status_code}: {r.text}"


# ─────────────────────────────────────────────
# POST /api/runs — invalid requests → 400
# ─────────────────────────────────────────────

class TestCreateRunInvalid:
    def _post_raw(self, payload):
        from app.main import app
        with patch("app.main.init_db", new_callable=AsyncMock):
            with TestClient(app) as c:
                r = c.post("/api/runs", json=payload)
        return r

    def test_wrong_execution_target_returns_400(self):
        bad = {**VALID_PAYLOAD, "execution_target": "host"}
        r = self._post_raw(bad)
        assert r.status_code == 400

    def test_invalid_sandbox_name_short_returns_400(self):
        bad = {**VALID_PAYLOAD, "sandbox_name": "sbx-abc"}  # only 3 chars after prefix
        r = self._post_raw(bad)
        assert r.status_code == 400

    def test_invalid_sandbox_name_no_prefix_returns_400(self):
        bad = {**VALID_PAYLOAD, "sandbox_name": "eval-abcdef01"}
        r = self._post_raw(bad)
        assert r.status_code == 400

    def test_invalid_sandbox_name_uppercase_returns_400(self):
        bad = {**VALID_PAYLOAD, "sandbox_name": "sbx-ABCDEF01"}
        r = self._post_raw(bad)
        assert r.status_code == 400

    def test_invalid_state_returns_400(self):
        bad = {**VALID_PAYLOAD, "state": "not_a_real_state"}
        r = self._post_raw(bad)
        assert r.status_code == 400

    def test_missing_run_id_returns_400(self):
        bad = {k: v for k, v in VALID_PAYLOAD.items() if k != "run_id"}
        r = self._post_raw(bad)
        assert r.status_code == 400

    def test_empty_body_returns_400(self):
        r = self._post_raw({})
        assert r.status_code == 400


# ─────────────────────────────────────────────
# Sandbox name regex
# ─────────────────────────────────────────────

class TestSandboxNameValidation:
    valid_names = [
        "sbx-abcdef01",
        "sbx-00000000",
        "sbx-abcdefabcdef",
        "sbx-123456789",
    ]
    invalid_names = [
        "sbx-abc",          # too short
        "sbx-ABCDEF01",     # uppercase
        "eval-abcdef01",    # wrong prefix
        "sbx_abcdef01",     # underscore
        "abcdef01",         # no prefix
        "sbx-",             # nothing after prefix
    ]

    def test_valid_names_accepted_by_regex(self):
        for name in self.valid_names:
            assert SANDBOX_RE.match(name), f"{name!r} should be valid"

    def test_invalid_names_rejected_by_regex(self):
        for name in self.invalid_names:
            assert not SANDBOX_RE.match(name), f"{name!r} should be invalid"
