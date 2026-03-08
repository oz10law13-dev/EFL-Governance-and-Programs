"""Phase 15 — GET /kdo/{decision_hash}, structured logging, GET /metrics."""
from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient

from efl_kernel.kernel.ral import RAL_SPEC
from efl_kernel.service import create_app

SESSION_REG = RAL_SPEC["moduleRegistration"]["SESSION"]


@pytest.fixture(scope="module")
def svc(tmp_path_factory):
    db = tmp_path_factory.mktemp("phase15") / "test_phase15.db"
    app = create_app(str(db))
    client = TestClient(app)
    return client, app.state.audit_store


def _session_payload() -> dict:
    return {
        "moduleVersion": SESSION_REG["moduleVersion"],
        "moduleViolationRegistryVersion": SESSION_REG["moduleViolationRegistryVersion"],
        "registryHash": SESSION_REG["registryHash"],
        "objectID": "obj-p15-session",
        "evaluationContext": {"athleteID": "a1", "sessionID": "s1"},
        "windowContext": [
            {"windowType": "ROLLING7DAYS", "anchorDate": "2026-01-01",
             "startDate": "2025-12-26", "endDate": "2026-01-01", "timezone": "UTC"},
            {"windowType": "ROLLING28DAYS", "anchorDate": "2026-01-01",
             "startDate": "2025-12-05", "endDate": "2026-01-01", "timezone": "UTC"},
        ],
        "session": {"contactLoad": 0, "exercises": []},
    }


# ─── GET /kdo/{decision_hash} ─────────────────────────────────────────────────

def test_get_kdo_found(svc):
    client, _ = svc
    r = client.post("/evaluate/session", json=_session_payload())
    assert r.status_code == 200
    decision_hash = r.json()["audit"]["decisionHash"]

    r2 = client.get(f"/kdo/{decision_hash}")
    assert r2.status_code == 200
    assert r2.json()["audit"]["decisionHash"] == decision_hash


def test_get_kdo_not_found(svc):
    client, _ = svc
    r = client.get("/kdo/nonexistent-hash-000")
    assert r.status_code == 404


def test_get_kdo_returns_correct_module_id(svc):
    client, _ = svc
    r = client.post("/evaluate/session", json=_session_payload())
    decision_hash = r.json()["audit"]["decisionHash"]

    r2 = client.get(f"/kdo/{decision_hash}")
    assert r2.status_code == 200
    assert r2.json()["module_id"] == "SESSION"


# ─── GET /metrics ─────────────────────────────────────────────────────────────

def test_metrics_shape(svc):
    client, _ = svc
    r = client.get("/metrics")
    assert r.status_code == 200
    body = r.json()
    assert "kdo_total" in body
    assert "by_module" in body
    assert "by_publish_state" in body
    assert isinstance(body["kdo_total"], int)


def test_metrics_count_increments_after_evaluate(svc):
    client, _ = svc
    before = client.get("/metrics").json()["kdo_total"]

    client.post("/evaluate/session", json=_session_payload())

    after = client.get("/metrics").json()
    assert after["kdo_total"] == before + 1
    assert "SESSION" in after["by_module"]


# ─── Structured logging ───────────────────────────────────────────────────────

def test_log_emitted_after_evaluate(svc, caplog):
    client, _ = svc
    with caplog.at_level(logging.INFO, logger="efl_kernel.service"):
        client.post("/evaluate/session", json=_session_payload())

    info_records = [r for r in caplog.records if r.levelname == "INFO"]
    assert len(info_records) >= 1
    assert any("decision_hash" in r.__dict__ for r in info_records)
