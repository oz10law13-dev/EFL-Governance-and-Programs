from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from efl_kernel.kernel.ral import RAL_SPEC
from efl_kernel.service import create_app

SESSION_REG = RAL_SPEC["moduleRegistration"]["SESSION"]
MESO_REG = RAL_SPEC["moduleRegistration"]["MESO"]
MACRO_REG = RAL_SPEC["moduleRegistration"]["MACRO"]


# ------------------------------------------------------------------ #
# Fixture                                                             #
# ------------------------------------------------------------------ #

@pytest.fixture(scope="module")
def svc(tmp_path_factory):
    db = tmp_path_factory.mktemp("svc") / "test_svc.db"
    app = create_app(str(db))
    client = TestClient(app)
    op_store = app.state.op_store
    audit_store = app.state.audit_store
    return client, op_store, audit_store, db


# ------------------------------------------------------------------ #
# Conformance base dicts — no hardcoded registry values              #
# ------------------------------------------------------------------ #

def _conformance_session_base() -> dict:
    return {
        "moduleVersion": SESSION_REG["moduleVersion"],
        "moduleViolationRegistryVersion": SESSION_REG["moduleViolationRegistryVersion"],
        "registryHash": SESSION_REG["registryHash"],
        "objectID": "obj-session-1",
        "evaluationContext": {"athleteID": "a1", "sessionID": "s1"},
        "windowContext": [
            {
                "windowType": "ROLLING7DAYS",
                "anchorDate": "2026-01-01",
                "startDate": "2025-12-26",
                "endDate": "2026-01-01",
                "timezone": "UTC",
            },
            {
                "windowType": "ROLLING28DAYS",
                "anchorDate": "2026-01-01",
                "startDate": "2025-12-05",
                "endDate": "2026-01-01",
                "timezone": "UTC",
            },
        ],
    }


def _conformance_meso_base() -> dict:
    return {
        "moduleVersion": MESO_REG["moduleVersion"],
        "moduleViolationRegistryVersion": MESO_REG["moduleViolationRegistryVersion"],
        "registryHash": MESO_REG["registryHash"],
        "objectID": "obj-meso-1",
        "evaluationContext": {"athleteID": "a1", "mesoID": "m1"},
        "windowContext": [
            {
                "windowType": "MESOCYCLE",
                "anchorDate": "2026-01-01",
                "startDate": "2025-12-05",
                "endDate": "2026-01-01",
                "timezone": "UTC",
            },
        ],
    }


def _conformance_macro_base() -> dict:
    return {
        "moduleVersion": MACRO_REG["moduleVersion"],
        "moduleViolationRegistryVersion": MACRO_REG["moduleViolationRegistryVersion"],
        "registryHash": MACRO_REG["registryHash"],
        "objectID": "obj-macro-1",
        "evaluationContext": {"athleteID": "a1", "seasonID": "season-1"},
        "windowContext": [
            {
                "windowType": "SEASON",
                "anchorDate": "2026-01-01",
                "startDate": "2025-01-01",
                "endDate": "2026-01-01",
                "timezone": "UTC",
            },
        ],
    }


# ------------------------------------------------------------------ #
# Payload builders                                                     #
# ------------------------------------------------------------------ #

def _session_payload(
    athlete_id: str,
    session_id: str,
    session_date: str,
    contact_load: float,
    exercises=None,
    anchor_date: str = "2026-01-15",
) -> dict:
    payload = _conformance_session_base()
    payload["objectID"] = session_id
    payload["evaluationContext"] = {"athleteID": athlete_id, "sessionID": session_id}
    payload["session"] = {
        "sessionDate": session_date,
        "contactLoad": contact_load,
        "exercises": exercises if exercises is not None else [],
    }
    anchor = date.fromisoformat(anchor_date)
    for entry in payload["windowContext"]:
        if entry["windowType"] == "ROLLING28DAYS":
            entry["anchorDate"] = anchor_date
            entry["startDate"] = (anchor - timedelta(days=28)).isoformat()
            entry["endDate"] = anchor_date
        elif entry["windowType"] == "ROLLING7DAYS":
            entry["anchorDate"] = anchor_date
            entry["startDate"] = (anchor - timedelta(days=7)).isoformat()
            entry["endDate"] = anchor_date
    return payload


def _meso_payload(athlete_id: str, meso_id: str, anchor_date: str) -> dict:
    payload = _conformance_meso_base()
    payload["objectID"] = meso_id
    payload["evaluationContext"] = {"athleteID": athlete_id, "mesoID": meso_id}
    anchor = date.fromisoformat(anchor_date)
    entry = payload["windowContext"][0]
    entry["anchorDate"] = anchor_date
    entry["startDate"] = (anchor - timedelta(days=28)).isoformat()
    entry["endDate"] = anchor_date
    entry["timezone"] = "UTC"
    return payload


def _macro_payload(athlete_id: str, season_id: str, anchor_date: str) -> dict:
    payload = _conformance_macro_base()
    payload["objectID"] = season_id
    payload["evaluationContext"] = {"athleteID": athlete_id, "seasonID": season_id}
    anchor = date.fromisoformat(anchor_date)
    entry = payload["windowContext"][0]
    entry["anchorDate"] = anchor_date
    entry["startDate"] = (anchor - timedelta(days=365)).isoformat()
    entry["endDate"] = anchor_date
    entry["timezone"] = "UTC"
    return payload


# ------------------------------------------------------------------ #
# Tests                                                               #
# ------------------------------------------------------------------ #

def test_health_returns_ok(svc):
    client, _, _, _ = svc
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "db_path" in body


def test_evaluate_session_clean_returns_200_and_kdo(svc):
    client, op_store, _, _ = svc
    op_store.upsert_athlete({
        "athlete_id": "ATH-SVC-01",
        "max_daily_contact_load": 999.0,
        "minimum_rest_interval_hours": 0.0,
        "e4_clearance": 1,
    })

    payload = _session_payload(
        athlete_id="ATH-SVC-01",
        session_id="S-SVC-01",
        session_date="2026-01-15T10:00:00+00:00",
        contact_load=0,
        exercises=[],
        anchor_date="2026-01-15",
    )

    r = client.post("/evaluate/session", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["module_id"] == "SESSION"
    assert body["resolution"]["finalPublishState"] == "LEGALREADY"
    assert isinstance(body["audit"]["decisionHash"], str)
    assert len(body["audit"]["decisionHash"]) > 0
    assert "violations" in body


def test_evaluate_session_violation_returns_200_with_kdo(svc):
    client, op_store, _, _ = svc
    op_store.upsert_athlete({
        "athlete_id": "ATH-SVC-VIOL",
        "max_daily_contact_load": 10.0,
        "minimum_rest_interval_hours": 24.0,
        "e4_clearance": 0,
    })

    payload = _session_payload(
        athlete_id="ATH-SVC-VIOL",
        session_id="S-SVC-VIOL-01",
        session_date="2026-01-15T10:00:00+00:00",
        contact_load=999.0,
        anchor_date="2026-01-15",
    )

    r = client.post("/evaluate/session", json=payload)
    assert r.status_code == 200
    body = r.json()
    codes = {v["code"] for v in body["violations"]}
    assert "SCM.MAXDAILYLOAD" in codes
    assert body["resolution"]["finalPublishState"] == "ILLEGALQUARANTINED"


def test_evaluate_session_commits_kdo_to_audit_store(svc):
    client, op_store, _, db = svc
    op_store.upsert_athlete({
        "athlete_id": "ATH-SVC-COMMIT",
        "max_daily_contact_load": 999.0,
        "minimum_rest_interval_hours": 0.0,
        "e4_clearance": 1,
    })

    payload = _session_payload(
        athlete_id="ATH-SVC-COMMIT",
        session_id="S-SVC-COMMIT-01",
        session_date="2026-01-15T10:00:00+00:00",
        contact_load=0,
        anchor_date="2026-01-15",
    )

    r = client.post("/evaluate/session", json=payload)
    assert r.status_code == 200
    decision_hash = r.json()["audit"]["decisionHash"]

    conn = sqlite3.connect(str(db))
    row = conn.execute(
        "SELECT decision_hash FROM kdo_log WHERE decision_hash = ?",
        (decision_hash,),
    ).fetchone()
    conn.close()
    assert row is not None


def test_evaluate_session_quarantine_still_commits_kdo(svc):
    # ATH-SVC-QUAR is never seeded → sentinel → SCM.MAXDAILYLOAD fires.
    # KDO is quarantined but must still be committed and returned as 200.
    client, _, _, db = svc

    payload = _session_payload(
        athlete_id="ATH-SVC-QUAR",
        session_id="S-SVC-QUAR",
        session_date="2026-01-15T10:00:00+00:00",
        contact_load=1.0,
        anchor_date="2026-01-15",
    )

    r = client.post("/evaluate/session", json=payload)
    assert r.status_code == 200
    body = r.json()
    codes = {v["code"] for v in body["violations"]}
    assert "SCM.MAXDAILYLOAD" in codes

    decision_hash = body["audit"]["decisionHash"]
    conn = sqlite3.connect(str(db))
    row = conn.execute(
        "SELECT decision_hash FROM kdo_log WHERE decision_hash = ?",
        (decision_hash,),
    ).fetchone()
    conn.close()
    assert row is not None


def test_evaluate_meso_returns_200_and_kdo(svc):
    client, op_store, _, _ = svc
    op_store.upsert_athlete({
        "athlete_id": "ATH-SVC-MESO",
        "max_daily_contact_load": 9999.0,
        "minimum_rest_interval_hours": 0.0,
        "e4_clearance": 0,
    })

    anchor = date.fromisoformat("2026-02-01")
    # Four sessions within ROLLING28DAYS of anchor (2026-01-04 to 2026-02-01).
    # avg=60.0, max=150.0, 150.0 > 120.0 → MESO.LOADIMBALANCE fires.
    sessions = [
        ("MESO-SVC-S1", anchor - timedelta(days=25), 30.0),
        ("MESO-SVC-S2", anchor - timedelta(days=18), 30.0),
        ("MESO-SVC-S3", anchor - timedelta(days=11), 30.0),
        ("MESO-SVC-S4", anchor - timedelta(days=4),  150.0),
    ]
    for sid, sdate, load in sessions:
        op_store.upsert_session({
            "session_id": sid,
            "athlete_id": "ATH-SVC-MESO",
            "session_date": sdate.isoformat() + "T10:00:00+00:00",
            "contact_load": load,
        })

    payload = _meso_payload(
        athlete_id="ATH-SVC-MESO",
        meso_id="MESO-SVC-01",
        anchor_date="2026-02-01",
    )

    r = client.post("/evaluate/meso", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["module_id"] == "MESO"
    codes = {v["code"] for v in body["violations"]}
    assert "MESO.LOADIMBALANCE" in codes


def test_evaluate_macro_returns_200_and_kdo(svc):
    client, op_store, _, _ = svc
    op_store.upsert_athlete({
        "athlete_id": "ATH-SVC-MAC",
        "max_daily_contact_load": 200.0,
        "minimum_rest_interval_hours": 24.0,
        "e4_clearance": 0,
    })
    op_store.upsert_season({
        "athlete_id": "ATH-SVC-MAC",
        "season_id": "SEASON-SVC-01",
        "competition_weeks": 10,
        "gpp_weeks": 2,
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
    })

    payload = _macro_payload(
        athlete_id="ATH-SVC-MAC",
        season_id="SEASON-SVC-01",
        anchor_date="2026-12-31",
    )

    r = client.post("/evaluate/macro", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["module_id"] == "MACRO"
    codes = {v["code"] for v in body["violations"]}
    assert "MACRO.PHASEMISMATCH" in codes


def test_evaluate_session_incomplete_payload_returns_200_with_kdo(svc):
    # Semantically incomplete payload — kernel fires a RAL synthetic violation.
    # This is NOT a 4xx; the kernel handles it and returns a KDO with violations.
    client, _, _, _ = svc

    r = client.post("/evaluate/session", json={"incomplete": "payload"})
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body["violations"], list)
    assert len(body["violations"]) > 0


def test_evaluate_session_malformed_json_returns_4xx(svc):
    # Raw bytes that are not valid JSON — FastAPI/Starlette rejects before
    # the handler runs. Never reaches the kernel.
    client, _, _, _ = svc

    r = client.post(
        "/evaluate/session",
        content=b"not valid json {",
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code in (400, 422)


def test_each_endpoint_commits_exactly_one_kdo_per_request(svc):
    client, op_store, _, db = svc
    op_store.upsert_athlete({
        "athlete_id": "ATH-SVC-COUNT",
        "max_daily_contact_load": 9999.0,
        "minimum_rest_interval_hours": 0.0,
        "e4_clearance": 1,
    })
    op_store.upsert_season({
        "athlete_id": "ATH-SVC-COUNT",
        "season_id": "SEASON-COUNT",
        "competition_weeks": 4,
        "gpp_weeks": 8,
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
    })

    conn = sqlite3.connect(str(db))
    initial = conn.execute("SELECT COUNT(*) FROM kdo_log").fetchone()[0]
    conn.close()

    r1 = client.post("/evaluate/session", json=_session_payload(
        athlete_id="ATH-SVC-COUNT",
        session_id="S-COUNT-01",
        session_date="2026-01-15T10:00:00+00:00",
        contact_load=0,
        anchor_date="2026-01-15",
    ))
    assert r1.status_code == 200

    r2 = client.post("/evaluate/meso", json=_meso_payload(
        athlete_id="ATH-SVC-COUNT",
        meso_id="MESO-COUNT-01",
        anchor_date="2026-02-01",
    ))
    assert r2.status_code == 200

    r3 = client.post("/evaluate/macro", json=_macro_payload(
        athlete_id="ATH-SVC-COUNT",
        season_id="SEASON-COUNT",
        anchor_date="2026-12-31",
    ))
    assert r3.status_code == 200

    conn = sqlite3.connect(str(db))
    final = conn.execute("SELECT COUNT(*) FROM kdo_log").fetchone()[0]
    conn.close()
    assert final == initial + 3
