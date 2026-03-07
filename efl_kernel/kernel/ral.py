from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

SPEC_PATH = Path(__file__).resolve().parent.parent / "specs" / "EFL_RAL_v1_3_0_frozen.json"


def canonicalize_and_hash(doc: dict, self_hash_field: str | None = None) -> str:
    working = copy.deepcopy(doc)
    if self_hash_field:
        working[self_hash_field] = ""
    payload = json.dumps(working, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


RAL_SPEC: dict[str, Any] = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
if canonicalize_and_hash(RAL_SPEC, "documentHash") != RAL_SPEC.get("documentHash"):
    raise RuntimeError("RAL documentHash verification failed")

SEVERITY_PRECEDENCE = RAL_SPEC["RALPrecedenceRule"]["precedenceOrder"]
OVERRIDE_REASON_REGISTRY = {
    e["code"]: {
        "status": e["status"],
        "allowedModules": e["allowedModules"],
        "defaultMaxOverridesPer28D": e["defaultMaxOverridesPer28D"],
    }
    for e in RAL_SPEC["RALOverrideReasonRegistry"]["entries"]
}
KERNEL_SYNTHETIC_VIOLATIONS = {
    v["code"]: {
        "severity": v["severity"],
        "overridePossible": v["overridePossible"],
        "logRequired": v["logRequired"],
    }
    for v in RAL_SPEC["RALKernelSyntheticViolationRegistry"]["violations"]
}
DD_RULES = {r["id"]: r for r in RAL_SPEC["RALDefaultDenyDoctrine"]["rules"]}
REQUIRED_WINDOWS_BY_MODULE = {r["moduleID"]: r["requiredWindowTypes"] for r in RAL_SPEC["RALRequiredWindowsByModule"]["requirements"]}
REQUIRED_CONTEXT_BY_MODULE = RAL_SPEC["KDOSCHEMA"]["constraints"]["requiredContextByModule"]
LINEAGE_KEYS = RAL_SPEC["RALLineageKeys"]["perModule"]
WINDOW_SEMANTICS = RAL_SPEC["RALWindowSemantics"]
PUBLISH_STATE_BASE_MAPPING = RAL_SPEC["RALPublishStateDerivation"]["baseMapping"]
FREEZE_POLICY = RAL_SPEC["freezePolicy"]



def compute_effective_label(violations: list[dict]) -> str:
    labels = []
    for v in violations:
        sev = v.get("severity")
        if sev == "HARDFAIL":
            labels.append("HARDFAILOVERRIDEPOSSIBLE" if v.get("overridePossible") else "HARDFAILNOOVERRIDE")
        elif sev in {"REGENERATE", "WARNING", "CLAMP", "QUARANTINE"}:
            labels.append(sev)
    if not labels:
        return "CLAMP"
    rank = {label: idx for idx, label in enumerate(SEVERITY_PRECEDENCE)}
    return min(labels, key=lambda l: rank.get(l, 999))



def derive_final_severity(effective_label: str) -> str:
    if effective_label in {"HARDFAILNOOVERRIDE", "HARDFAILOVERRIDEPOSSIBLE"}:
        return "HARDFAIL"
    return effective_label



def derive_publish_state(effective_label: str, violations: list[dict]) -> str:
    final_severity = derive_final_severity(effective_label)
    publish_state_mapping = {
        "BLOCKED": "ILLEGALQUARANTINED",
        "REGENERATE_REQUIRED": "REQUIRESREVIEW",
        "PUBLISH_WITH_WARNING": "LEGALOVERRIDE",
        "PUBLISH_WITH_CLAMP": "LEGALREADY",
    }
    for mapping in PUBLISH_STATE_BASE_MAPPING:
        when = mapping.get("when", {})
        if "finalEffectiveLabel" in when and when["finalEffectiveLabel"] == effective_label:
            return publish_state_mapping.get(mapping["publishState"], mapping["publishState"])
        if "finalSeverity" in when and when["finalSeverity"] == final_severity:
            return publish_state_mapping.get(mapping["publishState"], mapping["publishState"])
    return "ILLEGALQUARANTINED"



def derive_lineage_key(module_id: str, context: dict) -> str:
    if module_id == "SESSION":
        return f"{context.get('athleteID','')}|{context.get('sessionID','')}"
    if module_id == "MESO":
        return f"{context.get('athleteID','')}|{context.get('mesoID','')}"
    if module_id == "MACRO":
        return f"{context.get('athleteID','')}|{context.get('seasonID','')}"
    if module_id == "GOVERNANCE":
        left = context.get("policyCheckID") or context.get("evaluationDate", "")
        return f"{left}|{context.get('scopeKey','')}"
    if module_id == "PHYSIQUE":
        return f"{context.get('athleteID','')}|{context.get('sessionID','')}"
    raise RuntimeError("Unknown moduleID for lineage")



def compute_effective_cap(module_id: str, override_reason_code: str, violation_cap: int | None, module_level_caps: dict) -> int:
    default_cap = OVERRIDE_REASON_REGISTRY.get(override_reason_code, {}).get("defaultMaxOverridesPer28D")
    module_cap = module_level_caps.get(module_id)
    candidates = [c for c in (default_cap, module_cap, violation_cap) if c is not None]
    return min(candidates) if candidates else float("inf")
