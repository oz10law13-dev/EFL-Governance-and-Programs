from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from efl_kernel.service import create_app


# ------------------------------------------------------------------ #
# Fixture                                                             #
# ------------------------------------------------------------------ #

@pytest.fixture(scope="module")
def client(tmp_path_factory):
    db = tmp_path_factory.mktemp("ex_ep") / "test.db"
    app = create_app(str(db))
    return TestClient(app)


# ------------------------------------------------------------------ #
# GET /exercises                                                      #
# ------------------------------------------------------------------ #

def test_get_exercises_returns_all(client):
    resp = client.get("/exercises")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 200


def test_get_exercises_includes_normalized_fields(client):
    resp = client.get("/exercises")
    assert resp.status_code == 200
    first = resp.json()[0]
    assert "day_roles" in first
    assert "unilateral" in first


def test_get_exercises_filter_h_node(client):
    resp = client.get("/exercises?h_node=H2")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) > 0
    assert all(ex["h_node"] == "H2" for ex in data)


def test_get_exercises_filter_day_role(client):
    resp = client.get("/exercises?day_role=A")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) > 0
    assert all("A" in ex["day_roles"] for ex in data)


def test_get_exercises_filter_movement_family(client):
    resp = client.get("/exercises?movement_family=Squat")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) > 0
    assert all(ex["movement_family"] == "Squat" for ex in data)


def test_get_exercises_filter_node_max(client):
    resp = client.get("/exercises?node_max=3")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) > 0
    assert all(ex["node_max"] >= 3 for ex in data)


# ------------------------------------------------------------------ #
# GET /exercises/{canonical_id}                                       #
# ------------------------------------------------------------------ #

def test_get_exercise_by_id_found(client):
    resp = client.get("/exercises/ECA-PHY-0001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["canonical_id"] == "ECA-PHY-0001"
    assert data["exercise_name"] == "Back Squat"


def test_get_exercise_by_id_not_found(client):
    resp = client.get("/exercises/ECA-PHY-XXXX")
    assert resp.status_code == 404


# ------------------------------------------------------------------ #
# POST /check/exercise                                                #
# ------------------------------------------------------------------ #

def test_check_exercise_no_violations(client):
    resp = client.post("/check/exercise", json={
        "canonical_id": "ECA-PHY-0001",
        "band_count": 2,
        "node": 2,
        "day_role": "A",
        "tempo": "3:0:1:0",
        "set_count": 4,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["violations"] == []
    assert data["exercise"]["canonical_id"] == "ECA-PHY-0001"


def test_check_exercise_band_violation(client):
    # ECA-PHY-0001 band_max=3; band_count=4 → BAND_LIMIT_EXCEEDED
    resp = client.post("/check/exercise", json={
        "canonical_id": "ECA-PHY-0001",
        "band_count": 4,
    })
    assert resp.status_code == 200
    codes = [v["code"] for v in resp.json()["violations"]]
    assert "BAND_LIMIT_EXCEEDED" in codes


def test_check_exercise_not_found_exercise(client):
    resp = client.post("/check/exercise", json={"canonical_id": "ECA-PHY-XXXX"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["exercise"] is None
    codes = [v["code"] for v in data["violations"]]
    assert "EXERCISE_NOT_FOUND" in codes


def test_list_filter_band_max(client):
    resp = client.get("/exercises?band_max=2")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) > 0
    assert all(ex["band_max"] >= 2 for ex in data)


def test_list_filter_volume_class(client):
    resp = client.get("/exercises?volume_class=PRIMARY")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) > 0
    assert all(ex["volume_class"] == "PRIMARY" for ex in data)


def test_check_exercise_returns_sfi_contribution(client):
    # ECA-PHY-0025 Bulgarian Split Squat: unilateral, H2, node=2, set_count=4 → sfi=2.0
    resp = client.post("/check/exercise", json={
        "canonical_id": "ECA-PHY-0025",
        "node": 2,
        "set_count": 4,
    })
    assert resp.status_code == 200
    assert resp.json()["sfi_contribution"] == pytest.approx(2.0)
