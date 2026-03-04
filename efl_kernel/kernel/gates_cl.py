from __future__ import annotations


def run_cl_gates(raw_input: dict, dep_provider) -> list[dict]:
    violations = []
    for v in raw_input.get("gateViolations", []):
        if v.get("code", "").startswith("CL."):
            violations.append(dict(v))
    return violations
