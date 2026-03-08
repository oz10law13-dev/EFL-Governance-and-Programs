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
# PHYSIQUE.CLEARANCEMISSING
# MCC_PASS2_MISSING_OR_FAILED
# DCC_TEMPO_GOVERNANCE_UNAVAILABLE

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


def test_physique_clearance_gate_fires_on_missing_clearance():
    """PHYSIQUE.CLEARANCEMISSING emitted when whitelist exercise has e4_requires_clearance=True and athlete lacks clearance."""
    from efl_kernel.kernel.gates_physique import run_physique_gates
    from efl_kernel.kernel.dependency_provider import InMemoryDependencyProvider

    payload = {
        "evaluationContext": {"athleteID": "ath-no-clearance", "sessionID": "ps-1"},
        "physique_session": {
            "exercises": [
                {"exercise_id": "ECA-PHY-0027", "band": 2, "node": 2, "tempo": "3:0:1:0"},
            ]
        },
    }

    provider = InMemoryDependencyProvider(
        athlete_profile={"ath-no-clearance": {"e4_clearance": False}}
    )

    violations = run_physique_gates(payload, provider)
    codes = [v["code"] for v in violations]

    assert "PHYSIQUE.CLEARANCEMISSING" in codes
    clearance_v = next(v for v in violations if v["code"] == "PHYSIQUE.CLEARANCEMISSING")
    assert clearance_v["severity"] == "HARDFAIL"
    assert clearance_v["overridePossible"] is False
    assert clearance_v["details"]["exercise_id"] == "ECA-PHY-0027"


def test_physique_clearance_gate_suppressed_when_cleared():
    """PHYSIQUE.CLEARANCEMISSING NOT emitted when athlete has e4_clearance=True."""
    from efl_kernel.kernel.gates_physique import run_physique_gates
    from efl_kernel.kernel.dependency_provider import InMemoryDependencyProvider

    payload = {
        "evaluationContext": {"athleteID": "ath-cleared", "sessionID": "ps-2"},
        "physique_session": {
            "exercises": [
                {"exercise_id": "ECA-PHY-0027", "band": 2, "node": 2, "tempo": "3:0:1:0"},
            ]
        },
    }

    provider = InMemoryDependencyProvider(
        athlete_profile={"ath-cleared": {"e4_clearance": True}}
    )

    violations = run_physique_gates(payload, provider)
    codes = [v["code"] for v in violations]

    assert "PHYSIQUE.CLEARANCEMISSING" not in codes


def test_physique_clearance_gate_fires_for_slot_exercise():
    """PHYSIQUE.CLEARANCEMISSING emitted for day_slot exercise with _resolved_e4_requires_clearance=True."""
    from efl_kernel.kernel.gates_physique import run_physique_gates
    from efl_kernel.kernel.dependency_provider import InMemoryDependencyProvider

    payload = {
        "evaluationContext": {"athleteID": "ath-slot", "sessionID": "ps-3"},
        "physique_session": {"exercises": []},
        "context": {"athlete_id": "ath-slot"},
        "day_slots": [{"day_role": "DAY_B", "exercises": [
            {"eca_id": "ECA-PHY-0027", "role": "WORK", "band": 2, "node": 2, "set_count": 3},
        ]}],
    }

    provider = InMemoryDependencyProvider(
        athlete_profile={"ath-slot": {"e4_clearance": False}}
    )

    violations = run_physique_gates(payload, provider)
    codes = [v["code"] for v in violations]

    assert "PHYSIQUE.CLEARANCEMISSING" in codes


def test_inv_mcc_001_slot_context_copresence():
    """INV-MCC-001: day_slots non-empty + context absent → MCC_PASS2_MISSING_OR_FAILED fires, no slot-level MCC codes."""
    from efl_kernel.kernel.gates_physique import run_physique_gates
    from efl_kernel.kernel.dependency_provider import InMemoryDependencyProvider

    payload = {
        "evaluationContext": {"athleteID": "ath-inv", "sessionID": "ps-inv"},
        "physique_session": {"exercises": []},
        "day_slots": [{"day_role": "DAY_A", "exercises": []}],
    }

    provider = InMemoryDependencyProvider(
        athlete_profile={"ath-inv": {"e4_clearance": False}}
    )

    violations = run_physique_gates(payload, provider)
    codes = [v["code"] for v in violations]

    assert "MCC_PASS2_MISSING_OR_FAILED" in codes
    slot_level_codes = {c for c in codes if c.startswith("MCC_") and c != "MCC_PASS2_MISSING_OR_FAILED"}
    assert len(slot_level_codes) == 0, f"Unexpected slot-level codes: {slot_level_codes}"


def test_isometric_exercise_gets_n_a_duration_tempo_mode():
    """ECA-PHY-0023 (Plank, pattern_plane=Isometric) must get tempo_mode=N/A_DURATION (F6 fix)."""
    from efl_kernel.kernel.physique_adapter import run_physique_adapter

    payload = {
        "evaluationContext": {"athleteID": "x"},
        "physique_session": {"exercises": [{"exercise_id": "ECA-PHY-0023", "tempo": ""}]},
        "day_slots": [],
    }
    r = run_physique_adapter(payload)
    assert r.halt_codes == []
    assert r.normalized_exercises[0]["tempo_mode"] == "N/A_DURATION"


def test_unknown_horiz_vert_label_halts_adapter():
    """An unknown horiz_vert label in the whitelist must halt with UNKNOWN_HORIZ_VERT_LABEL (F5 fix)."""
    import efl_kernel.kernel.physique_adapter as adapter_module

    original = dict(adapter_module.WHITELIST_INDEX["ECA-PHY-0001"])
    try:
        adapter_module.WHITELIST_INDEX["ECA-PHY-0001"] = dict(original, horiz_vert="diagonal")
        payload = {
            "evaluationContext": {"athleteID": "x"},
            "physique_session": {"exercises": [{"exercise_id": "ECA-PHY-0001", "tempo": "3:0:1:0"}]},
            "day_slots": [],
        }
        r = adapter_module.run_physique_adapter(payload)
        assert "UNKNOWN_HORIZ_VERT_LABEL" in r.halt_codes
    finally:
        adapter_module.WHITELIST_INDEX["ECA-PHY-0001"] = original


def test_gap004_tempo_gov_unavailable_emits_mcc_violation():
    """GAP-004: adapter halt DCC_TEMPO_GOVERNANCE_UNAVAILABLE → _mcc_v (not _syn) in gates."""
    import efl_kernel.kernel.physique_adapter as adapter_module
    from efl_kernel.kernel.gates_physique import run_physique_gates
    from efl_kernel.kernel.dependency_provider import InMemoryDependencyProvider

    original_error = adapter_module._TEMPO_GOV_LOAD_ERROR
    try:
        adapter_module._TEMPO_GOV_LOAD_ERROR = True
        payload = {
            "evaluationContext": {"athleteID": "ath-gap004"},
            "physique_session": {"exercises": []},
            "day_slots": [],
        }
        provider = InMemoryDependencyProvider(athlete_profile={})
        violations = run_physique_gates(payload, provider)
        codes = [v["code"] for v in violations]
        assert "DCC_TEMPO_GOVERNANCE_UNAVAILABLE" in codes
        # Must be PHYSIQUE-registered violation (moduleID=PHYSIQUE), not RAL synthetic
        v = next(v for v in violations if v["code"] == "DCC_TEMPO_GOVERNANCE_UNAVAILABLE")
        assert v["moduleID"] == "PHYSIQUE"
    finally:
        adapter_module._TEMPO_GOV_LOAD_ERROR = original_error


def test_f1_authority_version_mismatch_halts_adapter():
    """F1: authority_versions with wrong whitelist_version halts with AUTHORITY_VERSION_MISMATCH."""
    from efl_kernel.kernel.physique_adapter import run_physique_adapter

    payload = {
        "evaluationContext": {"athleteID": "x"},
        "physique_session": {"exercises": []},
        "day_slots": [],
        "authority_versions": {"whitelist_version": "0.0.0"},
    }
    r = run_physique_adapter(payload)
    assert "AUTHORITY_VERSION_MISMATCH" in r.halt_codes


def test_f1_authority_version_correct_does_not_halt():
    """F1: authority_versions matching actual versions → no halt."""
    from efl_kernel.kernel.physique_adapter import run_physique_adapter, _WHITELIST_VERSION, _TEMPO_GOV_VERSION

    payload = {
        "evaluationContext": {"athleteID": "x"},
        "physique_session": {"exercises": []},
        "day_slots": [],
        "authority_versions": {
            "whitelist_version": _WHITELIST_VERSION,
            "tempo_gov_version": _TEMPO_GOV_VERSION,
        },
    }
    r = run_physique_adapter(payload)
    assert r.halt_codes == []


def test_f2_non_list_exercises_halts_schema_validation_failed():
    """F2: physique_session.exercises not a list → SCHEMA_VALIDATION_FAILED."""
    from efl_kernel.kernel.physique_adapter import run_physique_adapter

    payload = {
        "evaluationContext": {"athleteID": "x"},
        "physique_session": {"exercises": "not-a-list"},
        "day_slots": [],
    }
    r = run_physique_adapter(payload)
    assert "SCHEMA_VALIDATION_FAILED" in r.halt_codes


def test_f2_exercise_missing_id_halts_incomplete_input():
    """F2: exercise dict with no exercise_id → INCOMPLETE_INPUT."""
    from efl_kernel.kernel.physique_adapter import run_physique_adapter

    payload = {
        "evaluationContext": {"athleteID": "x"},
        "physique_session": {"exercises": [{"tempo": "3:0:1:0"}]},
        "day_slots": [],
    }
    r = run_physique_adapter(payload)
    assert "INCOMPLETE_INPUT" in r.halt_codes
