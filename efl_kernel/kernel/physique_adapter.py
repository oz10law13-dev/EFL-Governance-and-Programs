from __future__ import annotations

import dataclasses
import json
from pathlib import Path

_PHYSIQUE_DIR = Path(__file__).resolve().parent.parent.parent / "Physique"
_WHITELIST = json.loads((_PHYSIQUE_DIR / "efl_whitelist_v1_0_3.json").read_text(encoding="utf-8"))
_TEMPO_GOV = json.loads(
    (_PHYSIQUE_DIR / "efl_tempo_governance_v1_1_2_ENFORCEMENT_CLEAN.json").read_text(encoding="utf-8")
)
_MANIFEST = json.loads(
    (_PHYSIQUE_DIR / "physique_runtime_manifest_v1_0.json").read_text(encoding="utf-8")
)

WHITELIST_INDEX: dict[str, dict] = {ex["canonical_id"]: ex for ex in _WHITELIST["exercises"]}
ECCENTRIC_MINIMUMS: dict[str, int] = _TEMPO_GOV["eccentric_minimum_rules"]["class_based_minimums"]
ADAPTER_VERSION: str = _MANIFEST["version"]
DAY_ROLE_H_NODE_MAX: dict[str, int] = _TEMPO_GOV["day_role_cap_enforcement"]["day_role_h_node_max_values"]
TEMPO_GOV = _TEMPO_GOV

# Richer authoring labels → MCC enum domain. All other values pass through lowercased.
HORIZ_VERT_MAP: dict[str, str] = {"Incline": "horizontal"}


@dataclasses.dataclass
class PhysiqueAdapterResult:
    normalized_exercises: list[dict]
    halt_codes: list[str]
    adapter_version: str
    context: dict = dataclasses.field(default_factory=dict)
    day_slots: list[dict] = dataclasses.field(default_factory=list)
    resolved_slot_exercises: list[dict] = dataclasses.field(default_factory=list)


def _parse_tempo(tempo_str: str) -> tuple[bool, dict | None, bool, bool]:
    """Parse an ECICT tempo string.

    Returns (parseable, parsed_dict, x_in_invalid_position, c_explosive).
    parsed_dict keys: E, IB, IT, C (all int; C=0 when "X").
    """
    parts = tempo_str.strip().split(":")
    if len(parts) != 4:
        return False, None, False, False

    x_invalid = False
    c_explosive = False
    values: dict[str, int] = {}
    labels = ["E", "IB", "IT", "C"]

    for i, (label, part) in enumerate(zip(labels, parts)):
        part = part.strip()
        if part.upper() == "X":
            if label == "C":
                c_explosive = True
                values[label] = 0
            else:
                x_invalid = True
                values[label] = 0  # store 0 for downstream arithmetic even on invalid
        else:
            try:
                values[label] = int(part)
            except ValueError:
                return False, None, False, False

    return True, values, x_invalid, c_explosive


def _classify_tempo_mode(movement_family: str) -> str:
    """Classify tempo validation mode from movement family.

    Carry/Sled exercises use distance-based prescription → N/A_DISTANCE.
    All other resistance exercises use rep-based ECICT → ECICT.
    """
    if "carry" in movement_family.lower():
        return "N/A_DISTANCE"
    return "ECICT"


def _resolve_slot_exercises(day_slots: list[dict], whitelist_index: dict) -> list[dict]:
    """For each exercise in each day_slot, attempt whitelist resolution.

    Injects _resolved_node_max, _resolved_h_node, _resolved_volume_class,
    _resolved_movement_family from the whitelist (prefix _resolved_ makes the
    source unambiguous). If exercise_id or eca_id is present but not found in
    whitelist_index, marks the exercise with _resolution_error=True. If neither
    field is present, skips injection (non-ECA slot exercise).
    Returns a new list (shallow copy of slots, deep copy of exercise lists only).
    """
    result = []
    for slot in day_slots:
        new_slot = dict(slot)
        new_exs = []
        for ex in slot.get("exercises", []):
            new_ex = dict(ex)
            eid = ex.get("exercise_id") or ex.get("eca_id")
            if eid is not None:
                wl = whitelist_index.get(eid)
                if wl is None:
                    new_ex["_resolution_error"] = True
                else:
                    new_ex["_resolved_node_max"] = wl.get("node_max")
                    new_ex["_resolved_h_node"] = wl.get("h_node")
                    new_ex["_resolved_volume_class"] = wl.get("volume_class")
                    new_ex["_resolved_movement_family"] = wl.get("movement_family")
            new_exs.append(new_ex)
        new_slot["exercises"] = new_exs
        result.append(new_slot)
    return result


def run_physique_adapter(payload: dict) -> PhysiqueAdapterResult:
    """Normalize a physique payload for DCC/MCC gate evaluation.

    Accepts the full payload dict; extracts physique_session, day_slots, and context.
    Fail closed: if any exercise in physique_session cannot be resolved to the whitelist,
    halt immediately without partially normalizing the remaining exercises.
    """
    physique_session = payload.get("physique_session", {})
    raw_day_slots = payload.get("day_slots", [])
    context = payload.get("context", {})

    exercises = physique_session.get("exercises", [])
    normalized: list[dict] = []

    for ex_input in exercises:
        exercise_id = ex_input.get("exercise_id", "")
        wl_entry = WHITELIST_INDEX.get(exercise_id)
        if wl_entry is None:
            return PhysiqueAdapterResult(
                normalized_exercises=[],
                halt_codes=["UNKNOWN_EXERCISE_ID"],
                adapter_version=ADAPTER_VERSION,
                context=context,
                day_slots=raw_day_slots,
                resolved_slot_exercises=[],
            )

        # horiz_vert normalization
        horiz_vert_raw = wl_entry.get("horiz_vert")
        if horiz_vert_raw is None:
            horiz_vert_normalized = None
        else:
            horiz_vert_normalized = HORIZ_VERT_MAP.get(horiz_vert_raw, horiz_vert_raw.lower())

        movement_family = wl_entry.get("movement_family", "")
        tempo_mode = _classify_tempo_mode(movement_family)

        # Tempo parsing (record state; DCC gates fire violations, not adapter)
        tempo_str = ex_input.get("tempo", "")
        parseable, parsed, x_invalid, c_explosive = _parse_tempo(tempo_str)

        normalized.append({
            # Identity
            "exercise_id": exercise_id,
            "tempo_mode": tempo_mode,
            # horiz_vert
            "horiz_vert_raw": horiz_vert_raw,
            "horiz_vert_normalized": horiz_vert_normalized,
            "movement_family": movement_family,
            # Tempo parse state
            "tempo_parseable": parseable,
            "tempo_parsed": parsed,
            "x_in_invalid_position": x_invalid,
            "c_explosive": c_explosive,
            # Whitelist fields (injected from authority source, not from caller input)
            "tempo_class": wl_entry.get("tempo_class"),
            "eccentric_max": wl_entry.get("eccentric_max"),
            "isometric_bottom_max": wl_entry.get("isometric_bottom_max"),
            "isometric_top_max": wl_entry.get("isometric_top_max"),
            "explosive_concentric_allowed": wl_entry.get("explosive_concentric_allowed"),
            "tempo_can_escalate_hnode": wl_entry.get("tempo_can_escalate_hnode"),
            "band_max": wl_entry.get("band_max"),
            "node_max": wl_entry.get("node_max"),
            "h_node": wl_entry.get("h_node"),
            "day_role_allowed": wl_entry.get("day_role_allowed"),
        })

    # Normalize day_slots: apply HORIZ_VERT_MAP to each exercise's horiz_vert field.
    normalized_slots: list[dict] = []
    for slot in raw_day_slots:
        norm_slot = dict(slot)
        norm_exs = []
        for ex in slot.get("exercises", []):
            norm_ex = dict(ex)
            raw_hv = ex.get("horiz_vert")
            if raw_hv is not None:
                norm_ex["horiz_vert"] = HORIZ_VERT_MAP.get(raw_hv, raw_hv.lower())
            norm_exs.append(norm_ex)
        norm_slot["exercises"] = norm_exs
        normalized_slots.append(norm_slot)

    resolved_slots = _resolve_slot_exercises(normalized_slots, WHITELIST_INDEX)
    return PhysiqueAdapterResult(
        normalized_exercises=normalized,
        halt_codes=[],
        adapter_version=ADAPTER_VERSION,
        context=context,
        day_slots=normalized_slots,
        resolved_slot_exercises=resolved_slots,
    )
