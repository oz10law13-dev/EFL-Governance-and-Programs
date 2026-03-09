from __future__ import annotations

from datetime import datetime, timezone

from .dependency_provider import KernelDependencyProvider
from .gates_cl import run_cl_gates
from .gates_macro import run_macro_gates
from .gates_meso import run_meso_gates
from .gates_physique import run_physique_gates
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
from .registry import VIOLATION_REGISTRY, enforce_kernel_owned_fields, lookup_violation


def _match_prior_version(
    reg: dict, version: str, registry_version: str, registry_hash: str
) -> dict | None:
    """Check if caller's version matches a DEPRECATED prior version.

    Returns the matching prior version dict if found, None otherwise.
    RETIRED versions are not accepted.
    """
    for prior in reg.get("priorVersions", []):
        if prior.get("status") != "DEPRECATED":
            continue
        if (
            prior.get("moduleVersion") == version
            and prior.get("moduleViolationRegistryVersion") == registry_version
            and prior.get("registryHash") == registry_hash
        ):
            return prior
    return None


class KernelRunner:
    def __init__(self, dep_provider: KernelDependencyProvider):
        self.dep_provider = dep_provider

    def _syn_violation(self, code: str, module_id: str) -> dict:
        try:
            spec = KERNEL_SYNTHETIC_VIOLATIONS[code]
        except KeyError:
            raise KeyError(f"Unknown synthetic violation code: {code!r}")
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
        kdo = KDO(
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
        # Record version negotiation if a deprecated version was accepted
        if raw_input.get("_version_deprecated"):
            kdo.resolution["versionNegotiation"] = {
                "callerVersion": raw_input.get("_version_negotiated_from", ""),
                "currentVersion": raw_input.get("_version_negotiated_to", ""),
                "status": "DEPRECATED",
            }
        return kdo

    def evaluate(self, raw_input: dict, module_id: str) -> KDO:
        # Normalize PHYSIQUE declared input envelope (§5.1 spec-declared → transitional names)
        if module_id == "PHYSIQUE":
            from .physique_adapter import _normalize_physique_envelope
            raw_input = _normalize_physique_envelope(raw_input)

        # Step 0 - module identity
        if module_id not in RAL_SPEC.get("moduleRegistration", {}):
            return self._build_kdo(module_id, raw_input, [self._syn_violation("RAL.MODULEREGISTRATIONINCOMPLETE", module_id)])

        # Step 1 - required fields (must precede registry version check)
        required = ["moduleVersion", "moduleViolationRegistryVersion", "registryHash", "objectID", "evaluationContext", "windowContext"]
        if any(k not in raw_input for k in required):
            return self._build_kdo(module_id, raw_input, [self._syn_violation("RAL.MISSINGORUNDEFINEDREQUIREDSTATE", module_id)])

        # Step 0b - version negotiation
        reg = RAL_SPEC.get("moduleRegistration", {}).get(module_id, {})
        caller_version = raw_input.get("moduleVersion")
        caller_registry_version = raw_input.get("moduleViolationRegistryVersion")
        caller_hash = raw_input.get("registryHash")

        if (
            caller_version == reg.get("moduleVersion")
            and caller_registry_version == reg.get("moduleViolationRegistryVersion")
            and caller_hash == reg.get("registryHash")
        ):
            pass  # Current version — proceed normally
        else:
            prior = _match_prior_version(reg, caller_version, caller_registry_version, caller_hash)
            if prior is not None:
                # Deprecated version accepted — record negotiation for KDO
                raw_input["_version_deprecated"] = True
                raw_input["_version_negotiated_from"] = caller_version
                raw_input["_version_negotiated_to"] = reg.get("moduleVersion")
            else:
                return self._build_kdo(module_id, raw_input,
                    [self._syn_violation("RAL.MODULEREGISTRYMISMATCH", module_id)])

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
        elif module_id == "PHYSIQUE":
            violations = run_physique_gates(raw_input, self.dep_provider)
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

        # Step 9 - override cap breach
        lineage_key = eval_ctx.get("lineageKey", "")
        cap_violations = []
        for v in list(violations):
            if v.get("overrideUsed"):
                reason_code = v.get("overrideReasonCode")
                history = self.dep_provider.get_override_history(lineage_key, module_id, 28)
                cap = compute_effective_cap(module_id, reason_code, v.get("violationCap"), {})
                if history.get("byReasonCode", {}).get(reason_code, 0) >= cap:
                    cap_violations.append(self._syn_violation("RAL.OVERRIDEREASONCAPBREACH", module_id))
                if history.get("byViolationCode", {}).get(v.get("code"), 0) >= cap:
                    cap_violations.append(self._syn_violation("RAL.OVERRIDEVIOLATIONCAPBREACH", module_id))
        violations.extend(cap_violations)

        # Step 10 - review override cluster
        requires_review = False
        for v in violations:
            threshold = v.get("reviewOverrideThreshold28D")
            if v.get("overrideUsed") and threshold is not None:
                history = self.dep_provider.get_override_history(lineage_key, module_id, 28)
                prior_count = history.get("byViolationCode", {}).get(v.get("code"), 0)
                if prior_count + 1 >= threshold:
                    requires_review = True
                    break

        kdo = self._build_kdo(module_id, raw_input, violations)
        if requires_review:
            kdo.resolution["finalPublishState"] = "REQUIRESREVIEW"
        return kdo
