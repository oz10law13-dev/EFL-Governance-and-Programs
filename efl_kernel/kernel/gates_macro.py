from __future__ import annotations


def run_macro_gates(raw_input: dict, dep_provider) -> list[dict]:
    return [dict(v) for v in raw_input.get("gateViolations", []) if v.get("moduleID") == "MACRO"]
