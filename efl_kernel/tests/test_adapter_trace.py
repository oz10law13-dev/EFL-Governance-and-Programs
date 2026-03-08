"""F7 adapter_trace tests + F3 alias resolution tests."""
from __future__ import annotations


def test_trace_present_on_success():
    """F7: adapter_trace populated on success path with spec-declared key names."""
    from efl_kernel.kernel.physique_adapter import run_physique_adapter

    payload = {
        "evaluationContext": {"athleteID": "x"},
        "physique_session": {"exercises": [{"exercise_id": "ECA-PHY-0001", "tempo": "3:0:1:0"}]},
        "day_slots": [],
    }
    r = run_physique_adapter(payload)
    assert r.halt_codes == []
    assert "adapter_version" in r.adapter_trace
    assert "whitelist_version" in r.adapter_trace
    assert "tempo_gov_version" in r.adapter_trace
    assert r.adapter_trace.get("exercises_normalized") == 1
    assert isinstance(r.adapter_trace.get("alias_resolutions"), list)
    assert isinstance(r.adapter_trace.get("horiz_vert_mappings"), list)
    assert isinstance(r.adapter_trace.get("tempo_mode_assignments"), list)
    assert isinstance(r.adapter_trace.get("e4_injections_true"), list)


def test_trace_contains_halt_reason_on_halt():
    """F7: adapter_trace contains halt_reason on halt path."""
    from efl_kernel.kernel.physique_adapter import run_physique_adapter

    payload = {
        "evaluationContext": {"athleteID": "x"},
        "physique_session": {"exercises": [{"exercise_id": "ECA-NONEXISTENT-999", "tempo": "3:0:1:0"}]},
        "day_slots": [],
    }
    r = run_physique_adapter(payload)
    assert r.halt_codes == ["UNKNOWN_EXERCISE_ID"]
    assert r.adapter_trace.get("halt_reason") == ["UNKNOWN_EXERCISE_ID"]
    assert r.adapter_trace.get("adapter_version") is not None


def test_f3_alias_resolution_squat():
    """F3: ECA-SQUAT-001 resolves to ECA-PHY-0001 via alias table."""
    from efl_kernel.kernel.physique_adapter import run_physique_adapter

    payload = {
        "evaluationContext": {"athleteID": "x"},
        "physique_session": {"exercises": [{"exercise_id": "ECA-SQUAT-001", "tempo": "3:0:1:0"}]},
        "day_slots": [],
    }
    r = run_physique_adapter(payload)
    assert r.halt_codes == [], f"Unexpected halt: {r.halt_codes}"
    assert len(r.normalized_exercises) == 1
    assert r.normalized_exercises[0]["exercise_id"] == "ECA-PHY-0001"
    assert "ECA-SQUAT-001" in r.adapter_trace.get("alias_resolutions", [])


def test_f3_alias_resolution_hinge():
    """F3: ECA-HINGE-001 resolves to ECA-PHY-0004 via alias table."""
    from efl_kernel.kernel.physique_adapter import run_physique_adapter

    payload = {
        "evaluationContext": {"athleteID": "x"},
        "physique_session": {"exercises": [{"exercise_id": "ECA-HINGE-001", "tempo": "3:0:1:0"}]},
        "day_slots": [],
    }
    r = run_physique_adapter(payload)
    assert r.halt_codes == [], f"Unexpected halt: {r.halt_codes}"
    assert r.normalized_exercises[0]["exercise_id"] == "ECA-PHY-0004"
    assert "ECA-HINGE-001" in r.adapter_trace.get("alias_resolutions", [])


def test_f3_alias_resolution_isolate_011():
    """F3: ECA-ISOLATE-011 resolves to ECA-PHY-0016 (D5: included)."""
    from efl_kernel.kernel.physique_adapter import run_physique_adapter

    payload = {
        "evaluationContext": {"athleteID": "x"},
        "physique_session": {"exercises": [{"exercise_id": "ECA-ISOLATE-011", "tempo": "3:0:1:0"}]},
        "day_slots": [],
    }
    r = run_physique_adapter(payload)
    assert r.halt_codes == []
    assert r.normalized_exercises[0]["exercise_id"] == "ECA-PHY-0016"


def test_f3_press003_not_in_alias_table():
    """D5: ECA-PRESS-003 is NOT in alias table — must halt with UNKNOWN_EXERCISE_ID."""
    from efl_kernel.kernel.physique_adapter import run_physique_adapter

    payload = {
        "evaluationContext": {"athleteID": "x"},
        "physique_session": {"exercises": [{"exercise_id": "ECA-PRESS-003", "tempo": "3:0:1:0"}]},
        "day_slots": [],
    }
    r = run_physique_adapter(payload)
    assert "UNKNOWN_EXERCISE_ID" in r.halt_codes


def test_f3_alias_not_applied_to_slot_exercises():
    """D3/D constraint #10: alias lookup does NOT apply to slot exercises; unknown eca_id marks _resolution_error."""
    from efl_kernel.kernel.physique_adapter import run_physique_adapter

    payload = {
        "evaluationContext": {"athleteID": "x"},
        "physique_session": {"exercises": []},
        "day_slots": [{"day_role": "DAY_A", "exercises": [
            {"eca_id": "ECA-SQUAT-001", "band": 1, "node": 1, "role": "WORK", "set_count": 3},
        ]}],
    }
    r = run_physique_adapter(payload)
    assert r.halt_codes == []
    # slot exercise with alias ID → not resolved (no alias lookup in slots)
    slot_ex = r.resolved_slot_exercises[0]["exercises"][0]
    assert slot_ex.get("_resolution_error") is True


def test_trace_e4_flagged_recorded():
    """F7: exercises with e4_requires_clearance=True appear in adapter_trace.e4_flagged."""
    from efl_kernel.kernel.physique_adapter import run_physique_adapter

    payload = {
        "evaluationContext": {"athleteID": "x"},
        "physique_session": {"exercises": [{"exercise_id": "ECA-PHY-0027", "tempo": "3:0:1:0"}]},
        "day_slots": [],
    }
    r = run_physique_adapter(payload)
    assert r.halt_codes == []
    assert "ECA-PHY-0027" in r.adapter_trace.get("e4_injections_true", [])


def test_trace_horiz_vert_event_recorded_for_incline():
    """F7: Incline→horizontal translation recorded in adapter_trace.horiz_vert_events."""
    import efl_kernel.kernel.physique_adapter as adapter_module

    original = dict(adapter_module.WHITELIST_INDEX["ECA-PHY-0001"])
    try:
        adapter_module.WHITELIST_INDEX["ECA-PHY-0001"] = dict(original, horiz_vert="Incline")
        payload = {
            "evaluationContext": {"athleteID": "x"},
            "physique_session": {"exercises": [{"exercise_id": "ECA-PHY-0001", "tempo": "3:0:1:0"}]},
            "day_slots": [],
        }
        r = adapter_module.run_physique_adapter(payload)
        assert r.halt_codes == []
        events = r.adapter_trace.get("horiz_vert_mappings", [])
        assert any(e["raw"] == "Incline" and e["normalized"] == "horizontal" for e in events)
    finally:
        adapter_module.WHITELIST_INDEX["ECA-PHY-0001"] = original
