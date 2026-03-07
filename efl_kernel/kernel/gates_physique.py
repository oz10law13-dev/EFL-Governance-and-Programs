from __future__ import annotations

from collections import Counter
from datetime import date as _date

from .physique_adapter import (
    ECCENTRIC_MINIMUMS,
    DAY_ROLE_H_NODE_MAX,
    TEMPO_GOV,
    WHITELIST_INDEX,
    _parse_tempo,
    run_physique_adapter,
)
from .ral import KERNEL_SYNTHETIC_VIOLATIONS
from .registry import PHYSIQUE_SPEC

# H-node numeric rank (H4 is not in governance doc but defined here for completeness)
H_NODE_NUMERIC: dict[str, int] = {"H0": 0, "H1": 1, "H2": 2, "H3": 3, "H4": 4}

_SFI_THRESHOLDS = PHYSIQUE_SPEC["sfiThresholds"]
_SFI_FORMULA = PHYSIQUE_SPEC["sfiFormula"]


def _syn(code: str) -> dict:
    """Build a synthetic violation dict matching _syn_violation output in KernelRunner."""
    spec = KERNEL_SYNTHETIC_VIOLATIONS[code]
    return {
        "code": code,
        "moduleID": "PHYSIQUE",
        "severity": spec["severity"],
        "overridePossible": spec["overridePossible"],
        "overrideUsed": False,
        "allowedOverrideReasonCodes": [],
        "violationCap": None,
        "reviewOverrideThreshold28D": None,
        "clampAction": None,
        "publishStatePostClamp": None,
        "publishStatePostWarning": None,
    }


def _v(code: str, exercise_id: str) -> dict:
    """Build a gate violation dict in the shape expected by enforce_kernel_owned_fields."""
    return {"code": code, "moduleID": "PHYSIQUE", "overrideUsed": False, "exercise_id": exercise_id}


def _mcc_v(code: str) -> dict:
    """Build an MCC violation dict."""
    return {"code": code, "moduleID": "PHYSIQUE", "overrideUsed": False}


def _tempo_modifier(E: int, IB: int, IT: int) -> int:
    """Compute tempo h-node modifier from E and ISO_total (IB+IT)."""
    ISO = IB + IT
    if E <= 1:
        return -1
    if E in (2, 3):
        return 0 if ISO <= 2 else 1
    if E == 4:
        return 1 if ISO <= 2 else 2
    return 2  # E >= 5


def _h_effective(base_h_str: str, E: int, IB: int, IT: int) -> int:
    """Compute effective h-node numeric rank from base h-node string and tempo values."""
    base = H_NODE_NUMERIC.get(base_h_str, 0)
    return base + _tempo_modifier(E, IB, IT)


def _compute_sfi(slot: dict) -> float:
    """Compute Structural Fatigue Index for a single slot's WORK exercises."""
    node3_sets = 0
    unilateral_sets = 0
    h3_families: set[str] = set()
    h4_families: set[str] = set()
    for ex in slot.get("exercises", []):
        if ex.get("role") != "WORK":
            continue
        sc = ex.get("set_count", 0)
        if ex.get("node", 0) == 3:
            node3_sets += sc
        if ex.get("unilateral", False):
            unilateral_sets += sc
        h_rank = H_NODE_NUMERIC.get(ex.get("h_node", "H0"), 0)
        mf = ex.get("movement_family", "")
        if h_rank >= 3:
            h3_families.add(mf)
        if h_rank >= 4:
            h4_families.add(mf)
    return (
        node3_sets * _SFI_FORMULA["node3_sets_weight"]
        + unilateral_sets * _SFI_FORMULA["unilateral_sets_weight"]
        + len(h3_families) * _SFI_FORMULA["h3_archetype_weight"]
        + len(h4_families) * _SFI_FORMULA["h4_archetype_weight"]
    )


def run_physique_dcc_gates(adapter_result, dep_provider) -> list[dict]:
    """Implement all 7 DCC tempo violation codes (Pass 1A + 1B, LAW mode).

    These checks are stateless — all ceiling and minimum values are sourced from
    the whitelist and tempo governance artifacts injected by the pre-pass adapter.
    No dependency provider access is required.
    """
    violations: list[dict] = []

    for ex in adapter_result.normalized_exercises:
        eid = ex["exercise_id"]

        # Carry/Sled exercises are distance-based — skip all ECICT tempo validation.
        if ex["tempo_mode"] != "ECICT":
            continue

        # DCC_TEMPO_FORMAT_INVALID — tempo string could not be parsed as E:IB:IT:C
        if not ex["tempo_parseable"]:
            violations.append(_v("DCC_TEMPO_FORMAT_INVALID", eid))
            continue  # remaining tempo checks require parsed values

        parsed = ex["tempo_parsed"]
        E = parsed["E"]
        IB = parsed["IB"]
        IT = parsed["IT"]

        # DCC_TEMPO_X_IN_INVALID_POSITION — X appeared in E, IB, or IT position
        if ex["x_in_invalid_position"]:
            violations.append(_v("DCC_TEMPO_X_IN_INVALID_POSITION", eid))

        # DCC_TEMPO_EXPLOSIVE_NOT_ALLOWED_FOR_EXERCISE — C=X but exercise disallows it
        if ex["c_explosive"] and not ex["explosive_concentric_allowed"]:
            violations.append(_v("DCC_TEMPO_EXPLOSIVE_NOT_ALLOWED_FOR_EXERCISE", eid))

        # DCC_TEMPO_E_BELOW_MINIMUM — E below class-based eccentric minimum
        tempo_class = ex.get("tempo_class") or ""
        minimum = ECCENTRIC_MINIMUMS.get(tempo_class, 0)
        if E < minimum:
            violations.append(_v("DCC_TEMPO_E_BELOW_MINIMUM", eid))

        # DCC_TEMPO_E_EXCEEDS_CEILING — E above exercise eccentric_max
        eccentric_max = ex.get("eccentric_max")
        if eccentric_max is not None and E > eccentric_max:
            violations.append(_v("DCC_TEMPO_E_EXCEEDS_CEILING", eid))

        # DCC_TEMPO_IB_EXCEEDS_CEILING — IB above isometric_bottom_max
        ib_max = ex.get("isometric_bottom_max")
        if ib_max is not None and IB > ib_max:
            violations.append(_v("DCC_TEMPO_IB_EXCEEDS_CEILING", eid))

        # DCC_TEMPO_IT_EXCEEDS_CEILING — IT above isometric_top_max
        it_max = ex.get("isometric_top_max")
        if it_max is not None and IT > it_max:
            violations.append(_v("DCC_TEMPO_IT_EXCEEDS_CEILING", eid))

    return violations


def run_physique_mcc_gates(
    context: dict,
    day_slots: list[dict],
    dep_provider,
    whitelist: dict,
    tempo_gov: dict | None,
) -> list[dict]:
    """Implement 36 MCC gate codes for Phase 19A.

    Gates are organized in clusters A–P. Five codes are deferred:
    MCC_CHRONIC_YELLOW_GUARD_TRIGGERED, MCC_COLLAPSE_ESCALATION_TRIGGERED (Phase 19C),
    MCC_SFI_ELEVATED_WARNING, MCC_SFI_EXCESSIVE_WARNING (Phase 19D),
    MCC_PRIMEREPETITIONWARNING (future phase).
    """
    violations: list[dict] = []

    if not day_slots:
        return violations

    # ─── Local helpers ─────────────────────────────────────────────────────────
    def work(slot: dict) -> list[dict]:
        return [ex for ex in slot.get("exercises", []) if ex.get("role") == "WORK"]

    def has_node3_work(slot: dict) -> bool:
        return any(ex.get("node", 0) == 3 for ex in work(slot))

    def max_band_work(slot: dict) -> int:
        return max((ex.get("band", 0) for ex in work(slot)), default=0)

    # Pre-scan: emit MCC_ECA_SLOT_UNRESOLVABLE once per unresolvable slot exercise
    _unresolvable_seen: set[int] = set()
    for _slot in day_slots:
        for _ex in _slot.get("exercises", []):
            if _ex.get("_resolution_error"):
                _ex_key = id(_ex)
                if _ex_key not in _unresolvable_seen:
                    violations.append(_mcc_v("MCC_ECA_SLOT_UNRESOLVABLE"))
                    _unresolvable_seen.add(_ex_key)

    # ─── Derived counts ────────────────────────────────────────────────────────
    freq = context.get("frequency_per_week", 0)
    day_a_count = sum(1 for s in day_slots if s.get("day_role") == "DAY_A")
    day_b_count = sum(1 for s in day_slots if s.get("day_role") == "DAY_B")
    day_d_count = sum(1 for s in day_slots if s.get("day_role") == "DAY_D")

    # ─── A: Frequency / Day counts ─────────────────────────────────────────────
    # A1: FREQUENCY_NOT_SUPPORTED
    if freq not in {3, 4, 5, 6}:
        violations.append(_mcc_v("MCC_FREQUENCY_NOT_SUPPORTED"))

    # A2: DAY_A_FREQUENCY_EXCEEDED
    if day_a_count > 3:
        violations.append(_mcc_v("MCC_DAY_A_FREQUENCY_EXCEEDED"))

    # A3: DAY_B_FREQUENCY_EXCEEDED
    if day_b_count > 3:
        violations.append(_mcc_v("MCC_DAY_B_FREQUENCY_EXCEEDED"))

    # A4: D_MINIMUM_VIOLATED (≥1 DAY_D at 5×, ≥2 at 6×)
    d_min = 1 if freq == 5 else (2 if freq >= 6 else 0)
    if d_min > 0 and day_d_count < d_min:
        violations.append(_mcc_v("MCC_D_MINIMUM_VIOLATED"))

    # ─── B: Day Intent ─────────────────────────────────────────────────────────
    # B1: DAY_A_PATTERN_GUARANTEE_VIOLATED (≥1 DAY_A required)
    if day_a_count < 1:
        violations.append(_mcc_v("MCC_DAY_A_PATTERN_GUARANTEE_VIOLATED"))

    # B2: DAY_D_INTENT_VIOLATION — DAY_D slot must only contain low-stress WORK
    day_d_violated = False
    for slot in day_slots:
        if slot.get("day_role") != "DAY_D":
            continue
        for ex in work(slot):
            if ex.get("_resolution_error"):
                continue
            h_node_str = ex.get("_resolved_h_node")
            if h_node_str is None:
                continue  # Non-ECA slot exercise: skip B2 h_node check
            h_rank = H_NODE_NUMERIC.get(h_node_str, 0)
            eid = ex.get("exercise_id", "")
            wl = whitelist.get(eid)
            band = ex.get("band", 0)
            if wl is not None:
                allowed = [r.strip() for r in wl.get("day_role_allowed", "").split(",")]
                if "D" not in allowed or h_rank > 1 or band > 1:
                    day_d_violated = True
                    break
            else:
                # Unknown exercise in DAY_D — intent cannot be verified
                day_d_violated = True
                break
        if day_d_violated:
            break
    if day_d_violated:
        violations.append(_mcc_v("MCC_DAY_D_INTENT_VIOLATION"))

    # B3: DAY_C_PATTERN_REPETITION — ≥2 DAY_C slots with same c_day_focus in one week
    if freq >= 4:
        c_focuses = [
            s.get("c_day_focus")
            for s in day_slots
            if s.get("day_role") == "DAY_C" and s.get("c_day_focus")
        ]
        if any(v >= 2 for v in Counter(c_focuses).values()):
            violations.append(_mcc_v("MCC_DAY_C_PATTERN_REPETITION"))

    # ─── C: Adjacency ─────────────────────────────────────────────────────────
    # C1: ADJACENCY_VIOLATION — forbidden B→B, A(BAND3)→B, B→C(NODE3)
    for i in range(len(day_slots) - 1):
        a_slot = day_slots[i]
        b_slot = day_slots[i + 1]
        ra = a_slot.get("day_role")
        rb = b_slot.get("day_role")
        if (
            (ra == "DAY_B" and rb == "DAY_B")
            or (ra == "DAY_A" and rb == "DAY_B" and max_band_work(a_slot) >= 3)
            or (ra == "DAY_B" and rb == "DAY_C" and has_node3_work(b_slot))
        ):
            violations.append(_mcc_v("MCC_ADJACENCY_VIOLATION"))
            break

    # C2: CONSECUTIVE_NODE3_EXCEEDED — ≥3 consecutive slots with NODE3 WORK
    consecutive_n3 = 0
    for slot in day_slots:
        if has_node3_work(slot):
            consecutive_n3 += 1
            if consecutive_n3 >= 3:
                violations.append(_mcc_v("MCC_CONSECUTIVE_NODE3_EXCEEDED"))
                break
        else:
            consecutive_n3 = 0

    # ─── D: NODE Permission / Density ─────────────────────────────────────────
    d1_fired = False
    band2_node3_sets = 0
    total_node3_sets = 0

    for slot in day_slots:
        for ex in work(slot):
            node = ex.get("node", 0)
            band = ex.get("band", 0)
            set_count = ex.get("set_count", 0)

            if ex.get("_resolution_error"):
                continue

            # D1: NODE_PERMISSION_VIOLATION — node==3 but node_max < 3
            node_max_ex = ex.get("_resolved_node_max")
            if node_max_ex is not None:
                if node == 3 and node_max_ex < 3:
                    if not d1_fired:
                        violations.append(_mcc_v("MCC_NODE_PERMISSION_VIOLATION"))
                        d1_fired = True

            # D3: BAND_NODE_ILLEGAL_COMBINATION — band==3 AND node==3 simultaneously
            if band == 3 and node == 3:
                violations.append(_mcc_v("MCC_BAND_NODE_ILLEGAL_COMBINATION"))

            # Accumulate for D2
            if node == 3:
                total_node3_sets += set_count
                if band >= 2:
                    band2_node3_sets += set_count

    # D2: DENSITY_LEDGER_EXCEEDED — only if D1 didn't fire (D1 blocks D2)
    if not d1_fired:
        if band2_node3_sets > 20 or total_node3_sets > 40:
            violations.append(_mcc_v("MCC_DENSITY_LEDGER_EXCEEDED"))

    # ─── E: H-Node caps ────────────────────────────────────────────────────────
    h3_slot_count = 0
    h4_slot_count = 0
    h3_agg_fired = False

    for slot in day_slots:
        work_exs = work(slot)
        h3_families: set[str] = set()
        has_h3 = False
        has_h4 = False

        for ex in work_exs:
            h_rank = H_NODE_NUMERIC.get(ex.get("h_node", "H0"), 0)
            if h_rank >= 3:
                has_h3 = True
                h3_families.add(ex.get("movement_family", ""))
            if h_rank >= 4:
                has_h4 = True

        if has_h3:
            h3_slot_count += 1
            # E1 (per-slot): >2 distinct H3 movement_families in one slot
            if len(h3_families) > 2 and not h3_agg_fired:
                violations.append(_mcc_v("MCC_H3_AGGREGATE_EXCEEDED"))
                h3_agg_fired = True

        if has_h4:
            h4_slot_count += 1

    # E1 (weekly): >3 slots containing H3 WORK
    if h3_slot_count > 3 and not h3_agg_fired:
        violations.append(_mcc_v("MCC_H3_AGGREGATE_EXCEEDED"))

    # E2: H4_FREQUENCY_EXCEEDED — >1 slot with H4 WORK
    if h4_slot_count > 1:
        violations.append(_mcc_v("MCC_H4_FREQUENCY_EXCEEDED"))

    # ─── F: Pattern Balance ────────────────────────────────────────────────────
    push_sets = pull_sets = horiz_sets = vert_sets = frontal_sets = total_sets = 0

    for slot in day_slots:
        for ex in work(slot):
            sc = ex.get("set_count", 0)
            total_sets += sc
            pp = ex.get("push_pull")
            hv = ex.get("horiz_vert")
            mf = (ex.get("movement_family") or "").lower()
            if pp == "push":
                push_sets += sc
            elif pp == "pull":
                pull_sets += sc
            if hv == "horizontal":
                horiz_sets += sc
            elif hv == "vertical":
                vert_sets += sc
            if "frontal" in mf:
                frontal_sets += sc

    # F1: PATTERN_BALANCE_VIOLATED
    if total_sets > 0:
        def _pct(n: int) -> float:
            return n / total_sets

        balance_violated = (
            _pct(push_sets) < 0.40
            or _pct(pull_sets) < 0.40
            or _pct(horiz_sets) < 0.35
            or _pct(vert_sets) < 0.35
            or (freq >= 5 and _pct(frontal_sets) < 0.20)
        )
        if balance_violated:
            violations.append(_mcc_v("MCC_PATTERN_BALANCE_VIOLATED"))

    # F2: BAND3_PATTERN_EXCEEDED — per slot, >1 distinct movement_family at band==3
    for slot in day_slots:
        b3_families = {
            ex.get("movement_family")
            for ex in work(slot)
            if ex.get("band", 0) == 3
        }
        if len(b3_families) > 1:
            violations.append(_mcc_v("MCC_BAND3_PATTERN_EXCEEDED"))
            break

    # ─── G: Volume ─────────────────────────────────────────────────────────────
    # G1: SESSION_VOLUME_EXCEEDED — any slot WORK total > 25 sets
    for slot in day_slots:
        if sum(ex.get("set_count", 0) for ex in work(slot)) > 25:
            violations.append(_mcc_v("MCC_SESSION_VOLUME_EXCEEDED"))
            break

    # G2: VOLUME_CLASS_OVERRIDE_ATTEMPT — prescribed volume_class ≠ whitelist value
    seen_vc_viol: set[str] = set()
    for slot in day_slots:
        for ex in slot.get("exercises", []):
            eid = ex.get("exercise_id", "")
            if eid in seen_vc_viol:
                continue
            wl = whitelist.get(eid)
            if wl is None:
                continue
            wl_vc = wl.get("volume_class")
            if wl_vc is None:
                continue
            ex_vc = ex.get("volume_class")
            if ex_vc is not None and ex_vc != wl_vc:
                violations.append(_mcc_v("MCC_VOLUME_CLASS_OVERRIDE_ATTEMPT"))
                seen_vc_viol.add(eid)

    # ─── H: ECA Coverage ───────────────────────────────────────────────────────
    seen_missing: set[str] = set()
    seen_incomplete: set[str] = set()

    for slot in day_slots:
        for ex in slot.get("exercises", []):
            eid = ex.get("exercise_id", "")
            wl = whitelist.get(eid)
            if wl is None:
                # H1: ECA_COVERAGE_MISSING — exercise not in whitelist
                if eid not in seen_missing:
                    violations.append(_mcc_v("MCC_ECA_COVERAGE_MISSING"))
                    seen_missing.add(eid)
            else:
                # H2: ECA_PATTERN_INCOMPLETE — whitelist entry missing movement_family
                if wl.get("movement_family") is None and eid not in seen_incomplete:
                    violations.append(_mcc_v("MCC_ECA_PATTERN_INCOMPLETE"))
                    seen_incomplete.add(eid)

    # ─── I: Session Structure ──────────────────────────────────────────────────
    # I1: SESSION_DURATION_EXCEEDED — PRIME+PREP+WORK+CLEAR > 60 min
    for slot in day_slots:
        blocks = slot.get("session_blocks", {})
        total_min = sum(
            blocks.get(k, 0) for k in ("PRIME_min", "PREP_min", "WORK_min", "CLEAR_min")
        )
        if total_min > 60:
            violations.append(_mcc_v("MCC_SESSION_DURATION_EXCEEDED"))
            break

    # I2: WORK_BLOCK_INSUFFICIENT — WORK_min < 24
    for slot in day_slots:
        if slot.get("session_blocks", {}).get("WORK_min", 0) < 24:
            violations.append(_mcc_v("MCC_WORK_BLOCK_INSUFFICIENT"))
            break

    # I3: PRIME_SCOPE_VIOLATION — PRIME-role exercise with band>1 or h_node rank>1
    prime_viol_fired = False
    for slot in day_slots:
        for ex in slot.get("exercises", []):
            if ex.get("role") != "PRIME":
                continue
            h_rank = H_NODE_NUMERIC.get(ex.get("h_node", "H0"), 0)
            if ex.get("band", 0) > 1 or h_rank > 1:
                violations.append(_mcc_v("MCC_PRIME_SCOPE_VIOLATION"))
                prime_viol_fired = True
                break
        if prime_viol_fired:
            break

    # ─── J: Progression ────────────────────────────────────────────────────────
    # J1: MULTI_AXIS_PROGRESSION_VIOLATION — single exercise has >1 non-"none" axis
    j1_fired = False
    for slot in day_slots:
        for ex in slot.get("exercises", []):
            pa = ex.get("progression_axis")
            if isinstance(pa, list):
                if sum(1 for a in pa if a != "none") > 1:
                    violations.append(_mcc_v("MCC_MULTI_AXIS_PROGRESSION_VIOLATION"))
                    j1_fired = True
                    break
        if j1_fired:
            break

    # J2: FAMILY_MULTI_AXIS_VIOLATION — same movement_family with >1 distinct non-"none" axis
    family_axes: dict[str, set[str]] = {}
    for slot in day_slots:
        for ex in work(slot):
            mf = ex.get("movement_family", "")
            pa = ex.get("progression_axis")
            if pa is None:
                continue
            axes = [pa] if isinstance(pa, str) else pa
            for a in axes:
                if a != "none":
                    family_axes.setdefault(mf, set()).add(a)
    if any(len(axes) > 1 for axes in family_axes.values()):
        violations.append(_mcc_v("MCC_FAMILY_MULTI_AXIS_VIOLATION"))

    # ─── K: Route / C-Day History ──────────────────────────────────────────────
    # K1: ROUTE_SATURATION_VIOLATION — last 2 DAY_A route_history entries both MAX_STRENGTH_EXPRESSION
    route_history = context.get("route_history", [])
    day_a_hist = [r for r in route_history if r.get("day_role") == "DAY_A"]
    if len(day_a_hist) >= 2 and all(
        r.get("primary_route") == "MAX_STRENGTH_EXPRESSION" for r in day_a_hist[-2:]
    ):
        violations.append(_mcc_v("MCC_ROUTE_SATURATION_VIOLATION"))

    # K2: C_DAY_MESO_ROTATION_VIOLATION — same c_focus for >2 consecutive weeks
    c_history = context.get("c_day_focus_history", [])
    if len(c_history) >= 3:
        consecutive_c = 1
        for i in range(len(c_history) - 1, 0, -1):
            if c_history[i].get("c_focus") == c_history[i - 1].get("c_focus"):
                consecutive_c += 1
                if consecutive_c > 2:
                    violations.append(_mcc_v("MCC_C_DAY_MESO_ROTATION_VIOLATION"))
                    break
            else:
                break

    # ─── L: Readiness (slot-level) ─────────────────────────────────────────────
    # L1: READINESS_VIOLATION — RED slot with any WORK exercise band≥2
    for slot in day_slots:
        if slot.get("readiness_state") == "RED":
            if any(ex.get("band", 0) >= 2 for ex in work(slot)):
                violations.append(_mcc_v("MCC_READINESS_VIOLATION"))
                break

    # L2: READINESS_BAND_MISMATCH — YELLOW slot with any WORK exercise band==3
    for slot in day_slots:
        if slot.get("readiness_state") == "YELLOW":
            if any(ex.get("band", 0) == 3 for ex in work(slot)):
                violations.append(_mcc_v("MCC_READINESS_BAND_MISMATCH"))
                break

    # ─── L3/L4: Chronic Readiness History ──────────────────────────────────────
    # L3: CHRONIC_YELLOW_GUARD_TRIGGERED — payload-first, provider fallback
    yellow_count = context.get("chronic_yellow_count")
    if yellow_count is None and dep_provider is not None:
        _athlete_id = context.get("athlete_id")
        _anchor_raw = context.get("anchor_date")
        if _athlete_id and _anchor_raw:
            _anchor = _date.fromisoformat(str(_anchor_raw))
            _history = dep_provider.get_readiness_history(_athlete_id, _anchor)
            yellow_count = sum(1 for s in _history if s == "YELLOW")
    if yellow_count is not None and yellow_count >= 3:
        violations.append(_mcc_v("MCC_CHRONIC_YELLOW_GUARD_TRIGGERED"))

    # L4: COLLAPSE_ESCALATION_TRIGGERED — payload-first, provider fallback
    collapse_count = context.get("recent_collapse_count")
    if collapse_count is None and dep_provider is not None:
        _athlete_id = context.get("athlete_id")
        _anchor_raw = context.get("anchor_date")
        if _athlete_id and _anchor_raw:
            _anchor = _date.fromisoformat(str(_anchor_raw))
            collapse_count = dep_provider.get_collapse_count(_athlete_id, _anchor)
    if collapse_count is not None and collapse_count >= 1:
        violations.append(_mcc_v("MCC_COLLAPSE_ESCALATION_TRIGGERED"))

    # ─── M: SFI (Structural Fatigue Index) ──────────────────────────────────────
    # M1/M2 computed per slot; M2 takes priority over M1 (mutually exclusive per slot)
    m1_fired = m2_fired = False
    for slot in day_slots:
        sfi = _compute_sfi(slot)
        if sfi >= _SFI_THRESHOLDS["excessive"]:
            if not m2_fired:
                violations.append(_mcc_v("MCC_SFI_EXCESSIVE_WARNING"))
                m2_fired = True
        elif sfi >= _SFI_THRESHOLDS["elevated"]:
            if not m1_fired:
                violations.append(_mcc_v("MCC_SFI_ELEVATED_WARNING"))
                m1_fired = True
    # MCC_PRIMEREPETITIONWARNING — deferred: needs persistent PRIME history ledger (future phase)

    # ─── N: Tempo Governance ───────────────────────────────────────────────────
    if tempo_gov is not None:
        _run_n_cluster(violations, day_slots, whitelist)

    # ─── P: Long-Horizon Advisory ──────────────────────────────────────────────
    # P1: LONG_HORIZON_DELOAD_RECOMMENDED — week 4 without any DAY_D slot
    if context.get("current_week") == 4 and not any(
        s.get("day_role") == "DAY_D" for s in day_slots
    ):
        violations.append(_mcc_v("MCC_LONG_HORIZON_DELOAD_RECOMMENDED"))

    # P2: ROUTE_40PLUS_SAFETY_WARNING — 40+ population with MAX_STRENGTH_EXPRESSION + band3
    if context.get("population_overlay") == "adult_physique_40plus":
        for slot in day_slots:
            if slot.get("primary_route") == "MAX_STRENGTH_EXPRESSION":
                if any(ex.get("band", 0) == 3 for ex in work(slot)):
                    violations.append(_mcc_v("MCC_ROUTE_40PLUS_SAFETY_WARNING"))
                    break

    return violations


def _run_n_cluster(
    violations: list[dict],
    day_slots: list[dict],
    whitelist: dict,
) -> None:
    """Tempo Governance N-cluster gates (N1–N4).

    N1: MCC_TEMPO_DOWNGRADED_FOR_H_NODE_MAX — h_effective > day_role_max
    N2: MCC_TEMPO_ESCALATION_CLAMPED_TO_H3  — h_effective > 3, no escalation permission
    N3: MCC_TEMPO_DOWNGRADE_CHAIN_EXHAUSTED — downgrade chain exhausted
    N4: MCC_TEMPO_DOWNGRADE_REVALIDATION_FAILED — downgrade would violate E minimum
    """
    n1_fired = n2_fired = n3_fired = n4_fired = False

    for slot in day_slots:
        day_role = slot.get("day_role", "DAY_A")
        role_max = DAY_ROLE_H_NODE_MAX.get(day_role, 3)

        for ex in [e for e in slot.get("exercises", []) if e.get("role") == "WORK"]:
            if ex.get("_resolution_error"):
                continue
            base_h = ex.get("_resolved_h_node")
            if base_h is None:
                continue  # Non-ECA slot exercise: skip N-cluster check
            eid = ex.get("exercise_id", "")
            wl = whitelist.get(eid)
            if wl is None:
                continue

            tempo_str = ex.get("tempo", "")
            parseable, parsed, _, _ = _parse_tempo(tempo_str)
            if not parseable or parsed is None:
                continue

            E = parsed["E"]
            IB = parsed["IB"]
            IT = parsed["IT"]
            h_eff = _h_effective(base_h, E, IB, IT)
            tempo_can_escalate = wl.get("tempo_can_escalate_hnode", False)

            # N2: h_effective > 3 AND tempo_can_escalate=False → clamp to H3
            if h_eff > 3 and not tempo_can_escalate:
                if not n2_fired:
                    violations.append(_mcc_v("MCC_TEMPO_ESCALATION_CLAMPED_TO_H3"))
                    n2_fired = True
                h_eff = 3  # clamp for further checks

            # N1: h_effective > day_role_max → attempt downgrade
            if h_eff <= role_max:
                continue

            if not n1_fired:
                violations.append(_mcc_v("MCC_TEMPO_DOWNGRADED_FOR_H_NODE_MAX"))
                n1_fired = True

            # Run deterministic downgrade chain
            tempo_class = wl.get("tempo_class", "")
            eccentric_min = ECCENTRIC_MINIMUMS.get(tempo_class, 0)
            cur_E, cur_IB, cur_IT = E, IB, IT
            satisfied = False

            # Step 1: Reduce IT toward 0
            while cur_IT > 0 and not satisfied:
                cur_IT -= 1
                if _h_effective(base_h, cur_E, cur_IB, cur_IT) <= role_max:
                    satisfied = True

            # Step 2: Reduce IB toward 0
            if not satisfied:
                while cur_IB > 0 and not satisfied:
                    cur_IB -= 1
                    if _h_effective(base_h, cur_E, cur_IB, cur_IT) <= role_max:
                        satisfied = True

            # Step 3: Reduce E toward eccentric_min; fire N4 if E already at min
            if not satisfied:
                while not satisfied:
                    if cur_E <= eccentric_min:
                        # Cannot reduce E further without violating minimum
                        if not n4_fired:
                            violations.append(
                                _mcc_v("MCC_TEMPO_DOWNGRADE_REVALIDATION_FAILED")
                            )
                            n4_fired = True
                        break
                    cur_E -= 1
                    if _h_effective(base_h, cur_E, cur_IB, cur_IT) <= role_max:
                        satisfied = True

            # Step 4 (explosive) skipped — C=X does not affect h_node modifier

            # N3: chain exhausted if still not satisfied and N4 not fired
            if not satisfied and not n4_fired:
                if not n3_fired:
                    violations.append(_mcc_v("MCC_TEMPO_DOWNGRADE_CHAIN_EXHAUSTED"))
                    n3_fired = True


def _run_clearance_gate(raw_input: dict, dep_provider) -> list[dict]:
    """PHYSIQUE-GATE-GAP-001 closure.

    Emits PHYSIQUE.CLEARANCEMISSING (HARDFAIL, no override) for each exercise
    in physique_session.exercises that has e4_requires_clearance=True when the
    athlete profile does not carry e4_clearance=True.

    Fail-closed: absent e4_clearance in profile = False.
    Non-ECA exercises (no exercise_id) are skipped.
    Day-slot exercises not checked (Phase 9 decision).
    """
    violations = []
    athlete_id = (raw_input.get("evaluationContext") or {}).get("athleteID")
    if not athlete_id:
        return violations

    profile = dep_provider.get_athlete_profile(athlete_id) or {}
    has_clearance = bool(profile.get("e4_clearance", False))
    if has_clearance:
        return violations

    exercises = (raw_input.get("physique_session") or {}).get("exercises") or []
    seen_ids: set = set()
    for ex in exercises:
        if not isinstance(ex, dict):
            continue
        exercise_id = ex.get("exercise_id")
        if not exercise_id:
            continue
        if not ex.get("e4_requires_clearance", False):
            continue
        if exercise_id in seen_ids:
            continue
        seen_ids.add(exercise_id)
        violations.append({
            "code": "PHYSIQUE.CLEARANCEMISSING",
            "moduleID": "PHYSIQUE",
            "severity": "HARDFAIL",
            "overridePossible": False,
            "allowedOverrideReasonCodes": [],
            "violationCap": None,
            "reviewOverrideThreshold28D": None,
            "details": {
                "exercise_id": exercise_id,
                "athlete_id": athlete_id,
                "e4_clearance": False,
            },
        })
    return violations


def run_physique_gates(raw_input: dict, dep_provider) -> list[dict]:
    """Top-level PHYSIQUE gate function called by kernel Step 6 dispatch.

    Runs the clearance gate first (reads raw input + dep_provider directly),
    then the pre-pass adapter, then DCC and MCC gate layers in order.
    If the adapter halts, appends RAL.MISSINGORUNDEFINEDREQUIREDSTATE and
    returns without invoking any LAW-mode pass.
    """
    # Clearance gate — PHYSIQUE-GATE-GAP-001
    violations = list(_run_clearance_gate(raw_input, dep_provider))

    adapter_result = run_physique_adapter(raw_input)

    if adapter_result.halt_codes:
        violations.append(_syn("RAL.MISSINGORUNDEFINEDREQUIREDSTATE"))
        return violations

    violations += run_physique_dcc_gates(adapter_result, dep_provider)

    # O1: MCC_PASS2_MISSING_OR_FAILED — day_slots provided but context absent
    if adapter_result.day_slots and not adapter_result.context:
        violations.append(_mcc_v("MCC_PASS2_MISSING_OR_FAILED"))
    else:
        violations += run_physique_mcc_gates(
            adapter_result.context,
            adapter_result.resolved_slot_exercises,
            dep_provider,
            WHITELIST_INDEX,
            TEMPO_GOV,
        )

    return violations
