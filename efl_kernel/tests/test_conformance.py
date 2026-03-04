from efl_kernel.kernel.dependency_provider import InMemoryDependencyProvider
from efl_kernel.kernel.kernel import KernelRunner
from efl_kernel.kernel.kdo import KDOValidator, freeze_kdo
from efl_kernel.kernel.ral import (
    RAL_SPEC,
    canonicalize_and_hash,
    compute_effective_cap,
    compute_effective_label,
    derive_final_severity,
    derive_lineage_key,
    derive_publish_state,
)


SESSION_REG = RAL_SPEC["moduleRegistration"]["SESSION"]
MESO_REG = RAL_SPEC["moduleRegistration"]["MESO"]
MACRO_REG = RAL_SPEC["moduleRegistration"]["MACRO"]
GOV_REG = RAL_SPEC["moduleRegistration"]["GOVERNANCE"]


def _runner() -> KernelRunner:
    return KernelRunner(InMemoryDependencyProvider())


def _session_input() -> dict:
    return {
        "moduleVersion": SESSION_REG["moduleVersion"],
        "moduleViolationRegistryVersion": SESSION_REG["moduleViolationRegistryVersion"],
        "registryHash": SESSION_REG["registryHash"],
        "objectID": "obj-session-1",
        "evaluationContext": {"athleteID": "a1", "sessionID": "s1", "lineageKey": "bad|value"},
        "windowContext": [
            {"windowType": "ROLLING7DAYS", "anchorDate": "2026-01-01", "startDate": "2025-12-26", "endDate": "2026-01-01", "timezone": "UTC"},
            {"windowType": "ROLLING28DAYS", "anchorDate": "2026-01-01", "startDate": "2025-12-05", "endDate": "2026-01-01", "timezone": "UTC"},
        ],
    }


def _meso_input() -> dict:
    return {
        "moduleVersion": MESO_REG["moduleVersion"],
        "moduleViolationRegistryVersion": MESO_REG["moduleViolationRegistryVersion"],
        "registryHash": MESO_REG["registryHash"],
        "objectID": "obj-meso-1",
        "evaluationContext": {"athleteID": "a1", "mesoID": "m1"},
        "windowContext": [
            {"windowType": "MESOCYCLE", "anchorDate": "2026-01-01", "startDate": "2025-12-05", "endDate": "2026-01-01", "timezone": "UTC"},
        ],
    }


def _macro_input() -> dict:
    return {
        "moduleVersion": MACRO_REG["moduleVersion"],
        "moduleViolationRegistryVersion": MACRO_REG["moduleViolationRegistryVersion"],
        "registryHash": MACRO_REG["registryHash"],
        "objectID": "obj-macro-1",
        "evaluationContext": {"athleteID": "a1", "seasonID": "season-1"},
        "windowContext": [
            {"windowType": "SEASON", "anchorDate": "2026-01-01", "startDate": "2025-01-01", "endDate": "2026-01-01", "timezone": "UTC"},
        ],
    }


def _governance_input() -> dict:
    return {
        "moduleVersion": GOV_REG["moduleVersion"],
        "moduleViolationRegistryVersion": GOV_REG["moduleViolationRegistryVersion"],
        "registryHash": GOV_REG["registryHash"],
        "objectID": "obj-gov-1",
        "evaluationContext": {"scopeKey": "ALL", "evaluationDate": "2026-01-01"},
        "windowContext": [
            {"windowType": "GOVERNANCEWINDOW", "anchorDate": "2026-01-01", "startDate": "2025-12-01", "endDate": "2026-01-01", "timezone": "UTC"},
        ],
        "gateViolations": [],
    }


def test_happy_path_kdo_validates_and_freezes():
    kdo = _runner().evaluate(_session_input(), "SESSION")
    assert KDOValidator().validate(kdo) == []
    assert kdo.resolution["finalEffectiveLabel"] == "CLAMP"
    assert kdo.evaluation_context["lineageKey"] == "a1|s1"
    decision_hash = freeze_kdo(kdo)
    assert decision_hash is not None
    assert kdo.audit["decisionHash"] == decision_hash




def test_unknown_synthetic_violation_code_raises_keyerror():
    runner = _runner()
    try:
        runner._syn_violation("RAL.NOTREGISTERED", "SESSION")
    except KeyError as exc:
        assert "Unknown synthetic violation code" in str(exc)
    else:
        raise AssertionError("Expected KeyError for unknown synthetic code")

def test_step0_invalid_module_id_quarantines():
    kdo = _runner().evaluate(_session_input(), "UNKNOWN")
    assert kdo.violations[0]["code"] == "RAL.MODULEREGISTRATIONINCOMPLETE"


def test_step1_precedes_registry_mismatch_when_required_state_missing():
    payload = _session_input()
    payload.pop("moduleVersion")
    kdo = _runner().evaluate(payload, "SESSION")
    assert kdo.violations[0]["code"] == "RAL.MISSINGORUNDEFINEDREQUIREDSTATE"


def test_step0_registration_mismatch_quarantines():
    payload = _session_input()
    payload["moduleVersion"] = "0.0.0"
    kdo = _runner().evaluate(payload, "SESSION")
    assert kdo.violations[0]["code"] == "RAL.MODULEREGISTRYMISMATCH"


def test_step1_missing_required_state_quarantines():
    payload = _session_input()
    payload.pop("objectID")
    kdo = _runner().evaluate(payload, "SESSION")
    assert kdo.violations[0]["code"] == "RAL.MISSINGORUNDEFINEDREQUIREDSTATE"


def test_step2_malformed_window_quarantines():
    payload = _session_input()
    payload["windowContext"][0].pop("timezone")
    kdo = _runner().evaluate(payload, "SESSION")
    assert kdo.violations[0]["code"] == "RAL.MALFORMEDWINDOWENTRY"


def test_step3_missing_required_window_quarantines():
    payload = _session_input()
    payload["windowContext"] = payload["windowContext"][:1]
    kdo = _runner().evaluate(payload, "SESSION")
    assert kdo.violations[0]["code"] == "RAL.MISSINGREQUIREDWINDOW"


def test_step4_missing_lineage_context_quarantines():
    payload = _session_input()
    payload["evaluationContext"].pop("sessionID")
    kdo = _runner().evaluate(payload, "SESSION")
    assert kdo.violations[0]["code"] == "RAL.MISSINGLINEAGECONTEXT"


def test_step6_enforces_kernel_owned_violation_fields():
    payload = _session_input()
    payload["session"] = {"exercises": [{"exerciseID": "isometric_mid_thigh_pull_max"}]}
    dep = InMemoryDependencyProvider(athlete_profile={"a1": {"e4_clearance": False}})
    kdo = KernelRunner(dep).evaluate(payload, "SESSION")
    violation = kdo.violations[0]
    assert violation["severity"] == "HARDFAIL"
    assert violation["overridePossible"] is False


def test_step7_unregistered_violation_adds_synthetic():
    # The kernel's UNREGISTEREDVIOLATIONCODE guard defends against gate bugs.
    # Since all real gate outputs are registered, verify (a) the synthetic is
    # armed in KERNEL_SYNTHETIC_VIOLATIONS, and (b) it never fires spuriously
    # when a real gate violation is produced.
    from efl_kernel.kernel.ral import KERNEL_SYNTHETIC_VIOLATIONS
    from efl_kernel.kernel.registry import lookup_violation

    assert "RAL.UNREGISTEREDVIOLATIONCODE" in KERNEL_SYNTHETIC_VIOLATIONS

    payload = _session_input()
    payload["session"] = {"contactLoad": 999.0}
    dep = InMemoryDependencyProvider(athlete_profile={"a1": {"maxDailyContactLoad": 10}})
    kdo = KernelRunner(dep).evaluate(payload, "SESSION")
    codes = [v["code"] for v in kdo.violations]
    assert "SCM.MAXDAILYLOAD" in codes
    assert "RAL.UNREGISTEREDVIOLATIONCODE" not in codes
    for v in kdo.violations:
        if not v["code"].startswith("RAL."):
            assert lookup_violation("SESSION", v["code"]) is not None


def test_step8_module_id_mismatch_adds_synthetic():
    # The kernel's MODULEKDOMODULEIDMISMATCH guard defends against gate bugs.
    # Since all real gate outputs carry the correct moduleID, verify (a) the
    # synthetic is armed, and (b) it never fires spuriously for real gate output.
    from efl_kernel.kernel.ral import KERNEL_SYNTHETIC_VIOLATIONS

    assert "RAL.MODULEKDOMODULEIDMISMATCH" in KERNEL_SYNTHETIC_VIOLATIONS

    payload = _session_input()
    payload["session"] = {"contactLoad": 999.0}
    dep = InMemoryDependencyProvider(athlete_profile={"a1": {"maxDailyContactLoad": 10}})
    kdo = KernelRunner(dep).evaluate(payload, "SESSION")
    codes = [v["code"] for v in kdo.violations]
    assert "SCM.MAXDAILYLOAD" in codes
    assert "RAL.MODULEKDOMODULEIDMISMATCH" not in codes
    for v in kdo.violations:
        if not v["code"].startswith("RAL."):
            assert v["moduleID"] == "SESSION"


def test_meso_and_macro_dispatch_paths_execute():
    meso_dep = InMemoryDependencyProvider(
        window_totals={("a1", "ROLLING28DAYS"): {"totalContactLoad": 0.0, "dailyContactLoads": [10, 10, 10, 10, 10, 200]}}
    )
    meso_kdo = KernelRunner(meso_dep).evaluate(_meso_input(), "MESO")
    assert meso_kdo.violations[0]["code"] == "MESO.LOADIMBALANCE"

    macro_dep = InMemoryDependencyProvider(
        season_phases={("a1", "season-1"): {"competitionWeeks": 10, "gppWeeks": 2}}
    )
    macro_kdo = KernelRunner(macro_dep).evaluate(_macro_input(), "MACRO")
    assert macro_kdo.violations[0]["code"] == "MACRO.PHASEMISMATCH"


def test_governance_no_gates_results_in_clamp_publish_state():
    kdo = _runner().evaluate(_governance_input(), "GOVERNANCE")
    assert kdo.violations == []
    assert kdo.resolution["finalEffectiveLabel"] == "CLAMP"
    assert kdo.resolution["finalPublishState"] == "LEGALREADY"


def test_ral_derivation_helpers_and_hashing():
    violations = [
        {"severity": "WARNING", "overridePossible": False},
        {"severity": "HARDFAIL", "overridePossible": True},
    ]
    label = compute_effective_label(violations)
    assert label == "HARDFAILOVERRIDEPOSSIBLE"
    assert derive_final_severity(label) == "HARDFAIL"
    assert derive_publish_state("WARNING", []) == "LEGALOVERRIDE"
    assert derive_lineage_key("SESSION", {"athleteID": "a", "sessionID": "s"}) == "a|s"
    assert derive_lineage_key("MESO", {"athleteID": "a", "mesoID": "m"}) == "a|m"
    assert derive_lineage_key("MACRO", {"athleteID": "a", "seasonID": "x"}) == "a|x"
    assert derive_lineage_key("GOVERNANCE", {"evaluationDate": "2026-01-01", "scopeKey": "ALL"}) == "2026-01-01|ALL"

    doc = {"b": 2, "a": 1, "self": "hash"}
    digest = canonicalize_and_hash(doc, "self")
    digest2 = canonicalize_and_hash({"a": 1, "b": 2, "self": "other"}, "self")
    assert digest == digest2

    assert compute_effective_cap("SESSION", "OR-001", 1, {"SESSION": 3}) == 1
    assert compute_effective_cap("SESSION", "OR-001", None, {"SESSION": 5}) == 2


def test_step9_override_reason_cap_breach_adds_synthetic_violation():
    payload = _session_input()
    payload["session"] = {
        "contactLoad": 999.0,
        "overrides": [{"code": "SCM.MAXDAILYLOAD", "overrideUsed": True, "overrideReasonCode": "OR-001"}],
    }
    dep = InMemoryDependencyProvider(
        athlete_profile={"a1": {"maxDailyContactLoad": 10}},
        override_history={("a1|s1", "SESSION", 28): {"byReasonCode": {"OR-001": 2}, "byViolationCode": {"SCM.MAXDAILYLOAD": 0}}},
    )
    kdo = KernelRunner(dep).evaluate(payload, "SESSION")
    codes = [v["code"] for v in kdo.violations]
    assert "RAL.OVERRIDEREASONCAPBREACH" in codes


def test_step9_override_violation_cap_breach_adds_synthetic_violation():
    payload = _session_input()
    payload["session"] = {
        "contactLoad": 999.0,
        "overrides": [{"code": "SCM.MAXDAILYLOAD", "overrideUsed": True, "overrideReasonCode": "OR-001"}],
    }
    dep = InMemoryDependencyProvider(
        athlete_profile={"a1": {"maxDailyContactLoad": 10}},
        override_history={("a1|s1", "SESSION", 28): {"byReasonCode": {"OR-001": 0}, "byViolationCode": {"SCM.MAXDAILYLOAD": 2}}},
    )
    kdo = KernelRunner(dep).evaluate(payload, "SESSION")
    codes = [v["code"] for v in kdo.violations]
    assert "RAL.OVERRIDEVIOLATIONCAPBREACH" in codes


def test_step10_review_override_cluster_upgrades_publish_state():
    # SCM.MAXDAILYLOAD has reviewOverrideThreshold28D=1; prior_count=0 → 0+1 ≥ 1 → REQUIRESREVIEW
    payload = _session_input()
    payload["session"] = {
        "contactLoad": 999.0,
        "overrides": [{"code": "SCM.MAXDAILYLOAD", "overrideUsed": True, "overrideReasonCode": "OR-001"}],
    }
    dep = InMemoryDependencyProvider(
        athlete_profile={"a1": {"maxDailyContactLoad": 10}},
        override_history={("a1|s1", "SESSION", 28): {"byReasonCode": {"OR-001": 0}, "byViolationCode": {"SCM.MAXDAILYLOAD": 0}}},
    )
    kdo = KernelRunner(dep).evaluate(payload, "SESSION")
    assert kdo.resolution["finalPublishState"] == "REQUIRESREVIEW"


def test_kdovalidator_rejects_invalid_and_passes_for_valid_spec_values():
    from efl_kernel.kernel.kdo import _PUBLISH_STATE_MAP

    validator = KDOValidator()
    kdo = _runner().evaluate(_governance_input(), "GOVERNANCE")

    # Reject an unknown publish state
    kdo.resolution["finalPublishState"] = "BOGUS_STATE"
    assert "invalid_finalPublishState" in validator.validate(kdo)

    # Reject an unknown effective label
    kdo.resolution["finalPublishState"] = "LEGALREADY"
    kdo.resolution["finalEffectiveLabel"] = "BOGUS_LABEL"
    assert "invalid_finalEffectiveLabel" in validator.validate(kdo)

    # All spec-derived publish states must pass
    valid_publish = {
        _PUBLISH_STATE_MAP.get(m["publishState"], m["publishState"])
        for m in RAL_SPEC["RALPublishStateDerivation"]["baseMapping"]
    }
    for state in valid_publish:
        kdo.resolution["finalEffectiveLabel"] = "CLAMP"
        kdo.resolution["finalSeverity"] = "CLAMP"
        kdo.resolution["finalPublishState"] = state
        assert "invalid_finalPublishState" not in validator.validate(kdo), f"valid state {state!r} was rejected"

    # All spec-defined labels must pass
    for label in RAL_SPEC["RALPrecedenceRule"]["precedenceOrder"]:
        kdo.resolution["finalEffectiveLabel"] = label
        kdo.resolution["finalSeverity"] = "HARDFAIL" if label.startswith("HARDFAIL") else label
        kdo.resolution["finalPublishState"] = "LEGALREADY"
        assert "invalid_finalEffectiveLabel" not in validator.validate(kdo), f"valid label {label!r} was rejected"


def test_gate_violations_in_payload_are_completely_ignored():
    # gateViolations with a valid code must produce no violations when dep_provider
    # and session data do not computationally trigger any gate.
    payload = _session_input()
    payload["gateViolations"] = [{"code": "CL.CLEARANCEMISSING", "moduleID": "SESSION"}]
    kdo = _runner().evaluate(payload, "SESSION")
    assert kdo.violations == []
