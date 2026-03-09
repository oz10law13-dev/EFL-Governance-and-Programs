"""Phase 24 — Session Intake Workflow tests.

16 SQLite/route tests always run.
1 PostgreSQL test is skipped when EFL_TEST_DATABASE_URL is not set.
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from efl_kernel.service import create_app

PG_URL = os.environ.get("EFL_TEST_DATABASE_URL")
requires_pg = pytest.mark.skipif(not PG_URL, reason="EFL_TEST_DATABASE_URL not set")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def svc(tmp_path):
    db = str(tmp_path / "intake.db")
    app = create_app(db)
    client = TestClient(app)
    op_store = app.state.op_store
    audit_store = app.state.audit_store

    # Seed a test athlete
    op_store.upsert_athlete({
        "athlete_id": "ATH-INTAKE-01",
        "max_daily_contact_load": 150.0,
        "minimum_rest_interval_hours": 24.0,
        "e4_clearance": 1,
    })
    # Seed a low-cap athlete for violation tests
    op_store.upsert_athlete({
        "athlete_id": "ATH-INTAKE-LOW",
        "max_daily_contact_load": 10.0,
        "minimum_rest_interval_hours": 24.0,
        "e4_clearance": 0,
    })

    return client, op_store, audit_store, app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestIntakeSession:
    def test_intake_records_and_evaluates(self, svc):
        client, op_store, _, _ = svc
        r = client.post("/intake/session", json={
            "athlete_id": "ATH-INTAKE-01",
            "session_id": "S-INTAKE-01",
            "session_date": "2026-03-09T10:00:00+00:00",
            "contact_load": 50.0,
        })
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "recorded"
        assert body["session_id"] == "S-INTAKE-01"
        assert body["athlete_id"] == "ATH-INTAKE-01"
        assert body["evaluation"]["module_id"] == "SESSION"
        assert body["evaluation"]["publish_state"] == "LEGALREADY"
        assert body["evaluation"]["decision_hash"]

    def test_intake_maxdailyload_fires(self, svc):
        client, _, _, _ = svc
        r = client.post("/intake/session", json={
            "athlete_id": "ATH-INTAKE-LOW",
            "session_id": "S-MAXLOAD-01",
            "session_date": "2026-03-09T10:00:00+00:00",
            "contact_load": 50.0,  # 50 > cap of 10
        })
        assert r.status_code == 200
        violations = r.json()["evaluation"]["violations"]
        codes = [v["code"] for v in violations]
        assert "SCM.MAXDAILYLOAD" in codes

    def test_intake_minrest_fires(self, svc):
        client, _, _, _ = svc

        # First session
        r1 = client.post("/intake/session", json={
            "athlete_id": "ATH-INTAKE-01",
            "session_id": "S-REST-01",
            "session_date": "2026-03-09T08:00:00+00:00",
            "contact_load": 50.0,
        })
        assert r1.status_code == 200
        assert r1.json()["evaluation"]["publish_state"] == "LEGALREADY"

        # Second session 4 hours later — below 24h minimum rest
        r2 = client.post("/intake/session", json={
            "athlete_id": "ATH-INTAKE-01",
            "session_id": "S-REST-02",
            "session_date": "2026-03-09T12:00:00+00:00",
            "contact_load": 50.0,
        })
        assert r2.status_code == 200
        violations = r2.json()["evaluation"]["violations"]
        codes = [v["code"] for v in violations]
        assert "SCM.MINREST" in codes

    def test_intake_clearance_violation(self, svc):
        client, _, _, _ = svc
        # ATH-INTAKE-LOW has e4_clearance=0, depth_jump_24in requires E4
        r = client.post("/intake/session", json={
            "athlete_id": "ATH-INTAKE-LOW",
            "session_id": "S-CLEAR-01",
            "session_date": "2026-03-09T10:00:00+00:00",
            "contact_load": 5.0,
            "exercises": [
                {"exerciseID": "depth_jump_24in"}
            ],
        })
        assert r.status_code == 200
        violations = r.json()["evaluation"]["violations"]
        codes = [v["code"] for v in violations]
        assert "CL.CLEARANCEMISSING" in codes

    def test_intake_athlete_not_found_404(self, svc):
        client, _, _, _ = svc
        r = client.post("/intake/session", json={
            "athlete_id": "UNKNOWN-ATH",
            "session_id": "S-404-01",
            "session_date": "2026-03-09T10:00:00+00:00",
            "contact_load": 50.0,
        })
        assert r.status_code == 404
        assert "not found" in r.json()["detail"].lower()

    def test_intake_missing_field_400(self, svc):
        client, _, _, _ = svc
        r = client.post("/intake/session", json={
            "athlete_id": "ATH-INTAKE-01",
            "session_id": "S-MISS-01",
            "session_date": "2026-03-09T10:00:00+00:00",
            # missing contact_load
        })
        assert r.status_code == 400
        assert "contact_load" in r.json()["detail"]

    def test_intake_records_readiness_state(self, svc):
        client, op_store, _, _ = svc
        r = client.post("/intake/session", json={
            "athlete_id": "ATH-INTAKE-01",
            "session_id": "S-READY-01",
            "session_date": "2026-03-09T10:00:00+00:00",
            "contact_load": 50.0,
            "readiness_state": "GREEN",
        })
        assert r.status_code == 200
        history = op_store.get_readiness_history(
            "ATH-INTAKE-01",
            window_start="2026-03-01",
            anchor_date="2026-03-10T00:00:00+00:00",
        )
        assert "GREEN" in history

    def test_intake_records_is_collapsed(self, svc):
        client, op_store, _, _ = svc
        r = client.post("/intake/session", json={
            "athlete_id": "ATH-INTAKE-01",
            "session_id": "S-COLL-01",
            "session_date": "2026-03-09T10:00:00+00:00",
            "contact_load": 50.0,
            "is_collapsed": True,
        })
        assert r.status_code == 200
        # Verify via window query — session should exist
        rows = op_store.get_sessions_in_window(
            "ATH-INTAKE-01",
            window_start="2026-03-01",
            anchor_date="2026-03-10T00:00:00+00:00",
            exclude_session_id="",
        )
        found = [s for s in rows if s["session_id"] == "S-COLL-01"]
        assert len(found) == 1

    def test_intake_re_intake_overwrites(self, svc):
        client, _, audit_store, _ = svc
        # First intake
        r1 = client.post("/intake/session", json={
            "athlete_id": "ATH-INTAKE-01",
            "session_id": "S-DUP-01",
            "session_date": "2026-03-09T10:00:00+00:00",
            "contact_load": 50.0,
        })
        assert r1.status_code == 200
        dh1 = r1.json()["evaluation"]["decision_hash"]

        # Second intake with same session_id, different load
        r2 = client.post("/intake/session", json={
            "athlete_id": "ATH-INTAKE-01",
            "session_id": "S-DUP-01",
            "session_date": "2026-03-09T10:00:00+00:00",
            "contact_load": 60.0,
        })
        assert r2.status_code == 200
        dh2 = r2.json()["evaluation"]["decision_hash"]
        # Each intake produces a distinct KDO
        assert dh1 != dh2

    def test_intake_org_scoped(self, svc):
        client, op_store, _, app = svc
        # ATH-INTAKE-01 is in default org — not visible to other_org
        import os
        os.environ["EFL_API_KEYS"] = '{"key-a": "org_a", "key-b": "org_b"}'
        try:
            r = client.post("/intake/session",
                json={
                    "athlete_id": "ATH-INTAKE-01",
                    "session_id": "S-ORG-01",
                    "session_date": "2026-03-09T10:00:00+00:00",
                    "contact_load": 50.0,
                },
                headers={"x-api-key": "key-a"},
            )
            # Athlete not found in org_a
            assert r.status_code == 404
        finally:
            del os.environ["EFL_API_KEYS"]

    def test_intake_kdo_retrievable(self, svc):
        client, _, _, _ = svc
        r = client.post("/intake/session", json={
            "athlete_id": "ATH-INTAKE-01",
            "session_id": "S-KDO-01",
            "session_date": "2026-03-09T10:00:00+00:00",
            "contact_load": 50.0,
        })
        assert r.status_code == 200
        dh = r.json()["evaluation"]["decision_hash"]

        r2 = client.get(f"/kdo/{dh}")
        assert r2.status_code == 200
        assert r2.json()["audit"]["decisionHash"] == dh

    def test_intake_accumulates_sessions_for_future_evals(self, svc):
        """Multiple intakes store sessions that accumulate in op_sessions."""
        client, op_store, _, _ = svc

        for i in range(3):
            r = client.post("/intake/session", json={
                "athlete_id": "ATH-INTAKE-01",
                "session_id": f"S-ACC-{i+1:02d}",
                "session_date": f"2026-03-{10+i}T10:00:00+00:00",
                "contact_load": 40.0,
            })
            assert r.status_code == 200

        rows = op_store.get_sessions_in_window(
            "ATH-INTAKE-01",
            window_start="2026-03-01",
            anchor_date="2026-03-15T23:59:59+00:00",
            exclude_session_id="",
        )
        assert len(rows) >= 3

    def test_intake_default_exercises_empty(self, svc):
        client, _, _, _ = svc
        r = client.post("/intake/session", json={
            "athlete_id": "ATH-INTAKE-01",
            "session_id": "S-NOEX-01",
            "session_date": "2026-03-09T10:00:00+00:00",
            "contact_load": 50.0,
            # no exercises field
        })
        assert r.status_code == 200
        # No CL violations when no exercises
        violations = r.json()["evaluation"]["violations"]
        cl_violations = [v for v in violations if v["code"].startswith("CL.")]
        assert len(cl_violations) == 0

    def test_intake_response_shape(self, svc):
        client, _, _, _ = svc
        r = client.post("/intake/session", json={
            "athlete_id": "ATH-INTAKE-01",
            "session_id": "S-SHAPE-01",
            "session_date": "2026-03-09T10:00:00+00:00",
            "contact_load": 50.0,
        })
        assert r.status_code == 200
        body = r.json()
        assert "status" in body
        assert "session_id" in body
        assert "athlete_id" in body
        assert "evaluation" in body
        ev = body["evaluation"]
        assert "decision_hash" in ev
        assert "publish_state" in ev
        assert "violations" in ev
        assert "violation_count" in ev
        assert "module_id" in ev

    def test_intake_metrics_updated(self, svc):
        client, _, _, _ = svc
        # Get baseline
        m1 = client.get("/metrics").json()
        baseline = m1.get("kdo_total", 0)

        client.post("/intake/session", json={
            "athlete_id": "ATH-INTAKE-01",
            "session_id": "S-MET-01",
            "session_date": "2026-03-09T10:00:00+00:00",
            "contact_load": 50.0,
        })
        m2 = client.get("/metrics").json()
        assert m2["kdo_total"] == baseline + 1

    def test_intake_minrest_clean_when_rest_sufficient(self, svc):
        client, _, _, _ = svc

        r1 = client.post("/intake/session", json={
            "athlete_id": "ATH-INTAKE-01",
            "session_id": "S-OK-01",
            "session_date": "2026-03-07T10:00:00+00:00",
            "contact_load": 50.0,
        })
        assert r1.status_code == 200

        # 48 hours later — well above 24h minimum rest
        r2 = client.post("/intake/session", json={
            "athlete_id": "ATH-INTAKE-01",
            "session_id": "S-OK-02",
            "session_date": "2026-03-09T10:00:00+00:00",
            "contact_load": 50.0,
        })
        assert r2.status_code == 200
        violations = r2.json()["evaluation"]["violations"]
        codes = [v["code"] for v in violations]
        assert "SCM.MINREST" not in codes


# ---------------------------------------------------------------------------
# Version check
# ---------------------------------------------------------------------------

def test_version_bumped():
    app = create_app(":memory:")
    major = int(app.version.split(".")[0])
    assert major >= 24


# ---------------------------------------------------------------------------
# PG test
# ---------------------------------------------------------------------------

@requires_pg
def test_pg_intake_session():
    from efl_kernel.kernel.pg_pool import open_pg
    from efl_kernel.kernel.pg_operational_store import PgOperationalStore
    from efl_kernel.kernel.pg_audit_store import PgAuditStore

    app = create_app(database_url=PG_URL)
    client = TestClient(app)

    # Seed athlete in PG
    app.state.op_store.upsert_athlete({
        "athlete_id": "ATH-PG-INTAKE",
        "max_daily_contact_load": 150.0,
        "minimum_rest_interval_hours": 24.0,
        "e4_clearance": 1,
    })

    r = client.post("/intake/session", json={
        "athlete_id": "ATH-PG-INTAKE",
        "session_id": "S-PG-01",
        "session_date": "2026-03-09T10:00:00+00:00",
        "contact_load": 50.0,
    })
    assert r.status_code == 200
    assert r.json()["status"] == "recorded"
