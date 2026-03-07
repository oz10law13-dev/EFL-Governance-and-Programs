from __future__ import annotations

import copy
import json
from pathlib import Path

from .ral import canonicalize_and_hash

SPEC_DIR = Path(__file__).resolve().parent.parent / "specs"


def _load(path: str) -> dict:
    return json.loads((SPEC_DIR / path).read_text(encoding="utf-8"))


SCM_SPEC = _load("EFL_SCM_v1_1_1_frozen.json")
MESO_SPEC = _load("EFL_MESO_v1_0_2_frozen.json")
MACRO_SPEC = _load("EFL_MACRO_v1_0_2_frozen.json")
PHYSIQUE_SPEC = _load("EFL_PHYSIQUE_v1_0_0_frozen.json")
CL_SPEC = _load("EFL_Canonical_Law_v1_2_2_frozen.json")

for spec in (SCM_SPEC, MESO_SPEC, MACRO_SPEC, PHYSIQUE_SPEC):
    reg = copy.deepcopy(spec["violationRegistry"])
    expected = reg.get("registryHash")
    reg["registryHash"] = ""
    if canonicalize_and_hash(reg) != expected:
        raise RuntimeError(f"registry hash verification failed for {spec.get('moduleID')}")

_cl_reg = copy.deepcopy(CL_SPEC["CLVIOLATIONREGISTRY"])
_cl_reg_expected = _cl_reg.get("registryHash")
_cl_reg["registryHash"] = ""
if canonicalize_and_hash(_cl_reg) != _cl_reg_expected:
    raise RuntimeError("registry hash verification failed for CL_SPEC")

VIOLATION_REGISTRY: dict[tuple[str, str], dict] = {}

for spec in (SCM_SPEC, MESO_SPEC, MACRO_SPEC, PHYSIQUE_SPEC):
    for v in spec["violationRegistry"]["violations"]:
        VIOLATION_REGISTRY[(v["moduleID"], v["code"])] = {
            "severity": v["severity"],
            "overridePossible": v["overridePossible"],
            "allowedOverrideReasonCodes": v["allowedOverrideReasonCodes"],
            "violationCap": v["violationCap"],
            "reviewOverrideThreshold28D": v["reviewOverrideThreshold28D"],
            "clampBehavior": v.get("clampBehavior"),
        }

for v in CL_SPEC["CLVIOLATIONREGISTRY"]["violations"]:
    VIOLATION_REGISTRY[(v["moduleID"], v["code"])] = {
        "severity": v["severity"],
        "overridePossible": v["overridePossible"],
        "allowedOverrideReasonCodes": v["allowedOverrideReasonCodes"],
        "violationCap": v["violationCap"],
        "reviewOverrideThreshold28D": v["reviewOverrideThreshold28D"],
        "clampBehavior": v.get("clampBehavior"),
    }


def lookup_violation(module_id: str, code: str) -> dict | None:
    return VIOLATION_REGISTRY.get((module_id, code))


def enforce_kernel_owned_fields(violation: dict, module_id: str) -> dict:
    if violation.get("code", "").startswith("RAL."):
        return violation
    reg = lookup_violation(module_id, violation.get("code"))
    if not reg:
        return violation
    for key in ["severity", "overridePossible", "allowedOverrideReasonCodes", "violationCap", "reviewOverrideThreshold28D"]:
        violation[key] = reg[key]
    return violation


def validate_bidirectional_coverage() -> dict[str, list[str]]:
    coverage_file = Path(__file__).resolve().parent.parent / "tests" / "test_gate_coverage.py"
    text = coverage_file.read_text(encoding="utf-8") if coverage_file.exists() else ""
    by_module: dict[str, list[str]] = {}
    for (module, code) in VIOLATION_REGISTRY.keys():
        if code not in text:
            by_module.setdefault(module, []).append(code)
    return by_module
