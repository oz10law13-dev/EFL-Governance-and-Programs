from __future__ import annotations


def run_scm_gates(raw_input: dict, dep_provider) -> list[dict]:
    violations = []
    for v in raw_input.get("gateViolations", []):
        if v.get("moduleID") == "SESSION":
            violations.append(dict(v))
    return violations
