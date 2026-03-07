from __future__ import annotations

import json
from pathlib import Path

from .physique_adapter import ECCENTRIC_MINIMUMS, _parse_tempo
from .registry import PHYSIQUE_SPEC

_PHYSIQUE_DIR = Path(__file__).resolve().parent.parent.parent / "Physique"
_H_NODE_NUMERIC: dict[str, int] = {"H0": 0, "H1": 1, "H2": 2, "H3": 3, "H4": 4}
_SFI_FORMULA: dict = PHYSIQUE_SPEC["sfiFormula"]


def _normalize(ex: dict) -> dict:
    """Return a normalized copy of a whitelist exercise, adding derived fields."""
    out = dict(ex)
    out["day_roles"] = [r.strip() for r in ex.get("day_role_allowed", "").split(",") if r.strip()]
    out["unilateral"] = ex.get("uni_bi", "Bilateral") == "Unilateral"
    return out


class ExerciseCatalog:
    """Read-only exercise catalog backed by the whitelist JSON."""

    def __init__(self, whitelist_path: str | Path | None = None) -> None:
        path = Path(whitelist_path) if whitelist_path else _PHYSIQUE_DIR / "efl_whitelist_v1_0_3.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self._exercises: list[dict] = [_normalize(ex) for ex in data["exercises"]]
        self._index: dict[str, dict] = {ex["canonical_id"]: ex for ex in self._exercises}

    def list_exercises(self, filters: dict | None = None) -> list[dict]:
        """Return exercises matching all provided filters.

        Supported filter keys:
          h_node          — exact match on h_node field
          day_role        — membership check: day_role must be in exercise's day_roles list
          movement_family — exact match on movement_family field
          node_max        — exercises where node_max >= value (can operate at that node)
          band_max        — exercises where band_max >= value (can use at least that band)
          volume_class    — case-insensitive exact match
          equipment       — case-insensitive substring match against exercise.equipment
        """
        result = list(self._exercises)
        if not filters:
            return result
        if h_node := filters.get("h_node"):
            result = [ex for ex in result if ex.get("h_node") == h_node]
        if day_role := filters.get("day_role"):
            result = [ex for ex in result if day_role in ex["day_roles"]]
        if movement_family := filters.get("movement_family"):
            result = [ex for ex in result if ex.get("movement_family") == movement_family]
        if (node_max := filters.get("node_max")) is not None:
            result = [ex for ex in result if ex.get("node_max", 0) >= node_max]
        if (band_max := filters.get("band_max")) is not None:
            result = [ex for ex in result if ex.get("band_max", 0) >= band_max]
        if volume_class := filters.get("volume_class"):
            result = [ex for ex in result if (ex.get("volume_class") or "").lower() == volume_class.lower()]
        if equipment := filters.get("equipment"):
            result = [ex for ex in result if equipment.lower() in (ex.get("equipment") or "").lower()]
        return result

    def get_exercise(self, canonical_id: str) -> dict | None:
        """Return normalized exercise by canonical_id, or None if not found."""
        return self._index.get(canonical_id)

    def check_exercise(self, payload: dict) -> dict:
        """Stateless per-exercise validation.

        No KDO issued, no operational store reads, no audit commit.

        Required payload key: canonical_id
        Optional payload keys: band_count, node, day_role, tempo, set_count

        Returns: {exercise, violations, sfi_contribution}
          violations: list of {code, detail}
          sfi_contribution: float (informational; uses requested node + exercise attributes)
        """
        canonical_id = payload["canonical_id"]
        ex = self.get_exercise(canonical_id)

        if ex is None:
            return {
                "exercise": None,
                "violations": [
                    {"code": "EXERCISE_NOT_FOUND", "detail": f"No exercise with id {canonical_id!r}"}
                ],
                "sfi_contribution": 0.0,
            }

        violations: list[dict] = []

        # Band limit check
        band_count = payload.get("band_count")
        if band_count is not None and band_count > ex.get("band_max", 0):
            violations.append({
                "code": "BAND_LIMIT_EXCEEDED",
                "detail": f"band_count={band_count} exceeds band_max={ex['band_max']}",
            })

        # Node limit check
        node = payload.get("node")
        if node is not None and node > ex.get("node_max", 0):
            violations.append({
                "code": "NODE_LIMIT_EXCEEDED",
                "detail": f"node={node} exceeds node_max={ex['node_max']}",
            })

        # Day role check
        day_role = payload.get("day_role")
        if day_role is not None and day_role not in ex["day_roles"]:
            violations.append({
                "code": "DAY_ROLE_NOT_PERMITTED",
                "detail": f"day_role={day_role!r} not in permitted roles {ex['day_roles']}",
            })

        # Tempo check
        tempo_str = payload.get("tempo")
        if tempo_str is not None:
            parseable, parsed, x_invalid, c_explosive = _parse_tempo(tempo_str)
            if not parseable:
                violations.append({
                    "code": "TEMPO_PARSE_ERROR",
                    "detail": f"Cannot parse tempo {tempo_str!r}",
                })
            else:
                ecc = parsed["E"]
                ecc_max = ex.get("eccentric_max", 999)
                if ecc > ecc_max:
                    violations.append({
                        "code": "ECCENTRIC_TEMPO_VIOLATION",
                        "detail": f"E={ecc} exceeds eccentric_max={ecc_max}",
                    })
                ib = parsed["IB"]
                ib_max = ex.get("isometric_bottom_max", 999)
                if ib > ib_max:
                    violations.append({
                        "code": "ISOMETRIC_BOTTOM_VIOLATION",
                        "detail": f"IB={ib} exceeds isometric_bottom_max={ib_max}",
                    })
                it = parsed["IT"]
                it_max = ex.get("isometric_top_max", 999)
                if it > it_max:
                    violations.append({
                        "code": "ISOMETRIC_TOP_VIOLATION",
                        "detail": f"IT={it} exceeds isometric_top_max={it_max}",
                    })
                if c_explosive and not ex.get("explosive_concentric_allowed", False):
                    violations.append({
                        "code": "EXPLOSIVE_CONCENTRIC_NOT_PERMITTED",
                        "detail": "Explosive concentric (C=X) not permitted for this exercise",
                    })

        # SFI contribution (informational, based on requested node + exercise attributes)
        set_count = payload.get("set_count", 0)
        requested_node = node if node is not None else 0
        h_rank = _H_NODE_NUMERIC.get(ex.get("h_node", "H0"), 0)
        sfi_contribution = (
            (set_count * _SFI_FORMULA["node3_sets_weight"] if requested_node == 3 else 0.0)
            + (set_count * _SFI_FORMULA["unilateral_sets_weight"] if ex["unilateral"] else 0.0)
            + (_SFI_FORMULA["h3_archetype_weight"] if h_rank >= 3 else 0.0)
            + (_SFI_FORMULA["h4_archetype_weight"] if h_rank >= 4 else 0.0)
        )

        return {"exercise": ex, "violations": violations, "sfi_contribution": sfi_contribution}
