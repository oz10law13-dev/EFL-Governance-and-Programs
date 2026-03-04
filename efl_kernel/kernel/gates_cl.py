from __future__ import annotations

import json
from pathlib import Path

_EXERCISE_LIBRARY_PATH = Path(__file__).resolve().parent.parent / "specs" / "EFL_Exercise_Library_100_v1_0_1.json"
_EXERCISE_LIBRARY_RAW = json.loads(_EXERCISE_LIBRARY_PATH.read_text(encoding="utf-8"))
EXERCISE_LIBRARY: dict[str, dict] = {exercise["id"]: exercise for exercise in _EXERCISE_LIBRARY_RAW}


def _exercise_id(exercise: dict) -> str:
    return exercise.get("exerciseID") or exercise.get("exercise_id") or exercise.get("id") or ""


def run_cl_gates(raw_input: dict, dep_provider) -> list[dict]:
    violations: list[dict] = []
    eval_ctx = raw_input.get("evaluationContext", {})
    athlete_id = eval_ctx.get("athleteID", "")
    athlete_profile = dep_provider.get_athlete_profile(athlete_id)
    has_clearance = bool(athlete_profile.get("e4_clearance", False))

    exercises = raw_input.get("session", {}).get("exercises", [])
    for exercise in exercises:
        exercise_id = _exercise_id(exercise)
        exercise_def = EXERCISE_LIBRARY.get(exercise_id)
        if exercise_def is None:
            continue
        if exercise_def.get("e4_requires_clearance", False) and not has_clearance:
            violations.append({"code": "CL.CLEARANCEMISSING", "moduleID": "SESSION", "overrideUsed": False})

    for v in raw_input.get("gateViolations", []):
        if v.get("code", "").startswith("CL."):
            violations.append(dict(v))

    return violations
