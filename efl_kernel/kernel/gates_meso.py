from __future__ import annotations

from datetime import date


def run_meso_gates(raw_input: dict, dep_provider) -> list[dict]:
    violations: list[dict] = []
    eval_ctx = raw_input.get("evaluationContext", {})
    athlete_id = eval_ctx.get("athleteID", "")

    window = next((w for w in raw_input.get("windowContext", []) if w.get("windowType") == "MESOCYCLE"), None)
    if window is not None:
        anchor = date.fromisoformat(window["anchorDate"])
        totals = dep_provider.get_window_totals(athlete_id, "ROLLING28DAYS", anchor, eval_ctx.get("mesoID", ""))
        daily = [float(x) for x in totals.get("dailyContactLoads", [])]
        if len(daily) >= 2:
            average = sum(daily) / len(daily)
            if average > 0 and max(daily) > average * 2.0:
                violations.append({"code": "MESO.LOADIMBALANCE", "moduleID": "MESO", "overrideUsed": False})

    return violations
