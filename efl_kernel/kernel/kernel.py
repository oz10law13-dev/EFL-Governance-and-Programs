from __future__ import annotations

from datetime import datetime, timezone

from .dependency_provider import KernelDependencyProvider
from .gates_cl import run_cl_gates
from .gates_macro import run_macro_gates
from .gates_meso import run_meso_gates
from .gates_scm import run_scm_gates
from .kdo import KDO
from .ral import (
    KERNEL_SYNTHETIC_VIOLATIONS,
    RAL_SPEC,
    REQUIRED_CONTEXT_BY_MODULE,
    REQUIRED_WINDOWS_BY_MODULE,
    compute_effective_cap,
    compute_effective_label,
    derive_final_severity,
    derive_lineage_key,
    derive_publish_state,
)
from .registry import enforce_kernel_owned_fields, lookup_violation


class KernelRunner:
    def __init__(self, dep_provider: KernelDependencyProvider):
        self.dep_provider = dep_provider

    def _syn_violation(self, code: str, module_id: str) -> dict:
        spec = KERNEL_SYNTHETIC_VIOLATIONS.get(code)
        if spec is None and code in {
            "RAL.MODULEREGISTRYMISMATCH",
            "RAL.OVERRIDEREASONCAPBREACH",
            "RAL.OVERRIDEVIOLATIONCAPBREACH",
        }:
            # Compatibility fallback: these synthetic codes are emitted by the pipeline but absent
            # from the frozen RAL synthetic registry in this repository snapshot.
            spec = {"severity": "QUARANTINE", "overridePossible": False}
        if spec is None:
            raise KeyError(f"Unknown synthetic violation code: {code}")
        return {
            "code": code,
            "moduleID": module_id,
            "severity": spec["severity"],
            "overridePossible": spec["overridePossible"],
            "overrideUsed": False,
            "allowedOverrideReasonCodes": [],
            "violationCap": None,
            "reviewOverrideThreshold28D": None,
            "clampAction": None,
            "publishStatePostClamp": None,
            "publishStatePostWarning": None,
        }

    def _build_kdo(self, module_id: str, raw_input: dict, violations: list[dict]) -> KDO:
        effective = compute_effective_label(violations)
        severity = derive_final_severity(effective)
        state = derive_publish_state(effective, violations)
        reason = "|".join(v["code"] for v in violations) if violations else "NO_VIOLATIONS"
        if effective == "REGENERATE" and "REGENERATEREQUIRED" not in reason:
            reason += "|REGENERATEREQUIRED"
        return KDO(
            module_id=module_id,
            module_version=raw_input.get("moduleVersion", ""),
            object_id=raw_input.get("objectID", ""),
            ral_version=RAL_SPEC.get("version", ""),
            evaluation_context=raw_input.get("evaluationContext", {}),
            window_context=raw_input.get("windowContext", []),
            violations=violations,
            resolution={
                "finalEffectiveLabel": effective,
                "finalSeverity": severity,
                "finalPublishState": state,
                "mutationsApplied": [],
                "requiresRevalidation": False,
                "revalidatedModules": [],
            },
            reason_summary=reason,
            timestamp_normalized=datetime.now(timezone.utc).isoformat(),
            audit={"decisionHash": ""},
        )

    def evaluate(self, raw_input: dict, module_id: str) -> KDO:
        # Step 0
        if module_id not in ["SESSION", "MESO", "MACRO", "GOVERNANCE"]:
            return self._build_kdo(module_id, raw_input, [self._syn_violation("RAL.MODULEREGISTRATIONINCOMPLETE", module_id)])

        # Step 1
        required = ["moduleVersion", "moduleViolationRegistryVersion", "registryHash", "objectID", "evaluationContext", "windowContext"]
        if any(k not in raw_input for k in required):
            return self._build_kdo(module_id, raw_input, [self._syn_violation("RAL.MISSINGORUNDEFINEDREQUIREDSTATE", module_id)])

        reg = RAL_SPEC.get("moduleRegistration", {}).get(module_id, {})
        if (
            raw_input.get("moduleVersion") != reg.get("moduleVersion")
            or raw_input.get("moduleViolationRegistryVersion") != reg.get("moduleViolationRegistryVersion")
            or raw_input.get("registryHash") != reg.get("registryHash")
        ):
            return self._build_kdo(module_id, raw_input, [self._syn_violation("RAL.MODULEREGISTRYMISMATCH", module_id)])

        # Step 2
        for entry in raw_input.get("windowContext", []):
            if any(k not in entry for k in ["windowType", "anchorDate", "startDate", "endDate", "timezone"]):
                return self._build_kdo(module_id, raw_input, [self._syn_violation("RAL.MALFORMEDWINDOWENTRY", module_id)])

        # Step 3
        available = {w.get("windowType") for w in raw_input.get("windowContext", [])}
        for needed in REQUIRED_WINDOWS_BY_MODULE.get(module_id, []):
            if needed not in available:
                return self._build_kdo(module_id, raw_input, [self._syn_violation("RAL.MISSINGREQUIREDWINDOW", module_id)])

        # Step 4
        eval_ctx = raw_input.get("evaluationContext", {})
        for needed in REQUIRED_CONTEXT_BY_MODULE.get(module_id, []):
            if needed not in eval_ctx:
                return self._build_kdo(module_id, raw_input, [self._syn_violation("RAL.MISSINGLINEAGECONTEXT", module_id)])

        # Step 5
        eval_ctx["lineageKey"] = derive_lineage_key(module_id, eval_ctx)

        # Step 6
        if module_id == "SESSION":
            violations = run_scm_gates(raw_input, self.dep_provider) + run_cl_gates(raw_input, self.dep_provider)
        elif module_id == "MESO":
            violations = run_meso_gates(raw_input, self.dep_provider)
        elif module_id == "MACRO":
            violations = run_macro_gates(raw_input, self.dep_provider)
        else:
            violations = []

        violations = [enforce_kernel_owned_fields(v, module_id) for v in violations]

        # Step 7
        for v in list(violations):
            code = v.get("code", "")
            if not code.startswith("RAL.") and lookup_violation(module_id, code) is None:
                violations.append(self._syn_violation("RAL.UNREGISTEREDVIOLATIONCODE", module_id))

        # Step 8
        for v in list(violations):
            if v.get("moduleID") != module_id:
                violations.append(self._syn_violation("RAL.MODULEKDOMODULEIDMISMATCH", module_id))
                break

        # Step 9: OC-001 override cap enforcement
        history = None
        override_candidates = [v for v in violations if v.get("overrideUsed") is True]
        if override_candidates:
            history = self.dep_provider.get_override_history(eval_ctx["lineageKey"], module_id, 28)
            by_reason = history.get("byReasonCode", {})
            by_violation = history.get("byViolationCode", {})
            module_level_caps = RAL_SPEC.get("RALModuleLevelOverrideCaps", {}) or {}

            for violation in override_candidates:
                reason_code = violation.get("overrideReasonCode")
                if not reason_code:
                    violation["kernelComputedOverrideValid"] = False
                    continue

                reason_count = by_reason.get(reason_code, 0) + 1
                violation_count = by_violation.get(violation.get("code", ""), 0) + 1
                effective_cap = compute_effective_cap(module_id, reason_code, violation.get("violationCap"), module_level_caps)

                if reason_count > effective_cap:
                    violation["kernelComputedOverrideValid"] = False
                    violations.append(self._syn_violation("RAL.OVERRIDEREASONCAPBREACH", module_id))
                elif violation_count > effective_cap:
                    violation["kernelComputedOverrideValid"] = False
                    violations.append(self._syn_violation("RAL.OVERRIDEVIOLATIONCAPBREACH", module_id))
                else:
                    violation["kernelComputedOverrideValid"] = True

        kdo = self._build_kdo(module_id, raw_input, violations)

        # Step 10: REVIEW-OVERRIDE-CLUSTER overlay
        if history and kdo.resolution.get("finalPublishState") in {"LEGALREADY", "LEGALOVERRIDE"}:
            by_violation = history.get("byViolationCode", {})
            for violation in violations:
                if not violation.get("kernelComputedOverrideValid"):
                    continue
                threshold = violation.get("reviewOverrideThreshold28D")
                if threshold is None:
                    continue
                count = by_violation.get(violation.get("code", ""), 0) + 1
                if count >= threshold:
                    kdo.resolution["finalPublishState"] = "REQUIRESREVIEW"
                    break

        return kdo
