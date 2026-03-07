from __future__ import annotations

import hashlib
import json as jsonlib
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from efl_kernel.kernel.ral import RAL_SPEC
from efl_kernel.service import create_app

SESSION_REG = RAL_SPEC["moduleRegistration"]["SESSION"]
PHY_REG = RAL_SPEC["moduleRegistration"]["PHYSIQUE"]


# ------------------------------------------------------------------ #
# Fixtures                                                            #
# ------------------------------------------------------------------ #

@pytest.fixture(scope="module")
def svc(tmp_path_factory):
    db = tmp_path_factory.mktemp("authoring") / "test_authoring.db"
    app = create_app(str(db))
    client = TestClient(app)
    return (
        client,
        app,
        app.state.op_store,
        app.state.audit_store,
        app.state.artifact_store,
    )


# ------------------------------------------------------------------ #
# Payload helpers                                                     #
# ------------------------------------------------------------------ #

def _session_eval_payload(athlete_id: str, session_id: str, contact_load: float = 0) -> dict:
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
            "contactLoad": contact_load,
            "exercises": [],
        },
    }


def _physique_eval_payload() -> dict:
    anchor = date(2026, 1, 1)
    return {
        "moduleVersion": PHY_REG["moduleVersion"],
        "moduleViolationRegistryVersion": PHY_REG["moduleViolationRegistryVersion"],
        "registryHash": PHY_REG["registryHash"],
        "objectID": "obj-physique-auth-1",
        "evaluationContext": {"athleteID": "a1", "sessionID": "s1"},
        "windowContext": [
            {
                "windowType": "ROLLING7DAYS",
                "anchorDate": "2026-01-01",
                "startDate": (anchor - timedelta(days=7)).isoformat(),
                "endDate": "2026-01-01",
                "timezone": "UTC",
            },
            {
                "windowType": "ROLLING28DAYS",
                "anchorDate": "2026-01-01",
                "startDate": (anchor - timedelta(days=28)).isoformat(),
                "endDate": "2026-01-01",
                "timezone": "UTC",
            },
        ],
        "physique_session": {
            "exercises": [{"exercise_id": "ECA-PHY-0001", "tempo": "3:1:1:0"}],
        },
    }


# ------------------------------------------------------------------ #
# Tests                                                               #
# ------------------------------------------------------------------ #

def test_evaluate_physique_returns_kdo(svc):
    client, _, _, _, _ = svc
    r = client.post("/evaluate/physique", json=_physique_eval_payload())
    assert r.status_code == 200
    body = r.json()
    assert body["module_id"] == "PHYSIQUE"
    assert body["resolution"]["finalPublishState"] == "LEGALREADY"
    assert isinstance(body["audit"]["decisionHash"], str)
    assert len(body["audit"]["decisionHash"]) > 0
    assert "violations" in body


def test_list_artifact_versions_by_artifact_id(svc):
    client, _, _, _, _ = svc

    for i in range(2):
        r = client.post("/artifacts", json={
            "artifact_id": "ART-LIST-01",
            "module_id": "SESSION",
            "object_id": f"OBJ-LIST-{i}",
            "content": {"seq": i},
        })
        assert r.status_code == 201

    r = client.get("/artifacts", params={"artifact_id": "ART-LIST-01"})
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2
    assert all(v["artifact_id"] == "ART-LIST-01" for v in body)


def test_list_artifact_versions_empty(svc):
    client, _, _, _, _ = svc

    r = client.get("/artifacts", params={"artifact_id": "ART-NONEXISTENT-999"})
    assert r.status_code == 200
    assert r.json() == []


def test_author_session_legalready_promotes_to_live(svc):
    client, _, op_store, _, artifact_store = svc

    op_store.upsert_athlete({
        "athlete_id": "ATH-AUTH-LIVE",
        "max_daily_contact_load": 999.0,
        "minimum_rest_interval_hours": 0.0,
        "e4_clearance": 1,
    })

    r = client.post("/author/session", json={
        "artifact_id": "ART-AUTH-LIVE-01",
        "object_id": "OBJ-AUTH-LIVE-01",
        "content": {"session_plan": "clean"},
        "evaluation_payload": _session_eval_payload("ATH-AUTH-LIVE", "S-AUTH-LIVE-01", contact_load=0),
    })
    assert r.status_code == 200
    body = r.json()
    assert body["promoted"] is True
    assert body["lifecycle"] == "LIVE"
    assert body["requires_review"] is False
    assert body["publish_state"] == "LEGALREADY"
    assert isinstance(body["decision_hash"], str)

    # Verify artifact is actually LIVE in the store
    version = artifact_store.get_version(body["version_id"])
    assert version["lifecycle"] == "LIVE"


def test_author_session_illegalquarantined_stays_draft(svc):
    # ATH-AUTH-QUAR is never seeded → sentinel fires SCM.MAXDAILYLOAD → ILLEGALQUARANTINED
    client, _, _, audit_store, artifact_store = svc

    r = client.post("/author/session", json={
        "artifact_id": "ART-AUTH-QUAR-01",
        "object_id": "OBJ-AUTH-QUAR-01",
        "content": {"session_plan": "quarantine_test"},
        "evaluation_payload": _session_eval_payload("ATH-AUTH-QUAR", "S-AUTH-QUAR-01", contact_load=1.0),
    })
    assert r.status_code == 200
    body = r.json()
    assert body["promoted"] is False
    assert body["lifecycle"] == "DRAFT"
    assert body["requires_review"] is False
    assert body["publish_state"] == "ILLEGALQUARANTINED"

    # Verify no KDO link was created for this artifact version
    version_id = body["version_id"]
    link_row = audit_store._conn.execute(
        "SELECT * FROM artifact_kdo_links WHERE version_id = ?", (version_id,)
    ).fetchone()
    assert link_row is None


def test_author_session_requiresreview_stays_draft_with_flag(tmp_path, monkeypatch):
    # REQUIRESREVIEW is not reachable via current SESSION gates (no gate sets
    # overrideUsed=True). Monkeypatch runner.evaluate to force the state so
    # the /author/session branch logic is exercised end-to-end.
    db = str(tmp_path / "test_rr.db")
    app = create_app(db)
    client = TestClient(app)

    app.state.op_store.upsert_athlete({
        "athlete_id": "ATH-AUTH-RR",
        "max_daily_contact_load": 999.0,
        "minimum_rest_interval_hours": 0.0,
        "e4_clearance": 1,
    })

    original_evaluate = app.state.runner.evaluate

    def _force_requiresreview(payload, module_id):
        kdo = original_evaluate(payload, module_id)
        kdo.resolution["finalPublishState"] = "REQUIRESREVIEW"
        return kdo

    monkeypatch.setattr(app.state.runner, "evaluate", _force_requiresreview)

    r = client.post("/author/session", json={
        "artifact_id": "ART-AUTH-RR-01",
        "object_id": "OBJ-AUTH-RR-01",
        "content": {"session_plan": "rr_test"},
        "evaluation_payload": _session_eval_payload("ATH-AUTH-RR", "S-AUTH-RR-01", contact_load=0),
    })
    assert r.status_code == 200
    body = r.json()
    assert body["promoted"] is False
    assert body["lifecycle"] == "DRAFT"
    assert body["requires_review"] is True
    assert body["publish_state"] == "REQUIRESREVIEW"

    # KDO link must exist (linked but not promoted)
    version_id = body["version_id"]
    conn = app.state.artifact_store._conn
    link_row = conn.execute(
        "SELECT * FROM artifact_kdo_links WHERE version_id = ?", (version_id,)
    ).fetchone()
    assert link_row is not None
