"""Phase 16 — APIKeyMiddleware authentication."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from efl_kernel.kernel.ral import RAL_SPEC
from efl_kernel.service import create_app

SESSION_REG = RAL_SPEC["moduleRegistration"]["SESSION"]


@pytest.fixture()
def svc(tmp_path, monkeypatch):
    monkeypatch.delenv("EFL_API_KEY", raising=False)
    db = tmp_path / "test_phase16.db"
    app = create_app(str(db))
    client = TestClient(app)
    return client, monkeypatch


def _session_payload() -> dict:
    return {
        "moduleVersion": SESSION_REG["moduleVersion"],
        "moduleViolationRegistryVersion": SESSION_REG["moduleViolationRegistryVersion"],
        "registryHash": SESSION_REG["registryHash"],
        "objectID": "obj-p16-session",
        "evaluationContext": {"athleteID": "a1", "sessionID": "s1"},
        "windowContext": [
            {"windowType": "ROLLING7DAYS", "anchorDate": "2026-01-01",
             "startDate": "2025-12-26", "endDate": "2026-01-01", "timezone": "UTC"},
            {"windowType": "ROLLING28DAYS", "anchorDate": "2026-01-01",
             "startDate": "2025-12-05", "endDate": "2026-01-01", "timezone": "UTC"},
        ],
        "session": {"contactLoad": 0, "exercises": []},
    }


def test_auth_disabled_when_env_unset(svc):
    client, _ = svc
    r = client.post("/evaluate/session", json=_session_payload())
    assert r.status_code == 200


def test_correct_key_accepted(svc):
    client, monkeypatch = svc
    monkeypatch.setenv("EFL_API_KEY", "secret")
    r = client.post("/evaluate/session", json=_session_payload(), headers={"x-api-key": "secret"})
    assert r.status_code == 200


def test_wrong_key_rejected(svc):
    client, monkeypatch = svc
    monkeypatch.setenv("EFL_API_KEY", "secret")
    r = client.post("/evaluate/session", json=_session_payload(), headers={"x-api-key": "wrong"})
    assert r.status_code == 401
    assert r.json() == {"detail": "unauthorized"}


def test_missing_header_rejected(svc):
    client, monkeypatch = svc
    monkeypatch.setenv("EFL_API_KEY", "secret")
    r = client.post("/evaluate/session", json=_session_payload())
    assert r.status_code == 401


def test_health_exempt(svc):
    client, monkeypatch = svc
    monkeypatch.setenv("EFL_API_KEY", "secret")
    r = client.get("/health")
    assert r.status_code == 200


def test_metrics_not_exempt(svc):
    client, monkeypatch = svc
    monkeypatch.setenv("EFL_API_KEY", "secret")
    r = client.get("/metrics")
    assert r.status_code == 401
