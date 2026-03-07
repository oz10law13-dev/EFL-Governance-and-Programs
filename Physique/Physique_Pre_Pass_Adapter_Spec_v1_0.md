# Physique Pre-Pass Adapter Spec v1.0
## Phase 9 — Pre-Pass Normalization and Track A Decision Record

**Status:** SPEC-DRAFT
**Version:** 1.0.0
**Date:** 2026-03-06
**Phase:** 9 of 18 (Track A — last specification phase before Track B implementation)
**Preceding documents:**
- `Physique/Physique_Runtime_Binding_Spec_v1_0.md` (Phase 7)
- `Physique/physique_runtime_manifest_v1_0.json` (Phase 8)

---

## Table of Contents

1. [Purpose and Scope](#1-purpose-and-scope)
2. [Decision Record](#2-decision-record)
3. [Canonical Mode Label Vocabulary](#3-canonical-mode-label-vocabulary)
4. [Canonical Exercise ID Contract](#4-canonical-exercise-id-contract)
5. [Adapter Input Envelope (Declared Architecture)](#5-adapter-input-envelope-declared-architecture)
6. [Adapter Normalization Contract (Declared Architecture)](#6-adapter-normalization-contract-declared-architecture)
7. [Adapter Output Envelope (Declared Architecture)](#7-adapter-output-envelope-declared-architecture)
8. [Stop Conditions and Failure Modes](#8-stop-conditions-and-failure-modes)
9. [Tempo Governance Pass 1B Load Path](#9-tempo-governance-pass-1b-load-path)
10. [Kernel-Side Violation Registry](#10-kernel-side-violation-registry)
11. [Override Reason Code Cap Policy](#11-override-reason-code-cap-policy)
12. [GOVERNANCE Module Interaction](#12-governance-module-interaction)
13. [Open Questions Carried Forward](#13-open-questions-carried-forward)
14. [Phase 10 Prerequisites Checklist](#14-phase-10-prerequisites-checklist)
15. [Non-Negotiable Architectural Constraints](#15-non-negotiable-architectural-constraints)

---

## 1. Purpose and Scope

### 1.1 What this spec defines

This document defines two things:

1. **The pre-pass adapter contract**: the deterministic normalization layer that executes as part of Pass 0, before Pass 1A (DCC Legality) receives any exercise data. This is the bridge between authoring-shape exercise data and the runtime exercise contract.

2. **The Track A decision record**: formal decisions for the six open questions Phase 8 identified as must-resolve-before-Phase-9 or must-resolve-before-Phase-10 (Q9, Q1, Q8, Q7, Q3, Q6). These decisions are recorded here with rationale sourced from inspected artifacts so that Phase 10 has a canonical, traceable baseline.

### 1.2 What this spec does not define

- Loader code, Python, SQL, or any other implementation artifact
- Runtime binding of any Physique artifact (that begins at Phase 10)
- The kernel-side frozen Physique module spec content (artifact structure is defined here; content — violation codes and their fields — is Phase 10 work)
- The frozen RAL spec version bump (prerequisite conditions are defined here; the spec itself is Phase 10 work)
- Any change to frozen specs in `efl_kernel/specs/`

### 1.3 Relationship to Phase 7 §5.4.5 and Phase 10

Phase 7 §5.4.5 declared:

> "The Phase 9 pre-pass adapter is designed to execute before Pass 1A receives any exercise data. [...] The adapter contract itself is the subject of Phase 9."

This document fulfills that delegation. All adapter contracts stated here are declared architecture — target behavior once Physique is runtime-bound. None are currently implemented.

Phase 10 (Physique Loader/Registry Hook) may not begin until this document is approved.

---

## 2. Decision Record

### Decision Q9: Canonical Mode Label Vocabulary

**Decision ID:** Q9
**Title:** Canonical mode label vocabulary alignment

**Options considered:**
- Option A: Adopt `CONTROL` / `INFO` from Phase 7 §5.4.3 as canonical
- Option B: Adopt `CONTEXT` / `INFORMATIONAL` from `global_reason_codes_v1_0.json` and `efl_tempo_governance_v1_1_2_ENFORCEMENT_CLEAN.json`
- Option C: Introduce a new vocabulary distinct from both

**Selected option:** A — `CONTROL` and `INFO`

**Rationale:** Phase 7 §5.4.3 is the most recent authoritative specification document and was written with full knowledge of the existing label discrepancy. The mode labels `CONTROL` and `INFO` align with the Shell v1 architecture (which uses `CONTROL` for Pass 2 and reserves INFO for advisory annotation). `CONTEXT` and `INFORMATIONAL` are terminologically imprecise: "context" understates the restriction authority of Pass 2, and "informational" is redundant with the pass name `ADVISORY`. Phase 7 is the governing document; `global_reason_codes_v1_0.json` is updated to match.

**Consequence for Phase 10:** Phase 10 validators must use `CONTROL` and `INFO` as the canonical mode label vocabulary. Any implementation referencing `CONTEXT` or `INFORMATIONAL` is non-conformant.

**`global_reason_codes_v1_0.json` patch:** Two fields in `validation_pass_structure` are updated:
- `pass_2.mode`: `"CONTEXT"` → `"CONTROL"`
- `pass_3.mode`: `"INFORMATIONAL"` → `"INFO"`

No reason code entries are modified. See Section 3 for the authoritative table.

**Residual variance:** `efl_tempo_governance_v1_1_2_ENFORCEMENT_CLEAN.json` `validator_pass_semantics` uses `"CONTEXT"` and `"INFORMATIONAL"` (this file is read-only). This variance is documented as known and non-blocking: tempo governance is not the vocabulary authority; Phase 7 is. Phase 10 implementers must follow Phase 7 / Phase 9 vocabulary.

**Open dependencies after this decision:** None.

---

### Decision Q1: Canonical Exercise ID Format

**Decision ID:** Q1
**Title:** Canonical Physique exercise ID format and alias table policy

**Options considered:**
- Option A: Adopt `ECA-PHY-NNNN` from `efl_whitelist_v1_0_3.json` as canonical runtime format
- Option B: Adopt `ECA-{FAMILY}-NNN` from `adult_physique_v1_0_2.json` as canonical format
- Option C: Introduce a new unified format requiring re-issuance of both artifacts
- Option D: Adopt a flat numeric format to align with the current runtime exercise library

**Selected option:** A — `ECA-PHY-NNNN`

**Rationale:** `efl_whitelist_v1_0_3.json` is the designated runtime-adjacent artifact and future runtime exercise authority (Phase 8, `runtime_binding_candidates`). Its `canonical_id` field is the stable identifier the adapter resolves against at runtime. The `ECA-PHY-NNNN` format is a zero-padded four-digit namespace that is implementation-stable and does not encode semantic information in the ID (unlike the family-prefixed format, which creates coupling between the ID and the exercise's movement family classification, which is itself a runtime-sourced field). `adult_physique_v1_0_2.json` is a support/spec artifact with no runtime binding target; its ID format is the authoring format only.

**Alias table requirement:** Because authoring sessions may reference `ECA-{FAMILY}-NNN` IDs from `adult_physique_v1_0_2.json`, the adapter requires an explicit alias table mapping authoring IDs to canonical runtime IDs. This table is defined in Section 4.2. If an authoring ID is not present in either the whitelist directly or the alias table, the adapter must fail closed.

**Consequence for Phase 10:** Phase 10 loaders resolve exercise identity using `ECA-PHY-NNNN` as the primary key into the loaded whitelist. The alias table is a Phase 10 load-time artifact that must be integrity-verified alongside the whitelist.

**Open dependencies after this decision:** The alias table currently covers the 30 exercises in `efl_whitelist_v1_0_3.json`. As whitelist coverage expands, the alias table must be extended. Extension is append-only.

---

### Decision Q8: Tempo Governance Pass 1B Load Path

**Decision ID:** Q8
**Title:** How `efl_tempo_governance_v1_1_2_ENFORCEMENT_CLEAN.json` is loaded at runtime

**Options considered:**
- Option A: Load as a separate runtime artifact with its own hash verification, independent of whitelist loading
- Option B: Subsuming tempo governance rules into the whitelist (compiled combined artifact)
- Option C: Encoding tempo governance rules into the Physique frozen module spec (`EFL_PHYSIQUE_v1_0_0_frozen.json`)

**Selected option:** A — separate runtime artifact, loaded and hash-verified independently

**Rationale:** Tempo governance is an independent policy authority (rank 3 in the declared authority chain, Phase 7 §6.1) with its own version history, distinct from per-exercise data in the whitelist. It contains structural enforcement rules (modifier tables, eccentric minimums, downgrade sequences, day-role caps) that govern Pass 1B evaluation. These rules are not per-exercise; they are exercise-class-level and session-level constraints. Merging them into the whitelist would couple two independent authority domains into a single artifact that is harder to version, audit, and update independently. Option C would inappropriately store policy rules in what is designed to be a kernel violation registry artifact.

**Load path declared contract:** `efl_tempo_governance_v1_1_2_ENFORCEMENT_CLEAN.json` is designed to be loaded at process startup, before Pass 1B is invoked, and hash-verified against the SHA-256 pinned in `physique_runtime_manifest_v1_0.json`. See Section 9 for the full load path specification.

**Adapter interaction:** The adapter does not enforce Pass 1B rules. It injects per-exercise ceiling fields (sourced from the whitelist) into the normalized output envelope so that Pass 1B can evaluate them without re-resolving exercise identity. The tempo governance artifact itself is Pass 1B's concern, not the adapter's.

**Consequence for Phase 10:** Phase 10 must implement a separate loader for tempo governance alongside the whitelist loader. Both must be hash-verified before any pass evaluation begins.

**Open dependencies after this decision:** None.

---

### Decision Q7: Kernel-Side Violation Registry Loading Path

**Decision ID:** Q7
**Title:** Where Physique module violation codes live in the kernel `VIOLATION_REGISTRY`

**Options considered:**
- Option A: New frozen Physique module spec file (e.g., `EFL_PHYSIQUE_v1_0_0_frozen.json`) following the exact same pattern as `EFL_SCM_v1_1_1_frozen.json`, loaded by `registry.py`
- Option B: Extension block within a new frozen RAL spec version, embedding Physique module registration and violation registry in the same artifact
- Option C: Separate Physique-specific loader in Phase 10, independent of the existing `registry.py` load pattern

**Selected option:** A — `EFL_PHYSIQUE_v1_0_0_frozen.json`

**Rationale:** Option A is maximally consistent with the existing `registry.py` load pattern, which already loads SCM, MESO, and MACRO module specs and hash-verifies each against its `violationRegistry.registryHash`. No changes to the `registry.py` load loop are required — Physique is added alongside the three existing module specs. Option B would couple violation code registration to the RAL frozen spec bump, creating unnecessary interdependence between two separate governance concerns. Option C introduces a new code path that diverges from the established pattern without justification.

**Required artifact structure for `EFL_PHYSIQUE_v1_0_0_frozen.json`:**
```
{
  "moduleID": "PHYSIQUE",
  "violationRegistry": {
    "registryHash": "<sha256-of-registry-with-hash-zeroed>",
    "violations": [
      {
        "moduleID": "PHYSIQUE",
        "code": "...",
        "severity": "...",
        "overridePossible": false,
        "allowedOverrideReasonCodes": [],
        "violationCap": null,
        "reviewOverrideThreshold28D": null
      }
    ]
  }
}
```

The `registryHash` must be computed using `canonicalize_and_hash` from `efl_kernel/kernel/ral.py`, with the `registryHash` field set to `""` before hashing — identical to the verification pattern already applied to SCM/MESO/MACRO specs in `registry.py`.

**Consequence for Phase 10:** Phase 10 must write `EFL_PHYSIQUE_v1_0_0_frozen.json` with the Physique violation registry and add it to the `registry.py` load list. The `CL_SPEC` hash verification gap (Q4) should be resolved in this same Phase 10 work, since the load loop is being touched.

**Physique-side registry relationship:** `global_reason_codes_v1_0.json` (Physique-side) and `EFL_PHYSIQUE_v1_0_0_frozen.json` (kernel-side) serve different purposes. The global registry governs pass-output validation (which pass owns which code). The kernel registry governs KDO field enforcement (severity, override policy). Both must be populated before a Physique session can produce a valid KDO. They are not duplicates; they are complementary.

**Open dependencies after this decision:** The violation codes and their field values (severity, `overridePossible`, caps, etc.) are the content of `EFL_PHYSIQUE_v1_0_0_frozen.json`. This content is Phase 10 work, not Phase 9. Phase 9 defines only the artifact structure.

---

### Decision Q3: Override Reason Code Cap Policy

**Decision ID:** Q3
**Title:** Policy for Physique override reason codes submitted without a cap value

**Options considered:**
- Option A: Require explicit `defaultMaxOverridesPer28D` on every Physique override reason code; reject registration of any code without this field
- Option B: Assign a system-wide default cap (e.g., 2) to any code that omits the field
- Option C: Allow uncapped codes, relying on `compute_effective_cap` returning `float("inf")` as a deliberate policy for certain codes

**Selected option:** A — explicit cap required; no uncapped Physique override reason codes permitted

**Rationale:** `compute_effective_cap` in `ral.py` returns `float("inf")` when no candidates are found — effectively no ceiling. This is a gap risk, not a deliberate design feature, as confirmed by Q3's origin (Phase 7 §3.3 observation). Option B introduces a silent default that may not be appropriate for all Physique override types. Option C makes the absence of a cap indistinguishable from a misconfigured entry. The correct policy is to require explicit declaration so that every Physique override reason code has a known, auditable cap.

**Policy statement (governing):** Any Physique override reason code submitted for registration in the RAL `RALOverrideReasonRegistry` must include an explicit non-null `defaultMaxOverridesPer28D` integer value. A code submitted without this field, or with a null value, must be rejected at registration time. This applies to all override reason codes governing the PHYSIQUE module. No uncapped Physique override codes are permitted.

**Consequence for Phase 10:** When writing Physique override reason code entries into the new frozen RAL spec version, each entry must include a `defaultMaxOverridesPer28D` value. The registrar is responsible for determining the appropriate cap value based on DCC policy; Phase 9 does not prescribe specific cap values.

**Open dependencies after this decision:** None. Cap values for specific Physique override codes are Phase 10 content decisions.

---

### Decision Q6: GOVERNANCE Module Interaction

**Decision ID:** Q6
**Title:** Whether Physique evaluation uses the GOVERNANCE module

**Options considered:**
- Option A: Defer entirely — GOVERNANCE remains a no-op module for Physique; Phase 10 does not implement GOVERNANCE gates
- Option B: Implement a Physique GOVERNANCE evaluation gate in Phase 10
- Option C: Define a GOVERNANCE module spec now and defer implementation to a later phase

**Selected option:** A — Defer. GOVERNANCE remains a no-op for Physique evaluation. Out of Phase 10 scope.

**Rationale:** `kernel.py` line 122–123 implements GOVERNANCE as an empty-violation return — there is no `run_governance_gates` function anywhere in the codebase. No Physique policy authority consulted during Phase 9 inspection mandates GOVERNANCE-module evaluation as a prerequisite for session legality. Introducing GOVERNANCE evaluation in Phase 10 would expand scope beyond what has been specified in Phases 7–9, violating the "no phase may be skipped" constraint (a GOVERNANCE spec would be required first). The conservative and correct decision is deferral.

**Consequence for Phase 10:** Phase 10 does not add GOVERNANCE gates. The GOVERNANCE branch in `kernel.py` remains as-is (returns empty violations). If GOVERNANCE evaluation is ever needed, it requires its own specification phase before implementation.

**Open dependencies after this decision:** None for Phase 10. GOVERNANCE evaluation remains an open future scope item, not an open question for current phases.

---

## 3. Canonical Mode Label Vocabulary

**Status: Authoritative. Supersedes any conflicting label in other Physique artifacts.**

| Pass | Mode label | Definition |
|------|-----------|------------|
| Pass 0 (PARSE) | `PRE_LAW` | Pre-enforcement input parsing and adapter normalization. No legality decisions made. Failure halts the pipeline before any LAW pass. |
| Pass 1A (DCC Legality) | `LAW` | Authoritative for DCC training legality. Outcome is final. No lower mode may override a LAW rejection. |
| Pass 1B (Tempo Structural Safety) | `LAW` | Authoritative for tempo structural safety. Outcome is final. Governed by tempo governance authority. |
| Pass 2 (MCC Modulation) | `CONTROL` | May downgrade, defer, rotate, or suppress within DCC-legal space. May not override a LAW-mode illegal or rejected outcome. |
| Pass 3 (Advisory) | `INFO` | May annotate or warn. May not alter any LAW or CONTROL decision. |

### 3.1 Fields updated in `global_reason_codes_v1_0.json`

The `validation_pass_structure` object was updated as follows:

| Field path | Before | After |
|-----------|--------|-------|
| `validation_pass_structure.pass_2.mode` | `"CONTEXT"` | `"CONTROL"` |
| `validation_pass_structure.pass_3.mode` | `"INFORMATIONAL"` | `"INFO"` |

All 55 reason code entries in `reason_codes[]` are unchanged. All other fields in the document are unchanged. The `pass_0.mode`, `pass_1a.mode`, `pass_1b.mode` fields were already `"PRE_LAW"` and `"LAW"` respectively and required no change.

### 3.2 Known variance

`efl_tempo_governance_v1_1_2_ENFORCEMENT_CLEAN.json` `validator_pass_semantics.pass_2.mode` remains `"CONTEXT"` and `pass_3.mode` remains `"INFORMATIONAL"` (read-only artifact). This variance is documented and non-blocking. Phase 10 implementers follow Section 3 of this document, not the tempo governance vocabulary.

---

## 4. Canonical Exercise ID Contract

### 4.1 Canonical runtime format

**Canonical format: `ECA-PHY-NNNN`**

Where `N` is a zero-padded four-digit decimal integer. This format is sourced from `efl_whitelist_v1_0_3.json` field `canonical_id`. The whitelist is the runtime exercise authority (Phase 8 classification: `future_integration_target`, binding phase target: Phase 10).

**Primary key at runtime:** The adapter resolves exercise identity by looking up the incoming exercise identifier in the loaded whitelist using `canonical_id` as the primary key. If the incoming ID is already in `ECA-PHY-NNNN` format and exists in the whitelist, resolution succeeds directly.

### 4.2 Alias table (authoring ID → canonical ID)

Because `adult_physique_v1_0_2.json` (support/spec artifact) uses `ECA-{FAMILY}-NNN` format, and authoring sessions may reference these IDs, the adapter is designed to maintain an explicit alias table. The alias table maps authoring-format IDs to canonical `ECA-PHY-NNNN` IDs.

**Alias table policy:**
- The alias table is a Phase 10 artifact, defined when the Physique loader is implemented
- It is append-only: aliases may be added, never removed or renamed
- It must be integrity-verified at load time (hash-checked) alongside the whitelist
- If an incoming exercise ID is not found in the whitelist directly AND is not present in the alias table, the adapter must fail closed (halt with `UNKNOWN_EXERCISE_ID` error)
- The alias table must not be inlined into the whitelist; it is a separate resolution artifact

**Known alias entries (to be formalized in Phase 10):** The seven ID-family prefixes in `adult_physique_v1_0_2.json` (`ECA-SQUAT-*`, `ECA-HINGE-*`, `ECA-PRESS-*`, `ECA-PULL-*`, `ECA-CARRY-*`, `ECA-ISOLATE-*`, `ECA-TRUNK-*`) must each be mapped to corresponding `ECA-PHY-NNNN` entries. The mapping itself requires a content decision (which `ECA-PHY-NNNN` corresponds to which `ECA-SQUAT-NNN`) that is Phase 10 work.

### 4.3 Normalization failure behavior

If an exercise ID cannot be resolved — neither directly from the whitelist nor via the alias table — the adapter must:
- Halt immediately
- Return `UNKNOWN_EXERCISE_ID` error with the unresolved ID and its position in the input
- Not proceed to Pass 1A
- Not apply partial normalization to the remaining exercises

---

## 5. Adapter Input Envelope (Declared Architecture)

**Status: Declared Architecture — Target Behavior. This schema is not currently implemented.**

The adapter is designed to receive a structured input envelope containing the proposed session or prescription, authority version declarations, and the exercise list in authoring-shape format. The following describes the required top-level fields.

### 5.1 Required top-level fields

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `authority_versions` | object | Caller | Declared versions of all governing authorities. See §5.2. |
| `execution` | object | Caller | Request identity fields (request_id, timestamp). |
| `module_id` | string | Caller | The kernel module being evaluated (e.g., `"PHYSIQUE"`). |
| `evaluation_context` | object | Caller | athleteID and module-specific context fields. |
| `window_context` | array | Caller | Window entries (windowType, anchorDate, startDate, endDate, timezone). |
| `session` | object | Caller | The proposed session: day_role, readiness_state, frequency_context, exercises[]. |

### 5.2 Authority version declarations

All governing authorities must be declared by the caller. Version checking is the adapter's responsibility.

| Field | Required value format | Example |
|-------|----------------------|---------|
| `authority_versions.dcc` | String matching DCC document version | `"DCC-PHYSIQUE-v1.2.1"` |
| `authority_versions.whitelist` | String matching whitelist version | `"EFL_WHITELIST_v1.0.3"` |
| `authority_versions.tempo_governance` | String matching tempo governance version | `"EFL_TEMPO_GOVERNANCE_v1.1.2-ENFORCEMENT_CLEAN"` |
| `authority_versions.mcc` | String matching MCC version | `"MCC-DCC-PHYSIQUE-v1.0.1-PATCHPACK"` |
| `authority_versions.global_reason_codes` | String matching reason code registry version | `"EFL_GLOBAL_REASON_CODES_v1.0.0"` |

The adapter must verify each declared version matches the loaded artifact's version field. A mismatch between declared and loaded version is an `AUTHORITY_VERSION_MISMATCH` error and halts the pipeline.

### 5.3 Exercise entry in input envelope (authoring shape)

Each exercise in `session.exercises[]` may arrive in authoring shape:

| Field | Type | Notes |
|-------|------|-------|
| `exercise_id` | string | May be `ECA-PHY-NNNN` or authoring-format alias |
| `band` | integer | Proposed band (0–3) |
| `node` | integer | Proposed node (1–3) |
| `h_node` | string | Proposed H-node (H0–H4); may be overridden by whitelist |
| `tempo` | string | ECICT tempo string (E:IB:IT:C), optional |
| `day_role` | string | DAY_A / DAY_B / DAY_C / DAY_D |
| `sets` | integer | Proposed sets |
| `reps` | integer | Proposed reps |
| `overrides` | array | Caller-supplied override declarations, if any |

The adapter must not trust authoring-shape `movement_family`, `push_pull`, `horiz_vert`, `band_max`, `node_max`, `tempo_class`, or tempo ceilings from the caller. All these fields are injected from the loaded whitelist.

---

## 6. Adapter Normalization Contract (Declared Architecture)

**Status: Declared Architecture — Target Behavior. None of these steps are currently implemented.**

The adapter is designed to execute the following steps in strict sequence. Any step failure halts the pipeline immediately. No partial normalization is applied.

### Step 1: Authority version verification

Verify each declared `authority_versions` value matches the corresponding loaded artifact version. Any mismatch → `AUTHORITY_VERSION_MISMATCH` halt.

### Step 2: Input schema validation

Validate the full input envelope against the adapter input schema. Any missing required field, wrong type, or unrecognized field → `INCOMPLETE_INPUT` halt.

### Step 3: Exercise ID resolution

For each exercise in `session.exercises[]`:

1. If `exercise_id` matches `ECA-PHY-NNNN` format and exists in the loaded whitelist → resolved; proceed to Step 4.
2. If `exercise_id` matches an alias table entry → resolve to the `ECA-PHY-NNNN` canonical ID; proceed to Step 4.
3. Otherwise → `UNKNOWN_EXERCISE_ID` halt with the unresolved ID and position.

### Step 4: Canonical field injection

For each resolved exercise, inject the following fields from the whitelist entry into the normalized exercise record. These fields overwrite any caller-supplied values.

| Field injected | Whitelist source field | Overwrites caller value |
|---------------|----------------------|------------------------|
| `canonical_id` | `canonical_id` | Always |
| `movement_family` | `movement_family` | Always |
| `volume_class` | `volume_class` | Always |
| `tempo_class` | `tempo_class` | Always |
| `h_node_base` | `h_node` | Always (renamed to `h_node_base` to distinguish from effective H-node, which Pass 2 computes) |
| `band_max` | `band_max` | Always |
| `node_max` | `node_max` | Always |
| `day_role_allowed` | `day_role_allowed` | Always |
| `push_pull` | `push_pull` | Always |
| `eccentric_max` | `eccentric_max` | Always |
| `isometric_bottom_max` | `isometric_bottom_max` | Always |
| `isometric_top_max` | `isometric_top_max` | Always |
| `explosive_concentric_allowed` | `explosive_concentric_allowed` | Always |
| `tempo_can_escalate_hnode` | `tempo_can_escalate_hnode` | Always |

### Step 5: `horiz_vert` normalization to MCC runtime enum domain

The MCC runtime enum domain for `horiz_vert` is: `["horizontal", "vertical", "sagittal", "frontal"]` (sourced from `mcc-v1-0-1-patchpack.json` `$defs.HorizVert`).

Apply the following deterministic mapping table. If the whitelist value after injection is not in this table, halt with `UNKNOWN_HORIZ_VERT_LABEL`.

| Whitelist `horiz_vert` value | Normalized MCC value | Notes |
|------------------------------|---------------------|-------|
| `"horizontal"` | `"horizontal"` | Pass-through |
| `"vertical"` | `"vertical"` | Pass-through |
| `"sagittal"` | `"sagittal"` | Pass-through |
| `"frontal"` | `"frontal"` | Pass-through |
| `"Incline"` | `"horizontal"` | Incline press is a horizontal push pattern; mapped to closest MCC plane of motion enum. Sole richer label in whitelist v1.0.3. |
| `null` | `null` (pass-through) | Lower-body, core, and carry movements exempt from push/pull pattern balance counting. Null is preserved; Pass 2 treats null as exempt from pattern balance. |
| Any other value | — | `UNKNOWN_HORIZ_VERT_LABEL` halt. Do not guess. Do not default. |

The normalized field name in the output envelope is `horiz_vert_normalized`. The original whitelist value is preserved as `horiz_vert_raw` for auditability.

### Step 6: Tempo mode classification

For each exercise, classify `tempo_mode` based on `movement_family` and `pattern_plane` as sourced from the whitelist:

| Condition | `tempo_mode` assigned |
|-----------|----------------------|
| `pattern_plane` is `"Sagittal"`, `"Horizontal"`, `"Vertical"`, `"Frontal"`, `"Transverse"` (rep-based) | `"ECICT"` |
| `movement_family` is `"Carry/Sled"` or `"Carry"` | `"N/A_DISTANCE"` |
| `pattern_plane` is `"Isometric"` | `"N/A_DURATION"` |

If `tempo_mode` is `"N/A_DISTANCE"` or `"N/A_DURATION"`, the adapter marks the exercise as exempt from tempo parsing in Pass 1B.

### Step 7: Output envelope assembly

Assemble the normalized output envelope (see Section 7) from the validated and injected fields. The output envelope is the sole input to Pass 1A. Pass 1A must never receive un-normalized or unresolved exercise data.

### Conflict policy (governing)

If any mapping is missing, any whitelist field is null where a non-null value is required for a downstream pass, or any normalization step encounters an ambiguous or conflicting value, the adapter must fail closed and halt. It must not apply partial normalization and continue. It must not default silently.

---

## 7. Adapter Output Envelope (Declared Architecture)

**Status: Declared Architecture — Target Behavior.**

The output of the adapter is the normalized input envelope passed to Pass 1A. The following guarantees apply:

1. **Every exercise has a `canonical_id`** in `ECA-PHY-NNNN` format, confirmed to exist in the loaded whitelist.
2. **All whitelist-sourced fields are injected and authoritative.** No Pass 1A gate may re-resolve exercise identity or re-source whitelist fields from the caller.
3. **`horiz_vert_normalized` is in the MCC enum domain** (`horizontal`, `vertical`, `sagittal`, `frontal`, or `null`). The value `"Incline"` and any other richer label will never appear in the output.
4. **`tempo_mode` is classified** per Step 6; exercises marked `N/A_DISTANCE` or `N/A_DURATION` are explicitly exempt from Pass 1B tempo parsing.
5. **`h_node_base` is the whitelist H-node value**, not a caller-supplied value. Pass 2 computes `h_node_effective` from this base plus the tempo modifier.
6. **Authority versions are embedded** in the output envelope so that downstream passes can assert the authority context under which normalization occurred.

### 7.1 Output envelope top-level fields

| Field | Content |
|-------|---------|
| `authority_versions` | As declared in input and verified by adapter |
| `module_id` | As declared in input |
| `evaluation_context` | As declared in input (not modified by adapter) |
| `window_context` | As declared in input (not modified by adapter) |
| `session` | Session fields from input, with `exercises[]` replaced by normalized exercise records |
| `adapter_trace` | Object recording: normalization steps applied, any alias resolutions, `horiz_vert` mappings applied, and adapter version |

---

## 8. Stop Conditions and Failure Modes

**These are the Pass 0 stop conditions per Phase 7 §5.4.2.** Any failure in the adapter halts the pipeline before Pass 1A is invoked.

| Error code | Condition | Required error fields |
|-----------|-----------|----------------------|
| `AUTHORITY_VERSION_MISMATCH` | A declared `authority_versions` value does not match the loaded artifact's version | `field`, `declared_version`, `loaded_version` |
| `INCOMPLETE_INPUT` | A required field is missing from the input envelope | `missing_field`, `path` |
| `UNKNOWN_EXERCISE_ID` | An exercise ID is not found in the whitelist and not in the alias table | `exercise_id`, `position_in_array` |
| `UNKNOWN_HORIZ_VERT_LABEL` | A whitelist `horiz_vert` value is not in the normalization mapping table | `exercise_id`, `horiz_vert_value` |
| `WHITELIST_FIELD_NULL` | A whitelist field required for a downstream pass is null for a specific exercise | `exercise_id`, `field_name`, `required_by_pass` |
| `SCHEMA_VALIDATION_FAILED` | Input envelope does not conform to the adapter input schema | `path`, `issue`, `value` |
| `ADAPTER_LOAD_FAILURE` | A required artifact (whitelist, alias table) is not loaded or fails hash verification at startup | `artifact`, `failure_type` |

**Error output format (declared architecture):**

```json
{
  "pass": 0,
  "mode": "PRE_LAW",
  "status": "HALT",
  "error_code": "<one of the above codes>",
  "errors": [
    {
      "code": "<error_code>",
      "path": "<field path or exercise position>",
      "value": "<offending value, if applicable>",
      "detail": "<human-readable description>"
    }
  ]
}
```

All error outputs must be machine-parseable. No partial normalization output is produced on halt. The absence of a normalized output envelope signals Pass 1A must not execute.

---

## 9. Tempo Governance Pass 1B Load Path

### 9.1 Q8 decision implementation

Per Decision Q8 (Section 2): `efl_tempo_governance_v1_1_2_ENFORCEMENT_CLEAN.json` is designed to load as a separate runtime artifact, independently of the whitelist.

### 9.2 Load path declared contract

The target contract specifies:

- `efl_tempo_governance_v1_1_2_ENFORCEMENT_CLEAN.json` is designed to be loaded at process startup, before any pass evaluation begins
- The loaded artifact must be hash-verified against the SHA-256 pinned in `physique_runtime_manifest_v1_0.json` (`870ea66b75fa0f0d33e2fa69bb530ce63a833f67126926cce6edd432d5e2d1c9`)
- Hash verification failure must cause a startup halt — the process must not proceed to evaluation
- The tempo governance artifact is designed to be the sole runtime source for: the H-node modifier table (`h_node_modulation.tempo_modifier_table`), eccentric minimum rules (`eccentric_minimum_rules`), escalation policy (`h_node_modulation.escalation_policy`), day-role H-node caps (`day_role_cap_enforcement.day_role_h_node_max_values`), TUT ceiling definitions, and the deterministic downgrade sequence (`deterministic_downgrade_sequence`)

### 9.3 Adapter relationship to tempo governance

The adapter does not load or enforce tempo governance rules. The adapter's only interaction with tempo governance rules is indirect: it injects the per-exercise ceiling fields (`eccentric_max`, `isometric_bottom_max`, `isometric_top_max`, `explosive_concentric_allowed`, `tempo_can_escalate_hnode`, `tempo_class`) from the whitelist into the normalized output envelope, making them available for Pass 1B enforcement without re-resolving exercise identity.

Pass 1B applies the structural safety rules from the loaded tempo governance artifact against the injected per-exercise fields in the normalized envelope.

---

## 10. Kernel-Side Violation Registry

### 10.1 Q7 decision implementation

Per Decision Q7 (Section 2): the kernel-side Physique violation registry is a new frozen spec file, `EFL_PHYSIQUE_v1_0_0_frozen.json`, loaded by `efl_kernel/kernel/registry.py` alongside the existing module specs.

### 10.2 Required artifact structure

`EFL_PHYSIQUE_v1_0_0_frozen.json` is designed to contain:

```json
{
  "moduleID": "PHYSIQUE",
  "violationRegistry": {
    "registryHash": "<computed by canonicalize_and_hash with field zeroed>",
    "violations": [
      {
        "moduleID": "PHYSIQUE",
        "code": "<violation code string>",
        "severity": "<QUARANTINE | HARDFAILNOOVERRIDE | HARDFAILOVERRIDEPOSSIBLE | WARNING | CLAMP>",
        "overridePossible": false,
        "allowedOverrideReasonCodes": [],
        "violationCap": null,
        "reviewOverrideThreshold28D": null
      }
    ]
  }
}
```

The `registryHash` must be computed using `canonicalize_and_hash` from `efl_kernel/kernel/ral.py`, with `registryHash` set to `""` before hashing — identical to the verification applied to `EFL_SCM_v1_1_1_frozen.json`, `EFL_MESO_v1_0_2_frozen.json`, and `EFL_MACRO_v1_0_2_frozen.json` in `registry.py`.

### 10.3 Hash verification requirement

The `registry.py` load loop is designed to add `EFL_PHYSIQUE_v1_0_0_frozen.json` to its verification loop. Hash verification failure must raise `RuntimeError` and halt process startup. This is the same behavior as the existing module spec verification.

### 10.4 Violation code content

The specific violation codes to be placed in `EFL_PHYSIQUE_v1_0_0_frozen.json` are Phase 10 content work. They must be sourced from `global_reason_codes_v1_0.json` (Physique-side registry) and must not include codes from other module registries. Only codes with `"namespace": "DCC"` or `"namespace": "MCC"` that are governed by the Physique evaluation pipeline should appear.

### 10.5 Registry relationship

`global_reason_codes_v1_0.json` and `EFL_PHYSIQUE_v1_0_0_frozen.json` serve complementary roles:

- `global_reason_codes_v1_0.json`: governs post-pass output validation — is this code allowed in this pass?
- `EFL_PHYSIQUE_v1_0_0_frozen.json`: governs KDO field enforcement — what severity and override policy apply to this violation code in `enforce_kernel_owned_fields`?

Both must be loaded before a Physique session can produce a valid KDO.

---

## 11. Override Reason Code Cap Policy

### 11.1 Q3 decision implementation

Per Decision Q3 (Section 2): no uncapped Physique override reason codes are permitted.

### 11.2 Governing policy statement

Any Physique override reason code submitted for registration in the EFL RAL `RALOverrideReasonRegistry` must satisfy both of the following conditions:

1. **Explicit cap required:** The entry must include a non-null `defaultMaxOverridesPer28D` integer value greater than zero.
2. **Module scope explicit:** The entry must include `"PHYSIQUE"` in its `allowedModules` array.

A code submitted without `defaultMaxOverridesPer28D`, or with a null or zero value, must be rejected at registration time.

### 11.3 Failure behavior

If `compute_effective_cap` is called for a Physique override reason code and returns `float("inf")` (because no cap candidates are found), this indicates a registration error, not a policy decision. The runtime is designed to treat a `float("inf")` cap for a Physique code as a configuration failure and quarantine the session rather than permit unlimited overrides.

This behavior is to be specified in the Phase 10 implementation of the Physique gate function.

---

## 12. GOVERNANCE Module Interaction

### 12.1 Q6 decision implementation

Per Decision Q6 (Section 2): GOVERNANCE module evaluation is out of Phase 10 scope. GOVERNANCE remains a no-op for Physique evaluation.

### 12.2 Current state (implementation truth)

`kernel.py` accepts `"GOVERNANCE"` as a valid `module_id` but executes no gate function for it, returning an empty violations list. This behavior is unchanged by Phase 10.

### 12.3 Phase 10 scope impact

Phase 10 must not add GOVERNANCE gates for Physique. The GOVERNANCE branch in `kernel.py` remains unchanged. Any future GOVERNANCE evaluation requires a dedicated specification phase before implementation.

---

## 13. Open Questions Carried Forward

### Q2: RAL clean-session label

**Status:** Open — not resolved in Phase 9.
**Description:** `compute_effective_label` in `ral.py` returns `"CLAMP"` when there are zero violations. The RAL spec `precedenceOrder` ends with `"CLAMP"` but does not define a distinct clean/approved label. Whether `"CLAMP"` is the intended zero-violation label for a Physique session, or whether a dedicated label is required, must be confirmed by the RAL spec owner.
**Owner:** RAL spec owner.
**Resolution path:** Confirm RAL spec intent. If `"CLAMP"` is not the correct zero-violation label, a new frozen RAL spec version is required before Physique violation codes are registered (this would be bundled with the PHYSIQUE module registration version bump).
**Must resolve before:** Registration of Physique violation codes in the RAL (prior to Phase 10 implementation).

### Q4: CL_SPEC hash verification gap

**Status:** Open — ownership decision required.
**Description:** `EFL_Canonical_Law_v1_2_1.json` is loaded in `registry.py` without hash verification, unlike `EFL_SCM_*`, `EFL_MESO_*`, `EFL_MACRO_*`. This is a known gap.
**Owner:** Either the current kernel team (kernel patch) or Phase 10 implementation scope.
**Resolution path:** Phase 10 is already touching `registry.py` to add `EFL_PHYSIQUE_v1_0_0_frozen.json` to the load loop. The CL_SPEC hash verification gap should be closed in the same Phase 10 change, since the load pattern is already being modified. The fix is: add hash verification for `CL_SPEC` following the same pattern as the three module specs (zero `registryHash`, compute `canonicalize_and_hash`, compare to `CLVIOLATIONREGISTRY.registryHash` or equivalent).
**Recommended owner:** Phase 10 (bundle with Physique loader work as a correction to the existing gap).
**Must resolve before:** Phase 10 completion.

### Q5: Physique module ID finalization and frozen RAL spec version bump

**Status:** Partially resolved by Phase 9 decisions; final artifact is Phase 10 work.
**Description:** The working designation `PHYSIQUE` is confirmed as intent (Phase 7 §9.1, Phase 8 `module_registration_intent`). The RAL spec `EFL_RAL_v1_2_0_frozen.json` does not register `PHYSIQUE`. A new frozen RAL spec version is required.
**Resolution path:**
1. Q7 is now decided (Option A: `EFL_PHYSIQUE_v1_0_0_frozen.json`). The `registryHash` of that file's violation registry is a prerequisite input for the `moduleRegistration.registryHash` field in the new RAL spec.
2. Q2 must be resolved before the new RAL spec is written (if `CLAMP` is incorrect for zero violations, the RAL spec itself changes).
3. Required window types and required context fields for `PHYSIQUE` module must be defined in Phase 10.
4. Once all inputs are available, the new frozen RAL spec is produced following CLAUDE.md §3 protocol: new versioned file (e.g., `EFL_RAL_v1_3_0_frozen.json`), `documentHash` recomputed via `canonicalize_and_hash`, `SPEC_PATH` in `ral.py` updated.
**Owner:** Phase 10.
**Must resolve before:** Phase 10 completion.

---

## 14. Phase 10 Prerequisites Checklist

Phase 10 (Physique Loader/Registry Hook) must not begin until all items below are confirmed complete or in-progress with a clear owner.

| # | Prerequisite | Traceable to | Status |
|---|-------------|-------------|--------|
| 1 | Phase 7 `Physique_Runtime_Binding_Spec_v1_0.md` approved | Phase 7 | Complete |
| 2 | Phase 8 `physique_runtime_manifest_v1_0.json` approved | Phase 8 | Complete |
| 3 | Phase 9 `Physique_Pre_Pass_Adapter_Spec_v1_0.md` approved | This document | This phase |
| 4 | Canonical mode label vocabulary confirmed (`CONTROL` / `INFO`) | Section 3 | This phase — `global_reason_codes_v1_0.json` patched |
| 5 | Canonical exercise ID format confirmed (`ECA-PHY-NNNN`) | Section 4 | This phase |
| 6 | Alias table contract defined (policy in §4.2; content is Phase 10 work) | Section 4.2 | Policy: this phase. Content: Phase 10 |
| 7 | `horiz_vert` normalization mapping table defined and authoritative | Section 6 Step 5 | This phase |
| 8 | Adapter normalization steps documented (Steps 1–7) | Section 6 | This phase |
| 9 | Adapter stop conditions and error codes documented | Section 8 | This phase |
| 10 | Tempo governance load path confirmed (separate artifact, hash-verified) | Section 9 | This phase (Decision Q8) |
| 11 | Kernel-side violation registry artifact name and structure confirmed (`EFL_PHYSIQUE_v1_0_0_frozen.json`) | Section 10 | This phase (Decision Q7) |
| 12 | Override reason code cap policy confirmed (explicit cap required) | Section 11 | This phase (Decision Q3) |
| 13 | GOVERNANCE module deferral confirmed (no Phase 10 scope) | Section 12 | This phase (Decision Q6) |
| 14 | Shell v1 documents patched with declared-architecture header note | Phase 7 §10.2 | Required before Phase 10. Not yet done — owner must action. |
| 15 | Q2 (RAL clean-session label) resolved or formally deferred with owner acknowledgement | Section 13 | Open — must be resolved or formally deferred before Physique violation codes are written |
| 16 | Q4 (CL_SPEC hash gap) assigned to Phase 10 and scheduled | Section 13 | Open — Phase 10 scope recommended |
| 17 | Physique violation codes defined (content of `EFL_PHYSIQUE_v1_0_0_frozen.json`) | Section 10.4 | Phase 10 content work |
| 18 | Alias table content defined (authoring ID → `ECA-PHY-NNNN` mappings) | Section 4.2 | Phase 10 content work |
| 19 | Required window types and required context fields for `PHYSIQUE` module defined | Section 13 Q5 | Phase 10 content work |
| 20 | New frozen RAL spec version (`EFL_RAL_v1_3_0_frozen.json`) written per CLAUDE.md §3 | Section 13 Q5 | Phase 10 — requires items 15, 17, 19 complete first |

---

## 15. Non-Negotiable Architectural Constraints

These are the same seven constraints from Phase 7 §11, confirmed as governing all remaining phases.

1. **Deterministic legality.** Given identical inputs and the same loaded authority artifact versions, the runtime must produce identical outcomes on every invocation. No randomness, no timestamp-based branching in legality decisions, no LLM outputs in the legality path.

2. **Validation precedes publish.** A Physique session may not reach a legal publish state without passing all registered gate checks for its module. The adapter (Pass 0) must complete successfully before Pass 1A executes.

3. **Default deny / quarantine on missing dependencies.** If any required dependency is unavailable at adapter time (whitelist entry missing, alias table entry missing, authority version mismatch), the session must be quarantined, not approved by default. Unknown exercise ID = halt. Missing whitelist field = halt.

4. **Frozen specs remain frozen.** No artifact in `efl_kernel/specs/` may be edited in place. New versions follow the frozen spec protocol in CLAUDE.md §3.

5. **Append-only registry discipline.** Reason codes, violation codes, alias table entries, and H-node mapping entries, once registered, may not be removed or renamed. New entries may be added via formal versioned updates.

6. **No builder before real runtime.** Authoring tools and builder interfaces (Phase 18) must not be built before Phase 14 (Real Dependency Provider) and Phase 15 (Persisted Evaluation Path) are complete.

7. **LLM optional, never authoritative.** The runtime must produce correct legality outcomes with or without LLM involvement. LLM output is never a dependency for a KDO decision. The adapter, Pass 1A, Pass 1B, Pass 2, and Pass 3 stop-condition enforcement must all operate deterministically without LLM participation.

---

**END OF SPECIFICATION**

Document: `Physique/Physique_Pre_Pass_Adapter_Spec_v1_0.md`
Version: 1.0.0
Status: SPEC-DRAFT
Phase: 9 of 18
Date: 2026-03-06
