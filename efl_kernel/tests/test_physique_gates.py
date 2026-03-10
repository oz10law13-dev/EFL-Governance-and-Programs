from __future__ import annotations

from efl_kernel.kernel.dependency_provider import InMemoryDependencyProvider
from efl_kernel.kernel.kernel import KernelRunner
from efl_kernel.kernel.ral import RAL_SPEC

PHY_REG = RAL_SPEC["moduleRegistration"]["PHYSIQUE"]


def _runner() -> KernelRunner:
    return KernelRunner(InMemoryDependencyProvider())


def _physique_input(exercises=None) -> dict:
    return {
        "moduleVersion": PHY_REG["moduleVersion"],
        "moduleViolationRegistryVersion": PHY_REG["moduleViolationRegistryVersion"],
        "registryHash": PHY_REG["registryHash"],
        "objectID": "obj-physique-1",
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
        "physique_session": {"exercises": exercises or []},
    }


def _squat(tempo: str) -> dict:
    # ECA-PHY-0001 Back Squat: PRIMARY_COMPOUND, eccentric_max=6, ib_max=3, it_max=2,
    # explosive_concentric_allowed=True
    return {"exercise_id": "ECA-PHY-0001", "tempo": tempo}


def _lateral_raise(tempo: str) -> dict:
    # ECA-PHY-0093 Dumbbell Lateral Raise: ACCESSORY_ISOLATION, eccentric_max=4,
    # ib_max=3, it_max=1, explosive_concentric_allowed=False
    return {"exercise_id": "ECA-PHY-0093", "tempo": tempo}


def _codes(kdo) -> list[str]:
    return [v["code"] for v in kdo.violations]


# --- DCC_TEMPO_FORMAT_INVALID ---

def test_dcc_format_invalid_fires():
    kdo = _runner().evaluate(_physique_input([_squat("bad")]), "PHYSIQUE")
    assert "DCC_TEMPO_FORMAT_INVALID" in _codes(kdo)


def test_dcc_format_invalid_suppresses():
    kdo = _runner().evaluate(_physique_input([_squat("3:1:1:0")]), "PHYSIQUE")
    assert "DCC_TEMPO_FORMAT_INVALID" not in _codes(kdo)


# --- DCC_TEMPO_X_IN_INVALID_POSITION ---

def test_dcc_x_invalid_position_fires():
    # X in E position is invalid
    kdo = _runner().evaluate(_physique_input([_squat("X:1:0:0")]), "PHYSIQUE")
    assert "DCC_TEMPO_X_IN_INVALID_POSITION" in _codes(kdo)


def test_dcc_x_invalid_position_suppresses():
    # X in C position only is valid
    kdo = _runner().evaluate(_physique_input([_squat("3:0:0:X")]), "PHYSIQUE")
    assert "DCC_TEMPO_X_IN_INVALID_POSITION" not in _codes(kdo)


# --- DCC_TEMPO_EXPLOSIVE_NOT_ALLOWED_FOR_EXERCISE ---

def test_dcc_explosive_not_allowed_fires():
    # lateral raise: explosive_concentric_allowed=False; C=X is illegal
    kdo = _runner().evaluate(_physique_input([_lateral_raise("3:0:0:X")]), "PHYSIQUE")
    assert "DCC_TEMPO_EXPLOSIVE_NOT_ALLOWED_FOR_EXERCISE" in _codes(kdo)


def test_dcc_explosive_not_allowed_suppresses():
    # squat: explosive_concentric_allowed=True; C=X is legal
    kdo = _runner().evaluate(_physique_input([_squat("3:0:0:X")]), "PHYSIQUE")
    assert "DCC_TEMPO_EXPLOSIVE_NOT_ALLOWED_FOR_EXERCISE" not in _codes(kdo)


# --- DCC_TEMPO_E_BELOW_MINIMUM ---

def test_dcc_e_below_minimum_fires():
    # squat: PRIMARY_COMPOUND, minimum=1; E=0 is below minimum
    kdo = _runner().evaluate(_physique_input([_squat("0:0:0:0")]), "PHYSIQUE")
    assert "DCC_TEMPO_E_BELOW_MINIMUM" in _codes(kdo)


def test_dcc_e_below_minimum_suppresses():
    # squat: E=1 meets the minimum
    kdo = _runner().evaluate(_physique_input([_squat("1:0:0:0")]), "PHYSIQUE")
    assert "DCC_TEMPO_E_BELOW_MINIMUM" not in _codes(kdo)


def test_dcc_e_below_minimum_accessory_zero_ok():
    # lateral raise: ACCESSORY_ISOLATION, minimum=0; E=0 is allowed
    kdo = _runner().evaluate(_physique_input([_lateral_raise("0:0:0:0")]), "PHYSIQUE")
    assert "DCC_TEMPO_E_BELOW_MINIMUM" not in _codes(kdo)


# --- DCC_TEMPO_E_EXCEEDS_CEILING ---

def test_dcc_e_exceeds_ceiling_fires():
    # squat: eccentric_max=6; E=7 exceeds ceiling
    kdo = _runner().evaluate(_physique_input([_squat("7:0:0:0")]), "PHYSIQUE")
    assert "DCC_TEMPO_E_EXCEEDS_CEILING" in _codes(kdo)


def test_dcc_e_exceeds_ceiling_suppresses():
    # squat: E=6 is at the ceiling (boundary — must not fire)
    kdo = _runner().evaluate(_physique_input([_squat("6:0:0:0")]), "PHYSIQUE")
    assert "DCC_TEMPO_E_EXCEEDS_CEILING" not in _codes(kdo)


# --- DCC_TEMPO_IB_EXCEEDS_CEILING ---

def test_dcc_ib_exceeds_ceiling_fires():
    # squat: isometric_bottom_max=3; IB=4 exceeds ceiling
    kdo = _runner().evaluate(_physique_input([_squat("3:4:0:0")]), "PHYSIQUE")
    assert "DCC_TEMPO_IB_EXCEEDS_CEILING" in _codes(kdo)


def test_dcc_ib_exceeds_ceiling_suppresses():
    # squat: IB=3 is at the ceiling (boundary — must not fire)
    kdo = _runner().evaluate(_physique_input([_squat("3:3:0:0")]), "PHYSIQUE")
    assert "DCC_TEMPO_IB_EXCEEDS_CEILING" not in _codes(kdo)


# --- DCC_TEMPO_IT_EXCEEDS_CEILING ---

def test_dcc_it_exceeds_ceiling_fires():
    # squat: isometric_top_max=2; IT=3 exceeds ceiling
    kdo = _runner().evaluate(_physique_input([_squat("3:0:3:0")]), "PHYSIQUE")
    assert "DCC_TEMPO_IT_EXCEEDS_CEILING" in _codes(kdo)


def test_dcc_it_exceeds_ceiling_suppresses():
    # squat: IT=2 is at the ceiling (boundary — must not fire)
    kdo = _runner().evaluate(_physique_input([_squat("3:0:2:0")]), "PHYSIQUE")
    assert "DCC_TEMPO_IT_EXCEEDS_CEILING" not in _codes(kdo)


# --- Adapter halt ---

def test_adapter_halt_unknown_exercise():
    # Unknown exercise_id → adapter halts → RAL.MISSINGORUNDEFINEDREQUIREDSTATE
    payload = _physique_input([{"exercise_id": "ECA-PHY-9999", "tempo": "3:0:0:0"}])
    kdo = _runner().evaluate(payload, "PHYSIQUE")
    assert kdo.violations[0]["code"] == "RAL.MISSINGORUNDEFINEDREQUIREDSTATE"


# --- Zero violations → LEGALREADY ---

def test_physique_zero_violations_legalready():
    # Valid squat with clean tempo → no violations → LEGALREADY (CLAMP path)
    kdo = _runner().evaluate(_physique_input([_squat("3:1:1:0")]), "PHYSIQUE")
    assert kdo.violations == []
    assert kdo.resolution["finalPublishState"] == "LEGALREADY"


# --- Carry exercise skips ECICT tempo validation ---

def test_carry_exercise_skips_tempo_validation():
    # ECA-PHY-0124 Farmer Carry: movement_family="Carry" → N/A_DISTANCE → no DCC tempo checks
    carry = {"exercise_id": "ECA-PHY-0124", "tempo": "bad_tempo_not_ecict"}
    kdo = _runner().evaluate(_physique_input([carry]), "PHYSIQUE")
    assert "DCC_TEMPO_FORMAT_INVALID" not in _codes(kdo)
    assert kdo.resolution["finalPublishState"] == "LEGALREADY"
