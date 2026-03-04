from __future__ import annotations


def run_macro_gates(raw_input: dict, dep_provider) -> list[dict]:
    violations: list[dict] = []
    eval_ctx = raw_input.get("evaluationContext", {})
    athlete_id = eval_ctx.get("athleteID", "")
    season_id = eval_ctx.get("seasonID", "")

    phases = dep_provider.get_season_phases(athlete_id, season_id)
    competition_weeks = float(phases.get("competitionWeeks", 0) or 0)
    gpp_weeks = float(phases.get("gppWeeks", 0) or 0)

    if competition_weeks > 0 and (gpp_weeks <= 0 or (competition_weeks / gpp_weeks) > 2.0):
        violations.append({"code": "MACRO.PHASEMISMATCH", "moduleID": "MACRO", "overrideUsed": False})

    for v in raw_input.get("gateViolations", []):
        if v.get("moduleID") == "MACRO":
            violations.append(dict(v))
    return violations
