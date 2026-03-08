# Physique Pre-Pass Adapter Spec v1.1

**Document ID:** EFL-PHYSIQUE-ADAPTER-SPEC-001
**Status:** BINDING
**Version:** 1.1.0
**Date:** 2026-03-07
**Phase:** 9
**Supersedes:** `Physique/Physique_Pre_Pass_Adapter_Spec_v1_0.md` (SPEC-DRAFT, superseded)
**Preceding documents:**
- `Physique/Phase7_Runtime_Binding_Spec.md` (4 binding decisions)
- `Physique/Phase8_Runtime_Manifest.md` (PHYSIQUE module registration, Phase 8 gaps)

---

## Table of Contents

1. [Purpose and Scope](#1-purpose-and-scope)
2. [Artifact Reference Table](#2-artifact-reference-table)
3. [Execution Order](#3-execution-order)
4. [Implementation Fidelity](#4-implementation-fidelity)
5. [horiz_vert Normalization Contract](#5-horizvert-normalization-contract)
6. [e4_requires_clearance Injection Contract](#6-e4_requires_clearance-injection-contract)
7. [Tempo Mode Classification](#7-tempo-mode-classification)
8. [Normalized Exercise Output Contract](#8-normalized-exercise-output-contract)
9. [Slot Exercise Resolution Contract](#9-slot-exercise-resolution-contract)
10. [Halt Conditions](#10-halt-conditions)
11. [Clearance Gate (Phase 9)](#11-clearance-gate-phase-9)
12. [Open Questions](#12-open-questions)
13. [Deferred Items](#13-deferred-items)
14. [Phase 10 Prerequisites Checklist](#14-phase-10-prerequisites-checklist)

---

## 1. Purpose and Scope

This document is the binding specification for the PHYSIQUE pre-pass adapter as implemented at Phase 9 close. It replaces the SPEC-DRAFT status of v1.0 and corrects all artifact references, implementation fidelity claims, and execution order descriptions to match the actual runtime state.

**Scope:** `efl_kernel/kernel/physique_adapter.py`, `efl_kernel/kernel/gates_physique.py` (clearance gate interaction), and the whitelist artifacts these modules load.

**Not in scope:** DCC gate logic, MCC gate logic, kernel dispatch, KDO assembly, override processing.

---

## 2. Artifact Reference Table

All artifact references in this document are to the state at Phase 9 commit.

| Artifact | Version | Path | Notes |
|---|---|---|---|
| EFL Whitelist | 1.0.4 | `Physique/efl_whitelist_v1_0_4.json` | 30 exercises; adds `e4_requires_clearance` |
| PHYSIQUE Frozen Spec | 1.0.3 | `efl_kernel/specs/EFL_PHYSIQUE_v1_0_3_frozen.json` | 51 violation codes |
| RAL | 1.5.0 | `efl_kernel/specs/EFL_RAL_v1_5_0_frozen.json` | PHYSIQUE moduleVersion 1.0.3 |
| Phase 8 Manifest | — | `Physique/Phase8_Runtime_Manifest.md` | PHYSIQUE module registration record |
| Tempo Governance | 1.1.2 | `Physique/efl_tempo_governance_v1_1_2_ENFORCEMENT_CLEAN.json` | Eccentric minimums, day-role caps |
| Runtime Manifest | — | `Physique/physique_runtime_manifest_v1_0.json` | Adapter version string |

**Correction from v1.0 draft:** The v1.0 draft referenced `physique_runtime_manifest_v1_0.json` as the Phase 8 binding document. The actual Phase 8 binding document is `Phase8_Runtime_Manifest.md`. The JSON file is a runtime manifest that carries the adapter version string only.

---

## 3. Execution Order

### Phase 9 execution order (binding)

```
run_physique_gates(raw_input, dep_provider)
│
├─ Step 6.A: run_physique_adapter(raw_input)
│   ├─ Whitelist resolution for physique_session.exercises
│   ├─ horiz_vert normalization (F5: unknown labels halt)
│   ├─ tempo mode classification (F6: Isometric → N/A_DURATION)
│   ├─ _resolve_slot_exercises (whitelist fields injected with _resolved_ prefix)
│   └─ Returns PhysiqueAdapterResult
│
├─ [HALT if adapter_result.halt_codes non-empty]
│   └─ Emit RAL.MISSINGORUNDEFINEDREQUIREDSTATE only. Return.
│       Clearance violations are NOT emitted for unresolvable exercises.
│
├─ Step 6.B: _run_clearance_gate(adapter_result, dep_provider)
│   ├─ Reads e4_requires_clearance from adapter_result.normalized_exercises
│   ├─ Reads _resolved_e4_requires_clearance from adapter_result.resolved_slot_exercises
│   └─ Emits PHYSIQUE.CLEARANCEMISSING per qualifying exercise
│
├─ Step 6.C: run_physique_dcc_gates(adapter_result, dep_provider)
│
└─ Step 6.D: O1 guard or run_physique_mcc_gates
    ├─ If day_slots non-empty AND context absent: emit MCC_PASS2_MISSING_OR_FAILED
    └─ Otherwise: run_physique_mcc_gates(...)
```

### Execution order change from Phase 8

Phase 8 ran the clearance gate **before** the adapter using raw caller input. Phase 9 runs the adapter **first** and the clearance gate reads whitelist-resolved fields from the adapter result.

**Rationale:**
1. GAP-003: `e4_requires_clearance` was read from caller input, which callers could omit or falsify. Whitelist-resolution is the only authoritative source.
2. GAP-005: Slot exercises were never checked. The adapter resolves slot exercises; only after resolution is clearance checkable.
3. An unresolvable exercise (adapter halt) means clearance cannot be assessed — speculative clearance violations must not be emitted.

---

## 4. Implementation Fidelity

### What is implemented at Phase 9

| Component | Status | Notes |
|---|---|---|
| Whitelist load and index | IMPLEMENTED | `efl_whitelist_v1_0_4.json`, 30 exercises |
| Exercise ID resolution (physique_session) | IMPLEMENTED | Fail-closed halt on unknown ID |
| horiz_vert normalization (F5) | IMPLEMENTED | 4-branch logic; unknown label halts |
| tempo mode classification (F6) | IMPLEMENTED | N/A_DISTANCE (Carry), N/A_DURATION (Isometric), ECICT (all others) |
| Tempo parsing (ECICT) | IMPLEMENTED | E:IB:IT:C format; X validation |
| Whitelist field injection (normalized exercises) | IMPLEMENTED | See §8 for full field list |
| Slot exercise resolution | IMPLEMENTED | `_resolve_slot_exercises`; `_resolved_*` prefix |
| `_resolved_e4_requires_clearance` injection | IMPLEMENTED | Phase 9 addition |
| Clearance gate — session exercises | IMPLEMENTED | Phase 8 initial; Phase 9 restructured |
| Clearance gate — slot exercises | IMPLEMENTED | Phase 9 (GAP-005 closure) |
| `athlete_id` propagation through adapter | IMPLEMENTED | Phase 9; all halt/success paths |
| MCC_PASS2_MISSING_OR_FAILED registration | IMPLEMENTED | Phase 9 (GAP-002 closure); in v1.0.3 frozen spec |

### What is NOT implemented (deferred)

| Item | Deferred to | Description |
|---|---|---|
| F1: Authority version verification | Phase 10 | Payload `moduleVersion` not validated against RAL at adapter layer |
| F2: Input schema validation | Phase 10 | No JSON schema check before adapter runs |
| F3: Exercise alias table | Phase 10 | Alias expansion not implemented; only canonical IDs accepted |
| F7: adapter_trace field | Phase 10 | No per-exercise normalization trace in AdapterResult |
| GAP-004: DCC_TEMPO_GOVERNANCE_UNAVAILABLE | Phase 10 | Emitted by DCC gate but not in frozen spec |
| GAP-005 for day_slot e4_requires_clearance | CLOSED | Closed in Phase 9 via `_resolved_e4_requires_clearance` |

---

## 5. horiz_vert Normalization Contract

**Source:** `HORIZ_VERT_MAP` and passthrough domain in `physique_adapter.py`.

### Normalization table

| Whitelist value | Normalized value | Mechanism |
|---|---|---|
| `null` | `null` | Null passthrough |
| `"Incline"` | `"horizontal"` | HORIZ_VERT_MAP lookup |
| `"horizontal"` | `"horizontal"` | Passthrough domain |
| `"vertical"` | `"vertical"` | Passthrough domain |
| `"sagittal"` | `"sagittal"` | Passthrough domain |
| `"frontal"` | `"frontal"` | Passthrough domain |
| Any other value | HALT | `halt_codes=["UNKNOWN_HORIZ_VERT_LABEL"]` |

### Passthrough domain

The MCC domain values are `{"horizontal", "vertical", "sagittal", "frontal"}`. Values already in this set pass through unchanged. Values in `HORIZ_VERT_MAP` are translated. All other non-null values halt the adapter.

### F5 fix (Phase 9)

Prior to Phase 9, unknown labels were lowercased and passed through silently (`.lower()` fallback). This allowed non-domain values to reach the MCC layer. Phase 9 replaces the fallback with a halt.

### Scope

The F5 fix applies to both:
1. `physique_session.exercises` (exercise loop in `run_physique_adapter`)
2. `day_slots[*].exercises` (slot normalization loop in `run_physique_adapter`)

Both loops halt with `UNKNOWN_HORIZ_VERT_LABEL` on an unrecognized label.

---

## 6. e4_requires_clearance Injection Contract

### Whitelist field (v1.0.4)

`e4_requires_clearance` is a boolean field added to every exercise in `efl_whitelist_v1_0_4.json`. It is the **only authoritative source** for whether an exercise requires e4 clearance.

| Exercise ID | Name | e4_requires_clearance | Rationale |
|---|---|---|---|
| ECA-PHY-0027 | Rest-Pause Set (Technique) | `true` | H4 technique modifier; elevated fatigue demand |
| ECA-PHY-0028 | Myo-Reps (Technique) | `true` | H4 technique modifier; elevated fatigue demand |
| ECA-PHY-0029 | Drop Set (Technique) | `true` | H4 technique modifier; elevated fatigue demand |
| All others (27 exercises) | — | `false` | Not H4 or not a fatigue-demand modifier |

**ECA-PHY-0030 (Tempo Squat):** h_node="H0", volume_class="PRIMARY", movement_family="Squat". Despite its name, it is not an H4 technique modifier. `e4_requires_clearance=false`. This is binding.

### Injection paths

**Session exercises (`normalized_exercises`):**
- Field: `"e4_requires_clearance"` (no prefix)
- Source: `wl_entry.get("e4_requires_clearance", False)`
- Read by: `_run_clearance_gate` → `ex.get("e4_requires_clearance", False)`

**Slot exercises (`resolved_slot_exercises`):**
- Field: `"_resolved_e4_requires_clearance"` (`_resolved_` prefix = whitelist-authoritative)
- Source: `wl.get("e4_requires_clearance", False)` in `_resolve_slot_exercises`
- Read by: `_run_clearance_gate` → `ex.get("_resolved_e4_requires_clearance", False)`
- Exercises with `_resolution_error=True` are skipped (cannot assess clearance for unresolvable exercises)

### Caller cannot override

Callers cannot inject `e4_requires_clearance` into normalized exercises. The adapter reads only from the whitelist. A caller-supplied `e4_requires_clearance` field in `physique_session.exercises` is ignored after adapter normalization.

---

## 7. Tempo Mode Classification

**Function:** `_classify_tempo_mode(movement_family: str, pattern_plane: str | None) -> str`

| Condition | Tempo mode | Gate behavior |
|---|---|---|
| `"carry"` in `movement_family.lower()` | `"N/A_DISTANCE"` | DCC gates skip all ECICT validation |
| `pattern_plane.lower() == "isometric"` | `"N/A_DURATION"` | DCC gates skip all ECICT validation |
| Otherwise | `"ECICT"` | Full DCC tempo validation applies |

**Priority:** Distance check is evaluated before isometric. A hypothetical carry exercise with Isometric pattern_plane would return N/A_DISTANCE.

### F6 fix (Phase 9)

Prior to Phase 9, `_classify_tempo_mode` accepted only `movement_family` and could not return `N/A_DURATION`. ECA-PHY-0023 (Plank, `pattern_plane="Isometric"`) received `tempo_mode="ECICT"` which was wrong — the Plank is duration-prescribed, not rep-prescribed.

Phase 9 adds `pattern_plane` as a parameter and returns `N/A_DURATION` for isometric exercises. DCC gates skip all ECICT validation for exercises with `tempo_mode != "ECICT"`.

---

## 8. Normalized Exercise Output Contract

Fields injected into each entry of `PhysiqueAdapterResult.normalized_exercises`. All fields marked "whitelist-authoritative" are sourced from `efl_whitelist_v1_0_4.json` and cannot be overridden by caller input.

| Field | Source | Authority |
|---|---|---|
| `exercise_id` | Caller | Identity only |
| `tempo_mode` | Derived (`_classify_tempo_mode`) | Whitelist-authoritative |
| `horiz_vert_raw` | Whitelist | Whitelist-authoritative |
| `horiz_vert_normalized` | Derived (normalization table §5) | Whitelist-authoritative |
| `movement_family` | Whitelist | Whitelist-authoritative |
| `tempo_parseable` | Derived (tempo parser) | — |
| `tempo_parsed` | Derived (tempo parser) | — |
| `x_in_invalid_position` | Derived (tempo parser) | — |
| `c_explosive` | Derived (tempo parser) | — |
| `tempo_class` | Whitelist | Whitelist-authoritative |
| `eccentric_max` | Whitelist | Whitelist-authoritative |
| `isometric_bottom_max` | Whitelist | Whitelist-authoritative |
| `isometric_top_max` | Whitelist | Whitelist-authoritative |
| `explosive_concentric_allowed` | Whitelist | Whitelist-authoritative |
| `tempo_can_escalate_hnode` | Whitelist | Whitelist-authoritative |
| `band_max` | Whitelist | Whitelist-authoritative |
| `node_max` | Whitelist | Whitelist-authoritative |
| `h_node_base` | Whitelist (`h_node` field) | Whitelist-authoritative |
| `push_pull` | Whitelist | Whitelist-authoritative (Phase 9 addition) |
| `e4_requires_clearance` | Whitelist | Whitelist-authoritative (Phase 9 addition) |
| `day_role_allowed` | Whitelist | Whitelist-authoritative |

**Phase 9 field changes:**
- `h_node` renamed to `h_node_base` (no semantic change; rename avoids ambiguity with caller-supplied `h_node` on slot exercises)
- `push_pull` added (used by MCC F-cluster pattern balance gates via slot exercises; now also available on normalized exercises for future use)
- `e4_requires_clearance` added (see §6)

---

## 9. Slot Exercise Resolution Contract

**Function:** `_resolve_slot_exercises(day_slots, whitelist_index)`

For each exercise in each `day_slots[*].exercises`:

| Condition | Fields injected |
|---|---|
| `exercise_id` or `eca_id` present and found in whitelist | `_resolved_node_max`, `_resolved_h_node`, `_resolved_volume_class`, `_resolved_movement_family`, `_resolved_e4_requires_clearance` |
| ID present but not in whitelist | `_resolution_error=True` |
| No ID field | No injection (non-ECA slot exercise) |

The `_resolved_` prefix is the convention for whitelist-injected fields on slot exercises. Gates must read `_resolved_*` fields, not caller-supplied fields, for whitelist-authoritative values.

---

## 10. Halt Conditions

The adapter returns `halt_codes` non-empty in these cases. When `run_physique_gates` detects a halt, it emits `RAL.MISSINGORUNDEFINEDREQUIREDSTATE` and returns without running clearance, DCC, or MCC gates.

| halt_code | Trigger |
|---|---|
| `"UNKNOWN_EXERCISE_ID"` | `exercise_id` in `physique_session.exercises` not found in whitelist |
| `"UNKNOWN_HORIZ_VERT_LABEL"` | `horiz_vert` value from whitelist (or caller-supplied on slot exercise) is non-null, not in `HORIZ_VERT_MAP`, and not in the passthrough domain |

Note: `UNKNOWN_HORIZ_VERT_LABEL` reflects a whitelist data error, not a caller error, for session exercises (since horiz_vert is read from the whitelist, not the caller). For slot exercises, the caller supplies `horiz_vert` directly.

---

## 11. Clearance Gate (Phase 9)

Full specification in `Physique/Phase8_Runtime_Manifest.md` §7 (base gate design) updated by this document.

### Changes from Phase 8

| Aspect | Phase 8 | Phase 9 |
|---|---|---|
| Execution position | Before adapter | After adapter (adapter must succeed) |
| Source for session exercises | Caller `physique_session.exercises.e4_requires_clearance` | `adapter_result.normalized_exercises.e4_requires_clearance` (whitelist) |
| Slot exercises checked | No | Yes — via `_resolved_e4_requires_clearance` |
| `athlete_id` source | `raw_input.evaluationContext.athleteID` | `adapter_result.athlete_id` |
| Behavior on adapter halt | Phase 8: clearance ran before halt check | Phase 9: clearance suppressed; halt only |

### Deduplication

Deduplication by `exercise_id` is shared across both the session exercise list and the slot exercise list. If the same `exercise_id` appears in both lists, only one `PHYSIQUE.CLEARANCEMISSING` is emitted.

---

## 12. Open Questions

### Q2 — Zero-violation effective label (CLOSED)

**Status:** CLOSED. `CLAMP` is the correct effective label when there are zero violations. This is confirmed by `compute_effective_label` in `ral.py` which returns `"CLAMP"` when the labels list is empty, and by the RAL precedence rules. No action required.

### Q4 — CL_SPEC hash gap

**Status:** OPEN. `CL_SPEC` carries a `registryHash` that was added retroactively. The hash verification is in `registry.py`. There is a potential for divergence between the `CL_SPEC` hash and the actual violation registry content if the CL spec is modified without updating the hash. This is tracked as a Phase 10 audit item. No code change required at Phase 9.

---

## 13. Deferred Items

### F1 — Authority version verification

The payload `moduleVersion` and `registryHash` fields are validated by the kernel (Step 0b) against `RAL_SPEC.moduleRegistration`. The adapter itself does not perform this check. The kernel-level check is already implemented. No additional adapter-layer check is planned for Phase 9. Phase 10 may add an adapter-level assertion if payload provenance tracing is required.

### F2 — Input schema validation

The `physique_session`, `day_slots`, and `context` fields are not validated against a JSON schema before the adapter runs. The adapter is fail-closed on unknown exercise IDs and horiz_vert labels. Full schema validation is deferred to Phase 10.

### F3 — Exercise alias table

Exercise aliases (alternate IDs mapping to canonical IDs) are not implemented. The adapter accepts only canonical IDs (`canonical_id` from the whitelist). A caller supplying a legacy or alternate ID will receive `UNKNOWN_EXERCISE_ID`. Alias table content and resolution logic are Phase 10 scope.

### F7 — Adapter trace field

`PhysiqueAdapterResult` does not carry an `adapter_trace` field. No per-exercise normalization trace is emitted. This is deferred to Phase 10.

### GAP-004 — DCC_TEMPO_GOVERNANCE_UNAVAILABLE

`DCC_TEMPO_GOVERNANCE_UNAVAILABLE` is emitted by `run_physique_dcc_gates` when the tempo governance table is unavailable. It is not present in `EFL_PHYSIQUE_v1_0_3_frozen.json` and is not in `VIOLATION_REGISTRY`. `enforce_kernel_owned_fields` is a no-op for this code. Registration in a frozen spec is deferred to Phase 10.

---

## 14. Phase 10 Prerequisites Checklist

Items that must be completed before Phase 10 gate work begins.

| Item | Status | Action |
|---|---|---|
| PHYSIQUE module registered in RAL | DONE (Phase 8) | RAL v1.5.0, moduleVersion 1.0.3 |
| All PHYSIQUE violations in frozen spec | DONE (Phase 9) | 51 codes in v1.0.3; GAP-002 closed |
| Whitelist e4_requires_clearance field | DONE (Phase 9) | v1.0.4; H4 modifiers flagged |
| Clearance gate whitelist-authoritative | DONE (Phase 9) | GAP-003 + GAP-005 closed |
| adapter_result.athlete_id populated | DONE (Phase 9) | All halt and success paths |
| F5 horiz_vert passthrough fixed | DONE (Phase 9) | Unknown labels halt |
| F6 isometric tempo mode | DONE (Phase 9) | N/A_DURATION for Isometric pattern_plane |
| DCC_TEMPO_GOVERNANCE_UNAVAILABLE registered | NOT DONE | Must register in frozen spec v1.0.4 before Phase 10 |
| F1: adapter-layer version verification | DEFERRED | Phase 10 decision |
| F2: input schema validation | DEFERRED | Phase 10 decision |
| F3: alias table content | DEFERRED | Phase 10 decision |
| F7: adapter_trace | DEFERRED | Phase 10 decision |
| Q4: CL_SPEC hash audit | DEFERRED | Phase 10 audit |
| GAP-003/005 e4_requires_clearance for day_slot h_node pattern | DONE | Covered by `_resolved_e4_requires_clearance` |
