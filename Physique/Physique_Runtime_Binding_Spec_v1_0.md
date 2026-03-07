# Physique Runtime Binding Spec v1.0
## Phase 7 — Physique Runtime Binding Contract

**Status:** SPEC-DRAFT
**Version:** 1.0.0
**Date:** 2026-03-06
**Phase:** 7 of 18 (Track A — Physique Runtime Integration Specs)
**Preceding memo:** `Physique/Physique_Project_State_Memo_Post_Phase6.md`
**Writable by this phase:** this file only

---

## Table of Contents

1. [Purpose and Scope](#1-purpose-and-scope)
2. [Governing Documents and Authority Chain](#2-governing-documents-and-authority-chain)
3. [Current Runtime Implementation Truth](#3-current-runtime-implementation-truth)
4. [Physique Artifact Classification](#4-physique-artifact-classification)
5. [Target Runtime Binding Contract](#5-target-runtime-binding-contract)
6. [Authority Hierarchy and Precedence](#6-authority-hierarchy-and-precedence)
7. [Exercise Identity and Whitelist Contract](#7-exercise-identity-and-whitelist-contract)
8. [MCC Constraint Integration Contract](#8-mcc-constraint-integration-contract)
9. [Kernel Integration Points](#9-kernel-integration-points)
10. [Shell v1 Review Outcome](#10-shell-v1-review-outcome)
11. [Non-Negotiable Architectural Constraints](#11-non-negotiable-architectural-constraints)
12. [Ambiguities and Open Questions](#12-ambiguities-and-open-questions)

---

## 1. Purpose and Scope

This document defines the **runtime binding contract** for Physique artifacts against the EFL Kernel. It is a specification document only. It does not change code, schemas, frozen specs, or database files.

### 1.1 What this spec defines

- Which Physique artifacts are designated as future runtime integration targets
- The declared contract each artifact must satisfy to be considered runtime-bound
- The authority hierarchy that governs Physique evaluation once bound
- The interface points between Physique governance and the existing kernel dispatch path
- The conditions under which Shell v1 documents remain valid, require patching, or require a controlled version bump

### 1.2 What this spec does not define

- Implementation of any loader, registry hook, adapter, or validation bridge (Phase 10–11)
- The operational data schema or SQLite store (Phase 12–13)
- The real dependency provider (Phase 14)
- Builder or authoring tooling (Phase 18)
- Any change to currently frozen EFL_* specs in `efl_kernel/specs/`

### 1.3 Relationship to the roadmap

This is Phase 7. The full Track A sequence is:

| Phase | Title | Status |
|-------|-------|--------|
| 7 | Physique Runtime Binding Spec | This document |
| 8 | Physique Runtime Manifest | Not yet started |
| 9 | Physique Pre-Pass Adapter Spec | Not yet started |

Track B implementation (Phases 10–18) must not begin before Phases 7–9 are complete and reviewed.

---

## 2. Governing Documents and Authority Chain

The following documents govern this spec in precedence order. Lower entries may not contradict higher entries.

| Rank | Document | Role | Location |
|------|----------|------|----------|
| 1 | `CLAUDE.md` | Working rules; immutable during execution | `C:/EFL-Kernel/CLAUDE.md` |
| 2 | `Physique_Project_State_Memo_Post_Phase6.md` | Authoritative current-state memo; overrides any other description of what is or is not runtime-bound | `Physique/` |
| 3 | `DCC-Physique-v1.2.1-PATCHED.md` | Training law authority (legal/illegal); highest domain authority | `Physique/` |
| 4 | `efl_tempo_governance_v1_1_2_ENFORCEMENT_CLEAN.json` | Active tempo authority under DCC | `Physique/` |
| 5 | `EFL_RAL_v1_2_0_frozen.json` | Kernel RAL spec; governs kernel dispatch, violation registry, publish state derivation | `efl_kernel/specs/` |
| 6 | `EFL_SCM_v1_1_1_frozen.json`, `EFL_MESO_v1_0_2_frozen.json`, `EFL_MACRO_v1_0_2_frozen.json`, `EFL_Canonical_Law_v1_2_1.json` | Module violation registries; currently runtime-bound | `efl_kernel/specs/` |
| 7 | This document | Binding contract for Physique integration | `Physique/` |

### 2.1 Authority boundary note

DCC-Physique defines training legality (legal/illegal). The kernel RAL defines kernel-level violation governance (severity, override, publish state). These are currently separate authority domains. This spec defines how they are designed to interoperate once Physique is runtime-bound. They do not currently interoperate at runtime.

---

## 3. Current Runtime Implementation Truth

This section states only what is verifiably true in the current implementation as inspected. It uses present tense only for things that are implemented now.

### 3.1 What is currently runtime-bound

- Frozen specs in `efl_kernel/specs/` are loaded and hash-verified at import time in `efl_kernel/kernel/registry.py` and `efl_kernel/kernel/ral.py`
- Kernel dispatch routes SESSION, MESO, MACRO, and GOVERNANCE modules through `kernel.py`
- Violation registry is built from `EFL_SCM_v1_1_1_frozen.json`, `EFL_MESO_v1_0_2_frozen.json`, `EFL_MACRO_v1_0_2_frozen.json`, and `EFL_Canonical_Law_v1_2_1.json`
- The exercise library at `efl_kernel/specs/EFL_Exercise_Library_100_v1_0_1.json` is loaded at import time by `gates_cl.py` and used for clearance gate evaluation
- `KernelDependencyProvider` defines the interface for runtime aggregate access; `InMemoryDependencyProvider` and `SQLiteDependencyProvider` are the available implementations
- `KDOValidator` derives all allowed field sets from `RAL_SPEC` at class definition time (not hardcoded)
- `freeze_kdo` produces a canonical SHA-256 hash over the full KDO dict

### 3.2 What is not currently runtime-bound

- No Physique artifact in `Physique/` is loaded, imported, validated, or referenced by any file in `efl_kernel/`
- `DCC-Physique-v1.2.1-PATCHED.md` is active policy authority but is not parsed or enforced by any kernel module
- `efl_tempo_governance_v1_1_2_ENFORCEMENT_CLEAN.json` is active tempo authority but is not parsed or enforced by any kernel module
- `efl_whitelist_v1_0_3.json` and `mcc-v1-0-1-patchpack.json` are future integration targets with no current runtime binding
- The Physique exercise ID namespace (`ECA-PHY-*` in `efl_whitelist_v1_0_3.json`, `ECA-SQUAT-*` in `adult_physique_v1_0_2.json`) is entirely separate from the current runtime exercise library (`EFL_Exercise_Library_100_v1_0_1.json`) and the two have not been reconciled
- No Physique violation codes exist in any current module violation registry
- No Physique reason codes exist in the RAL override reason registry

### 3.3 Observed implementation findings from deterministic viability review

The following findings are recorded as context for Phase 8–9 planning:

- `EFL_Canonical_Law_v1_2_1.json` is loaded by `registry.py` without hash verification, unlike the three module specs which are verified. This gap should be addressed before or during Phase 10.
- `compute_effective_cap` in `ral.py` returns `float("inf")` when no caps are registered for a reason code. This means an uncapped override reason code has no ceiling. Whether this is intentional policy or a gap requires confirmation against the RAL spec before Physique override reason codes are registered.
- `compute_effective_label` returns `"CLAMP"` when there are zero violations. Whether `CLAMP` is the intended clean-session label or whether a dedicated clean label (e.g., `APPROVED`) is missing requires RAL spec confirmation.

---

## 4. Physique Artifact Classification

This section records the authoritative classification from the Phase 6 memo. It is reproduced here as a stable reference for Phases 7–9.

### 4.1 Active policy authority — not runtime-bound

| Artifact | Role | Notes |
|----------|------|-------|
| `DCC-Physique-v1.2.1-PATCHED.md` | Training law | Highest domain authority; defines legal/illegal for Physique sessions; not yet kernel-enforced |
| `efl_tempo_governance_v1_1_2_ENFORCEMENT_CLEAN.json` | Tempo authority under DCC | Active enforcement policy; defines tempo ceilings, H-node escalation rules, explosive concentric permissions |

### 4.2 Future integration targets

| Artifact | Designated Role | Blocker before binding |
|----------|-----------------|----------------------|
| `efl_whitelist_v1_0_3.json` | Runtime exercise authority (transitional candidate) | Pre-pass adapter spec (Phase 9); ECA ID namespace reconciliation; canonical identity contract |
| `mcc-v1-0-1-patchpack.json` | MCC constraint schema | MCC integration contract (Section 8); commit-time density validation path; kernel hook (Phase 10–11) |

### 4.3 Support and spec only

| Artifact | Role |
|----------|------|
| `adult_physique_v1_0_2.json` | Best current authoring candidate; richer shape than whitelist v1.0.3; not a runtime artifact |
| `efl_physique_framework_v2_1_tempo_validated.json` | Framework reference; not runtime-bound |
| `Minimal_Runtime_Shell_v1_0_SPEC.md` | Declared runtime shell architecture; see Section 10 for review outcome |
| `Minimal_Runtime_Shell_v1_0_INVARIANTS.md` | Declared invariants; see Section 10 for review outcome |
| `EFL_Physique_Program_Framework_v2_1.md` | Program design reference; not runtime-bound |

---

## 5. Target Runtime Binding Contract

This section defines what it means for a Physique artifact to be considered runtime-bound. These are the conditions the target contract specifies. None of these conditions are currently met.

### 5.1 Definition: runtime-bound

A Physique artifact is runtime-bound when all of the following are true:

1. It is loaded at process startup via a deterministic path with integrity verification (hash or schema)
2. Its content governs a decision that affects a KDO outcome (violation firing, publish state, override eligibility, or severity)
3. The dependency on that artifact is registered in a Physique runtime manifest (Phase 8)
4. At least one test asserts that a missing or corrupted version of the artifact causes a fail-closed outcome

### 5.2 Required contracts for each integration target

#### 5.2.1 Whitelist (`efl_whitelist_v1_0_3.json`)

The target contract specifies:

- A canonical Physique exercise ID format must be established before runtime binding (current formats `ECA-PHY-*` and `ECA-SQUAT-*` are inconsistent across artifacts and must be resolved)
- The whitelist is designed to be the authoritative source of per-exercise constraints: `band_max`, `node_max`, `h_node`, `day_role_allowed`, `volume_class`, `tempo_class`, and tempo ceilings
- A pre-pass adapter (Phase 9) is designed to normalize authoring-shape fields into MCC runtime enum domains before validation
- The adapter must fail closed if no mapping is defined for a richer authoring label (e.g., `horiz_vert = "Incline"` → if no MCC mapping exists, reject; do not silently collapse)
- The whitelist must not be flattened into MCC schema shape directly; the authoring contract and the runtime exercise contract are distinct

#### 5.2.2 MCC (`mcc-v1-0-1-patchpack.json`)

The target contract specifies:

- The MCC schema enforces type safety, identity fields, and permission gates at schema level
- Business logic (frequency composition, route saturation, family-axis locking, pattern balance, density ledger thresholds, H3 aggregate caps, adjacency rules) is designed to be runtime-enforced, not schema-enforced
- MCC is designed to be restriction-only: it may downgrade, defer, rotate, or suppress; it may not expand legality beyond DCC
- Density constraint validation is designed to occur at commit time against current ledger state, not at proposal time
- MCC violation codes must be registered in a Physique-scoped violation registry before kernel integration; they may not be added directly to existing frozen module registries

### 5.3 Binding sequence

The target integration sequence is designed to be:

```
Phase 9: Pre-Pass Adapter Spec defined
Phase 10: Physique Loader/Registry Hook — whitelist loaded, hash-verified, registered
Phase 11: Physique Validation Bridge — MCC constraints evaluated, violations emitted
Phase 12: Operational Data Schema — Physique fields added to operational store
Phase 13: SQLite Operational Store — density ledger and session history persisted
Phase 14: Real Dependency Provider — aggregates sourced from operational store
```

No phase may be skipped. Phase 10 must not begin before Phase 9 is approved.

### 5.4 Validation Pass Contract (Declared Architecture)

**Status: Declared Architecture — Target Behavior. None of these passes are currently implemented for Physique runtime evaluation. This section states the intended execution contract once Physique is runtime-bound.**

#### 5.4.1 Execution order

The target validation pipeline is designed to execute in this fixed order:

```
PARSE (Pass 0)
  → Pass 1A: DCC Legality [LAW]
  → Pass 1B: Tempo Structural Safety [LAW]
  → Pass 2: MCC Modulation [CONTROL]
  → Pass 3: Advisory [INFO]
```

The Phase 9 pre-pass adapter executes as part of Pass 0, before Pass 1A receives any exercise data (see §5.4.5).

#### 5.4.2 Stop conditions

- **Pass 0 fails** (parse error, schema rejection, missing required field, or adapter normalization failure) → halt immediately; do not invoke any LAW-mode pass.
- **Pass 1A returns an illegal outcome** → halt; do not proceed to Pass 1B, Pass 2, or Pass 3.
- **Pass 1B returns a reject outcome** → halt; do not proceed to Pass 2 or Pass 3.
- **Pass 2 exhausts the allowed modulation and downgrade chain without producing a valid candidate** → emit the appropriate MCC failure outcome and require substitution or regeneration; do not proceed to Pass 3 on the failed candidate.

Stop conditions are non-negotiable. No lower-mode pass may execute after a higher-mode pass has issued a halt.

#### 5.4.3 Mode-lock rule

Each pass operates in exactly one mode. Modes are hierarchically ordered and mutually exclusive within a single evaluation run:

| Pass | Mode | Authority |
|------|------|-----------|
| 1A | LAW | Authoritative for DCC training legality; outcome is final |
| 1B | LAW | Authoritative for tempo structural safety; outcome is final |
| 2 | CONTROL | May downgrade, defer, rotate, or suppress within DCC-legal space only |
| 3 | INFO | May annotate or warn; may not alter any LAW or CONTROL decision |

A CONTROL-mode pass may not override a LAW-mode illegal or rejected outcome. An INFO-mode pass may not alter legality or control decisions under any condition.

#### 5.4.4 Reason-code scope by pass ownership

Reason codes are scoped to the pass that owns them. Ownership is determined by the authority that governs the underlying rule — not by code string format or prefix.

| Pass | Owns codes governed by |
|------|------------------------|
| Pass 1A | DCC-Physique training law (band/node/family/day-role legality and DCC↔MCC handshake gates) |
| Pass 1B | Tempo Governance structural safety rules (tempo ceilings, eccentric minimums, H-node effective limits, explosive concentric gate) |
| Pass 2 | MCC restriction and modulation rules (route saturation, density thresholds, adjacency, family-axis locking, downgrade actions, TUT accumulation limits) |
| Pass 3 | Advisory annotations only (SFI warnings, pattern balance notices, and other non-blocking observations) |

A reason code emitted in the wrong pass is a hard failure and must halt evaluation. An unknown reason code in any pass is a hard failure and must halt evaluation. Both conditions apply regardless of which authority registered the code.

#### 5.4.5 Pre-pass adapter placement (Phase 9)

The Phase 9 pre-pass adapter is designed to execute before Pass 1A receives any exercise data. Its responsibilities in the target contract:

- Resolve each exercise identity against the canonical runtime whitelist
- Normalize authoring-shape fields (e.g., richer `horiz_vert` labels) into the MCC runtime enum domain via an explicit, deterministic mapping table
- Inject whitelist-sourced canonical fields (`band_max`, `node_max`, `h_node`, `tempo_class`, tempo ceilings) into the normalized input envelope
- Fail closed if any exercise identity cannot be resolved, or if any authoring-to-runtime normalization mapping is missing or ambiguous

A missing, ambiguous, or conflicting normalization must halt at Pass 0 before Pass 1A is invoked. Pass 1A must never receive un-normalized or unresolved exercise data. The adapter contract itself is the subject of Phase 9.

---

## 6. Authority Hierarchy and Precedence

This section states the declared authority hierarchy for Physique evaluation. This is the target contract. At present, kernel enforcement only covers the EFL_* frozen spec domain.

### 6.1 Declared precedence (target state)

| Rank | Authority | Domain | Mutable | Conflict rule |
|------|-----------|--------|---------|---------------|
| 1 | DCC-Physique v1.2.1 | Training legality (legal/illegal) | No | Stops all lower ranks |
| 2 | EFL RAL v1.2.0 | Kernel violation governance, override policy, publish state | No (frozen) | Governs kernel dispatch outcomes |
| 3 | Tempo governance v1.1.2 | Tempo constraints under DCC | No | Subordinate to DCC; cannot expand DCC legality |
| 4 | MCC v1.0.1 | Mesocycle-level restriction | No (schema) | Can only restrict; cannot expand legality beyond DCC |
| 5 | Whitelist v1.0.3 | Per-exercise identity and constraints | No (once bound) | Sourced from whitelist; not from caller input |
| 6 | Runtime shell / kernel | Enforcement infrastructure | Yes | No authority; mechanically enforces higher layers |
| 7 | LLM output | Disposable suggestions | Yes | Zero authority; discarded if it conflicts with any higher rank |

### 6.2 Conflict resolution (non-negotiable)

- If DCC declares a session illegal, no lower authority may override that decision
- If MCC attempts to expand legality beyond DCC, the MCC action must be rejected
- If LLM output contradicts any authority at rank 1–5, discard LLM output and return the authoritative decision
- LLM may assist with proposal generation, summarization, UI interaction, and constrained draft generation
- LLM may not decide legality, state transitions, reason-code truth, or publish eligibility

### 6.3 Domain boundary: DCC vs RAL

DCC-Physique governs whether a Physique session is **legal or illegal** in the domain of training science law.

The EFL RAL governs **how a violation outcome is processed**: severity, override eligibility, override caps, publish state derivation, and KDO structure.

These are designed to operate in sequence: DCC produces a violation determination; RAL governs how that violation is represented and dispatched in the KDO. The integration contract between them (how Physique violations map to RAL violation registry entries) is to be specified in Phase 8 (Runtime Manifest) and Phase 11 (Validation Bridge).

---

## 7. Exercise Identity and Whitelist Contract

### 7.1 Identity problem (recorded ambiguity)

As of this writing, three distinct exercise ID namespaces exist across Physique artifacts:

| Artifact | ID format observed | Example |
|----------|--------------------|---------|
| `efl_whitelist_v1_0_3.json` | `ECA-PHY-NNNN` | `ECA-PHY-0001` |
| `adult_physique_v1_0_2.json` | `ECA-SQUAT-NNN` | `ECA-SQUAT-001` |
| `efl_kernel/specs/EFL_Exercise_Library_100_v1_0_1.json` | plain string (no namespace prefix) | `"id": "..."` |

These namespaces are not currently reconciled. The runtime binding contract requires one canonical Physique exercise ID format before Phase 10. This reconciliation is an open question recorded in Section 12.

### 7.2 Declared whitelist contract (target state)

The target contract specifies:

- The whitelist is the authoritative source for per-exercise constraints at runtime
- Per-exercise fields that the runtime is designed to consume: `canonical_id` (or equivalent resolved field), `band_max`, `node_max`, `h_node`, `volume_class`, `tempo_class`, `eccentric_max`, `isometric_bottom_max`, `isometric_top_max`, `explosive_concentric_allowed`, `tempo_can_escalate_hnode`, `day_role_allowed`
- These values must be sourced from the loaded whitelist at runtime, not from caller-supplied input
- If a whitelist entry is missing for a requested exercise, the runtime is designed to fail closed (quarantine the session), not default silently

### 7.3 Authoring shape vs runtime shape

The Phase 6 memo established:

- `adult_physique_v1_0_2.json` carries the richer authoring shape (canonical authoring candidate)
- `efl_whitelist_v1_0_3.json` is the transitional/runtime-adjacent shape
- These must not be flattened directly into MCC schema; a deterministic pre-pass adapter is required between them

The pre-pass adapter contract is the subject of Phase 9. Until Phase 9 is complete, the whitelist is a future integration target only.

---

## 8. MCC Constraint Integration Contract

### 8.1 MCC role

The MCC (Meso Constraint Controller) is designed to be the stateful restriction layer beneath DCC legality. Its role is restriction-only:

- Downgrade band or node
- Defer exercises to a later mesocycle week
- Rotate exercises to alternatives within the same movement family
- Suppress advanced H-node techniques (H4→H3, H3→H2)

MCC may not introduce new exercises, increase any magnitude field, or declare a DCC-illegal session legal.

### 8.2 Schema-enforced vs runtime-enforced boundary

The `mcc-v1-0-1-patchpack.json` schema establishes this boundary explicitly. The target contract respects it:

**Schema-enforced (by MCC schema):**
- Type safety
- Identity fields (`exercise_id`, `subject_id`, `session_id`)
- Permission gates (`node <= node_max`)
- ReasonCode enum stability (append-only)
- Minimum required audit fields

**Runtime-enforced (not by schema):**
- Frequency composition rules (DAY_A/B/C/D ratios, 3–6 day bounds)
- Route saturation across mesocycles
- Family-level axis locking (one axis per movement family per week)
- Pattern balance percentages (push/pull, horizontal/vertical, frontal)
- Density ledger thresholds (BAND2+NODE3 counts per window)
- Volume landmarks
- H3 aggregate caps
- D-minimum rules
- Session Fatigue Index (SFI) advisory thresholds
- Readiness-driven BAND/volume downgrades
- C-day mesocycle rotation rules
- Adjacency rules (forbidden day-role patterns)

Runtime-enforced constraints require the operational data schema (Phase 12) and SQLite operational store (Phase 13) before they can be evaluated correctly.

### 8.3 Violation code registration requirement

Before any MCC constraint can fire a violation that reaches the KDO:

- A Physique-scoped violation registry must be defined (Phase 8 — Runtime Manifest)
- Each MCC violation code must have: severity, `overridePossible`, `allowedOverrideReasonCodes`, `violationCap`, `reviewOverrideThreshold28D`
- These entries must be loaded and hash-verified at startup, following the same pattern as `enforce_kernel_owned_fields` in `registry.py`
- MCC violation codes must not be added to existing frozen module registries (`EFL_SCM_*`, `EFL_MESO_*`, `EFL_MACRO_*`)

### 8.4 Commit-time density validation

The target contract specifies that MCC density constraints (e.g., BAND2+NODE3 set counts per 7-day window) must be validated at commit time against current ledger state, not at proposal time. Proposal-time MCC evaluation is advisory. Commit-time check is authoritative. This requires the ledger concurrency model described in `Minimal_Runtime_Shell_v1_0_INVARIANTS.md` (INV-LEDGER-001, INV-LEDGER-002).

---

## 9. Kernel Integration Points

This section identifies where Physique integration is designed to connect to the existing kernel. None of these integration points are currently implemented.

### 9.1 Module registration

The target contract specifies a new module ID — the working designation is `PHYSIQUE` — must be registered in the RAL spec before it can be dispatched by `kernel.py`. This requires a new frozen RAL spec version per the frozen spec protocol in CLAUDE.md Section 3. The new spec must:

- Add `PHYSIQUE` to `RALRequiredWindowsByModule`
- Add `PHYSIQUE` to `KDOSCHEMA.constraints.requiredContextByModule`
- Add a `moduleRegistration` entry for `PHYSIQUE` with `moduleVersion`, `moduleViolationRegistryVersion`, and `registryHash`
- Recompute `documentHash` using `canonicalize_and_hash` from `ral.py`

This spec version bump is the subject of Phase 8 (Runtime Manifest).

### 9.2 Gate function

The target contract specifies a `run_physique_gates` function analogous to `run_scm_gates`, `run_meso_gates`, and `run_macro_gates`. It is designed to:

- Receive `raw_input` and a `KernelDependencyProvider`
- Source all aggregate data (density ledger totals, route history, family-axis history, prior session facts) exclusively from the dependency provider
- Never source aggregates from `raw_input` or any caller-supplied dict (per CLAUDE.md Rule 5)
- Return a list of violation dicts conforming to the Physique violation registry

### 9.3 Dependency provider extension

The `KernelDependencyProvider` interface is designed to be extended with Physique-specific query methods before Phase 10. Required additions include at minimum:

- `get_density_ledger(athlete_id, window_days)` — returns current density counters
- `get_route_history(athlete_id, meso_id)` — returns route history for saturation check
- `get_family_axis_history(athlete_id, week)` — returns family-axis assignments for lock check

These methods must follow the same contract as existing methods: they raise `NotImplementedError` on the base class and are implemented by the concrete provider.

### 9.4 Enforce kernel-owned fields

Once Physique violations are registered, `enforce_kernel_owned_fields` in `registry.py` is designed to overwrite gate-supplied severity and override fields with registry truth for all `PHYSIQUE`-module violation codes. No changes to the existing `enforce_kernel_owned_fields` logic are required; the Physique violations simply need to be present in `VIOLATION_REGISTRY`.

---

## 10. Shell v1 Review Outcome

**Overall outcome: CONDITIONAL**

The Shell v1 documents (`Minimal_Runtime_Shell_v1_0_SPEC.md` and `Minimal_Runtime_Shell_v1_0_INVARIANTS.md`) were reviewed against the five criteria from the Phase 6 memo.

### 10.1 Review criteria and findings

**Criterion 1: Do they still accurately describe fail-closed runtime behavior?**
Finding: YES. The fail-closed principle is stated throughout and is architecturally consistent with the EFL Kernel's existing fail-closed design. The default deny / quarantine behavior described in the Shell matches the kernel's `ILLEGALQUARANTINED` publish state. No patches required for this criterion.

**Criterion 2: Do they accurately describe canonical field injection and normalization boundaries?**
Finding: MOSTLY YES. The pre-pass ECA resolution contract (Section 4 of Shell v1 SPEC) describes field injection correctly and identifies the authoring-taxonomy boundary with the correct fail-closed rule. One gap: the spec does not name the specific adapter artifact (Phase 9) that performs normalization; it describes the behavior but not the artifact boundary. This is acceptable at v1 and can be addressed in Phase 9.

**Criterion 3: Do they distinguish authoring contract vs runtime contract?**
Finding: PARTIALLY. The Shell v1 SPEC identifies the authoring/MCC boundary at Section 4.3 (ECA Resolution Rules, note on richer authoring labels) and correctly states the fail-closed rule for missing mappings. However, the documents do not distinguish between `efl_whitelist_v1_0_3.json` (transitional/runtime-adjacent) and `adult_physique_v1_0_2.json` (richer authoring candidate) as separate artifacts with distinct roles. This distinction was established in Phase 6 and postdates the Shell v1 docs. A minimal patch to the Shell v1 SPEC noting this distinction is recommended before Phase 10, not required before Phase 9.

**Criterion 4: Do they reflect current truth that Physique is not yet runtime-bound?**
Finding: NO. The Shell v1 documents were authored assuming Physique is runtime-bound. They describe the pre-pass validator, orchestrator, commit/rollback service, and trace layer as if they exist. They do not. This is not a defect in the documents' architecture; it is a documentation framing issue. The documents describe target state as implemented state. Before Phase 10, the documents should carry an explicit header note distinguishing declared architecture from current implementation, or a controlled patch should add such a note. This is a required action before Phase 10.

**Criterion 5: Do they accurately describe implemented vs declarative coupling?**
Finding: NO (same root cause as Criterion 4). The module structure in Section 12 (`runtime/` folder tree) is declared architecture, not implemented code. No `runtime/` directory exists in the repo. The invariants in the INVARIANTS document reference enforcement locations (`trace/hash.py`, `ledger/commit.py`, etc.) that do not exist. These are correctly treated as target-state contracts, not current-state descriptions, but the documents do not say so.

### 10.2 Conditional requirements

Shell v1 documents may remain active and be referenced by Phase 8 and Phase 9 under the following conditions:

1. **Required before Phase 10:** A patch (or header note) must be added to both Shell v1 documents explicitly stating that they describe declared architecture, not current implementation, and that no `runtime/` module path currently exists.

2. **Recommended before Phase 10:** A minimal patch to Shell v1 SPEC Section 4 noting the authoring artifact distinction (`adult_physique_v1_0_2.json` vs `efl_whitelist_v1_0_3.json`) established in Phase 6.

3. **Not required:** A full version bump to v2 is not warranted. The architecture described is sound, the invariants are correct, and the fail-closed principles are consistent with the kernel's design. Patch minimally.

### 10.3 Shell v1 invariants that remain fully valid

All invariants in `Minimal_Runtime_Shell_v1_0_INVARIANTS.md` remain architecturally valid as target-state contracts:

- INV-HASH-001/002: Hash determinism — consistent with `canonicalize_and_hash` in `ral.py`
- INV-CODE-001/002: Reason code scoping — consistent with kernel's append-only registry discipline
- INV-LEDGER-001/002: Linearizable commits, commit-time density validation — required by MCC integration (Section 8.4)
- INV-MCC-001: Restriction-only — consistent with Section 8.1 of this spec
- INV-AUTH-001/002: DCC overrides all, ECA canonical fields authoritative — consistent with Section 6
- INV-COMMIT-001/002: Atomic delta application — required before Phase 13
- INV-ROLLBACK-001/002: Inverse delta, trace immutability — consistent with audit requirements
- INV-ECA-001/002: Single version per run, unknown IDs rejected — required before Phase 10

---

## 11. Non-Negotiable Architectural Constraints

These constraints apply to all future phases. They may not be relaxed by implementation decisions.

1. **Deterministic legality.** Given identical inputs and the same loaded authority artifacts, the runtime must produce identical outcomes on every invocation. No randomness, no timestamp-based branching in legality decisions, no LLM outputs in the legality path.

2. **Validation precedes publish.** A Physique session may not reach `LEGALREADY` or `LEGALOVERRIDE` publish state without passing all registered gate checks for its module.

3. **Default deny / quarantine on missing dependencies.** If any required dependency (whitelist entry, density ledger, route history, athlete profile) is unavailable, the session must be quarantined (`ILLEGALQUARANTINED`), not approved by default.

4. **Frozen specs remain frozen.** No artifact in `efl_kernel/specs/` may be edited in place. New versions must follow the frozen spec protocol in CLAUDE.md Section 3.

5. **Append-only registry discipline.** Reason codes and violation codes, once registered, may not be removed or renamed. New codes may be added via new frozen spec versions.

6. **Aggregates from the dependency provider only.** Load totals, density counters, route history, prior session timestamps, and season phase counts must be fetched from `KernelDependencyProvider`. They must never be read from `raw_input` or any caller-supplied dict. This applies to all future Physique gate implementations.

7. **LLM optional, never authoritative.** The system must produce correct legality outcomes with or without LLM involvement. LLM output is never a dependency for a KDO decision.

8. **No builder before real runtime.** Authoring tools and builder interfaces (Phase 18) must not be built before a real dependency provider (Phase 14) and persisted evaluation path (Phase 15) exist.

9. **KDOValidator allowed sets from spec at runtime.** Allowed values for `finalEffectiveLabel`, `finalSeverity`, and `finalPublishState` must be derived from the loaded `RAL_SPEC` at import time. They must not be hardcoded in any validator.

---

## 12. Ambiguities and Open Questions

The following ambiguities are recorded for resolution in Phase 8 (Runtime Manifest) and Phase 9 (Pre-Pass Adapter Spec). They are not resolved in this document.

### Q1: Exercise ID namespace reconciliation

Three exercise ID formats exist across Physique artifacts (`ECA-PHY-*`, `ECA-SQUAT-*`, and the current runtime library format). These must be reconciled into one canonical format before Phase 10. Resolution must specify:
- The canonical format for Physique exercise IDs
- Whether `efl_whitelist_v1_0_3.json` must be re-issued with corrected IDs, or whether an alias table is acceptable
- How the Physique exercise namespace relates to the current `EFL_Exercise_Library_100_v1_0_1.json` namespace (separate domain, or merged registry)

### Q2: RAL clean-session label

`compute_effective_label` returns `"CLAMP"` when there are zero violations. Whether this is the intended label for a clean Physique session, or whether a dedicated label is required, must be confirmed against the RAL spec before Physique violations are registered. If `"CLAMP"` is incorrect for the zero-violation case, a RAL spec version bump is required.

### Q3: Uncapped override reason codes

`compute_effective_cap` returns `float("inf")` when no caps are registered for a reason code. Physique override reason codes will require defined caps before registration. The policy for what happens if a Physique reason code is registered without a cap must be stated explicitly in Phase 8.

### Q4: CL_SPEC hash verification gap

`EFL_Canonical_Law_v1_2_1.json` is loaded in `registry.py` without hash verification, unlike the three module specs. This gap must be addressed. The question is whether this is corrected in the current kernel (requiring a CLAUDE.md Rule 1–2 compliant change) or deferred to Phase 10 as part of Physique loader work. This affects which phase owns the fix.

### Q5: Physique module ID

The working designation for the Physique kernel module is `PHYSIQUE`. This must be confirmed as the canonical module ID before it is registered in the RAL spec. Once registered, it cannot be renamed.

### Q6: GOVERNANCE module

`kernel.py` accepts `GOVERNANCE` as a valid module ID but runs no gates for it (returns empty violations). Whether Physique introduces any GOVERNANCE-module evaluation, or whether GOVERNANCE remains a no-op module, must be clarified in Phase 8.

### Q7: Physique violation registry location

MCC violation codes must not be added to existing frozen module registries. The target location for the Physique violation registry (a new frozen spec file, a Physique-specific registry artifact, or an extension to the RAL) must be determined in Phase 8 before any violation codes are written.

### Q8: Tempo governance integration path

`efl_tempo_governance_v1_1_2_ENFORCEMENT_CLEAN.json` is active policy authority under DCC. Its fields (tempo ceilings, H-node escalation rules, `explosive_concentric_allowed`, `tempo_can_escalate_hnode`) overlap with per-exercise fields in `efl_whitelist_v1_0_3.json`. The precedence rule when they conflict, and whether tempo governance loads as a separate runtime artifact or is subsumed into the whitelist, must be specified in Phase 8.

---

**END OF SPECIFICATION**

Document: `Physique/Physique_Runtime_Binding_Spec_v1_0.md`
Version: 1.0.0
Status: SPEC-DRAFT
Phase: 7 of 18
Date: 2026-03-06
