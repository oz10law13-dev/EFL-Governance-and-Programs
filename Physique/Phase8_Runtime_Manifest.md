# Phase 8 Runtime Manifest — PHYSIQUE Module Registration

**Document ID:** EFL-PHYSIQUE-P8-MANIFEST-001
**Status:** BINDING
**Phase:** 8
**Date:** 2026-03-07
**Author:** EFL Kernel Engineering

---

## §1 Document Purpose

This document is the authoritative runtime manifest for the PHYSIQUE module as of Phase 8. It declares what is implemented, registered, and enforced at runtime — not what is intended or planned. All statements are sourced from the frozen spec files and kernel source code at commit time.

This document supersedes all prior PHYSIQUE runtime descriptions. Phase 7 binding decisions remain in force and are cross-referenced where relevant.

---

## §2 Phase 8 Change Summary

| Item | Before Phase 8 | After Phase 8 |
|---|---|---|
| RAL version | `1.3.0` | `1.4.0` |
| PHYSIQUE frozen spec | `EFL_PHYSIQUE_v1_0_1_frozen.json` (48 codes) | `EFL_PHYSIQUE_v1_0_2_frozen.json` (50 codes) |
| PHYSIQUE moduleVersion in RAL | `1.0.0` | `1.0.2` |
| `MCC_ECA_SLOT_UNRESOLVABLE` | Direct insertion in `registry.py` | Frozen spec (PHYSIQUE v1.0.2) |
| `PHYSIQUE.CLEARANCEMISSING` | Not defined anywhere | Frozen spec + gate enforced |
| PHYSIQUE-GATE-GAP-001 | OPEN | **CLOSED** |
| Direct insertions in `registry.py` | 1 (`MCC_ECA_SLOT_UNRESOLVABLE`) | 0 |

---

## §3 Module Registration Map

Source: `EFL_RAL_v1_4_0_frozen.json`, `moduleRegistration`
RAL documentHash: `0ed89408fd370e6493891cad54f839b571082f1344ffae78582b53d7843251c8`

| Module | moduleVersion | moduleViolationRegistryVersion | registryHash |
|---|---|---|---|
| SESSION | 1.1.1 | 1.1.1 | (from RAL v1.4.0) |
| MESO | 1.0.2 | 1.0.2 | (from RAL v1.4.0) |
| MACRO | 1.0.2 | 1.0.2 | (from RAL v1.4.0) |
| GOVERNANCE | 1.0.0 | 1.0.0 | (from RAL v1.4.0) |
| **PHYSIQUE** | **1.0.2** | **1.0.2** | `18e48073a08eac4f755c6bc4fc9755158917415188316a8d8ad38d304be02f3c` |

---

## §4 Frozen Spec Inventory

### EFL_PHYSIQUE_v1_0_2_frozen.json

| Field | Value |
|---|---|
| specID | `EFL-PHYSIQUE` |
| version | `1.0.2` |
| moduleID | `PHYSIQUE` |
| moduleVersion | `1.0.2` |
| moduleViolationRegistryVersion | `1.0.2` |
| violations count | 50 |
| registryHash | `18e48073a08eac4f755c6bc4fc9755158917415188316a8d8ad38d304be02f3c` |
| documentHash | `1ac740c4fd0278edd94be2c1cb99ea8a21961fffe35e88467ebc9b5d9e183596` |

### EFL_RAL_v1_4_0_frozen.json

| Field | Value |
|---|---|
| version | `1.4.0` |
| documentHash | `0ed89408fd370e6493891cad54f839b571082f1344ffae78582b53d7843251c8` |

---

## §5 Kernel Wiring

| File | Change | Status |
|---|---|---|
| `efl_kernel/kernel/ral.py` | SPEC_PATH → `EFL_RAL_v1_4_0_frozen.json` | ACTIVE |
| `efl_kernel/kernel/registry.py` | Loads `EFL_PHYSIQUE_v1_0_2_frozen.json`; no direct insertions | ACTIVE |
| `efl_kernel/kernel/gates_physique.py` | `_run_clearance_gate` added; `run_physique_gates` updated | ACTIVE |
| `efl_kernel/kernel/kernel.py` | PHYSIQUE dispatch at Step 6 (unchanged from Phase 7) | ACTIVE |

Hash verification at import: `registry.py` verifies `registryHash` for all 5 module specs (SESSION, MESO, MACRO, PHYSIQUE, CL) and `documentHash` for RAL. Any tampering raises `RuntimeError` before the kernel accepts any evaluation request.

---

## §6 PHYSIQUE Evaluation Flow

Executed by `run_physique_gates(raw_input, dep_provider)` in `gates_physique.py`.

```
Step 0  — kernel.py: payload schema validation, moduleVersion check against RAL registration
Step 1  — kernel.py: RAL required context check (athleteID, sessionID)
Step 2  — kernel.py: RAL required windows check (ROLLING7DAYS, ROLLING28DAYS)
Step 3  — kernel.py: enforce_kernel_owned_fields on all violations
         ...
Step 6  — kernel.py: dispatch → run_physique_gates(raw_input, dep_provider)

  [Inside run_physique_gates]

  6.A  _run_clearance_gate(raw_input, dep_provider)
       ├─ Read evaluationContext.athleteID
       ├─ dep_provider.get_athlete_profile(athleteID)
       ├─ Fail-closed: absent e4_clearance = False
       ├─ For each exercise with e4_requires_clearance=True and exercise_id set:
       │   emit PHYSIQUE.CLEARANCEMISSING (HARDFAIL, no override)
       └─ Deduplicates by exercise_id (one violation per unique ID)

  6.B  run_physique_adapter(raw_input)
       ├─ Returns AdapterResult with halt_codes, context, day_slots, resolved_slot_exercises
       └─ If halt_codes non-empty → append RAL.MISSINGORUNDEFINEDREQUIREDSTATE, return

  6.C  run_physique_dcc_gates(adapter_result, dep_provider)
       └─ Tempo format and constraint gates (7 codes)

  6.D  O1 guard: if day_slots non-empty and context absent
       └─ emit MCC_PASS2_MISSING_OR_FAILED, return

  6.E  run_physique_mcc_gates(context, resolved_slot_exercises, dep_provider, WHITELIST_INDEX, TEMPO_GOV)
       └─ All MCC gates (43 codes)

Step 7  — kernel.py: compute_effective_label, derive_publish_state, assemble KDO
```

Key property: **clearance gate (6.A) runs before adapter (6.B)**. If the adapter halts, clearance violations are preserved in the returned list — they are not discarded by an adapter halt.

---

## §7 Clearance Gate Specification

**Gate:** `_run_clearance_gate`
**Closes:** PHYSIQUE-GATE-GAP-001
**Violation code:** `PHYSIQUE.CLEARANCEMISSING`
**Severity:** HARDFAIL
**Override possible:** False
**Allowed override reason codes:** []

### Triggering conditions (all must hold)

1. `evaluationContext.athleteID` is present in `raw_input`
2. `dep_provider.get_athlete_profile(athleteID)` returns a profile where `e4_clearance` is not `True`
3. At least one entry in `physique_session.exercises` has `e4_requires_clearance=True` and a non-empty `exercise_id`

### Non-triggering conditions

- Athlete profile absent or empty → treated as `e4_clearance=False` (fail-closed), gate **still fires** if exercises qualify
- `athleteID` absent → gate returns no violations (no athlete to check)
- `e4_clearance=True` in profile → gate suppressed entirely
- Exercise has `e4_requires_clearance` absent or `False` → skipped
- Exercise has no `exercise_id` → skipped
- Day-slot exercises → not checked by this gate (Phase 9 decision — see §10 PHYSIQUE-GAP-005)

### Deduplication

One violation per unique `exercise_id`. If the same exercise_id appears multiple times in `physique_session.exercises`, only one `PHYSIQUE.CLEARANCEMISSING` is emitted for it.

### Violation shape

```json
{
  "code": "PHYSIQUE.CLEARANCEMISSING",
  "moduleID": "PHYSIQUE",
  "severity": "HARDFAIL",
  "overridePossible": false,
  "allowedOverrideReasonCodes": [],
  "violationCap": null,
  "reviewOverrideThreshold28D": null,
  "details": {
    "exercise_id": "<exercise_id>",
    "athlete_id": "<athleteID>",
    "e4_clearance": false
  }
}
```

---

## §8 Violation Registry Summary — PHYSIQUE (50 codes)

Source: `EFL_PHYSIQUE_v1_0_2_frozen.json` + `VIOLATION_REGISTRY` at runtime.

### DCC Gates (7 codes)

| Code | Severity | Override |
|---|---|---|
| `DCC_TEMPO_EXPLOSIVE_NOT_ALLOWED_FOR_EXERCISE` | HARDFAIL | No |
| `DCC_TEMPO_E_BELOW_MINIMUM` | HARDFAIL | No |
| `DCC_TEMPO_E_EXCEEDS_CEILING` | HARDFAIL | No |
| `DCC_TEMPO_FORMAT_INVALID` | HARDFAIL | No |
| `DCC_TEMPO_IB_EXCEEDS_CEILING` | HARDFAIL | No |
| `DCC_TEMPO_IT_EXCEEDS_CEILING` | HARDFAIL | No |
| `DCC_TEMPO_X_IN_INVALID_POSITION` | HARDFAIL | No |

### MCC Gates (42 codes)

| Code | Severity | Override |
|---|---|---|
| `MCC_ADJACENCY_VIOLATION` | HARDFAIL | Yes |
| `MCC_BAND3_PATTERN_EXCEEDED` | WARNING | Yes |
| `MCC_BAND_NODE_ILLEGAL_COMBINATION` | HARDFAIL | Yes |
| `MCC_CHRONIC_YELLOW_GUARD_TRIGGERED` | HARDFAIL | Yes |
| `MCC_COLLAPSE_ESCALATION_TRIGGERED` | HARDFAIL | Yes |
| `MCC_CONSECUTIVE_NODE3_EXCEEDED` | HARDFAIL | Yes |
| `MCC_C_DAY_MESO_ROTATION_VIOLATION` | WARNING | Yes |
| `MCC_DAY_A_FREQUENCY_EXCEEDED` | HARDFAIL | Yes |
| `MCC_DAY_A_PATTERN_GUARANTEE_VIOLATED` | HARDFAIL | Yes |
| `MCC_DAY_B_FREQUENCY_EXCEEDED` | HARDFAIL | Yes |
| `MCC_DAY_C_PATTERN_REPETITION` | HARDFAIL | Yes |
| `MCC_DAY_D_INTENT_VIOLATION` | HARDFAIL | Yes |
| `MCC_DENSITY_LEDGER_EXCEEDED` | WARNING | Yes |
| `MCC_D_MINIMUM_VIOLATED` | HARDFAIL | Yes |
| `MCC_ECA_COVERAGE_MISSING` | HARDFAIL | Yes |
| `MCC_ECA_PATTERN_INCOMPLETE` | HARDFAIL | Yes |
| `MCC_ECA_SLOT_UNRESOLVABLE` | HARDFAIL | No |
| `MCC_FAMILY_MULTI_AXIS_VIOLATION` | HARDFAIL | Yes |
| `MCC_FREQUENCY_NOT_SUPPORTED` | HARDFAIL | Yes |
| `MCC_H3_AGGREGATE_EXCEEDED` | WARNING | Yes |
| `MCC_H4_FREQUENCY_EXCEEDED` | HARDFAIL | Yes |
| `MCC_MULTI_AXIS_PROGRESSION_VIOLATION` | HARDFAIL | Yes |
| `MCC_NODE_PERMISSION_VIOLATION` | HARDFAIL | Yes |
| `MCC_PATTERN_BALANCE_VIOLATED` | WARNING | Yes |
| `MCC_PRIME_SCOPE_VIOLATION` | HARDFAIL | Yes |
| `MCC_READINESS_BAND_MISMATCH` | WARNING | Yes |
| `MCC_READINESS_VIOLATION` | WARNING | Yes |
| `MCC_ROUTE_SATURATION_VIOLATION` | WARNING | Yes |
| `MCC_SESSION_DURATION_EXCEEDED` | HARDFAIL | Yes |
| `MCC_SESSION_VOLUME_EXCEEDED` | WARNING | Yes |
| `MCC_SFI_ELEVATED_WARNING` | WARNING | Yes |
| `MCC_SFI_EXCESSIVE_WARNING` | WARNING | Yes |
| `MCC_TEMPO_DOWNGRADED_FOR_H_NODE_MAX` | CLAMP | No |
| `MCC_TEMPO_DOWNGRADED_FOR_TUT_CEILING` | CLAMP | No |
| `MCC_TEMPO_DOWNGRADE_CHAIN_EXHAUSTED` | WARNING | Yes |
| `MCC_TEMPO_DOWNGRADE_REVALIDATION_FAILED` | WARNING | Yes |
| `MCC_TEMPO_ESCALATION_APPROVED` | CLAMP | No |
| `MCC_TEMPO_ESCALATION_CLAMPED_TO_H3` | WARNING | Yes |
| `MCC_TEMPO_ESCALATION_REQUIRES_OPT_IN` | HARDFAIL | Yes |
| `MCC_TEMPO_MODIFIED_BY_MCC` | CLAMP | No |
| `MCC_VOLUME_CLASS_OVERRIDE_ATTEMPT` | HARDFAIL | Yes |
| `MCC_WORK_BLOCK_INSUFFICIENT` | HARDFAIL | Yes |

### Clearance Gate (1 code)

| Code | Severity | Override |
|---|---|---|
| `PHYSIQUE.CLEARANCEMISSING` | HARDFAIL | No |

**Total: 50 codes**

---

## §9 PHYSIQUE-GATE-GAP-001 Closure

**Status: CLOSED**

| Field | Value |
|---|---|
| Gap ID | PHYSIQUE-GATE-GAP-001 |
| Opened | Phase 7 Runtime Binding Spec §8 |
| Closed | Phase 8 (this document) |
| Gap description | e4_clearance enforcement missing from PHYSIQUE evaluation path |
| Resolution | `_run_clearance_gate` added to `gates_physique.py`; executes before adapter; emits `PHYSIQUE.CLEARANCEMISSING` (HARDFAIL, no override) per qualifying exercise |
| Violation registered | Yes — `EFL_PHYSIQUE_v1_0_2_frozen.json` |
| Test coverage | `test_physique_clearance_gate_fires_on_missing_clearance`, `test_physique_clearance_gate_suppressed_when_cleared` |

---

## §10 Known Gaps at Phase 8 Close

### PHYSIQUE-GAP-002: MCC_PASS2_MISSING_OR_FAILED unregistered

| Field | Value |
|---|---|
| Status | OPEN |
| Description | `MCC_PASS2_MISSING_OR_FAILED` is emitted by the O1 guard in `run_physique_gates` when `day_slots` is non-empty and `context` is absent. It is not present in `EFL_PHYSIQUE_v1_0_2_frozen.json` and therefore not in `VIOLATION_REGISTRY`. `enforce_kernel_owned_fields` does not find a registry entry for it. |
| Impact | Violation emitted with caller-supplied fields; `enforce_kernel_owned_fields` is a no-op for this code |
| Resolution target | Phase 9 — register in frozen spec v1.0.3 |

### PHYSIQUE-GAP-003: e4_requires_clearance sourced from caller input

| Field | Value |
|---|---|
| Status | OPEN |
| Description | The clearance gate reads `e4_requires_clearance` from the caller-supplied `physique_session.exercises` entries. This field is not whitelist-authoritative — callers can omit it or set it to `False` for exercises that require clearance. |
| Impact | Clearance gate can be bypassed by omitting `e4_requires_clearance` from exercise entries |
| Resolution target | Phase 9 — pre-pass adapter injects `_resolved_e4_requires_clearance` from whitelist; gate reads `_resolved_*` field |

### PHYSIQUE-GAP-004: DCC_TEMPO_GOVERNANCE_UNAVAILABLE unregistered

| Field | Value |
|---|---|
| Status | OPEN |
| Description | `DCC_TEMPO_GOVERNANCE_UNAVAILABLE` is emitted by `run_physique_dcc_gates` when the tempo governance table is unavailable. It is not in the frozen spec. |
| Impact | Same as GAP-002: `enforce_kernel_owned_fields` is a no-op |
| Resolution target | Phase 10 |

### PHYSIQUE-GAP-005: e4_clearance not checked for day_slot exercises

| Field | Value |
|---|---|
| Status | OPEN — by design at Phase 8 |
| Description | `_run_clearance_gate` checks `physique_session.exercises` only. Exercises referenced in `day_slots` are not checked against e4_clearance. |
| Rationale | Day-slot exercises are resolved from the whitelist by `_resolve_slot_exercises`; `e4_requires_clearance` is not yet a whitelist field. Phase 9 will add it. |
| Resolution target | Phase 9 — after GAP-003 resolved, extend clearance gate to resolved slot exercises |

---

## §11 Bidirectional Coverage

All 50 PHYSIQUE violation codes are present as coverage markers in `efl_kernel/tests/test_gate_coverage.py`. `validate_bidirectional_coverage()` returns `{}` at Phase 8 close.

The O1 invariant code (`MCC_PASS2_MISSING_OR_FAILED`) is intentionally absent from the frozen spec and from coverage markers — covered by PHYSIQUE-GAP-002 for Phase 9.

---

## §12 SFI Configuration

Source: `EFL_PHYSIQUE_v1_0_2_frozen.json` top-level fields (unchanged from v1.0.1).

| Field | Value |
|---|---|
| `sfiThresholds.elevated` | 15 |
| `sfiThresholds.excessive` | 25 |
| `sfiFormula.h3_archetype_weight` | 2.0 |
| `sfiFormula.h4_archetype_weight` | 4.0 |
| `sfiFormula.node3_sets_weight` | 1.0 |
| `sfiFormula.unilateral_sets_weight` | 0.5 |

These values are loaded at module import by `gates_physique.py:_SFI_THRESHOLDS` and `_SFI_FORMULA`. They are kernel-owned and cannot be overridden by caller input.

---

## §13 References

| Document | Role |
|---|---|
| `EFL_RAL_v1_4_0_frozen.json` | Module registration authority |
| `EFL_PHYSIQUE_v1_0_2_frozen.json` | Violation registry authority |
| `efl_kernel/kernel/gates_physique.py` | Gate implementation |
| `efl_kernel/kernel/registry.py` | Registry loading and hash verification |
| `efl_kernel/kernel/ral.py` | RAL loading and precedence rules |
| `efl_kernel/tests/test_gate_coverage.py` | Bidirectional coverage verification |
| `efl_kernel/tests/test_conformance.py` | Module registration conformance tests |
| `Physique/Phase7_Runtime_Binding_Spec.md` | Prior binding decisions (4 verdicts) |
| `Physique/Phase6_Design_Doc.md` | Design history |
