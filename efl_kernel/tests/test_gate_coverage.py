# Coverage markers for registry codes:
# SCM.MAXDAILYLOAD
# SCM.MINREST
# CL.CLEARANCEMISSING
# MESO.LOADIMBALANCE
# MACRO.PHASEMISMATCH
# DCC_TEMPO_EXPLOSIVE_NOT_ALLOWED_FOR_EXERCISE
# DCC_TEMPO_E_BELOW_MINIMUM
# DCC_TEMPO_E_EXCEEDS_CEILING
# DCC_TEMPO_FORMAT_INVALID
# DCC_TEMPO_IB_EXCEEDS_CEILING
# DCC_TEMPO_IT_EXCEEDS_CEILING
# DCC_TEMPO_X_IN_INVALID_POSITION
# MCC_ADJACENCY_VIOLATION
# MCC_BAND_NODE_ILLEGAL_COMBINATION
# MCC_DAY_A_PATTERN_GUARANTEE_VIOLATED
# MCC_D_MINIMUM_VIOLATED
# MCC_MULTI_AXIS_PROGRESSION_VIOLATION
# MCC_NODE_PERMISSION_VIOLATION
# MCC_TEMPO_ESCALATION_REQUIRES_OPT_IN
# MCC_BAND3_PATTERN_EXCEEDED
# MCC_H3_AGGREGATE_EXCEEDED
# MCC_READINESS_BAND_MISMATCH
# MCC_READINESS_VIOLATION
# MCC_ROUTE_SATURATION_VIOLATION
# MCC_SESSION_VOLUME_EXCEEDED
# MCC_SFI_EXCESSIVE_WARNING
# MCC_TEMPO_DOWNGRADE_CHAIN_EXHAUSTED
# MCC_TEMPO_DOWNGRADE_REVALIDATION_FAILED
# MCC_C_DAY_MESO_ROTATION_VIOLATION
# MCC_DENSITY_LEDGER_EXCEEDED
# MCC_PATTERN_BALANCE_VIOLATED
# MCC_SFI_ELEVATED_WARNING
# MCC_TEMPO_ESCALATION_CLAMPED_TO_H3
# MCC_TEMPO_DOWNGRADED_FOR_H_NODE_MAX
# MCC_TEMPO_DOWNGRADED_FOR_TUT_CEILING
# MCC_TEMPO_ESCALATION_APPROVED
# MCC_TEMPO_MODIFIED_BY_MCC
# MCC_CHRONIC_YELLOW_GUARD_TRIGGERED
# MCC_COLLAPSE_ESCALATION_TRIGGERED
# MCC_CONSECUTIVE_NODE3_EXCEEDED
# MCC_DAY_A_FREQUENCY_EXCEEDED
# MCC_DAY_B_FREQUENCY_EXCEEDED
# MCC_DAY_C_PATTERN_REPETITION
# MCC_DAY_D_INTENT_VIOLATION
# MCC_ECA_COVERAGE_MISSING
# MCC_ECA_PATTERN_INCOMPLETE
# MCC_FAMILY_MULTI_AXIS_VIOLATION
# MCC_FREQUENCY_NOT_SUPPORTED
# MCC_H4_FREQUENCY_EXCEEDED
# MCC_PRIME_SCOPE_VIOLATION
# MCC_SESSION_DURATION_EXCEEDED
# MCC_VOLUME_CLASS_OVERRIDE_ATTEMPT
# MCC_WORK_BLOCK_INSUFFICIENT
# MCC_ECA_SLOT_UNRESOLVABLE

from efl_kernel.kernel.registry import validate_bidirectional_coverage


def test_registry_coverage_markers_present():
    missing = validate_bidirectional_coverage()
    assert missing == {}


def test_slot_unknown_eca_id_emits_unresolvable(tmp_path):
    from datetime import date, timedelta
    from fastapi.testclient import TestClient
    from efl_kernel.kernel.ral import RAL_SPEC
    from efl_kernel.service import create_app

    PHY_REG = RAL_SPEC["moduleRegistration"]["PHYSIQUE"]
    _ANCHOR = date(2026, 1, 1)
    app = create_app(str(tmp_path / "test.db"))
    app.state.op_store.upsert_athlete({
        "athlete_id": "ATH-UNRESOLVABLE",
        "max_daily_contact_load": 9999.0,
        "minimum_rest_interval_hours": 0.0,
        "e4_clearance": 1,
    })
    client = TestClient(app)
    payload = {
        "moduleVersion": PHY_REG["moduleVersion"],
        "moduleViolationRegistryVersion": PHY_REG["moduleViolationRegistryVersion"],
        "registryHash": PHY_REG["registryHash"],
        "objectID": "obj-unresolvable-test",
        "evaluationContext": {"athleteID": "ATH-UNRESOLVABLE", "sessionID": "S-UNRESOLVABLE"},
        "windowContext": [
            {"windowType": "ROLLING7DAYS", "anchorDate": _ANCHOR.isoformat(),
             "startDate": (_ANCHOR - timedelta(days=7)).isoformat(),
             "endDate": _ANCHOR.isoformat(), "timezone": "UTC"},
            {"windowType": "ROLLING28DAYS", "anchorDate": _ANCHOR.isoformat(),
             "startDate": (_ANCHOR - timedelta(days=28)).isoformat(),
             "endDate": _ANCHOR.isoformat(), "timezone": "UTC"},
        ],
        "physique_session": {"exercises": [{"exercise_id": "ECA-PHY-0001", "tempo": "3:0:1:0"}]},
        "context": {"athlete_id": "ATH-UNRESOLVABLE"},
        "day_slots": [{"day_role": "DAY_C", "exercises": [{
            "eca_id": "ECA-NONEXISTENT-999",
            "band": 1, "node": 1, "role": "WORK", "set_count": 3,
        }]}],
    }
    resp = client.post("/evaluate/physique", json=payload)
    codes = [v["code"] for v in resp.json().get("violations", [])]
    assert "MCC_ECA_SLOT_UNRESOLVABLE" in codes
    assert "MCC_NODE_PERMISSION_VIOLATION" not in codes
    assert "MCC_DAY_D_INTENT_VIOLATION" not in codes
    assert "MCC_TEMPO_DOWNGRADED_FOR_H_NODE_MAX" not in codes
    assert "MCC_TEMPO_DOWNGRADE_CHAIN_EXHAUSTED" not in codes
    assert "MCC_TEMPO_DOWNGRADE_REVALIDATION_FAILED" not in codes
