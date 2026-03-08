"""Phase 17 — Audit/Operational DB separation."""
from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

from efl_kernel.kernel.ral import RAL_SPEC
from efl_kernel.service import create_app

SESSION_REG = RAL_SPEC["moduleRegistration"]["SESSION"]


def _tables(db_path: str) -> set[str]:
    conn = sqlite3.connect(db_path)
    result = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table', 'index')"
    )}
    conn.close()
    return result


@pytest.fixture()
def sep_app(tmp_path):
    """Separated DB mode: audit_db != op_db."""
    audit_db = str(tmp_path / "audit.db")
    op_db    = str(tmp_path / "op.db")
    app    = create_app(db_path=audit_db, op_db_path=op_db)
    client = TestClient(app)
    return client, audit_db, op_db


@pytest.fixture()
def single_app(tmp_path):
    """Single-path backward compat mode."""
    db     = str(tmp_path / "single.db")
    app    = create_app(db_path=db)
    client = TestClient(app)
    return client, db


def _session_payload() -> dict:
    return {
        "moduleVersion": SESSION_REG["moduleVersion"],
        "moduleViolationRegistryVersion": SESSION_REG["moduleViolationRegistryVersion"],
        "registryHash": SESSION_REG["registryHash"],
        "objectID": "obj-p17-session",
        "evaluationContext": {"athleteID": "a1", "sessionID": "s1"},
        "windowContext": [
            {"windowType": "ROLLING7DAYS", "anchorDate": "2026-01-01",
             "startDate": "2025-12-26", "endDate": "2026-01-01", "timezone": "UTC"},
            {"windowType": "ROLLING28DAYS", "anchorDate": "2026-01-01",
             "startDate": "2025-12-05", "endDate": "2026-01-01", "timezone": "UTC"},
        ],
        "session": {"contactLoad": 0, "exercises": []},
    }


def _athlete_payload() -> dict:
    return {
        "athlete_id": "a17",
        "max_daily_contact_load": 100,
        "minimum_rest_interval_hours": 24,
        "e4_clearance": True,
    }


# ─── Separation tests ─────────────────────────────────────────────────────────

def test_audit_tables_isolated_to_audit_db(sep_app):
    _, audit_db, op_db = sep_app
    assert "kdo_log" in _tables(audit_db)
    assert "override_ledger" in _tables(audit_db)
    assert "kdo_log" not in _tables(op_db)
    assert "override_ledger" not in _tables(op_db)


def test_op_tables_isolated_to_op_db(sep_app):
    _, audit_db, op_db = sep_app
    assert "op_athletes" in _tables(op_db)
    assert "artifact_versions" in _tables(op_db)
    assert "op_athletes" not in _tables(audit_db)
    assert "artifact_versions" not in _tables(audit_db)


def test_kdo_committed_to_audit_db(sep_app):
    client, audit_db, op_db = sep_app
    r = client.post("/evaluate/session", json=_session_payload())
    assert r.status_code == 200

    conn = sqlite3.connect(audit_db)
    count = conn.execute("SELECT COUNT(*) FROM kdo_log").fetchone()[0]
    conn.close()
    assert count == 1
    assert "kdo_log" not in _tables(op_db)


def test_athlete_upserted_to_op_db(sep_app):
    client, audit_db, op_db = sep_app
    r = client.post("/athletes", json=_athlete_payload())
    assert r.status_code == 200

    conn = sqlite3.connect(op_db)
    count = conn.execute("SELECT COUNT(*) FROM op_athletes").fetchone()[0]
    conn.close()
    assert count == 1
    assert "op_athletes" not in _tables(audit_db)


# ─── Backward compat ──────────────────────────────────────────────────────────

def test_backward_compat_single_path(single_app):
    client, db = single_app
    r1 = client.post("/evaluate/session", json=_session_payload())
    assert r1.status_code == 200
    r2 = client.post("/athletes", json=_athlete_payload())
    assert r2.status_code == 200

    tables = _tables(db)
    assert "kdo_log" in tables
    assert "op_athletes" in tables


# ─── Env var separation ───────────────────────────────────────────────────────

def test_env_var_separation(tmp_path, monkeypatch):
    audit_db = str(tmp_path / "env_audit.db")
    op_db    = str(tmp_path / "env_op.db")
    monkeypatch.setenv("EFL_AUDIT_DB_PATH", audit_db)
    monkeypatch.setenv("EFL_OP_DB_PATH", op_db)
    monkeypatch.delenv("EFL_DB_PATH", raising=False)

    app = create_app()
    TestClient(app)  # trigger app startup / schema creation

    assert "kdo_log" in _tables(audit_db)
    assert "op_athletes" in _tables(op_db)
    assert "kdo_log" not in _tables(op_db)
