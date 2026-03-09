"""Phase 18 — Governed Authoring / Builder Prep."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from efl_kernel.kernel.ral import RAL_SPEC
from efl_kernel.service import create_app

PHY_REG = RAL_SPEC["moduleRegistration"]["PHYSIQUE"]


@pytest.fixture()
def svc(tmp_path):
    audit_db = str(tmp_path / "audit_p18.db")
    op_db    = str(tmp_path / "op_p18.db")
    app = create_app(db_path=audit_db, op_db_path=op_db)
    client = TestClient(app)
    app.state.op_store.upsert_athlete({
        "athlete_id": "ATH-P18-01",
        "max_daily_contact_load": 999.0,
        "minimum_rest_interval_hours": 0.0,
        "e4_clearance": 1,
    })
    return client, app


def _constraints(
    athlete_id: str = "ATH-P18-01",
    session_id: str = "S-P18-01",
    day_role: str = "A",
    target_exercise_count: int = 3,
) -> dict:
    return {
        "athlete_id": athlete_id,
        "session_id": session_id,
        "day_role": day_role,
        "target_exercise_count": target_exercise_count,
    }


# ─── Test 1 — response shape ──────────────────────────────────────────────────

def test_propose_returns_valid_shape(svc):
    client, _ = svc
    r = client.post("/propose/physique", json=_constraints())
    assert r.status_code == 200
    body = r.json()
    assert "candidate_payload" in body
    assert "pre_validation" in body
    assert "exercises_selected" in body
    assert "constraints_applied" in body
    cp = body["candidate_payload"]
    assert "moduleVersion" in cp
    assert "moduleViolationRegistryVersion" in cp
    assert "registryHash" in cp
    assert "objectID" in cp
    assert "evaluationContext" in cp
    assert "windowContext" in cp
    assert "physique_session" in cp


# ─── Test 2 — no pre-validation violations ────────────────────────────────────

def test_propose_candidate_has_no_pre_validation_violations(svc):
    client, _ = svc
    r = client.post("/propose/physique", json=_constraints())
    assert r.status_code == 200
    for entry in r.json()["pre_validation"]:
        assert entry["violations"] == [], (
            f"Exercise {entry['canonical_id']} has unexpected "
            f"pre-validation violations: {entry['violations']}"
        )


# ─── Test 3 — day_role respected ──────────────────────────────────────────────

def test_propose_respects_day_role(svc):
    client, _ = svc
    r = client.post("/propose/physique", json=_constraints(day_role="A"))
    assert r.status_code == 200
    exercises = r.json()["candidate_payload"]["physique_session"]["exercises"]
    assert len(exercises) > 0
    for ex in exercises:
        assert ex["day_role"] == "A"


# ─── Test 4 — candidate evaluates to LEGALREADY ───────────────────────────────

def test_propose_candidate_evaluates_to_legalready(svc):
    client, _ = svc
    r = client.post("/propose/physique", json=_constraints())
    assert r.status_code == 200
    candidate = r.json()["candidate_payload"]

    r2 = client.post("/evaluate/physique", json=candidate)
    assert r2.status_code == 200, (
        f"/evaluate/physique returned {r2.status_code}: {r2.text}"
    )
    body2 = r2.json()
    assert body2["resolution"]["finalPublishState"] == "LEGALREADY", (
        f"Expected LEGALREADY, got: {body2['resolution']['finalPublishState']}\n"
        f"Violations: {body2.get('violations', [])}"
    )


# ─── Test 5 — full pipeline promotes to LIVE ──────────────────────────────────

def test_pipeline_propose_to_live(svc):
    client, _ = svc
    r = client.post("/pipeline/physique", json={
        "constraints": _constraints(),
        "artifact_id": "ART-P18-01",
        "object_id": "OBJ-P18-01",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["promoted"] is True
    assert body["lifecycle"] == "LIVE"
    assert body["publish_state"] == "LEGALREADY"
    assert body["violations"] == []
    assert "proposal" in body
    assert "version_id" in body
    assert "decision_hash" in body


# ─── Test 6 — pipeline rejects unseen athlete ─────────────────────────────────

def test_pipeline_rejected_returns_violations(svc):
    client, app = svc
    # Seed athlete with e4_clearance=0.
    # movement_families=["Technique Modifier"] + day_role="B" targets only
    # ECA-PHY-0027/0028/0029 which require E4 clearance.
    # With e4_clearance=0, PHYSIQUE.CLEARANCEMISSING fires → ILLEGALQUARANTINED.
    app.state.op_store.upsert_athlete({
        "athlete_id": "ATH-P18-QUAR",
        "max_daily_contact_load": 999.0,
        "minimum_rest_interval_hours": 0.0,
        "e4_clearance": 0,
    })
    r = client.post("/pipeline/physique", json={
        "constraints": {
            "athlete_id": "ATH-P18-QUAR",
            "session_id": "S-P18-QUAR",
            "day_role": "B",
            "target_exercise_count": 1,
            "movement_families": ["Technique Modifier"],
        },
        "artifact_id": "ART-P18-QUAR",
        "object_id": "OBJ-P18-QUAR",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["promoted"] is False
    assert len(body["violations"]) > 0


# ─── Test 7 — 422 on missing required fields ──────────────────────────────────

def test_propose_missing_required_field_returns_422(svc):
    client, _ = svc
    r = client.post("/propose/physique", json={})
    assert r.status_code == 422

    r2 = client.post("/propose/physique", json={
        "athlete_id": "ATH-P18-01",
        "session_id": "S-P18-X",
        # day_role intentionally absent
    })
    assert r2.status_code == 422


# ─── Test 8 — determinism ─────────────────────────────────────────────────────

def test_proposal_is_deterministic(svc):
    client, _ = svc
    c = _constraints()
    r1 = client.post("/propose/physique", json=c)
    r2 = client.post("/propose/physique", json=c)
    assert r1.status_code == 200
    assert r2.status_code == 200
    # Compare excluding windowContext (date.today()-relative dates are stable
    # within a test run but the comparison is scoped to exercise selection)
    cp1 = {k: v for k, v in r1.json()["candidate_payload"].items()
           if k != "windowContext"}
    cp2 = {k: v for k, v in r2.json()["candidate_payload"].items()
           if k != "windowContext"}
    assert cp1 == cp2, (
        "propose() is not deterministic — same constraints produced "
        "different payloads on consecutive calls"
    )
