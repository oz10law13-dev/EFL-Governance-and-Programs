"""Whitelist v1.0.5 validation tests — 200-exercise expansion."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from efl_kernel.kernel.exercise_catalog import ExerciseCatalog
from efl_kernel.kernel.physique_adapter import WHITELIST_INDEX


_PHYSIQUE_DIR = Path(__file__).resolve().parent.parent.parent / "Physique"
_WL_PATH = _PHYSIQUE_DIR / "efl_whitelist_v1_0_5.json"


@pytest.fixture(scope="module")
def wl_data():
    return json.loads(_WL_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def cat():
    return ExerciseCatalog()


# ── 1. Count ──────────────────────────────────────────────────────────────────

def test_whitelist_has_200_exercises(wl_data):
    assert len(wl_data["exercises"]) == 200


def test_total_exercises_field_matches(wl_data):
    assert wl_data["total_exercises"] == 200


# ── 2. ID range ───────────────────────────────────────────────────────────────

def test_ids_are_contiguous_0001_to_0200(wl_data):
    ids = sorted(ex["canonical_id"] for ex in wl_data["exercises"])
    expected = [f"ECA-PHY-{i:04d}" for i in range(1, 201)]
    assert ids == expected


def test_no_duplicate_ids(wl_data):
    ids = [ex["canonical_id"] for ex in wl_data["exercises"]]
    assert len(ids) == len(set(ids))


# ── 3. Version ────────────────────────────────────────────────────────────────

def test_version_is_1_0_5(wl_data):
    assert wl_data["version"] == "1.0.5"


# ── 4. Remapped exercises present at new IDs ─────────────────────────────────

_REMAP = {
    "ECA-PHY-0013": "Romanian Deadlift",
    "ECA-PHY-0014": "Conventional Deadlift",
    "ECA-PHY-0015": "Leg Press",
    "ECA-PHY-0025": "Bulgarian Split Squat",
    "ECA-PHY-0026": "Walking Lunge",
    "ECA-PHY-0035": "Barbell Bench Press",
    "ECA-PHY-0036": "Incline Dumbbell Press",
    "ECA-PHY-0047": "Overhead Press",
    "ECA-PHY-0055": "Pull-Up",
    "ECA-PHY-0056": "Seated Cable Row",
    "ECA-PHY-0067": "Barbell Bent-Over Row",
    "ECA-PHY-0068": "Lat Pulldown",
    "ECA-PHY-0077": "Dumbbell Biceps Curl",
    "ECA-PHY-0085": "Cable Triceps Pushdown",
    "ECA-PHY-0093": "Dumbbell Lateral Raise",
    "ECA-PHY-0101": "Leg Extension",
    "ECA-PHY-0106": "Lying Leg Curl",
    "ECA-PHY-0016": "Hip Thrust",
    "ECA-PHY-0114": "Plank",
    "ECA-PHY-0116": "Cable Woodchop",
    "ECA-PHY-0124": "Farmer Carry",
    "ECA-PHY-0127": "Sled Drag",
    "ECA-PHY-0129": "Band External Rotation",
    "ECA-PHY-0130": "Face Pull",
    "ECA-PHY-0135": "Rest-Pause Set",
    "ECA-PHY-0136": "Myo-Reps",
    "ECA-PHY-0137": "Drop Set",
    "ECA-PHY-0003": "Tempo Squat",
}


def test_remapped_exercises_at_correct_ids(cat):
    for cid, name_fragment in _REMAP.items():
        ex = cat.get_exercise(cid)
        assert ex is not None, f"{cid} missing from catalog"
        assert name_fragment in ex["exercise_name"], (
            f"{cid}: expected name containing {name_fragment!r}, got {ex['exercise_name']!r}"
        )


# ── 5. Property changes applied ──────────────────────────────────────────────

def test_hip_thrust_volume_class_primary(cat):
    ex = cat.get_exercise("ECA-PHY-0016")
    assert ex["volume_class"] == "PRIMARY"


def test_walking_lunge_node_max_2(cat):
    ex = cat.get_exercise("ECA-PHY-0026")
    assert ex["node_max"] == 2


def test_plank_day_roles_bcd(cat):
    ex = cat.get_exercise("ECA-PHY-0114")
    assert set(ex["day_roles"]) == {"B", "C", "D"}


# ── 6. Schema consistency ────────────────────────────────────────────────────

_REQUIRED_FIELDS = {
    "exercise_name", "canonical_id", "movement_family", "primary_joint",
    "pattern_plane", "push_pull", "horiz_vert", "compound_isolation",
    "uni_bi", "equipment", "volume_class", "h_node", "band_max",
    "node_max", "day_role_allowed", "notes", "tempo_class", "eccentric_max",
    "isometric_bottom_max", "isometric_top_max", "explosive_concentric_allowed",
    "tempo_can_escalate_hnode", "e4_requires_clearance",
}


def test_all_exercises_have_required_fields(wl_data):
    for ex in wl_data["exercises"]:
        missing = _REQUIRED_FIELDS - set(ex.keys())
        assert missing == set(), f"{ex['canonical_id']} missing fields: {missing}"
