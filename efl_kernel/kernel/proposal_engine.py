from __future__ import annotations

from datetime import date, timedelta

from .exercise_catalog import ExerciseCatalog
from .ral import RAL_SPEC


class PhysiqueProposalEngine:
    """Deterministic physique session proposal generator.

    Generates complete, conformant physique evaluation payloads from
    constraints. Uses ExerciseCatalog (whitelist-backed) for exercise
    selection. No LLM. No randomness. No operational store reads.
    No KDO produced. Same constraints always produce the same candidate
    (exercises sorted by canonical_id before slicing).
    """

    def __init__(self, catalog: ExerciseCatalog) -> None:
        self._catalog = catalog

    def propose(self, constraints: dict) -> dict:
        """Generate a candidate physique evaluation payload.

        Required keys: athlete_id, session_id, day_role
        Optional keys:
          target_exercise_count (int, default 3)
          band_max (int, upper-bound cap on exercise band_max field)
          node_max (int, upper-bound cap on exercise node_max field)
          movement_families (list[str], restrict to these families)

        Returns:
          {
            "candidate_payload": dict,   # complete conformant eval payload
            "pre_validation": list,      # [{canonical_id, violations}]
            "exercises_selected": int,
            "constraints_applied": dict,
          }
        """
        # A3. Validate required fields
        for field in ("athlete_id", "session_id", "day_role"):
            if field not in constraints:
                raise ValueError(f"Missing required constraint: {field!r}")

        day_role = constraints["day_role"]

        # A4. Exercise selection — day_role filter (membership check)
        result = self._catalog.list_exercises({"day_role": day_role})

        # Upper-bound caps as post-filters (list_exercises band_max means >=)
        if constraints.get("band_max") is not None:
            result = [ex for ex in result
                      if ex.get("band_max", 0) <= constraints["band_max"]]
        if constraints.get("node_max") is not None:
            result = [ex for ex in result
                      if ex.get("node_max", 0) <= constraints["node_max"]]
        if constraints.get("movement_families") is not None:
            result = [ex for ex in result
                      if ex.get("movement_family") in constraints["movement_families"]]

        # A5. Sort by canonical_id for determinism, then slice
        candidates = sorted(result, key=lambda ex: ex["canonical_id"])
        target = constraints.get("target_exercise_count", 3)
        selected = candidates[:target]

        # A6. Build exercise dicts
        exercises = [
            {
                "exercise_id": ex["canonical_id"],
                "band_count": 1,
                "node": 1,
                "day_role": day_role,
                "tempo": "3:0:1:0",
                "set_count": 3,
            }
            for ex in selected
        ]

        # A7. Build windowContext
        today = date.today()
        anchor = today.isoformat()
        seven_ago = (today - timedelta(days=7)).isoformat()
        twenty_eight_ago = (today - timedelta(days=28)).isoformat()

        window_context = [
            {
                "windowType": "ROLLING7DAYS",
                "anchorDate": anchor,
                "startDate": seven_ago,
                "endDate": anchor,
                "timezone": "UTC",
            },
            {
                "windowType": "ROLLING28DAYS",
                "anchorDate": anchor,
                "startDate": twenty_eight_ago,
                "endDate": anchor,
                "timezone": "UTC",
            },
        ]

        # A8. Build candidate_payload — read moduleRegistration at call time
        reg = RAL_SPEC["moduleRegistration"]["PHYSIQUE"]

        candidate_payload = {
            "moduleVersion": reg["moduleVersion"],
            "moduleViolationRegistryVersion": reg["moduleViolationRegistryVersion"],
            "registryHash": reg["registryHash"],
            "objectID": f"proposal-{constraints['session_id']}",
            "evaluationContext": {
                "athleteID": constraints["athlete_id"],
                "sessionID": constraints["session_id"],
            },
            "windowContext": window_context,
            "physique_session": {
                "day_role": day_role,
                "exercises": exercises,
            },
        }

        # A9. Pre-validation
        pre_validation = [
            {
                "canonical_id": ex["canonical_id"],
                "violations": self._catalog.check_exercise({
                    "canonical_id": ex["canonical_id"],
                    "band_count": 1,
                    "node": 1,
                    "day_role": day_role,
                    "tempo": "3:0:1:0",
                    "set_count": 3,
                })["violations"],
            }
            for ex in selected
        ]

        # A10. Return
        return {
            "candidate_payload": candidate_payload,
            "pre_validation": pre_validation,
            "exercises_selected": len(selected),
            "constraints_applied": dict(constraints),
        }
