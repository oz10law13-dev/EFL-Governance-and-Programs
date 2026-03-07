# Minimal Runtime Shell v1.0
## Bounded Compiler Architecture for DCC-Physique v1.2.1 + MCC

**Status:** DESIGN-LOCKED  
**Version:** 1.0.0  
**Date:** 2026-01-25  
**Authority Dependencies:**
- DCC-Physique v1.2.1 (immutable law)
- ECA v1.2 (exercise catalog authority)
- efl_tempo_governance_v1_1_2_ENFORCEMENT_CLEAN.json (active tempo authority under DCC)
- MCC v1.0.0/v1.0.1-PATCHPACK (meso constraint controller)
- LLM Execution Protocol v1.0 (runtime behavior contract)
**Authority Boundary Note:** This runtime shell is enforcement infrastructure, not a competing law source. It is subordinate to controlling `Physique/DCC-Physique-v1.2.1-PATCHED.md` and active tempo authority `Physique/efl_tempo_governance_v1_1_2_ENFORCEMENT_CLEAN.json`.

> **DECLARED ARCHITECTURE — NOT CURRENT IMPLEMENTATION**
> This document describes a target-state runtime architecture. As of Phase 9 (2026-03-06), no `runtime/` module path exists in the repository. The pre-pass validator, orchestrator, commit/rollback service, trace layer, and all module references in Section 12 are declared implementation contracts, not currently deployed code. The authoring artifact (`adult_physique_v1_0_2.json`) and the runtime-adjacent whitelist (`efl_whitelist_v1_0_3.json`) are distinct artifacts with different roles; see `Physique_Project_State_Memo_Post_Phase6.md` §Best governance answer and `Physique_Runtime_Binding_Spec_v1_0.md` §4.3 for the canonical distinction. Phase 10 is the first implementation phase.

---

## Table of Contents

1. [System Objective](#1-system-objective)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Authority & Immutability Model](#3-authority--immutability-model)
4. [Pre-Pass Input Validator](#4-pre-pass-input-validator)
5. [LLM Orchestrator](#5-llm-orchestrator)
6. [Post-Pass Output Validator](#6-post-pass-output-validator)
7. [Commit / Rollback Service](#7-commit--rollback-service)
8. [Trace + Hash Layer](#8-trace--hash-layer)
9. [API Surface](#9-api-surface)
10. [JSON Schema Specifications](#10-json-schema-specifications)
11. [Ledger Delta Model](#11-ledger-delta-model)
12. [Implementation Scaffold](#12-implementation-scaffold)
13. [UI / Export Neutrality](#13-ui--export-neutrality)
14. [Non-Goals](#14-non-goals)
15. [Versioning & Stability](#15-versioning--stability)

---

## 1. System Objective

The Minimal Runtime Shell exists to guarantee that:

1. **The LLM cannot guess, infer, or drift** — all inputs are schema-validated and ECA-resolved before the LLM sees them
2. **All legality decisions are auditable, replayable, and reproducible** — via canonical hashing and immutable trace storage
3. **State (MCC ledgers) is atomic, persistent, and reversible** — via delta-based commit/rollback
4. **The system fails closed on ambiguity, missing data, or authority violations** — no defaults, no inference, no "close enough"

### Core Principle

**The LLM produces JSON only. The shell decides truth.**

The LLM is a bounded execution engine, not a planner. It applies immutable law (DCC), enforces stateful restrictions (MCC), and explains outcomes (advisory) — but never touches persistence, never invents rules, and never expands authority.

---

## 2. High-Level Architecture

```
Client / UI / API
        |
        v
┌─────────────────────┐
│ Pre-Pass Validator  │  ← schema + ECA resolution + fail-closed
└─────────────────────┘
        |
        v
┌─────────────────────┐
│ LLM Orchestrator    │  ← LAW → CONTROL → ADVISORY (mode-locked)
└─────────────────────┘
        |
        v
┌─────────────────────┐
│ Post-Pass Validator │  ← schema + reason-code enforcement
└─────────────────────┘
        |
        v
┌─────────────────────┐
│ Commit / Rollback   │  ← atomic ledger updates (delta-based)
└─────────────────────┘
        |
        v
┌─────────────────────┐
│ Trace + Hash Store  │  ← immutable audit record
└─────────────────────┘
```

### Hard Rule

**The LLM never reads or writes persistence. Ever.**

---

## 3. Authority & Immutability Model

| Layer | Role | Mutable | Notes |
|-------|------|---------|-------|
| **DCC-Physique v1.2.1** | Training law (legal/illegal) | ❌ | Highest authority; stops all lower ranks |
| **ECA v1.2** | Exercise definitions | ❌ | Exact IDs only; canonical source of truth |
| **MCC** | Stateful restriction | ❌ | Can only restrict/defer/rotate; cannot expand legality |
| **Execution Protocol** | Runtime law | ❌ | Compiler contract; defines pass behavior |
| **Runtime Shell** | Enforcement infrastructure | ✅ | No authority; mechanically enforces higher layers |
| **LLM Output** | Disposable suggestions | ✅ | Zero authority; discarded if conflicts with higher ranks |

### Conflict Resolution (Non-Negotiable)

- If two authorities disagree → **higher rank wins automatically**
- If Authority 3 (MCC) attempts to expand legality beyond Authority 1 (DCC) → **reject the MCC action**
- If LLM output contradicts any higher authority → **discard LLM output, return legal decision only**

---

## 4. Pre-Pass Input Validator (Outside LLM)

### 4.1 Responsibilities

1. **JSON Schema validation** — enforce types, enums, required fields
2. **ECA ID resolution** — resolve every `eca_id` against the canonical datastore
3. **ECA version pinning** — enforce single ECA version per run
4. **Fail-closed error reporting** — return machine-grade errors with exact field paths

**No defaults. No inference. No "close enough."**

### 4.2 Canonical Input Envelope

```json
{
  "authority_versions": {
    "dcc": "DCC-PHYSIQUE-v1.2.1",
    "eca": "ECA-v1.2",
    "mcc": "MCC-v1.0.0"
  },
  "execution": {
    "request_id": "uuid",
    "timestamp": "iso8601"
  },
  "proposal": {
    "frequency": 4,
    "day_role": "DAY_A",
    "readiness_state": "GREEN",
    "route": "SUBMAX_HYPERTROPHY_VOLUME",
    "meso_week": 3,
    "session_blocks": {
      "PRIME_min": 10,
      "PREP_min": 10,
      "WORK_min": 28,
      "CLEAR_min": 8
    },
    "proposed_band": 2,
    "proposed_node": 2,
    "proposed_h_node": "H1",
    "exercises": [
      {
        "eca_id": "ECA-000123",
        "band": 2,
        "node": 2,
        "h_node": "H1"
      }
    ]
  },
  "state_inputs": {
    "route_history": [],
    "family_axis_history": [],
    "c_day_focus_history": [],
    "density_ledger": {},
    "chronic_readiness_history": []
  }
}
```

### 4.3 ECA Resolution Rules

For each `exercises[i].eca_id`:

1. **Must exist** in ECA datastore
2. **Must match** declared `eca` version in `authority_versions`
3. **Canonical fields are injected:**
   - `name`
   - `movement_family`
   - `node_max`
   - `volume_class`
   - `push_pull`, `horiz_vert`
   - archetype flags

4. **Authoring-taxonomy boundary (deterministic):**
   - ECA/whitelist authoring may include richer labels than MCC runtime enums (e.g., `horiz_vert = "Incline"`).
   - Before MCC schema validation, runtime MUST normalize richer authoring labels into the active MCC enum domain (`horizontal|vertical|sagittal|frontal`) via an explicit adapter contract.
   - If no mapping is defined for a richer label, runtime MUST fail closed (reject) rather than defaulting or silently collapsing categories.

### 4.4 Design Choice: Fail-Closed (Recommended for v1)

**Policy:** If proposal fields conflict with ECA canonical values → return `ECA_FIELD_CONFLICT` and halt.

This keeps "what the LLM saw" and "what the engine believes" identical, making the canonical hash meaningful.

**Alternative (v2):** Normalize mode — shell overwrites proposal fields with ECA canonical values and logs normalization events.

### 4.5 Pre-Pass Error Format

```json
{
  "status": "INCOMPLETE",
  "error_code": "UNKNOWN_EXERCISE",
  "errors": [
    {
      "path": "proposal.exercises[1].eca_id",
      "issue": "not_found",
      "value": "ECA-XYZ"
    }
  ]
}
```

#### Allowed Error Codes

- `INCOMPLETE_INPUT` — missing required field(s)
- `UNKNOWN_EXERCISE` — ECA ID not found
- `ECA_VERSION_MISMATCH` — mixed ECA versions in one run
- `ECA_FIELD_CONFLICT` — proposal field conflicts with canonical ECA value
- `AUTHORITY_INVERSION` — attempt to override higher authority

---

## 5. LLM Orchestrator (Mode-Locked)

### 5.1 Pass Separation (Non-Negotiable)

| Pass | Mode | Purpose | Allowed | Forbidden |
|------|------|---------|---------|-----------|
| **Pass 1** | LAW | DCC legality only | Apply rules verbatim; emit reason codes | Optimization, intent interpretation, suggestions |
| **Pass 2** | CONTROL | MCC restriction only | Downgrade, defer, rotate, suppress | Rule creation, permission expansion, "better alternatives" |
| **Pass 3** | ADVISORY | Explanation only | Explain outcomes, surface warnings, present compliant alternatives | Changing legality, inventing rules, coaching to circumvent law |

Each pass:
- **Separate invocation** — fresh context each time
- **Explicit mode field required** — shell enforces mode matching
- **No shared chat history** — prevents cross-mode leakage

### 5.2 Pass Invocation Contract

```json
{
  "mode": "LAW",
  "input": { "...normalized input..." }
}
```

If the response `mode` does not match the requested `mode` → **reject**.

### 5.3 Execution Ordering (Hard Rule)

1. Run **Pass 1** with `mode=LAW`
   - If `dcc_status = "ILLEGAL"` → **STOP** (store trace; do not call Pass 2)
2. Else run **Pass 2** with `mode=CONTROL` and include ledger inputs
3. Run **Pass 3** with `mode=ADVISORY` only after Pass 2 (or after Pass 1 if MCC inputs absent)

---

## 6. Post-Pass Output Validator (Outside LLM)

### 6.1 Responsibilities

1. **Enforce exact JSON schemas per pass** — no extra fields (`additionalProperties: false`)
2. **Verify reason codes** against append-only registry
3. **Enforce execution ordering:**
   - Pass 2 forbidden if Pass 1 = ILLEGAL
   - Pass 3 forbidden if Pass 1 = ILLEGAL
4. **Reject mode mismatches** — response mode must equal requested mode

### 6.2 Required Pass Envelope

Every pass output must include:

```json
{
  "mode": "LAW",
  "pass": 1,
  "...": "pass-specific fields"
}
```

### 6.3 Reason Code Registry

- **Single source of truth:** `reason_codes.json`
- **Append-only** — never remove or rename codes
- **Scoped codes:**
  - DCC codes → Pass 1 only
  - MCC codes → Pass 2 only
  - Warning types → Pass 3 only

Unknown code = **hard failure**.

### 6.4 Post-Pass Error Example

```json
{
  "status": "INVALID_OUTPUT",
  "error_code": "SCHEMA_VIOLATION",
  "errors": [
    {
      "path": "dcc_reason_codes[0]",
      "issue": "unknown_reason_code",
      "value": "NEW_CODE"
    }
  ]
}
```

#### Allowed Error Codes

- `SCHEMA_VIOLATION` — JSON shape mismatch
- `UNKNOWN_REASON_CODE` — code not in registry
- `MODE_MISMATCH` — response mode ≠ requested mode
- `PASS_OUT_OF_ORDER` — attempted Pass 2/3 after Pass 1 ILLEGAL

---

## 7. Commit / Rollback Service (Ledger-Backed)

### 7.1 Transaction Model

**Propose → Validate → Commit**

1. **Propose:** pre-pass validated input
2. **Validate:** Pass 1/2/3 + post-pass validation
3. **Commit:** atomic ledger update + session issuance

**Rollback:** inverse ledger deltas

### 7.2 Ledger Delta Model (Core Concept)

Every committed session stores **deltas**, not just totals.

```json
{
  "route_history_delta": [
    { "meso": 3, "day_role": "DAY_A", "route": "SUBMAX_HYPERTROPHY_VOLUME" }
  ],
  "density_delta": [
    { "key": "total_node3_sets", "delta": 4 },
    { "key": "h3_sessions_7d", "delta": 1 }
  ],
  "family_axis_delta": [
    { "week": 3, "movement_family": "SQUAT", "axis": "LOAD" }
  ],
  "c_focus_delta": []
}
```

### 7.3 Atomic Commit Rules

- All deltas applied in **one DB transaction**
- Session row + trace row written in **same transaction**
- Failure → **full rollback**
- **No partial state ever visible**

### 7.4 Rollback Rules

1. Load stored delta bundle for `session_id`
2. Apply **inverse deltas**
3. Mark session as `ROLLED_BACK`
4. **Never delete historical trace**

Rollback is **deterministic and auditable**.

### 7.5 Database Schema (Minimum Viable)

#### Table: `sessions`

| Column | Type | Description |
|--------|------|-------------|
| `session_id` | UUID | Primary key |
| `proposal_id` | UUID | Link to validated proposal |
| `status` | ENUM | ILLEGAL, LEGAL, LEGAL-RESTRICTED, ROLLED_BACK |
| `authority_versions` | JSONB | DCC/ECA/MCC versions |
| `created_at` | TIMESTAMP | Creation timestamp |
| `canonical_hash` | VARCHAR(64) | SHA256 hash for reproducibility |

#### Table: `session_traces`

| Column | Type | Description |
|--------|------|-------------|
| `session_id` | UUID | Foreign key to sessions |
| `input_json` | JSONB | Normalized input |
| `pass1_json` | JSONB | Pass 1 output |
| `pass2_json` | JSONB | Pass 2 output (nullable) |
| `pass3_json` | JSONB | Pass 3 output (nullable) |
| `delta_bundle` | JSONB | Ledger deltas for rollback |

#### Table: `ledger_route_history`

| Column | Type | Description |
|--------|------|-------------|
| `athlete_id` | UUID | Scope identifier |
| `meso_number` | INT | Mesocycle number |
| `day_role` | VARCHAR | DAY_A/B/C/D |
| `primary_route` | VARCHAR | Training route |
| `session_id` | UUID | Source session |

#### Table: `ledger_density`

| Column | Type | Description |
|--------|------|-------------|
| `athlete_id` | UUID | Scope identifier |
| `window_start` | DATE | Rolling window anchor |
| `metric_key` | VARCHAR | e.g., "total_node3_sets" |
| `value` | INT | Counter value |
| `session_id` | UUID | Source session |

#### Table: `ledger_family_axis`

| Column | Type | Description |
|--------|------|-------------|
| `athlete_id` | UUID | Scope identifier |
| `week` | INT | Week number |
| `movement_family` | VARCHAR | SQUAT/HINGE/PRESS/PULL/etc. |
| `progression_axis` | VARCHAR | VOLUME/LOAD/DENSITY/COMPLEXITY |
| `session_id` | UUID | Source session |

#### Table: `ledger_c_day_focus`

| Column | Type | Description |
|--------|------|-------------|
| `athlete_id` | UUID | Scope identifier |
| `week` | INT | Week number |
| `c_focus` | VARCHAR | Tissue focus tag |
| `session_id` | UUID | Source session |

---

## 8. Trace + Hash Layer

### 8.1 Stored Artifacts (Immutable)

For every committed session:

- Raw normalized input
- Pass 1 JSON
- Pass 2 JSON (if executed)
- Pass 3 JSON (if executed)
- Final committed plan
- Authority versions
- Delta bundle

### 8.2 Canonical Hash

```python
hash = SHA256(
  normalized_input +
  authority_versions +
  pass1_json +
  pass2_json +
  pass3_json
)
```

Used for:
- **Reproducibility** — same inputs + authorities = same hash
- **Drift detection** — different hash = LLM behavior changed
- **Audit verification** — hash proves integrity

---

## 9. API Surface (Minimal)

### Endpoints

#### `POST /proposals`

**Purpose:** Pre-pass validation + ECA resolution

**Input:** Raw proposal envelope

**Output:**
```json
{
  "proposal_id": "uuid",
  "status": "VALID",
  "normalized_input": { "..." }
}
```

**Errors:** `INCOMPLETE`, `UNKNOWN_EXERCISE`, `ECA_VERSION_MISMATCH`, `ECA_FIELD_CONFLICT`

---

#### `POST /proposals/{id}/validate`

**Purpose:** Run Pass 1/2/3 orchestration

**Input:** None (uses stored proposal)

**Output:**
```json
{
  "validation_id": "uuid",
  "pass1": { "..." },
  "pass2": { "..." },
  "pass3": { "..." },
  "delta_bundle": { "..." }
}
```

**Errors:** `SCHEMA_VIOLATION`, `UNKNOWN_REASON_CODE`, `MODE_MISMATCH`

---

#### `POST /proposals/{id}/commit`

**Purpose:** Atomic ledger update + session issuance

**Input:**
```json
{
  "validation_id": "uuid"
}
```

**Output:**
```json
{
  "session_id": "uuid",
  "canonical_hash": "sha256...",
  "status": "COMMITTED"
}
```

**Errors:** `VALIDATION_NOT_FOUND`, `ALREADY_COMMITTED`, `LEDGER_CONFLICT`

---

#### `POST /sessions/{id}/rollback`

**Purpose:** Reverse ledger deltas

**Input:** None

**Output:**
```json
{
  "session_id": "uuid",
  "status": "ROLLED_BACK",
  "deltas_reversed": { "..." }
}
```

**Errors:** `SESSION_NOT_FOUND`, `ALREADY_ROLLED_BACK`

---

## 10. JSON Schema Specifications

All schemas are located in `runtime/schemas/` and use JSON Schema Draft 2020-12.

See separate schema files:
- `input.schema.json`
- `pass1.schema.json`
- `pass2.schema.json`
- `pass3.schema.json`
- `ledger_delta.schema.json`

Full schema definitions are provided in the implementation scaffold.

---

## 11. Ledger Delta Model

### 11.1 Delta Computation Rules

For each committed session, compute:

1. **Route history delta:**
   - Add one entry: `{ meso: current_meso, day_role: session.day_role, route: session.route }`

2. **Density delta:**
   - Count all `node=3` sets → `total_node3_sets`
   - Count all `band=2 AND node=3` sets → `band2_node3_sets`
   - If session has H3 archetypes → increment `h3_sessions_7d` by 1
   - If session has H4 archetypes → increment `h4_blocks_7d` by 1
   - Sum all working sets → add to `total_working_sets`

3. **Family-axis delta:**
   - For each `movement_family` with a non-`none` progression axis:
     - Add entry: `{ week: current_week, movement_family: family, axis: axis }`

4. **C-day focus delta:**
   - If `day_role = "DAY_C"`:
     - Add entry: `{ week: current_week, c_focus: session.c_day_focus }`

### 11.2 Rollback Computation

To rollback session `S`:

1. Load `S.delta_bundle`
2. For each delta type:
   - **Route history:** delete rows where `session_id = S`
   - **Density:** subtract delta values (or delete rows if stored as deltas)
   - **Family-axis:** delete rows where `session_id = S`
   - **C-day focus:** delete rows where `session_id = S`
3. Mark `S.status = ROLLED_BACK`

---

## 12. Implementation Scaffold

### 12.1 Folder Structure

```
runtime/
├── app.py
├── schemas/
│   ├── input.schema.json
│   ├── pass1.schema.json
│   ├── pass2.schema.json
│   ├── pass3.schema.json
│   └── ledger_delta.schema.json
├── authorities/
│   ├── reason_codes.json
│   ├── eca_store.json
│   └── dcc_rules.json
├── prepass/
│   ├── __init__.py
│   ├── validate_input.py
│   ├── eca_resolver.py
│   └── errors.py
├── postpass/
│   ├── __init__.py
│   ├── validate_output.py
│   └── reason_registry.py
├── orchestrator/
│   ├── __init__.py
│   ├── run_pass1.py
│   ├── run_pass2.py
│   └── run_pass3.py
├── ledger/
│   ├── __init__.py
│   ├── db.py
│   ├── commit.py
│   ├── rollback.py
│   └── deltas.py
├── trace/
│   ├── __init__.py
│   ├── hash.py
│   └── store.py
└── tests/
    ├── test_prepass.py
    ├── test_orchestrator.py
    ├── test_ledger.py
    └── test_integration.py
```

### 12.2 Key Module Responsibilities

#### `prepass/validate_input.py`
- Load and validate against input.schema.json
- Return normalized input or structured error

#### `prepass/eca_resolver.py`
- Fetch canonical ECA records
- Inject canonical fields
- Enforce version pinning
- Detect conflicts (fail-closed mode)

#### `postpass/validate_output.py`
- Validate against pass-specific schema
- Check mode/pass matching
- Verify reason codes against registry

#### `ledger/commit.py`
- Compute delta bundle
- Start DB transaction
- Insert session + trace
- Apply all deltas
- Commit or rollback

#### `ledger/rollback.py`
- Load delta bundle
- Apply inverse deltas
- Mark session ROLLED_BACK
- Maintain trace immutability

---

## 13. UI / Export Neutrality

This runtime supports:

1. **JSON-only services** — pure API, no UI
2. **GUI tools** — front-end over the same endpoints
3. **BridgeAthletic-style exports** — post-commit transformation only

### Export Rule

**Exports occur only after commit and cannot change legality or ledgers.**

Add endpoint: `GET /sessions/{id}/export/bridgeathletic`

This transforms the committed plan into BA-compatible fields but never alters the session or its ledgers.

---

## 14. Non-Goals (Explicit)

This runtime **does not:**

1. Optimize programs
2. Coach users
3. Suggest illegal alternatives
4. Infer missing inputs
5. Auto-correct rule violations
6. Generate training plans from scratch
7. Interpret intent
8. Make subjective decisions

These behaviors are **intentionally excluded** to maintain the bounded compiler model.

---

## 15. Versioning & Stability

### Runtime Shell Version

**Current:** v1.0.0

### Backward Compatibility

This runtime is backward-compatible with:

- DCC-Physique v1.2+
- ECA v1.2+
- MCC v1.x

### Breaking Changes

Breaking changes require:

1. Version increment to v2.0
2. Explicit migration guide
3. Deprecation notice for previous version

### Schema Stability

All JSON Schemas in `schemas/` are **append-only**:

- New optional fields may be added
- Required fields may not be removed
- Enum values may be added but not removed or renamed
- Breaking schema changes require new schema version (e.g., `input.v2.schema.json`)

---

## Final Characterization

This system is now:

**A compiler + transaction engine for training legality, with deterministic execution, stateful risk control, and full auditability.**

At this point:

- **The LLM is replaceable** — it's a JSON transformer, nothing more
- **The runtime is the product** — authority enforcement, state management, and audit trail are system-level concerns, not LLM concerns

---

## Appendix A: Quick Reference

### Error Codes

#### Pre-Pass Errors
- `INCOMPLETE_INPUT`
- `UNKNOWN_EXERCISE`
- `ECA_VERSION_MISMATCH`
- `ECA_FIELD_CONFLICT`
- `AUTHORITY_INVERSION`

#### Post-Pass Errors
- `SCHEMA_VIOLATION`
- `UNKNOWN_REASON_CODE`
- `MODE_MISMATCH`
- `PASS_OUT_OF_ORDER`

#### Commit/Rollback Errors
- `VALIDATION_NOT_FOUND`
- `ALREADY_COMMITTED`
- `LEDGER_CONFLICT`
- `SESSION_NOT_FOUND`
- `ALREADY_ROLLED_BACK`

### Reason Code Scopes

| Scope | Pass | Examples |
|-------|------|----------|
| DCC | Pass 1 (LAW) | `MCC_BAND_NODE_ILLEGAL_COMBINATION`, `MCC_READINESS_VIOLATION` |
| MCC | Pass 2 (CONTROL) | `MCC_ROUTE_SATURATION_VIOLATION`, `MCC_FAMILY_MULTI_AXIS_VIOLATION` |
| Advisory | Pass 3 (ADVISORY) | `SFI_ELEVATED`, `PATTERN_BALANCE_WARNING` |

### Ledger Delta Keys

- `total_node3_sets`
- `band2_node3_sets`
- `h3_sessions_7d`
- `h4_blocks_7d`
- `total_working_sets`

---

**END OF SPECIFICATION**

Document Version: 1.0.0  
Last Updated: 2026-01-25  
Status: DESIGN-LOCKED
