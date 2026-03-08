from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
from pathlib import Path

_PHYSIQUE_DIR = Path(__file__).resolve().parent.parent.parent / "Physique"
_WHITELIST = json.loads((_PHYSIQUE_DIR / "efl_whitelist_v1_0_4.json").read_text(encoding="utf-8"))
try:
    _TEMPO_GOV = json.loads(
        (_PHYSIQUE_DIR / "efl_tempo_governance_v1_1_2_ENFORCEMENT_CLEAN.json").read_text(encoding="utf-8")
    )
    _TEMPO_GOV_LOAD_ERROR = False
except Exception:
    _TEMPO_GOV = {}
    _TEMPO_GOV_LOAD_ERROR = True
_MANIFEST = json.loads(
    (_PHYSIQUE_DIR / "physique_runtime_manifest_v1_0.json").read_text(encoding="utf-8")
)

_ALIAS_TABLE_PATH = _PHYSIQUE_DIR / "physique_alias_table_v1_0.json"
try:
    _alias_raw = json.loads(_ALIAS_TABLE_PATH.read_text(encoding="utf-8"))
    _alias_check = copy.deepcopy(_alias_raw)
    _alias_check["documentHash"] = ""
    _alias_actual_hash = hashlib.sha256(
        json.dumps(_alias_check, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    if _alias_actual_hash != _alias_raw.get("documentHash", ""):
        raise RuntimeError("alias table hash mismatch")
    ALIAS_INDEX: dict[str, str] = _alias_raw.get("aliases", {})
    _ALIAS_TABLE_LOAD_ERROR = False
except Exception:
    ALIAS_INDEX = {}
    _ALIAS_TABLE_LOAD_ERROR = True

WHITELIST_INDEX: dict[str, dict] = {ex["canonical_id"]: ex for ex in _WHITELIST["exercises"]}
ECCENTRIC_MINIMUMS: dict[str, int] = _TEMPO_GOV["eccentric_minimum_rules"]["class_based_minimums"]
ADAPTER_VERSION: str = _MANIFEST["version"]
_WHITELIST_VERSION: str = _WHITELIST.get("version", "")
_TEMPO_GOV_VERSION: str = _TEMPO_GOV.get("version", "") if not _TEMPO_GOV_LOAD_ERROR else ""
DAY_ROLE_H_NODE_MAX: dict[str, int] = _TEMPO_GOV["day_role_cap_enforcement"]["day_role_h_node_max_values"]
TEMPO_GOV = _TEMPO_GOV

# Richer authoring labels → MCC enum domain. All other values pass through lowercased.
HORIZ_VERT_MAP: dict[str, str] = {"Incline": "horizontal"}


@dataclasses.dataclass
class PhysiqueAdapterResult:
    normalized_exercises: list[dict]
    halt_codes: list[str]
    adapter_version: str
    athlete_id: str = ""
    adapter_trace: dict = dataclasses.field(default_factory=dict)
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


def _classify_tempo_mode(movement_family: str, pattern_plane: str | None) -> str:
    """Classify tempo validation mode from movement family and pattern plane.

    Carry/Sled exercises use distance-based prescription → N/A_DISTANCE.
    Isometric exercises use duration-based prescription → N/A_DURATION.
    All other resistance exercises use rep-based ECICT → ECICT.
    """
    mf = movement_family.lower()
    if "carry" in mf:
        return "N/A_DISTANCE"
    if pattern_plane and pattern_plane.lower() == "isometric":
        return "N/A_DURATION"
    return "ECICT"


def _validate_input_shape(payload: dict) -> list[str]:
    """F2: Validate payload shape. Returns halt codes (empty = valid).

    physique_session absent or None → treated as empty session (valid).
    exercises absent or None → treated as empty list (valid).
    """
    physique_session = payload.get("physique_session")
    if physique_session is None:
        return []
    if not isinstance(physique_session, dict):
        return ["SCHEMA_VALIDATION_FAILED"]
    exercises = physique_session.get("exercises")
    if exercises is None:
        return []
    if not isinstance(exercises, list):
        return ["SCHEMA_VALIDATION_FAILED"]
    for ex in exercises:
        if not isinstance(ex, dict):
            return ["SCHEMA_VALIDATION_FAILED"]
        if not ex.get("exercise_id"):
            return ["INCOMPLETE_INPUT"]
    return []


def _verify_authority_versions(authority_versions: dict) -> list[str]:
    """F1: Validate-if-present (D1). Returns ["AUTHORITY_VERSION_MISMATCH"] on mismatch."""
    if not authority_versions:
        return []
    if "whitelist_version" in authority_versions:
        if authority_versions["whitelist_version"] != _WHITELIST_VERSION:
            return ["AUTHORITY_VERSION_MISMATCH"]
    if "tempo_gov_version" in authority_versions:
        if authority_versions["tempo_gov_version"] != _TEMPO_GOV_VERSION:
            return ["AUTHORITY_VERSION_MISMATCH"]
    return []


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
                    new_ex["_resolved_e4_requires_clearance"] = wl.get("e4_requires_clearance", False)
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
    athlete_id = (payload.get("evaluationContext") or {}).get("athleteID", "")

    # 3g — early-exit guards (F2, GAP-004, alias load, F1)
    shape_errors = _validate_input_shape(payload)
    if shape_errors:
        halt_codes = shape_errors
        return PhysiqueAdapterResult(
            normalized_exercises=[], halt_codes=halt_codes, adapter_version=ADAPTER_VERSION,
            athlete_id=athlete_id,
            adapter_trace={"adapter_version": ADAPTER_VERSION, "halt_reason": halt_codes},
        )

    if _TEMPO_GOV_LOAD_ERROR:
        halt_codes = ["DCC_TEMPO_GOVERNANCE_UNAVAILABLE"]
        return PhysiqueAdapterResult(
            normalized_exercises=[], halt_codes=halt_codes, adapter_version=ADAPTER_VERSION,
            athlete_id=athlete_id,
            adapter_trace={"adapter_version": ADAPTER_VERSION, "halt_reason": halt_codes},
        )

    if _ALIAS_TABLE_LOAD_ERROR:
        halt_codes = ["ADAPTER_LOAD_FAILURE"]
        return PhysiqueAdapterResult(
            normalized_exercises=[], halt_codes=halt_codes, adapter_version=ADAPTER_VERSION,
            athlete_id=athlete_id,
            adapter_trace={"adapter_version": ADAPTER_VERSION, "halt_reason": halt_codes},
        )

    version_errors = _verify_authority_versions(payload.get("authority_versions") or {})
    if version_errors:
        halt_codes = version_errors
        return PhysiqueAdapterResult(
            normalized_exercises=[], halt_codes=halt_codes, adapter_version=ADAPTER_VERSION,
            athlete_id=athlete_id,
            adapter_trace={"adapter_version": ADAPTER_VERSION, "halt_reason": halt_codes},
        )

    physique_session = payload.get("physique_session") or {}
    raw_day_slots = payload.get("day_slots", [])
    context = payload.get("context", {})

    exercises = physique_session.get("exercises", [])
    normalized: list[dict] = []

    # 3i — trace lists
    _trace_resolved_via_alias: list[str] = []
    _trace_horiz_vert_events: list[dict] = []
    _trace_tempo_modes: list[dict] = []
    _trace_e4_flagged: list[str] = []

    for ex_input in exercises:
        exercise_id = ex_input.get("exercise_id", "")
        wl_entry = WHITELIST_INDEX.get(exercise_id)
        # 3h — alias resolution after WHITELIST_INDEX miss
        if wl_entry is None:
            canonical_id = ALIAS_INDEX.get(exercise_id)
            if canonical_id:
                wl_entry = WHITELIST_INDEX.get(canonical_id)
                if wl_entry is not None:
                    _trace_resolved_via_alias.append(exercise_id)
                    exercise_id = canonical_id
        if wl_entry is None:
            halt_codes = ["UNKNOWN_EXERCISE_ID"]
            return PhysiqueAdapterResult(
                normalized_exercises=[],
                halt_codes=halt_codes,
                adapter_version=ADAPTER_VERSION,
                athlete_id=athlete_id,
                adapter_trace={"adapter_version": ADAPTER_VERSION, "halt_reason": halt_codes},
                context=context,
                day_slots=raw_day_slots,
                resolved_slot_exercises=[],
            )

        # horiz_vert normalization (F5 fix: unknown labels halt instead of lowercasing)
        horiz_vert_raw = wl_entry.get("horiz_vert")
        if horiz_vert_raw is None:
            horiz_vert_normalized = None
        elif horiz_vert_raw in HORIZ_VERT_MAP:
            horiz_vert_normalized = HORIZ_VERT_MAP[horiz_vert_raw]
            _trace_horiz_vert_events.append({"exercise_id": exercise_id, "raw": horiz_vert_raw, "normalized": horiz_vert_normalized})
        elif horiz_vert_raw in ("horizontal", "vertical", "sagittal", "frontal"):
            horiz_vert_normalized = horiz_vert_raw
        else:
            halt_codes = ["UNKNOWN_HORIZ_VERT_LABEL"]
            return PhysiqueAdapterResult(
                normalized_exercises=[],
                halt_codes=halt_codes,
                adapter_version=ADAPTER_VERSION,
                athlete_id=athlete_id,
                adapter_trace={"adapter_version": ADAPTER_VERSION, "halt_reason": halt_codes},
                context=context,
                day_slots=raw_day_slots,
                resolved_slot_exercises=[],
            )

        movement_family = wl_entry.get("movement_family", "")
        pattern_plane = wl_entry.get("pattern_plane")
        tempo_mode = _classify_tempo_mode(movement_family, pattern_plane)
        _trace_tempo_modes.append({"exercise_id": exercise_id, "tempo_mode": tempo_mode})

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
            "h_node_base": wl_entry.get("h_node"),
            "push_pull": wl_entry.get("push_pull"),
            "e4_requires_clearance": wl_entry.get("e4_requires_clearance", False),
            "day_role_allowed": wl_entry.get("day_role_allowed"),
        })
        if wl_entry.get("e4_requires_clearance", False):
            _trace_e4_flagged.append(exercise_id)

    # Normalize day_slots: apply horiz_vert mapping; unknown labels halt (F5 fix).
    normalized_slots: list[dict] = []
    for slot in raw_day_slots:
        norm_slot = dict(slot)
        norm_exs = []
        for ex in slot.get("exercises", []):
            norm_ex = dict(ex)
            raw_hv = ex.get("horiz_vert")
            if raw_hv is not None:
                if raw_hv in HORIZ_VERT_MAP:
                    norm_ex["horiz_vert"] = HORIZ_VERT_MAP[raw_hv]
                elif raw_hv in ("horizontal", "vertical", "sagittal", "frontal"):
                    norm_ex["horiz_vert"] = raw_hv
                else:
                    halt_codes = ["UNKNOWN_HORIZ_VERT_LABEL"]
                    return PhysiqueAdapterResult(
                        normalized_exercises=[],
                        halt_codes=halt_codes,
                        adapter_version=ADAPTER_VERSION,
                        athlete_id=athlete_id,
                        adapter_trace={"adapter_version": ADAPTER_VERSION, "halt_reason": halt_codes},
                        context=context,
                        day_slots=raw_day_slots,
                        resolved_slot_exercises=[],
                    )
            norm_exs.append(norm_ex)
        norm_slot["exercises"] = norm_exs
        normalized_slots.append(norm_slot)

    resolved_slots = _resolve_slot_exercises(normalized_slots, WHITELIST_INDEX)
    return PhysiqueAdapterResult(
        normalized_exercises=normalized,
        halt_codes=[],
        adapter_version=ADAPTER_VERSION,
        athlete_id=athlete_id,
        adapter_trace={
            "adapter_version": ADAPTER_VERSION,
            "whitelist_version": _WHITELIST_VERSION,
            "tempo_gov_version": _TEMPO_GOV_VERSION,
            "exercises_normalized": len(normalized),
            "alias_resolutions": _trace_resolved_via_alias,
            "horiz_vert_mappings": _trace_horiz_vert_events,
            "tempo_mode_assignments": _trace_tempo_modes,
            "e4_injections_true": _trace_e4_flagged,
        },
        context=context,
        day_slots=normalized_slots,
        resolved_slot_exercises=resolved_slots,
    )
