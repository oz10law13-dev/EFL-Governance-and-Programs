from __future__ import annotations

import pytest

from efl_kernel.kernel.exercise_catalog import ExerciseCatalog


# ------------------------------------------------------------------ #
# Fixture                                                             #
# ------------------------------------------------------------------ #

@pytest.fixture(scope="module")
def cat():
    return ExerciseCatalog()


# ------------------------------------------------------------------ #
# Load / normalization                                                #
# ------------------------------------------------------------------ #

def test_catalog_loads_all_exercises(cat):
    assert len(cat.list_exercises()) == 30


def test_catalog_normalizes_day_roles_from_csv(cat):
    # ECA-PHY-0001 Back Squat: day_role_allowed="A,C" → ["A", "C"]
    ex = cat.get_exercise("ECA-PHY-0001")
    assert ex["day_roles"] == ["A", "C"]


def test_catalog_normalizes_day_roles_single(cat):
    # ECA-PHY-0004 Deadlift: day_role_allowed="A" → ["A"]
    ex = cat.get_exercise("ECA-PHY-0004")
    assert ex["day_roles"] == ["A"]


def test_catalog_normalizes_unilateral_true(cat):
    # ECA-PHY-0006 Bulgarian Split Squat: uni_bi="Unilateral"
    ex = cat.get_exercise("ECA-PHY-0006")
    assert ex["unilateral"] is True


def test_catalog_normalizes_unilateral_false(cat):
    # ECA-PHY-0001 Back Squat: uni_bi="Bilateral"
    ex = cat.get_exercise("ECA-PHY-0001")
    assert ex["unilateral"] is False


# ------------------------------------------------------------------ #
# list_exercises                                                      #
# ------------------------------------------------------------------ #

def test_list_exercises_no_filter_returns_all(cat):
    assert len(cat.list_exercises()) == 30


def test_list_exercises_empty_filter_returns_all(cat):
    assert len(cat.list_exercises({})) == 30


def test_list_exercises_filter_by_h_node(cat):
    results = cat.list_exercises({"h_node": "H2"})
    assert len(results) > 0
    assert all(ex["h_node"] == "H2" for ex in results)


def test_list_exercises_filter_by_day_role_membership(cat):
    # day_role=A filters exercises where "A" is in day_roles list
    results = cat.list_exercises({"day_role": "A"})
    assert len(results) > 0
    assert all("A" in ex["day_roles"] for ex in results)
    # ECA-PHY-0005 Leg Press is B,C only — must not appear
    ids = {ex["canonical_id"] for ex in results}
    assert "ECA-PHY-0005" not in ids


def test_list_exercises_filter_by_movement_family(cat):
    results = cat.list_exercises({"movement_family": "Squat"})
    assert len(results) > 0
    assert all(ex["movement_family"] == "Squat" for ex in results)


def test_list_exercises_filter_by_node(cat):
    # node=3 → exercises with node_max >= 3
    results = cat.list_exercises({"node": 3})
    assert len(results) > 0
    assert all(ex["node_max"] >= 3 for ex in results)
    # ECA-PHY-0004 Deadlift has node_max=1 → must not appear
    ids = {ex["canonical_id"] for ex in results}
    assert "ECA-PHY-0004" not in ids


def test_list_exercises_combined_filter(cat):
    results = cat.list_exercises({"h_node": "H2", "day_role": "B"})
    assert len(results) > 0
    assert all(ex["h_node"] == "H2" and "B" in ex["day_roles"] for ex in results)


def test_list_exercises_no_match_returns_empty(cat):
    assert cat.list_exercises({"movement_family": "NonExistentFamily"}) == []


# ------------------------------------------------------------------ #
# get_exercise                                                        #
# ------------------------------------------------------------------ #

def test_get_exercise_found(cat):
    ex = cat.get_exercise("ECA-PHY-0001")
    assert ex is not None
    assert ex["exercise_name"] == "Back Squat"


def test_get_exercise_not_found(cat):
    assert cat.get_exercise("ECA-PHY-XXXX") is None


def test_get_exercise_returns_normalized(cat):
    ex = cat.get_exercise("ECA-PHY-0001")
    assert "day_roles" in ex
    assert "unilateral" in ex


# ------------------------------------------------------------------ #
# check_exercise — happy path                                        #
# ------------------------------------------------------------------ #

def test_check_exercise_no_violations(cat):
    result = cat.check_exercise({
        "canonical_id": "ECA-PHY-0001",
        "band_count": 2,
        "node": 2,
        "day_role": "A",
        "tempo": "3:0:1:0",
        "set_count": 4,
    })
    assert result["violations"] == []
    assert result["exercise"]["canonical_id"] == "ECA-PHY-0001"


def test_check_exercise_band_at_limit_ok(cat):
    # ECA-PHY-0001 band_max=3; band_count=3 → no violation
    result = cat.check_exercise({"canonical_id": "ECA-PHY-0001", "band_count": 3})
    codes = [v["code"] for v in result["violations"]]
    assert "BAND_LIMIT_EXCEEDED" not in codes


def test_check_exercise_node_at_limit_ok(cat):
    # ECA-PHY-0001 node_max=2; node=2 → no violation
    result = cat.check_exercise({"canonical_id": "ECA-PHY-0001", "node": 2})
    codes = [v["code"] for v in result["violations"]]
    assert "NODE_LIMIT_EXCEEDED" not in codes


# ------------------------------------------------------------------ #
# check_exercise — violations                                        #
# ------------------------------------------------------------------ #

def test_check_exercise_band_limit_exceeded(cat):
    # ECA-PHY-0001 band_max=3; band_count=4 → violation
    result = cat.check_exercise({"canonical_id": "ECA-PHY-0001", "band_count": 4})
    codes = [v["code"] for v in result["violations"]]
    assert "BAND_LIMIT_EXCEEDED" in codes


def test_check_exercise_node_limit_exceeded(cat):
    # ECA-PHY-0004 Deadlift: node_max=1; node=2 → violation
    result = cat.check_exercise({"canonical_id": "ECA-PHY-0004", "node": 2})
    codes = [v["code"] for v in result["violations"]]
    assert "NODE_LIMIT_EXCEEDED" in codes


def test_check_exercise_day_role_not_permitted(cat):
    # ECA-PHY-0004 Deadlift: day_roles=["A"]; day_role="B" → violation
    result = cat.check_exercise({"canonical_id": "ECA-PHY-0004", "day_role": "B"})
    codes = [v["code"] for v in result["violations"]]
    assert "DAY_ROLE_NOT_PERMITTED" in codes


def test_check_exercise_day_role_permitted(cat):
    result = cat.check_exercise({"canonical_id": "ECA-PHY-0001", "day_role": "A"})
    codes = [v["code"] for v in result["violations"]]
    assert "DAY_ROLE_NOT_PERMITTED" not in codes


def test_check_exercise_eccentric_violation(cat):
    # ECA-PHY-0001 eccentric_max=6; E=7 → violation
    result = cat.check_exercise({"canonical_id": "ECA-PHY-0001", "tempo": "7:0:1:0"})
    codes = [v["code"] for v in result["violations"]]
    assert "ECCENTRIC_TEMPO_VIOLATION" in codes


def test_check_exercise_isometric_top_violation(cat):
    # ECA-PHY-0015 Dumbbell Lateral Raise: isometric_top_max=1; IT=2 → violation
    result = cat.check_exercise({"canonical_id": "ECA-PHY-0015", "tempo": "3:0:2:0"})
    codes = [v["code"] for v in result["violations"]]
    assert "ISOMETRIC_TOP_VIOLATION" in codes


def test_check_exercise_explosive_concentric_not_permitted(cat):
    # ECA-PHY-0015 Dumbbell Lateral Raise: explosive_concentric_allowed=false
    result = cat.check_exercise({"canonical_id": "ECA-PHY-0015", "tempo": "3:0:1:X"})
    codes = [v["code"] for v in result["violations"]]
    assert "EXPLOSIVE_CONCENTRIC_NOT_PERMITTED" in codes


def test_check_exercise_tempo_parse_error(cat):
    result = cat.check_exercise({"canonical_id": "ECA-PHY-0001", "tempo": "3010"})
    codes = [v["code"] for v in result["violations"]]
    assert "TEMPO_PARSE_ERROR" in codes


def test_check_exercise_not_found(cat):
    result = cat.check_exercise({"canonical_id": "ECA-PHY-XXXX"})
    assert result["exercise"] is None
    codes = [v["code"] for v in result["violations"]]
    assert "EXERCISE_NOT_FOUND" in codes


# ------------------------------------------------------------------ #
# check_exercise — SFI contribution                                  #
# ------------------------------------------------------------------ #

def test_check_exercise_sfi_zero_when_bilateral_h1_node1(cat):
    # ECA-PHY-0001: bilateral, H1 (h_rank=1<3), node=1 → sfi=0
    result = cat.check_exercise({"canonical_id": "ECA-PHY-0001", "node": 1, "set_count": 4})
    assert result["sfi_contribution"] == 0.0


def test_check_exercise_sfi_node3_and_unilateral(cat):
    # ECA-PHY-0007 Walking Lunge: unilateral=True, H2 (h_rank=2<3), node=3, set_count=4
    # sfi = (4×1.0 for node3) + (4×0.5 for unilateral) = 4 + 2 = 6.0
    result = cat.check_exercise({"canonical_id": "ECA-PHY-0007", "node": 3, "set_count": 4})
    assert result["sfi_contribution"] == pytest.approx(6.0)
