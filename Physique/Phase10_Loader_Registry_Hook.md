# Phase 10 — Loader, Registry Hook & Authority Verification

**Status:** BINDING
**Phase:** 10
**Date:** 2026-03-07
**Predecessor:** Physique_Pre_Pass_Adapter_Spec_v1_1.md (Phase 9, BINDING)

---

## Scope

Phase 10 closes the following open items from the Phase 9 deferred list:

| Item | Description | Resolution |
|---|---|---|
| GAP-004 | `DCC_TEMPO_GOVERNANCE_UNAVAILABLE` unregistered; no dispatch path | Registered in PHYSIQUE spec v1.0.4; wrapped load; special dispatch |
| F1 | Authority version verification absent | `_verify_authority_versions`: validate-if-present (D1) |
| F2 | Input shape validation absent | `_validate_input_shape`: SCHEMA_VALIDATION_FAILED / INCOMPLETE_INPUT |
| F3 | Alias table absent; legacy IDs cause UNKNOWN_EXERCISE_ID | `physique_alias_table_v1_0.json` + adapter alias resolution |
| F7 | `adapter_trace` absent from `PhysiqueAdapterResult` | Added; populated on all paths |
| Q4 | Test for MCC_ECA_SLOT_UNRESOLVABLE confirmed closed | No action (test already passing) |

---

## Artifact Versions

| Artifact | Version | Notes |
|---|---|---|
| `EFL_PHYSIQUE_v1_0_4_frozen.json` | 1.0.4 | +1 code: DCC_TEMPO_GOVERNANCE_UNAVAILABLE (52 total) |
| `EFL_RAL_v1_6_0_frozen.json` | 1.6.0 | PHYSIQUE moduleVersion 1.0.4 |
| `efl_whitelist_v1_0_4.json` | 1.0.4 | Unchanged from Phase 9 |
| `physique_alias_table_v1_0.json` | 1.0 | New; 12 entries; hash-verified |
| `physique_runtime_manifest_v1_0.json` | (unchanged) | |

---

## GAP-004: DCC_TEMPO_GOVERNANCE_UNAVAILABLE

### Problem

The tempo governance file (`efl_tempo_governance_v1_1_2_ENFORCEMENT_CLEAN.json`) is loaded at module level. If it is unavailable or corrupted, the adapter would raise an unhandled exception. There was no registered violation to represent this failure, and no dispatch path to surface it to the caller.

### Resolution

**Spec (PHYSIQUE v1.0.4):** `DCC_TEMPO_GOVERNANCE_UNAVAILABLE` added to the violation registry.

```json
{
  "moduleID": "PHYSIQUE",
  "code": "DCC_TEMPO_GOVERNANCE_UNAVAILABLE",
  "severity": "HARDFAIL",
  "overridePossible": false,
  "allowedOverrideReasonCodes": [],
  "violationCap": null,
  "reviewOverrideThreshold28D": null,
  "clampBehavior": null
}
```

**Adapter (`physique_adapter.py`):** `_TEMPO_GOV` load is wrapped in try/except. On load failure, `_TEMPO_GOV_LOAD_ERROR = True`. Early in `run_physique_adapter`, this flag halts with `halt_codes=["DCC_TEMPO_GOVERNANCE_UNAVAILABLE"]`.

**Gate dispatch (`gates_physique.py`):** The `run_physique_gates` halt branch is split:

```python
if adapter_result.halt_codes:
    if "DCC_TEMPO_GOVERNANCE_UNAVAILABLE" in adapter_result.halt_codes:
        violations.append(_mcc_v("DCC_TEMPO_GOVERNANCE_UNAVAILABLE"))
    else:
        violations.append(_syn("RAL.MISSINGORUNDEFINEDREQUIREDSTATE"))
    return violations
```

**Why `_mcc_v` not `_syn`:** `DCC_TEMPO_GOVERNANCE_UNAVAILABLE` is a registered PHYSIQUE violation (present in VIOLATION_REGISTRY). `enforce_kernel_owned_fields` must be able to find it. `_syn` bypasses registry lookup and is reserved for RAL-level synthetic violations where no PHYSIQUE registration exists.

---

## F1: Authority Version Verification

### Decision: D1 — Validate-if-Present (Option A)

If `authority_versions` is absent or null, no check is performed. If present, each declared key is validated against the loaded artifact version. A single mismatch on any key halts with `AUTHORITY_VERSION_MISMATCH`.

### Implementation

**Constants (module level):**
- `_WHITELIST_VERSION: str` — from `_WHITELIST["version"]`
- `_TEMPO_GOV_VERSION: str` — from `_TEMPO_GOV["version"]` (empty string if load error)

**Function:**
```python
def _verify_authority_versions(authority_versions: dict) -> list[str]:
    if not authority_versions:
        return []
    if "whitelist_version" in authority_versions:
        if authority_versions["whitelist_version"] != _WHITELIST_VERSION:
            return ["AUTHORITY_VERSION_MISMATCH"]
    if "tempo_gov_version" in authority_versions:
        if authority_versions["tempo_gov_version"] != _TEMPO_GOV_VERSION:
            return ["AUTHORITY_VERSION_MISMATCH"]
    return []
```

**Wire shape (D2: current only):** `payload.authority_versions.whitelist_version` and `payload.authority_versions.tempo_gov_version`. Absent field = skip that check.

---

## F2: Input Shape Validation

### Implementation

```python
def _validate_input_shape(payload: dict) -> list[str]:
    physique_session = payload.get("physique_session")
    if not isinstance(physique_session, dict):
        return ["SCHEMA_VALIDATION_FAILED"]
    exercises = physique_session.get("exercises")
    if not isinstance(exercises, list):
        return ["SCHEMA_VALIDATION_FAILED"]
    for ex in exercises:
        if not isinstance(ex, dict):
            return ["SCHEMA_VALIDATION_FAILED"]
        if not ex.get("exercise_id"):
            return ["INCOMPLETE_INPUT"]
    return []
```

**Halt codes:**
- `SCHEMA_VALIDATION_FAILED`: `physique_session` not a dict, `exercises` not a list, or an exercise entry is not a dict.
- `INCOMPLETE_INPUT`: an exercise dict is present but has no `exercise_id`.

**Scope (D2):** Validates only the current wire shape (`physique_session.exercises[*].exercise_id`). Day_slots shape is not validated at this level.

---

## F3: Alias Table

### Artifact: `Physique/physique_alias_table_v1_0.json`

Maps `adult_physique_v1_0_2.json` legacy IDs (`ECA-FAMILY-NNN` format) to canonical whitelist IDs (`ECA-PHY-NNNN` format). The table is append-only. Missing entries are intentional (not oversights).

**Content decision (D5):** Only exercises present in both the legacy source and the whitelist are included. `ECA-PRESS-003` is explicitly excluded (no whitelist counterpart). `ECA-ISOLATE-011 → ECA-PHY-0016` is included.

**Entries (12):**
| Legacy ID | Canonical ID |
|---|---|
| ECA-HINGE-001 | ECA-PHY-0004 |
| ECA-HINGE-002 | ECA-PHY-0003 |
| ECA-ISOLATE-001 | ECA-PHY-0018 |
| ECA-ISOLATE-011 | ECA-PHY-0016 |
| ECA-PRESS-002 | ECA-PHY-0010 |
| ECA-PULL-011 | ECA-PHY-0014 |
| ECA-PULL-012 | ECA-PHY-0013 |
| ECA-PULL-020 | ECA-PHY-0021 |
| ECA-SQUAT-001 | ECA-PHY-0001 |
| ECA-SQUAT-002 | ECA-PHY-0002 |
| ECA-SQUAT-011 | ECA-PHY-0006 |
| ECA-SQUAT-020 | ECA-PHY-0005 |

**Hash verification:** documentHash (`02ff224b9617bfd363fc74e36d41defefe677e12a1df9c2d1628049190daedaa`) verified at module load. On failure, `_ALIAS_TABLE_LOAD_ERROR = True` and adapter halts with `ADAPTER_LOAD_FAILURE`.

### Resolution Logic

Alias lookup applies **only** to `physique_session.exercises` after a direct `WHITELIST_INDEX` miss. It is NOT applied to slot exercises (D constraint #10). `_resolve_slot_exercises` uses its own eca_id path.

```
exercise_id → WHITELIST_INDEX miss → ALIAS_INDEX lookup → canonical_id → WHITELIST_INDEX hit
                                                        → miss → halt UNKNOWN_EXERCISE_ID
```

On alias resolution, `exercise_id` is replaced with `canonical_id` for all downstream processing. The original alias ID is recorded in `adapter_trace.resolved_via_alias`.

---

## F7: adapter_trace

`PhysiqueAdapterResult.adapter_trace: dict` is populated on all return paths.

**Halt path (minimum):**
```json
{"adapter_version": "<version>", "halt_reason": ["<halt_code>"]}
```

**Success path (full):**
```json
{
  "adapter_version": "<version>",
  "whitelist_version": "<version>",
  "tempo_gov_version": "<version>",
  "resolved_via_alias": ["<original_id>", ...],
  "horiz_vert_events": [{"exercise_id": "...", "raw": "Incline", "normalized": "horizontal"}, ...],
  "tempo_modes": [{"exercise_id": "...", "tempo_mode": "ECICT"}, ...],
  "e4_flagged": ["<exercise_id>", ...]
}
```

---

## Early-Exit Guard Order

Within `run_physique_adapter`, early-exit guards execute in the following fixed order:

1. **F2** — `_validate_input_shape` (shape must be valid before any field access)
2. **GAP-004** — `_TEMPO_GOV_LOAD_ERROR` (governance required for DCC gate evaluation)
3. **F3 load** — `_ALIAS_TABLE_LOAD_ERROR` (alias table required for ID resolution)
4. **F1** — `_verify_authority_versions` (optional caller contract check)

The per-exercise WHITELIST_INDEX + alias lookup, and horiz_vert normalization, follow in the exercise loop.

---

## Conformance Values (Phase 10)

| Field | Value |
|---|---|
| PHYSIQUE `moduleVersion` | `1.0.4` |
| PHYSIQUE `moduleViolationRegistryVersion` | `1.0.4` |
| PHYSIQUE `registryHash` | `7140d801e3194e0bbc74adc7f3c6d03bb503edc3124c3f0dfc0b71a02c185ec0` |
| PHYSIQUE `documentHash` | `d9c8fe5dedeb85915a2f8314ed5236de565401613bc04b4a8f676f6915396984` |
| RAL version | `1.6.0` |
| RAL `documentHash` | `1997671cecc986912d8ee07e7161cc266ffc6bce62b9ef7ef5bb4d8f37a0abf1` |
| alias table `documentHash` | `02ff224b9617bfd363fc74e36d41defefe677e12a1df9c2d1628049190daedaa` |

---

## Deferred to Phase 11+

The following items remain open:

| Item | Description |
|---|---|
| F1 extended | Version fields for additional authority artifacts beyond whitelist + tempo_gov |
| F2 extended | Shape validation for day_slots wire shape |
| F3 extended | Alias table versioning and append-only audit trail |
| F7 extended | Service-level exposure of adapter_trace in API response body |

---

## Test Coverage

| Test file | New tests | Description |
|---|---|---|
| `test_gate_coverage.py` | 5 | GAP-004 dispatch, F1 mismatch/correct, F2 shape errors |
| `test_adapter_trace.py` | 9 | F7 trace fields, F3 alias resolution, D5 decisions |
| `test_conformance.py` | 0 new (1 updated) | PHYSIQUE hashes updated to v1.0.4 |

Final suite: **356 passed, 1 skipped**.
