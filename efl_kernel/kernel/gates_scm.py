from __future__ import annotations

from datetime import datetime


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _session_contact_load(raw_input: dict) -> float:
    session = raw_input.get("session", {})
    if "contactLoad" in session:
        return float(session.get("contactLoad") or 0.0)
    total = 0.0
    for exercise in session.get("exercises", []):
        reps = float(exercise.get("reps", 0) or 0)
        sets = float(exercise.get("sets", 1) or 1)
        contacts = float(exercise.get("plyo_contacts_per_rep", 0) or 0)
        total += reps * sets * contacts
    return total


def run_scm_gates(raw_input: dict, dep_provider) -> list[dict]:
    violations: list[dict] = []
    eval_ctx = raw_input.get("evaluationContext", {})
    athlete_id = eval_ctx.get("athleteID", "")
    athlete_profile = dep_provider.get_athlete_profile(athlete_id)

    contact_load = _session_contact_load(raw_input)
    max_daily = athlete_profile.get("maxDailyContactLoad", float("inf"))
    if contact_load > float(max_daily):
        violations.append({"code": "SCM.MAXDAILYLOAD", "moduleID": "SESSION", "overrideUsed": False})

    session_dt = _parse_dt(raw_input.get("session", {}).get("sessionDate"))
    if session_dt is not None:
        prior = dep_provider.get_prior_session(athlete_id, session_dt)
        prior_dt = _parse_dt((prior or {}).get("sessionDate"))
        if prior_dt is not None:
            min_rest_hours = float(athlete_profile.get("minimumRestIntervalHours", 24))
            elapsed_hours = (session_dt - prior_dt).total_seconds() / 3600.0
            if elapsed_hours < min_rest_hours:
                violations.append({"code": "SCM.MINREST", "moduleID": "SESSION", "overrideUsed": False})

    return violations
