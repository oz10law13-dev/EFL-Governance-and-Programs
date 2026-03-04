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
        "gateViolations": [{"code": "SCM.MAXDAILYLOAD", "moduleID": "SESSION"}],
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
        "gateViolations": [{"code": "MESO.LOADIMBALANCE", "moduleID": "MESO"}],
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
        "gateViolations": [{"code": "MACRO.PHASEMISMATCH", "moduleID": "MACRO"}],
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
    assert kdo.resolution["finalEffectiveLabel"] == "HARDFAILOVERRIDEPOSSIBLE"
    assert kdo.evaluation_context["lineageKey"] == "a1|s1"
    decision_hash = freeze_kdo(kdo)
    assert decision_hash is not None
    assert kdo.audit["decisionHash"] == decision_hash


def test_step0_invalid_module_id_quarantines():
    kdo = _runner().evaluate(_session_input(), "UNKNOWN")
    assert kdo.violations[0]["code"] == "RAL.MODULEREGISTRATIONINCOMPLETE"


def test_step0_registration_mismatch_quarantines():
    payload = _session_input()
    payload["moduleVersion"] = "0.0.0"
    kdo = _runner().evaluate(payload, "SESSION")
    assert kdo.violations[0]["code"] == "RAL.MODULEREGISTRATIONINCOMPLETE"


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
    payload["gateViolations"] = [
        {
            "code": "SCM.MAXDAILYLOAD",
            "moduleID": "SESSION",
            "severity": "WARNING",
            "overridePossible": False,
        }
    ]
    kdo = _runner().evaluate(payload, "SESSION")
    violation = kdo.violations[0]
    assert violation["severity"] == "HARDFAIL"
    assert violation["overridePossible"] is True


def test_step7_unregistered_violation_adds_synthetic():
    payload = _session_input()
    payload["gateViolations"] = [{"code": "SCM.UNKNOWN", "moduleID": "SESSION"}]
    kdo = _runner().evaluate(payload, "SESSION")
    codes = [v["code"] for v in kdo.violations]
    assert "RAL.UNREGISTEREDVIOLATIONCODE" in codes


def test_step8_module_id_mismatch_adds_synthetic():
    payload = _session_input()
    payload["gateViolations"] = [{"code": "CL.CLEARANCEMISSING", "moduleID": "MESO"}]
    kdo = _runner().evaluate(payload, "SESSION")
    codes = [v["code"] for v in kdo.violations]
    assert "RAL.MODULEKDOMODULEIDMISMATCH" in codes


def test_meso_and_macro_dispatch_paths_execute():
    meso_kdo = _runner().evaluate(_meso_input(), "MESO")
    macro_kdo = _runner().evaluate(_macro_input(), "MACRO")
    assert meso_kdo.violations[0]["code"] == "MESO.LOADIMBALANCE"
    assert macro_kdo.violations[0]["code"] == "MACRO.PHASEMISMATCH"


def test_governance_no_gates_results_in_clamp_publish_state():
    kdo = _runner().evaluate(_governance_input(), "GOVERNANCE")
    assert kdo.violations == []
    assert kdo.resolution["finalEffectiveLabel"] == "CLAMP"
    assert kdo.resolution["finalPublishState"] == "PUBLISH_WITH_CLAMP"


def test_ral_derivation_helpers_and_hashing():
    violations = [
        {"severity": "WARNING", "overridePossible": False},
        {"severity": "HARDFAIL", "overridePossible": True},
    ]
    label = compute_effective_label(violations)
    assert label == "HARDFAILOVERRIDEPOSSIBLE"
    assert derive_final_severity(label) == "HARDFAIL"
    assert derive_publish_state("WARNING", []) == "PUBLISH_WITH_WARNING"
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
