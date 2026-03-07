from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from efl_kernel.kernel.ral import RAL_SPEC
from efl_kernel.service import create_app

PHY_REG = RAL_SPEC["moduleRegistration"]["PHYSIQUE"]
_ANCHOR = date(2026, 1, 1)


def _phy_payload(exercise_id: str, tempo: str = "3:0:1:0", context: dict | None = None) -> dict:
    """Minimal valid physique eval payload. Omitting day_slots avoids slot-level MCC gates."""
    payload = {
        "moduleVersion": PHY_REG["moduleVersion"],
        "moduleViolationRegistryVersion": PHY_REG["moduleViolationRegistryVersion"],
        "registryHash": PHY_REG["registryHash"],
        "objectID": f"obj-loop-{exercise_id}",
        "evaluationContext": {"athleteID": "ATH-LOOP-01", "sessionID": "S-LOOP-01"},
        "windowContext": [
            {
                "windowType": "ROLLING7DAYS",
                "anchorDate": _ANCHOR.isoformat(),
                "startDate": (_ANCHOR - timedelta(days=7)).isoformat(),
                "endDate": _ANCHOR.isoformat(),
                "timezone": "UTC",
            },
            {
                "windowType": "ROLLING28DAYS",
                "anchorDate": _ANCHOR.isoformat(),
                "startDate": (_ANCHOR - timedelta(days=28)).isoformat(),
                "endDate": _ANCHOR.isoformat(),
                "timezone": "UTC",
            },
        ],
        "physique_session": {
            "exercises": [{"exercise_id": exercise_id, "tempo": tempo}],
        },
    }
    if context:
        payload["context"] = context
    return payload


def _phy_payload_with_slot(
    exercise_id: str, band: int, node: int, tempo: str = "3:0:1:0", context: dict | None = None
) -> dict:
    """Physique eval payload with a day_slot (required to trigger slot-level MCC gates like D3).

    context must be provided (non-empty) so that O1 (MCC_PASS2_MISSING_OR_FAILED) does not fire
    in place of the slot-level MCC gates. Without context, O1 fires when day_slots is non-empty.
    """
    payload = _phy_payload(exercise_id, tempo, context)
    payload["day_slots"] = [{
        "day_role": "DAY_C",
        "exercises": [{
            "exercise_id": exercise_id,
            "band": band,
            "node": node,
            "role": "WORK",
            "set_count": 3,
        }]
    }]
    return payload


@pytest.fixture
def app_client(tmp_path):
    db = str(tmp_path / "os_loop.db")
    app = create_app(db)
    client = TestClient(app)
    app.state.op_store.upsert_athlete({
        "athlete_id": "ATH-LOOP-01",
        "max_daily_contact_load": 9999.0,
        "minimum_rest_interval_hours": 0.0,
        "e4_clearance": 1,
    })
    return client, app


# ─── Invariant 1 ───────────────────────────────────────────────────────────
# The catalog never returns an exercise illegal within its own declared envelope.

def test_catalog_to_check_to_legal(app_client):
    """Any exercise returned by /exercises is legal at its own ceiling (band_max, node_max, day_role)."""
    client, _ = app_client
    exercises = client.get("/exercises?day_role=A").json()
    assert len(exercises) > 0
    ex = exercises[0]
    cid = ex["canonical_id"]

    result = client.post("/check/exercise", json={
        "canonical_id": cid,
        "band_count": ex["band_max"],   # at ceiling — still legal
        "node": ex["node_max"],          # at ceiling — still legal
        "day_role": "A",
        "set_count": 3,
    }).json()

    assert result["violations"] == [], (
        f"Exercise {cid} declared day_role=A with band_max={ex['band_max']} and "
        f"node_max={ex['node_max']}, but check_exercise reported violations: {result['violations']}"
    )


# ─── Invariant 2 ───────────────────────────────────────────────────────────
# Catalog → check → full governed eval is one coherent chain.

def test_catalog_to_check_to_eval_legalready(app_client):
    """An exercise that check_exercise approves also produces LEGALREADY from /evaluate/physique."""
    client, app = app_client
    exercises = client.get("/exercises?day_role=A&node_max=2").json()
    assert len(exercises) > 0
    ex = exercises[0]
    cid = ex["canonical_id"]

    # Stateless fast-path: no violations at conservative band/node
    check = client.post("/check/exercise", json={
        "canonical_id": cid,
        "band_count": 1,
        "node": 1,
        "day_role": "A",
        "tempo": "3:0:1:0",
        "set_count": 3,
    }).json()
    assert check["violations"] == []

    # Full governed path: KDO must be clean and committed
    db_path = app.state.db_path
    with sqlite3.connect(db_path) as conn:
        kdo_before = conn.execute("SELECT COUNT(*) FROM kdo_log").fetchone()[0]

    phy_resp = client.post("/evaluate/physique", json=_phy_payload(cid)).json()

    with sqlite3.connect(db_path) as conn:
        kdo_after = conn.execute("SELECT COUNT(*) FROM kdo_log").fetchone()[0]

    assert phy_resp["resolution"]["finalPublishState"] == "LEGALREADY"
    assert kdo_after == kdo_before + 1


# ─── Invariant 3 ───────────────────────────────────────────────────────────
# Stateless fast-path and full governed path agree on violations.

def test_band_violation_check_and_eval_agree(app_client):
    """BAND_LIMIT_EXCEEDED from check_exercise correlates with gate violations in full physique eval."""
    client, _ = app_client

    # Find an exercise with band_max=1
    all_exercises = client.get("/exercises").json()
    low_band = [ex for ex in all_exercises if ex["band_max"] == 1]
    assert low_band, "Whitelist must contain at least one exercise with band_max=1"
    ex = low_band[0]
    cid = ex["canonical_id"]

    # Stateless check: band_count=3 exceeds band_max=1
    check = client.post("/check/exercise", json={"canonical_id": cid, "band_count": 3}).json()
    check_codes = [v["code"] for v in check["violations"]]
    assert "BAND_LIMIT_EXCEEDED" in check_codes

    # Full physique eval: band=3 AND node=3 in slot triggers D3 (MCC_BAND_NODE_ILLEGAL_COMBINATION).
    # D3 fires unconditionally for any exercise when band==3 and node==3 simultaneously,
    # certifying the governed path also rejects the session.
    # context must be non-empty so O1 (MCC_PASS2_MISSING_OR_FAILED) does not preempt D3.
    phy_resp = client.post(
        "/evaluate/physique",
        json=_phy_payload_with_slot(cid, band=3, node=3, context={"athlete_id": "ATH-LOOP-01"}),
    ).json()
    viol_codes = [v["code"] for v in phy_resp.get("violations", [])]
    assert "MCC_BAND_NODE_ILLEGAL_COMBINATION" in viol_codes
    assert phy_resp["resolution"]["finalPublishState"] != "LEGALREADY"


# ─── Invariant 4 ───────────────────────────────────────────────────────────
# Persistent world state (readiness history) actually influences gate outcomes.

def test_readiness_history_persisted_and_gate_fires(app_client):
    """Seeded YELLOW sessions in op_store cause L3 gate to fire via provider path (not payload hint)."""
    client, app = app_client
    op_store = app.state.op_store
    anchor_date = date(2026, 3, 7)

    # Seed 4 YELLOW sessions within the 7-day window before anchor_date
    for i in range(4):
        session_date = (anchor_date - timedelta(days=i + 1)).isoformat() + "T10:00:00+00:00"
        op_store.upsert_session({
            "session_id": f"S-YELLOW-{i}",
            "athlete_id": "ATH-LOOP-01",
            "session_date": session_date,
            "contact_load": 50.0,
            "readiness_state": "YELLOW",
        })

    # context has athlete_id + anchor_date but NOT chronic_yellow_count.
    # Absence of chronic_yellow_count forces the provider path (real store lookup).
    # A day_slot is required: run_physique_mcc_gates early-returns with [] when day_slots is empty,
    # so L3 would never run without at least one slot.
    ctx = {
        "athlete_id": "ATH-LOOP-01",
        "anchor_date": anchor_date.isoformat(),
    }
    phy_resp = client.post(
        "/evaluate/physique",
        json=_phy_payload_with_slot("ECA-PHY-0001", band=1, node=1, context=ctx),
    ).json()

    viol_codes = [v["code"] for v in phy_resp.get("violations", [])]
    assert "MCC_CHRONIC_YELLOW_GUARD_TRIGGERED" in viol_codes, (
        "L3 gate must fire from store-persisted readiness history, not from a payload hint. "
        f"Violations found: {viol_codes}"
    )
