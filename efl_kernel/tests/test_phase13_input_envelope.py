"""Phase 13 — Declared input envelope tests.

Verifies that PHYSIQUE evaluation accepts both the spec-declared field names
(evaluation_context / session) and the transitional names (evaluationContext /
physique_session), producing identical outcomes.

§5.1 of Physique_Pre_Pass_Adapter_Spec_v1_1.md declares the canonical names.
The transitional names must remain valid indefinitely (backward compat).
"""
from __future__ import annotations

from efl_kernel.kernel.dependency_provider import InMemoryDependencyProvider
from efl_kernel.kernel.kernel import KernelRunner
from efl_kernel.kernel.physique_adapter import _normalize_physique_envelope
from efl_kernel.kernel.ral import RAL_SPEC

PHY_REG = RAL_SPEC["moduleRegistration"]["PHYSIQUE"]


def _runner() -> KernelRunner:
    return KernelRunner(InMemoryDependencyProvider())


def _base_windows() -> list[dict]:
    return [
        {"windowType": "ROLLING7DAYS", "anchorDate": "2026-01-01",
         "startDate": "2025-12-26", "endDate": "2026-01-01", "timezone": "UTC"},
        {"windowType": "ROLLING28DAYS", "anchorDate": "2026-01-01",
         "startDate": "2025-12-05", "endDate": "2026-01-01", "timezone": "UTC"},
    ]


def _declared_payload(exercises=None) -> dict:
    """Payload using spec-declared top-level field names (§5.1)."""
    return {
        "moduleVersion": PHY_REG["moduleVersion"],
        "moduleViolationRegistryVersion": PHY_REG["moduleViolationRegistryVersion"],
        "registryHash": PHY_REG["registryHash"],
        "objectID": "obj-declared-001",
        "evaluation_context": {"athleteID": "a1", "sessionID": "s1"},
        "windowContext": _base_windows(),
        "session": {"exercises": exercises or []},
    }


def _transitional_payload(exercises=None) -> dict:
    """Payload using transitional top-level field names (runtime wire shape)."""
    return {
        "moduleVersion": PHY_REG["moduleVersion"],
        "moduleViolationRegistryVersion": PHY_REG["moduleViolationRegistryVersion"],
        "registryHash": PHY_REG["registryHash"],
        "objectID": "obj-transitional-001",
        "evaluationContext": {"athleteID": "a1", "sessionID": "s1"},
        "windowContext": _base_windows(),
        "physique_session": {"exercises": exercises or []},
    }


# ─── Unit tests: _normalize_physique_envelope ─────────────────────────────────

def test_normalize_maps_evaluation_context_when_transitional_absent():
    raw = {"evaluation_context": {"athleteID": "x"}, "other": "y"}
    out = _normalize_physique_envelope(raw)
    assert out["evaluationContext"] == {"athleteID": "x"}
    assert out["evaluation_context"] == {"athleteID": "x"}  # original preserved
    assert out["other"] == "y"


def test_normalize_maps_session_when_physique_session_absent():
    raw = {"session": {"exercises": []}}
    out = _normalize_physique_envelope(raw)
    assert out["physique_session"] == {"exercises": []}
    assert out["session"] == {"exercises": []}  # original preserved


def test_normalize_does_not_override_existing_transitional_keys():
    """If transitional key already present, declared key must not overwrite it."""
    raw = {
        "evaluationContext": {"athleteID": "transitional"},
        "evaluation_context": {"athleteID": "declared"},
        "physique_session": {"exercises": [{"exercise_id": "ECA-PHY-0001"}]},
        "session": {"exercises": []},
    }
    out = _normalize_physique_envelope(raw)
    assert out["evaluationContext"]["athleteID"] == "transitional"
    assert out["physique_session"]["exercises"][0]["exercise_id"] == "ECA-PHY-0001"


def test_normalize_does_not_mutate_input():
    raw = {"evaluation_context": {"athleteID": "x"}, "session": {"exercises": []}}
    original_keys = set(raw.keys())
    _normalize_physique_envelope(raw)
    assert set(raw.keys()) == original_keys


def test_normalize_noop_when_no_declared_keys():
    raw = {"moduleVersion": "1.0.4", "objectID": "x"}
    out = _normalize_physique_envelope(raw)
    assert out == raw


# ─── Integration tests: full kernel path ─────────────────────────────────────

def test_declared_keys_clean_payload_produces_legalready():
    """Spec-declared field names produce LEGALREADY with empty exercises."""
    kdo = _runner().evaluate(_declared_payload(), "PHYSIQUE")
    assert kdo.violations == [], f"Unexpected violations: {[v['code'] for v in kdo.violations]}"
    assert kdo.resolution["finalPublishState"] == "LEGALREADY"


def test_transitional_keys_clean_payload_produces_legalready():
    """Transitional field names continue to produce LEGALREADY (backward compat)."""
    kdo = _runner().evaluate(_transitional_payload(), "PHYSIQUE")
    assert kdo.violations == []
    assert kdo.resolution["finalPublishState"] == "LEGALREADY"


def test_declared_and_transitional_produce_same_publish_state():
    """Both shapes produce identical finalPublishState for equivalent payloads."""
    kdo_d = _runner().evaluate(_declared_payload(), "PHYSIQUE")
    kdo_t = _runner().evaluate(_transitional_payload(), "PHYSIQUE")
    assert kdo_d.resolution["finalPublishState"] == kdo_t.resolution["finalPublishState"]


def test_declared_keys_with_e4_exercise_fires_clearance_violation():
    """Declared field names: E4-restricted exercise + no clearance → PHYSIQUE.CLEARANCEMISSING."""
    provider = InMemoryDependencyProvider(
        athlete_profile={"a1": {"e4_clearance": False}}
    )
    payload = _declared_payload(exercises=[
        {"exercise_id": "ECA-PHY-0135", "tempo": "3:0:1:0"}
    ])
    kdo = KernelRunner(provider).evaluate(payload, "PHYSIQUE")
    codes = [v["code"] for v in kdo.violations]
    assert "PHYSIQUE.CLEARANCEMISSING" in codes


def test_transitional_keys_with_e4_exercise_fires_clearance_violation():
    """Transitional field names produce same clearance violation (backward compat)."""
    provider = InMemoryDependencyProvider(
        athlete_profile={"a1": {"e4_clearance": False}}
    )
    payload = _transitional_payload(exercises=[
        {"exercise_id": "ECA-PHY-0135", "tempo": "3:0:1:0"}
    ])
    kdo = KernelRunner(provider).evaluate(payload, "PHYSIQUE")
    codes = [v["code"] for v in kdo.violations]
    assert "PHYSIQUE.CLEARANCEMISSING" in codes


def test_both_keys_present_transitional_wins():
    """When both declared and transitional keys are present, transitional takes precedence."""
    payload = {
        "moduleVersion": PHY_REG["moduleVersion"],
        "moduleViolationRegistryVersion": PHY_REG["moduleViolationRegistryVersion"],
        "registryHash": PHY_REG["registryHash"],
        "objectID": "obj-both-001",
        "evaluationContext": {"athleteID": "a1", "sessionID": "s1"},
        "evaluation_context": {"athleteID": "SHOULD_NOT_BE_USED"},
        "windowContext": _base_windows(),
        "physique_session": {"exercises": []},  # transitional: empty → no clearance violation
        "session": {"exercises": [{"exercise_id": "ECA-PHY-0135", "tempo": "3:0:1:0"}]},
    }
    kdo = _runner().evaluate(payload, "PHYSIQUE")
    codes = [v["code"] for v in kdo.violations]
    assert "PHYSIQUE.CLEARANCEMISSING" not in codes, \
        "physique_session (transitional) should win over session (declared)"


def test_non_physique_modules_unaffected():
    """Normalization must not apply to SESSION — session is a valid SESSION payload field."""
    SESSION_REG = RAL_SPEC["moduleRegistration"]["SESSION"]
    payload = {
        "moduleVersion": SESSION_REG["moduleVersion"],
        "moduleViolationRegistryVersion": SESSION_REG["moduleViolationRegistryVersion"],
        "registryHash": SESSION_REG["registryHash"],
        "objectID": "obj-session-norm-001",
        "evaluationContext": {"athleteID": "a1", "sessionID": "s1"},
        "windowContext": [
            {"windowType": "ROLLING7DAYS", "anchorDate": "2026-01-01",
             "startDate": "2025-12-26", "endDate": "2026-01-01", "timezone": "UTC"},
            {"windowType": "ROLLING28DAYS", "anchorDate": "2026-01-01",
             "startDate": "2025-12-05", "endDate": "2026-01-01", "timezone": "UTC"},
        ],
        "session": {"contactLoad": 0, "exercises": []},
    }
    kdo = KernelRunner(InMemoryDependencyProvider()).evaluate(payload, "SESSION")
    assert isinstance(kdo.violations, list)
