from __future__ import annotations

from copy import deepcopy

from efl_kernel.kernel.dependency_provider import InMemoryDependencyProvider
from efl_kernel.kernel.kernel import KernelRunner
from efl_kernel.kernel.ral import RAL_SPEC


SESSION_REG = RAL_SPEC["moduleRegistration"]["SESSION"]
MESO_REG = RAL_SPEC["moduleRegistration"]["MESO"]
MACRO_REG = RAL_SPEC["moduleRegistration"]["MACRO"]


def _base_session_input() -> dict:
    return {
        "moduleVersion": SESSION_REG["moduleVersion"],
        "moduleViolationRegistryVersion": SESSION_REG["moduleViolationRegistryVersion"],
        "registryHash": SESSION_REG["registryHash"],
        "objectID": "session-functional-1",
        "evaluationContext": {"athleteID": "ath-functional", "sessionID": "session-functional-1"},
        "windowContext": [
            {
                "windowType": "ROLLING7DAYS",
                "anchorDate": "2026-01-01",
                "startDate": "2025-12-26",
                "endDate": "2026-01-01",
                "timezone": "America/Chicago",
            },
            {
                "windowType": "ROLLING28DAYS",
                "anchorDate": "2026-01-01",
                "startDate": "2025-12-05",
                "endDate": "2026-01-01",
                "timezone": "America/Chicago",
            },
        ],
        "session": {
            "sessionDate": "2026-01-01T12:00:00+00:00",
            "contactLoad": 100,
            "exercises": [],
        },
    }


def _base_meso_input() -> dict:
    return {
        "moduleVersion": MESO_REG["moduleVersion"],
        "moduleViolationRegistryVersion": MESO_REG["moduleViolationRegistryVersion"],
        "registryHash": MESO_REG["registryHash"],
        "objectID": "meso-functional-1",
        "evaluationContext": {"athleteID": "ath-functional", "mesoID": "meso-functional-1"},
        "windowContext": [
            {
                "windowType": "MESOCYCLE",
                "anchorDate": "2026-01-01",
                "startDate": "2025-12-05",
                "endDate": "2026-01-01",
                "timezone": "America/Chicago",
            },
        ],
    }


def _base_macro_input() -> dict:
    return {
        "moduleVersion": MACRO_REG["moduleVersion"],
        "moduleViolationRegistryVersion": MACRO_REG["moduleViolationRegistryVersion"],
        "registryHash": MACRO_REG["registryHash"],
        "objectID": "macro-functional-1",
        "evaluationContext": {"athleteID": "ath-functional", "seasonID": "season-functional-1"},
        "windowContext": [
            {
                "windowType": "SEASON",
                "anchorDate": "2026-01-01",
                "startDate": "2025-01-01",
                "endDate": "2026-01-01",
                "timezone": "America/Chicago",
            },
        ],
    }


def test_all_registered_gate_codes_emitted_by_live_gate_logic():
    seen_codes: set[str] = set()

    session_1 = _base_session_input()
    provider_1 = InMemoryDependencyProvider(
        athlete_profile={"ath-functional": {"maxDailyContactLoad": 80, "minimumRestIntervalHours": 24, "e4_clearance": False}},
        prior_session={"ath-functional": {"sessionDate": "2026-01-01T00:30:00+00:00"}},
    )
    kdo_1 = KernelRunner(provider_1).evaluate(session_1, "SESSION")
    seen_codes |= {v["code"] for v in kdo_1.violations}

    session_2 = deepcopy(_base_session_input())
    session_2["session"]["contactLoad"] = 50
    session_2["session"]["exercises"] = [{"exerciseID": "isometric_mid_thigh_pull_max"}]
    provider_2 = InMemoryDependencyProvider(
        athlete_profile={"ath-functional": {"maxDailyContactLoad": 200, "minimumRestIntervalHours": 1, "e4_clearance": False}},
        prior_session={"ath-functional": {"sessionDate": "2025-12-30T00:00:00+00:00"}},
    )
    kdo_2 = KernelRunner(provider_2).evaluate(session_2, "SESSION")
    seen_codes |= {v["code"] for v in kdo_2.violations}

    meso_input = _base_meso_input()
    meso_provider = InMemoryDependencyProvider(
        window_totals={
            ("ath-functional", "ROLLING28DAYS"): {"totalContactLoad": 280, "dailyContactLoads": [5, 5, 5, 5, 5, 255]}
        }
    )
    meso_kdo = KernelRunner(meso_provider).evaluate(meso_input, "MESO")
    seen_codes |= {v["code"] for v in meso_kdo.violations}

    macro_input = _base_macro_input()
    macro_provider = InMemoryDependencyProvider(season_phases={("ath-functional", "season-functional-1"): {"competitionWeeks": 10, "gppWeeks": 2}})
    macro_kdo = KernelRunner(macro_provider).evaluate(macro_input, "MACRO")
    seen_codes |= {v["code"] for v in macro_kdo.violations}

    assert "SCM.MAXDAILYLOAD" in seen_codes
    assert "SCM.MINREST" in seen_codes
    assert "CL.CLEARANCEMISSING" in seen_codes
    assert "MESO.LOADIMBALANCE" in seen_codes
    assert "MACRO.PHASEMISMATCH" in seen_codes


def test_unknown_exercise_id_is_ignored_by_cl_gate():
    raw = _base_session_input()
    raw["session"]["contactLoad"] = 0
    raw["session"]["exercises"] = [{"exerciseID": "does_not_exist"}]

    provider = InMemoryDependencyProvider(
        athlete_profile={"ath-functional": {"maxDailyContactLoad": 500, "minimumRestIntervalHours": 1, "e4_clearance": False}},
        prior_session={},
    )
    kdo = KernelRunner(provider).evaluate(raw, "SESSION")

    assert kdo.violations == []
