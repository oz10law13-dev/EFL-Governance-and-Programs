"""Phase 14 — Operational CRUD route tests.

POST /athletes, GET /athletes/{athlete_id}
POST /sessions
POST /seasons, GET /seasons/{athlete_id}/{season_id}
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from efl_kernel.service import create_app


@pytest.fixture(scope="module")
def svc(tmp_path_factory):
    db = tmp_path_factory.mktemp("crud") / "test_crud.db"
    app = create_app(str(db))
    client = TestClient(app)
    return client, app


# ─── POST /athletes ───────────────────────────────────────────────────────────

def test_post_athlete_creates_and_returns_row(svc):
    client, _ = svc
    r = client.post("/athletes", json={
        "athlete_id": "ATH-CRUD-001",
        "max_daily_contact_load": 120.0,
        "minimum_rest_interval_hours": 24.0,
        "e4_clearance": 1,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["athlete_id"] == "ATH-CRUD-001"
    assert body["max_daily_contact_load"] == 120.0
    assert body["e4_clearance"] == 1


def test_post_athlete_upsert_updates_existing(svc):
    client, _ = svc
    client.post("/athletes", json={
        "athlete_id": "ATH-CRUD-UPD",
        "max_daily_contact_load": 100.0,
        "minimum_rest_interval_hours": 24.0,
        "e4_clearance": 0,
    })
    r = client.post("/athletes", json={
        "athlete_id": "ATH-CRUD-UPD",
        "max_daily_contact_load": 200.0,
        "minimum_rest_interval_hours": 24.0,
        "e4_clearance": 1,
    })
    assert r.status_code == 200
    assert r.json()["max_daily_contact_load"] == 200.0


def test_post_athlete_missing_required_field_returns_400(svc):
    client, _ = svc
    r = client.post("/athletes", json={
        "athlete_id": "ATH-CRUD-BAD",
        # missing max_daily_contact_load
        "minimum_rest_interval_hours": 24.0,
        "e4_clearance": 0,
    })
    assert r.status_code == 400
    assert "max_daily_contact_load" in r.json()["detail"]


# ─── GET /athletes/{athlete_id} ───────────────────────────────────────────────

def test_get_athlete_found(svc):
    client, _ = svc
    client.post("/athletes", json={
        "athlete_id": "ATH-CRUD-GET",
        "max_daily_contact_load": 80.0,
        "minimum_rest_interval_hours": 12.0,
        "e4_clearance": 0,
    })
    r = client.get("/athletes/ATH-CRUD-GET")
    assert r.status_code == 200
    assert r.json()["athlete_id"] == "ATH-CRUD-GET"


def test_get_athlete_not_found_returns_404(svc):
    client, _ = svc
    r = client.get("/athletes/ATH-NOBODY-999")
    assert r.status_code == 404


# ─── POST /sessions ───────────────────────────────────────────────────────────

def test_post_session_creates(svc):
    client, _ = svc
    r = client.post("/sessions", json={
        "session_id": "SES-CRUD-001",
        "athlete_id": "ATH-CRUD-001",
        "session_date": "2026-03-01T10:00:00+00:00",
        "contact_load": 85.0,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["session_id"] == "SES-CRUD-001"


def test_post_session_with_optional_fields(svc):
    client, _ = svc
    r = client.post("/sessions", json={
        "session_id": "SES-CRUD-OPT",
        "athlete_id": "ATH-CRUD-001",
        "session_date": "2026-03-02T10:00:00+00:00",
        "contact_load": 70.0,
        "readiness_state": "GREEN",
        "is_collapsed": 0,
    })
    assert r.status_code == 200


def test_post_session_missing_required_field_returns_400(svc):
    client, _ = svc
    r = client.post("/sessions", json={
        "session_id": "SES-CRUD-BAD",
        "athlete_id": "ATH-CRUD-001",
        # missing session_date
        "contact_load": 50.0,
    })
    assert r.status_code == 400
    assert "session_date" in r.json()["detail"]


def test_post_session_no_athlete_fk_check(svc):
    # FK is NOT enforced at API layer — store handles missing athlete via sentinel
    client, _ = svc
    r = client.post("/sessions", json={
        "session_id": "SES-CRUD-NOFK",
        "athlete_id": "ATH-NONEXISTENT-999",
        "session_date": "2026-03-03T10:00:00+00:00",
        "contact_load": 50.0,
    })
    assert r.status_code == 200  # succeeds — FK not checked at API layer


# ─── POST /seasons ────────────────────────────────────────────────────────────

def test_post_season_creates_and_returns_row(svc):
    client, _ = svc
    r = client.post("/seasons", json={
        "athlete_id": "ATH-CRUD-001",
        "season_id": "S2026",
        "competition_weeks": 6,
        "gpp_weeks": 10,
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["athlete_id"] == "ATH-CRUD-001"
    assert body["season_id"] == "S2026"
    assert body["competition_weeks"] == 6
    assert body["gpp_weeks"] == 10


def test_post_season_upsert_updates_existing(svc):
    client, _ = svc
    client.post("/seasons", json={
        "athlete_id": "ATH-CRUD-001",
        "season_id": "S2026-UPD",
        "competition_weeks": 4,
        "gpp_weeks": 8,
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
    })
    r = client.post("/seasons", json={
        "athlete_id": "ATH-CRUD-001",
        "season_id": "S2026-UPD",
        "competition_weeks": 8,
        "gpp_weeks": 12,
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
    })
    assert r.status_code == 200
    assert r.json()["competition_weeks"] == 8


def test_post_season_missing_required_field_returns_400(svc):
    client, _ = svc
    r = client.post("/seasons", json={
        "athlete_id": "ATH-CRUD-001",
        "season_id": "S2026-BAD",
        # missing competition_weeks
        "gpp_weeks": 8,
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
    })
    assert r.status_code == 400
    assert "competition_weeks" in r.json()["detail"]


def test_post_season_no_athlete_fk_check(svc):
    client, _ = svc
    r = client.post("/seasons", json={
        "athlete_id": "ATH-NONEXISTENT-999",
        "season_id": "S2026-NOFK",
        "competition_weeks": 4,
        "gpp_weeks": 8,
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
    })
    assert r.status_code == 200  # FK not checked at API layer


# ─── GET /seasons/{athlete_id}/{season_id} ────────────────────────────────────

def test_get_season_found(svc):
    client, _ = svc
    client.post("/seasons", json={
        "athlete_id": "ATH-CRUD-001",
        "season_id": "S2026-GET",
        "competition_weeks": 4,
        "gpp_weeks": 8,
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
    })
    r = client.get("/seasons/ATH-CRUD-001/S2026-GET")
    assert r.status_code == 200
    body = r.json()
    assert body["season_id"] == "S2026-GET"


def test_get_season_not_found_returns_404(svc):
    client, _ = svc
    r = client.get("/seasons/ATH-NOBODY/S-NOBODY")
    assert r.status_code == 404
