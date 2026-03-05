from __future__ import annotations

import hashlib
import json as jsonlib
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from efl_kernel.kernel.ral import RAL_SPEC
from efl_kernel.service import create_app

SESSION_REG = RAL_SPEC["moduleRegistration"]["SESSION"]


# ------------------------------------------------------------------ #
# Fixture                                                             #
# ------------------------------------------------------------------ #

@pytest.fixture(scope="module")
def svc(tmp_path_factory):
    db = tmp_path_factory.mktemp("art") / "test_art.db"
    app = create_app(str(db))
    client = TestClient(app)
    return (
        client,
        app.state.op_store,
        app.state.audit_store,
        app.state.artifact_store,
        db,
    )


# ------------------------------------------------------------------ #
# Payload helpers                                                     #
# ------------------------------------------------------------------ #

def _clean_session_payload(athlete_id: str, session_id: str) -> dict:
    anchor = date(2026, 1, 15)
    return {
        "moduleVersion": SESSION_REG["moduleVersion"],
        "moduleViolationRegistryVersion": SESSION_REG["moduleViolationRegistryVersion"],
        "registryHash": SESSION_REG["registryHash"],
        "objectID": session_id,
        "evaluationContext": {"athleteID": athlete_id, "sessionID": session_id},
        "windowContext": [
            {
                "windowType": "ROLLING7DAYS",
                "anchorDate": "2026-01-15",
                "startDate": (anchor - timedelta(days=7)).isoformat(),
                "endDate": "2026-01-15",
                "timezone": "UTC",
            },
            {
                "windowType": "ROLLING28DAYS",
                "anchorDate": "2026-01-15",
                "startDate": (anchor - timedelta(days=28)).isoformat(),
                "endDate": "2026-01-15",
                "timezone": "UTC",
            },
        ],
        "session": {
            "sessionDate": "2026-01-15T10:00:00+00:00",
            "contactLoad": 0,
            "exercises": [],
        },
    }


def _quarantine_session_payload(athlete_id: str, session_id: str) -> dict:
    # No athlete seeded for this athlete_id → sentinel fires SCM.MAXDAILYLOAD
    payload = _clean_session_payload(athlete_id, session_id)
    payload["session"]["contactLoad"] = 1.0
    return payload


# ------------------------------------------------------------------ #
# Tests                                                               #
# ------------------------------------------------------------------ #

def test_commit_artifact_returns_201_draft(svc):
    client, _, _, _, _ = svc
    r = client.post("/artifacts", json={
        "artifact_id": "ART-HTTP-01",
        "module_id": "SESSION",
        "object_id": "OBJ-01",
        "content": {"session": {"contactLoad": 100}},
    })
    assert r.status_code == 201
    body = r.json()
    assert body["lifecycle"] == "DRAFT"


def test_link_kdo_and_promote_legalready(svc):
    client, op_store, _, _, _ = svc

    op_store.upsert_athlete({
        "athlete_id": "ATH-ART-LIVE",
        "max_daily_contact_load": 999.0,
        "minimum_rest_interval_hours": 0.0,
        "e4_clearance": 1,
    })

    # Step 1: Create artifact
    r = client.post("/artifacts", json={
        "artifact_id": "ART-LIVE-01",
        "module_id": "SESSION",
        "object_id": "OBJ-LIVE-01",
        "content": {"session_plan": "load=0"},
    })
    assert r.status_code == 201
    version_id = r.json()["version_id"]
    content_hash = r.json()["content_hash"]

    # Step 2: Evaluate to get a committed LEGALREADY KDO
    r_eval = client.post(
        "/evaluate/session",
        json=_clean_session_payload("ATH-ART-LIVE", "S-ART-LIVE-01"),
    )
    assert r_eval.status_code == 200
    kdo_body = r_eval.json()
    assert kdo_body["resolution"]["finalPublishState"] == "LEGALREADY"
    decision_hash = kdo_body["audit"]["decisionHash"]

    # Step 3: Link KDO
    r = client.post(f"/artifacts/{version_id}/link-kdo", json={
        "decision_hash": decision_hash,
        "content_hash_at_eval": content_hash,
    })
    assert r.status_code == 200

    # Step 4: Promote
    r = client.post(f"/artifacts/{version_id}/promote")
    assert r.status_code == 200
    assert r.json()["lifecycle"] == "LIVE"


def test_promote_without_kdo_link_returns_409(svc):
    client, _, _, _, _ = svc

    r = client.post("/artifacts", json={
        "artifact_id": "ART-NOLINK-01",
        "module_id": "SESSION",
        "object_id": "OBJ-NOLINK",
        "content": {"x": 1},
    })
    assert r.status_code == 201
    version_id = r.json()["version_id"]

    r = client.post(f"/artifacts/{version_id}/promote")
    assert r.status_code == 409


def test_promote_hash_mismatch_returns_409(svc):
    client, op_store, _, _, _ = svc

    op_store.upsert_athlete({
        "athlete_id": "ATH-ART-MISMATCH",
        "max_daily_contact_load": 999.0,
        "minimum_rest_interval_hours": 0.0,
        "e4_clearance": 1,
    })

    # Create artifact
    r = client.post("/artifacts", json={
        "artifact_id": "ART-MISMATCH-01",
        "module_id": "SESSION",
        "object_id": "OBJ-MISMATCH",
        "content": {"x": 2},
    })
    assert r.status_code == 201
    version_id = r.json()["version_id"]

    # Get a real LEGALREADY KDO
    r_eval = client.post(
        "/evaluate/session",
        json=_clean_session_payload("ATH-ART-MISMATCH", "S-ART-MISMATCH"),
    )
    assert r_eval.status_code == 200
    decision_hash = r_eval.json()["audit"]["decisionHash"]

    # Link with a WRONG content_hash_at_eval (INV-2 mismatch)
    r = client.post(f"/artifacts/{version_id}/link-kdo", json={
        "decision_hash": decision_hash,
        "content_hash_at_eval": "wrong_hash_value",
    })
    assert r.status_code == 200

    # Promote → 409 (hash mismatch)
    r = client.post(f"/artifacts/{version_id}/promote")
    assert r.status_code == 409


def test_promote_illegalquarantined_returns_409(svc):
    # ATH-ART-QUAR is never seeded → sentinel → SCM.MAXDAILYLOAD → ILLEGALQUARANTINED
    client, _, _, _, _ = svc

    r_eval = client.post(
        "/evaluate/session",
        json=_quarantine_session_payload("ATH-ART-QUAR", "S-ART-QUAR"),
    )
    assert r_eval.status_code == 200
    kdo_body = r_eval.json()
    assert kdo_body["resolution"]["finalPublishState"] == "ILLEGALQUARANTINED"
    decision_hash = kdo_body["audit"]["decisionHash"]

    # Create artifact
    r = client.post("/artifacts", json={
        "artifact_id": "ART-QUAR-01",
        "module_id": "SESSION",
        "object_id": "OBJ-QUAR",
        "content": {"quarantine_test": True},
    })
    assert r.status_code == 201
    version_id = r.json()["version_id"]
    content_hash = r.json()["content_hash"]

    # Link
    r = client.post(f"/artifacts/{version_id}/link-kdo", json={
        "decision_hash": decision_hash,
        "content_hash_at_eval": content_hash,
    })
    assert r.status_code == 200

    # Promote → 409 (INV-3: ILLEGALQUARANTINED not eligible)
    r = client.post(f"/artifacts/{version_id}/promote")
    assert r.status_code == 409


def test_review_and_promote_requiresreview(svc):
    client, _, audit_store, _, _ = svc

    # Step 1: Create artifact
    r = client.post("/artifacts", json={
        "artifact_id": "ART-RR-01",
        "module_id": "SESSION",
        "object_id": "OBJ-RR-01",
        "content": {"type": "session_plan", "load": 50},
    })
    assert r.status_code == 201
    version_id = r.json()["version_id"]
    content_hash = r.json()["content_hash"]

    # Step 2: Insert a crafted REQUIRESREVIEW KDO directly into kdo_log.
    # audit_store.get_kdo reads kdo_json — no revalidation of the KDO structure.
    crafted_kdo = {"resolution": {"finalPublishState": "REQUIRESREVIEW"}}
    kdo_json_str = jsonlib.dumps(crafted_kdo, sort_keys=True, separators=(",", ":"))
    dh = hashlib.sha256(kdo_json_str.encode()).hexdigest()
    audit_store._conn.execute(
        "INSERT OR IGNORE INTO kdo_log "
        "(decision_hash, timestamp_normalized, module_id, object_id, kdo_json) "
        "VALUES (?, ?, ?, ?, ?)",
        (dh, "2026-01-01T00:00:00+00:00", "SESSION", "OBJ-RR-01", kdo_json_str),
    )
    audit_store._conn.commit()

    # Step 3: Link KDO
    r = client.post(f"/artifacts/{version_id}/link-kdo", json={
        "decision_hash": dh,
        "content_hash_at_eval": content_hash,
    })
    assert r.status_code == 200

    # Step 4: Promote without review → 409 (INV-4)
    r = client.post(f"/artifacts/{version_id}/promote")
    assert r.status_code == 409

    # Step 5: Add APPROVE review
    r = client.post(f"/artifacts/{version_id}/review", json={
        "decision_hash": dh,
        "reviewer_id": "coach-test",
        "reason": "verified",
        "decision": "APPROVE",
    })
    assert r.status_code == 200

    # Step 6: Promote with APPROVE → 200, LIVE
    r = client.post(f"/artifacts/{version_id}/promote")
    assert r.status_code == 200
    assert r.json()["lifecycle"] == "LIVE"


def test_get_artifact_version(svc):
    client, _, _, _, _ = svc

    r = client.post("/artifacts", json={
        "artifact_id": "ART-GET-01",
        "module_id": "SESSION",
        "object_id": "OBJ-GET-01",
        "content": {"get_test": True},
    })
    assert r.status_code == 201
    version_id = r.json()["version_id"]

    r = client.get(f"/artifacts/{version_id}")
    assert r.status_code == 200
    assert r.json()["version_id"] == version_id


def test_get_nonexistent_version_returns_404(svc):
    client, _, _, _, _ = svc

    r = client.get("/artifacts/does-not-exist")
    assert r.status_code == 404


def test_retire_endpoint(svc):
    client, _, _, _, _ = svc

    r = client.post("/artifacts", json={
        "artifact_id": "ART-RETIRE-01",
        "module_id": "SESSION",
        "object_id": "OBJ-RETIRE-01",
        "content": {"retire_test": True},
    })
    assert r.status_code == 201
    version_id = r.json()["version_id"]

    r = client.post(f"/artifacts/{version_id}/retire")
    assert r.status_code == 200
    assert r.json()["lifecycle"] == "RETIRED"
