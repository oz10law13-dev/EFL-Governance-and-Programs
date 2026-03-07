# Physique Runtime Binding Spec v1.0

---

## §1 Document Metadata

| Field | Value |
|---|---|
| **Document ID** | PHYSIQUE-RUNTIME-BINDING-v1.0 |
| **Version** | 1.0 |
| **Status** | BINDING |
| **Effective Date** | 2026-03-07 |
| **Supersedes** | Open-decision deferrals in `Physique_Project_State_Memo_Post_Phase6.md`; "declared architecture" scoping in `Minimal_Runtime_Shell_v1_0_SPEC.md` and `Minimal_Runtime_Shell_v1_0_INVARIANTS.md` |
| **Consumed by** | Phase 8 (gate additions), Phase 9 (handshake spec), Phase 10 (SQLite provider and DCC_TEMPO_GOVERNANCE_UNAVAILABLE registration) |
| **Nature** | Spec-only. No code changes, no frozen spec modifications, no violation code registrations are part of this document. |

---

## §2 Authority Hierarchy

The following hierarchy is verbatim from DCC-Physique v1.2.1 §Authority Hierarchy with one runtime-layer addendum:

1. **EFL Governance v4.1** — Organizational top-level law
2. **DCC v2.2** — Session structure, block budgets, PRIME binding, readiness modifiers
3. **DCC-Physique v1.2.1** — Physique-specific adaptations, frequency hardening (Patch F), DCC↔MCC enforcement handshake (Patch F-04)
4. **EPA Exercise Progression Law v1.0.2** — ONEAXISATATIME progression binding
5. **ECA v1.1-K with Patches K–P** — Exercise metadata, enforcement rules, permission gates. Runtime materialization: `efl_whitelist_v1_0_3.json` (see §4)
6. **MCC v1.0.1** — Long-horizon accumulation, adjacency, density, route saturation. Runtime materialization: `mcc-v1-0-1-patchpack.json` (runtime-enforced; not schema-validated at intake)
7. **Tempo Governance v1.1.2** — Tempo prescription, ceilings, minimums, H-node modulation. Runtime materialization: `efl_tempo_governance_v1_1_2_ENFORCEMENT_CLEAN.json`
8. **Runtime Kernel** — Final arbitration layer; kernel-owned fields (severity, overridePossible, allowedOverrideReasonCodes) override all caller input regardless of authority level

**Conflict Resolution Rule:** Always apply the most restrictive rule unless DCC-Physique v1.2.1 explicitly grants a scoped exception.

**Authority Tie-Break Clause:** Program Framework v2.1 and any other generator or template document is non-authoritative. If a framework's frequency composition, sequencing, or template conflicts with DCC-Physique v1.2.1, the framework is wrong by definition. The only valid way to legalize a framework variance is an explicit DCC-Physique patch.

---

## §3 Runtime Architecture — Layer Map

The following describes the *actual* kernel layers as implemented, not declared architecture:

```
POST /evaluate/physique
    │
    ▼
Steps 0–5: RAL guards
  - Step 0: Module registration check
  - Step 1: Required fields + version/hash match
  - Step 2: Window entry shape validation
  - Step 3: Required window types present
  - Step 4: Lineage context fields present
  - Step 5: Lineage key derivation
    │
    ▼
run_physique_adapter()                          [physique_adapter.py]
  ├─ Halt path (UNKNOWN_EXERCISE_ID):
  │    Any physique_session exercise not in WHITELIST_INDEX →
  │    return immediately with halt_codes=["UNKNOWN_EXERCISE_ID"],
  │    normalized_exercises=[], resolved_slot_exercises=[]
  │    No gates run.
  │
  └─ Success path:
       For each physique_session exercise:
         - Resolve via WHITELIST_INDEX (exercise_id key)
         - Inject whitelist fields: tempo_class, eccentric_max, isometric_bottom_max,
           isometric_top_max, explosive_concentric_allowed, tempo_can_escalate_hnode,
           band_max, node_max, h_node, day_role_allowed, movement_family
         - Normalize horiz_vert via HORIZ_VERT_MAP
         - Parse ECICT tempo string (_parse_tempo) →
           tempo_parseable, tempo_parsed, x_in_invalid_position, c_explosive
       For each day_slots exercise:
         - Normalize horiz_vert via HORIZ_VERT_MAP
         - Resolve via _resolve_slot_exercises(normalized_slots, WHITELIST_INDEX):
           exercise_id lookup (eca_id fallback)
           If found: inject _resolved_node_max, _resolved_h_node,
                     _resolved_volume_class, _resolved_movement_family
           If not found: mark _resolution_error=True
    │
    ▼
run_physique_dcc_gates(adapter_result, dep_provider)
                                                [gates_physique.py — Pass 1A+1B, LAW mode]
  - Reads from adapter_result.normalized_exercises (whitelist-resolved)
  - Emits up to 7 DCC tempo violation codes:
    DCC_TEMPO_FORMAT_INVALID, DCC_TEMPO_X_IN_INVALID_POSITION,
    DCC_TEMPO_EXPLOSIVE_NOT_ALLOWED_FOR_EXERCISE, DCC_TEMPO_E_BELOW_MINIMUM,
    DCC_TEMPO_E_EXCEEDS_CEILING, DCC_TEMPO_IB_EXCEEDS_CEILING,
    DCC_TEMPO_IT_EXCEEDS_CEILING
    │
    ▼
run_physique_mcc_gates(day_slots, context, dep_provider, adapter_result)
                                                [gates_physique.py — Pass 2, CONTROL mode]
  - Input: adapter_result.resolved_slot_exercises (whitelist-resolved slot exercises)
  - Early return: if not day_slots → return [] (all MCC gates including L3 silenced)
  - O1 precondition: if day_slots present but context absent → O1 fires, slot gates skip
  - Pre-scan: for each slot exercise with _resolution_error=True →
      emit MCC_ECA_SLOT_UNRESOLVABLE once (tracked by id())
  - Gate groups (all read _resolved_* fields for permission-critical decisions):
      D1: node permission (reads _resolved_node_max; skips on _resolution_error)
      B2: h_node for tempo escalation/downgrade (reads _resolved_h_node; skips on _resolution_error)
      N-cluster: h_node base for h_effective computation (reads _resolved_h_node; skips on _resolution_error)
      + all remaining MCC gates (frequency, adjacency, density, readiness, SFI, etc.)
    │
    ▼
Steps 7–10: Post-gate kernel pipeline
  - Step 7: Kernel-owned field enforcement (enforce_kernel_owned_fields) +
            unregistered code detection (RAL.UNREGISTEREDVIOLATIONCODE)
  - Step 8: Module ID cross-check (RAL.MODULEKDOMODULEIDMISMATCH)
  - Step 9: Override cap enforcement (OC-001/OC-002a/OC-002b)
  - Step 10: REVIEW-OVERRIDE-CLUSTER overlay
    │
    ▼
KDO assembly + SHA-256 seal (freeze_kdo / canonicalize_and_hash)
```

**Structural invariants:**

- The adapter runs before any gate. Gates never access raw payload exercise dicts directly.
- `_resolved_*` prefix denotes whitelist-authoritative fields. Caller-supplied values for these fields are silently ignored by gates.
- The halt path (`halt_codes=["UNKNOWN_EXERCISE_ID"]`) returns before any gate runs. The KDO is assembled with an empty violation list plus the halt synthetic violation.
- MCC gates require both non-empty `day_slots` and a non-empty `context` dict to run past the O1 precondition.

---

## §4 ECA Runtime Binding

**BINDING DECLARATION:** `efl_whitelist_v1_0_3.json` is the authoritative runtime ECA source for this kernel.

| Attribute | Value |
|---|---|
| **Bound artifact** | `C:\EFL-Kernel\Physique\efl_whitelist_v1_0_3.json` |
| **Document ID** | EFL_WHITELIST_v1.0.3 |
| **Exercise count** | 30 |
| **Load point** | `physique_adapter.py` module-level — `WHITELIST_INDEX` dict at import time |
| **Lookup key** | `canonical_id` field (e.g., `"ECA-PHY-0001"`) |
| **Immutability** | Loaded once per process; immutable for the lifetime of any evaluation request (INV-ECA-001 satisfied) |

**Prior "transitional" status rescinded:** `Physique_Project_State_Memo_Post_Phase6.md` described this artifact as "transitional or derived artifact until explicitly bound." The enforcement hardening patch (committed) made v1.0.3 the exclusive authoritative source for `_resolved_*` fields consumed by gates. That label is hereby superseded by this binding declaration.

**Fields injected for physique_session exercises (normalized path):**

| Field | Whitelist source | Gate consumer |
|---|---|---|
| `tempo_class` | `tempo_class` | DCC eccentric minimum gate |
| `eccentric_max` | `eccentric_max` | DCC ceiling gate |
| `isometric_bottom_max` | `isometric_bottom_max` | DCC IB ceiling gate |
| `isometric_top_max` | `isometric_top_max` | DCC IT ceiling gate |
| `explosive_concentric_allowed` | `explosive_concentric_allowed` | DCC explosive gate |
| `tempo_can_escalate_hnode` | `tempo_can_escalate_hnode` | MCC escalation gate |
| `band_max` | `band_max` | (future readiness gate) |
| `node_max` | `node_max` | MCC node permission |
| `h_node` | `h_node` | MCC h_node / B2 gate |
| `day_role_allowed` | `day_role_allowed` | MCC day role gate |
| `movement_family` | `movement_family` | MCC family/pattern gates |
| `horiz_vert_normalized` | `horiz_vert` (via HORIZ_VERT_MAP) | MCC pattern balance |

**Fields injected for day_slots exercises (resolved path):**

| Field | Whitelist source |
|---|---|
| `_resolved_node_max` | `node_max` |
| `_resolved_h_node` | `h_node` |
| `_resolved_volume_class` | `volume_class` |
| `_resolved_movement_family` | `movement_family` |

**Unknown exercise handling:**

| Path | Behavior |
|---|---|
| `physique_session` | Halt immediately → `halt_codes=["UNKNOWN_EXERCISE_ID"]`; no gates run |
| `day_slots` | Mark `_resolution_error=True`; pre-scan emits `MCC_ECA_SLOT_UNRESOLVABLE` (HARDFAIL, `overridePossible=False`, no cap); D1/B2/N-cluster skip via `continue` |

**Authoring vs runtime key distinction:**

- Shell SPEC §4.1 references `eca_id` as the authoring-layer exercise identifier
- The runtime kernel uses `exercise_id` as the primary lookup key in MCC schema (`mcc-v1-0-1-patchpack.json` EXERCISE schema requires `exercise_id`; `eca_id` is not a schema field)
- `_resolve_slot_exercises()` accepts `eca_id` as a fallback (`eid = ex.get("exercise_id") or ex.get("eca_id")`) for authoring-layer payloads
- `eca_id` values and `exercise_id` values inhabit the same `canonical_id` namespace; no collision is possible

**Versioning rule for new exercises:** v1.0.3 must not be edited in-place. A v1.0.4 (or successor) file must be created. The adapter's load path in `physique_adapter.py:10` must be updated to point to the new file.

---

## §5 Slot Exercise Binding

**Current implementation state:** Post-enforcement-hardening patch (committed; all tests passing as of 2026-03-07).

**Resolver function:** `_resolve_slot_exercises(day_slots, whitelist_index)` — `physique_adapter.py:80–109`

**Call site:** `run_physique_gates()` in `gates_physique.py` passes `adapter_result.resolved_slot_exercises` to `run_physique_mcc_gates()`. The raw `adapter_result.day_slots` is NOT passed to MCC gates (O1 precondition guard continues to read `adapter_result.day_slots` for truthiness only).

**Gate field reads (post-patch):**

| Gate | Reads | Skips on |
|---|---|---|
| Pre-scan | `_resolution_error` | — (emit per unresolvable exercise) |
| D1 (MCC_NODE_PERMISSION_VIOLATION) | `_resolved_node_max` | `_resolution_error=True` |
| B2 (h_node / tempo downgrade) | `_resolved_h_node` | `_resolution_error=True` |
| N-cluster (h_effective / SFI) | `_resolved_h_node` | `_resolution_error=True` |

**Pre-scan deduplication:** `id()` of the exercise dict is tracked in `_unresolvable_seen`. Each unresolvable exercise emits `MCC_ECA_SLOT_UNRESOLVABLE` exactly once regardless of how many gate groups would have processed it.

**Cascade suppression:** The `continue` on `_resolution_error` in D1, B2, and N-cluster ensures that a caller who supplies an invalid `eca_id`/`exercise_id` cannot cause secondary violations to appear that would mislead enforcement review.

---

## §6 Tempo Governance Binding

**BINDING DECLARATION:** `efl_tempo_governance_v1_1_2_ENFORCEMENT_CLEAN.json` is the authoritative tempo governance source for this kernel.

| Attribute | Value |
|---|---|
| **Bound artifact** | `C:\EFL-Kernel\Physique\efl_tempo_governance_v1_1_2_ENFORCEMENT_CLEAN.json` |
| **Document ID** | EFL_TEMPO_GOVERNANCE_v1.1.2 |
| **Load point** | `physique_adapter.py` module-level — `TEMPO_GOV`, `ECCENTRIC_MINIMUMS`, `DAY_ROLE_H_NODE_MAX` |

**Authority cascade (from tempo governance §authority_hierarchy):**
1. DCC-Physique v1.2.1 (training law)
2. Tempo Governance v1.1.2 (structural safety: ceilings, minimums, H-node modulation)
3. MCC v1.0.1 (accumulation control: TUT limits, downgrade integration)

Tempo rules may REJECT a DCC-legal prescription if ceilings are exceeded or minimums violated, but cannot LEGALIZE an otherwise illegal prescription.

**Pass structure:**

| Pass | Function | Mode | Authority |
|---|---|---|---|
| 1A (DCC legality) + 1B (structural safety) | `run_physique_dcc_gates()` | LAW | DCC-Physique v1.2.1 + Tempo Governance v1.1.2 |
| 2 (MCC modulation + tempo downgrade) | `run_physique_mcc_gates()` | CONTROL | MCC v1.0.1 + Tempo Governance v1.1.2 |

**Tempo field binding (adapter → gate):**

| Adapter-level constant/field | Source path in JSON | Gate consumer(s) |
|---|---|---|
| `ECCENTRIC_MINIMUMS` | `eccentric_minimum_rules.class_based_minimums` | DCC eccentric minimum gate (Pass 1A) |
| `DAY_ROLE_H_NODE_MAX` | `day_role_cap_enforcement.day_role_h_node_max_values` | MCC downgrade gate (Pass 2) |
| `tempo_class` (per exercise) | whitelist `tempo_class` | DCC eccentric minimum gate |
| `eccentric_max` | whitelist `eccentric_max` | DCC E-ceiling gate |
| `isometric_bottom_max` | whitelist `isometric_bottom_max` | DCC IB-ceiling gate |
| `isometric_top_max` | whitelist `isometric_top_max` | DCC IT-ceiling gate |
| `explosive_concentric_allowed` | whitelist `explosive_concentric_allowed` | DCC explosive gate |
| `tempo_can_escalate_hnode` | whitelist `tempo_can_escalate_hnode` | MCC escalation gate |

**ECICT parse state (adapter → gate, per normalized exercise):**

| Field | Meaning |
|---|---|
| `tempo_parseable` | Whether the ECICT string parsed successfully (bool) |
| `tempo_parsed` | Dict with keys E, IB, IT, C (all int; C=0 when "X") |
| `x_in_invalid_position` | True if "X" appeared outside the C position |
| `c_explosive` | True if C="X" (explosive concentric) |

**H-node modulation (implemented in `gates_physique.py:52–67`):**

```
h_node_effective = h_node_base_numeric + tempo_modifier(E, IB, IT)

tempo_modifier:
  E ≤ 1           → -1
  E ∈ {2,3}       → 0 if (IB+IT) ≤ 2, else +1
  E = 4            → +1 if (IB+IT) ≤ 2, else +2
  E ≥ 5            → +2
```

**TUT calculation (per tempo governance §notation_standard.tut_calculation):**

```
TUT_per_rep = E + IB + IT + C_effective
C_effective = 0 if C = "X", else C
```

---

## §7 Violation Registration

**Registration layers (in enforcement precedence):**

### Layer 1: Frozen spec registries

Loaded in `registry.py` at module import; SHA-256 hash-verified before use:

| Spec file | Module | Violations |
|---|---|---|
| `EFL_SCM_v1_1_1_frozen.json` | SESSION | SCM.* codes |
| `EFL_MESO_v1_0_2_frozen.json` | MESO | MESO.* codes |
| `EFL_MACRO_v1_0_2_frozen.json` | MACRO | MACRO.* codes |
| `EFL_PHYSIQUE_v1_0_1_frozen.json` | PHYSIQUE | 54 MCC/DCC codes |
| `EFL_Canonical_Law_v1_2_2_frozen.json` | CL | CL.* codes |

### Layer 2: VIOLATION_REGISTRY dict

Built in `registry.py`; key `(moduleID, code)`. Populated from frozen specs, then extended by direct insertion.

### Layer 3: Direct insertion (post-spec-loading)

```python
# registry.py — after all spec-loading loops
VIOLATION_REGISTRY[("PHYSIQUE", "MCC_ECA_SLOT_UNRESOLVABLE")] = {
    "severity": "HARDFAIL",
    "overridePossible": False,
    "allowedOverrideReasonCodes": [],
    "violationCap": None,
    "reviewOverrideThreshold28D": None,
    "clampBehavior": None,
}
```

Frozen PHYSIQUE spec NOT modified. `enforce_kernel_owned_fields()` and `lookup_violation()` read from `VIOLATION_REGISTRY`; both work correctly for this entry.

### Layer 4: RAL synthetic violations

`KERNEL_SYNTHETIC_VIOLATIONS` in `ral.py`; separate dict; RAL-owned codes only. Not part of VIOLATION_REGISTRY.

**Bidirectional coverage enforcement:**

`validate_bidirectional_coverage()` in `registry.py:84–91` checks every `(module, code)` in `VIOLATION_REGISTRY` against comment markers in `tests/test_gate_coverage.py`. The test `test_registry_coverage_markers_present` asserts this returns `{}`.

**Current PHYSIQUE runtime code count:** 54 (frozen spec) + 1 direct insertion = **55 registered codes**.

**`DCC_TEMPO_GOVERNANCE_UNAVAILABLE` status:** Not registered. No gate emits it. See §8 Decision 3.

---

## §8 Open Decisions — Binding Verdicts

### Decision 1: e4_clearance Enforcement in PHYSIQUE Gates

**Finding:**

`e4_clearance` is stored in the `op_athletes` table and read by `gates_cl.py:19–20` for `CL.CLEARANCEMISSING` during **SESSION** module evaluations only. No gate in `gates_physique.py` reads `e4_clearance`. No PHYSIQUE violation code exists for clearance failure.

Consequence: An athlete with `e4_clearance=False` (or missing) can receive a PHYSIQUE evaluation result of `LEGALREADY`. The clearance gap exists at the PHYSIQUE layer specifically.

**Verdict: Option B — Formally Reserved for Phase 8.**

The gap is documented as:

> **PHYSIQUE-GATE-GAP-001:** `e4_clearance` is stored and enforced at the SESSION layer via `CL.CLEARANCEMISSING`. PHYSIQUE evaluations do not enforce e4 clearance independently. An athlete without e4 clearance can pass a PHYSIQUE evaluation and receive `LEGALREADY`. Phase 8 must add a PHYSIQUE-specific clearance gate.

Phase 8 requirements to close this gap:
1. Add a new violation code (e.g., `PHYSIQUE_E4_CLEARANCE_MISSING`) to the PHYSIQUE frozen spec
2. Recompute `registryHash` and `documentHash` for the new PHYSIQUE spec version
3. Update RAL `moduleRegistration` entry for PHYSIQUE
4. Add a gate function in `gates_physique.py` that reads `dep_provider.get_athlete_profile()` and checks `e4_clearance`
5. Add a coverage marker and test to `test_gate_coverage.py`

---

### Decision 2: Whitelist v1.0.3 as Runtime Authority

**Finding:**

`physique_adapter.py` loads `efl_whitelist_v1_0_3.json` at module-level as `WHITELIST_INDEX`. The enforcement hardening patch (committed 2026-03-07) made this the exclusive authoritative source for `_resolved_*` fields consumed by D1, B2, and N-cluster gates. The whitelist governs fail-closed behavior for unknown exercises in both the physique_session path (halt) and the day_slots path (MCC_ECA_SLOT_UNRESOLVABLE).

`Physique_Project_State_Memo_Post_Phase6.md` had labelled this artifact "transitional or derived artifact until explicitly bound."

**Verdict: Option A — `efl_whitelist_v1_0_3.json` v1.0.3 is the bound runtime ECA authority.**

Rationale: The enforcement hardening patch already made v1.0.3 the de facto runtime authority. Gates read only `_resolved_*` fields from this source; caller-supplied exercise metadata is ignored for gate decisions. The "transitional" label is superseded by this declaration.

**Binding scope:** All 30 exercises in v1.0.3 are authoritative. Any `canonical_id` not present in this file is unresolvable at runtime and will trigger the appropriate fail-closed response.

**Versioning rule:** New exercises require a new versioned file (v1.0.4 or successor). The file must not be edited in-place. The load path in `physique_adapter.py:10` must be updated to point to the new file after creation.

---

### Decision 3: DCC_TEMPO_GOVERNANCE_UNAVAILABLE Registration

**Finding:**

`DCC_TEMPO_GOVERNANCE_UNAVAILABLE` is referenced conceptually in tempo governance architecture (a code that would fire if tempo governance data is unavailable at evaluation time) but is **not registered** in any frozen spec file, not present in `VIOLATION_REGISTRY`, and not emitted by any gate. If `efl_tempo_governance_v1_1_2_ENFORCEMENT_CLEAN.json` is absent from disk when the adapter module loads, Python raises `FileNotFoundError` — the process fails to start rather than emitting a violation code.

**Verdict: Declare as Phase 10 Requirement.**

Phase 7 cannot register this code (spec-only, no code changes). The current fail-closed behavior (process-level import failure) is acceptable for Phase 7 scope. Phase 10 must:

1. Add `DCC_TEMPO_GOVERNANCE_UNAVAILABLE` to the PHYSIQUE frozen spec `violationRegistry.violations` array
2. Recompute `registryHash` and `documentHash` for the new spec version
3. Update the RAL `moduleRegistration` entry for PHYSIQUE
4. Update the adapter load path (`physique_adapter.py`) to catch `FileNotFoundError` / JSON decode errors and return a `PhysiqueAdapterResult` with `halt_codes=["DCC_TEMPO_GOVERNANCE_UNAVAILABLE"]` instead of raising
5. Add a coverage marker and test to `test_gate_coverage.py`

Until Phase 10: any corruption or absence of tempo governance JSON = process-level failure. This is fail-closed at the service level, not at the violation level.

---

### Decision 4: Minimal Runtime Shell v1.0 Review Verdict

**Review criteria** (from `Physique_Project_State_Memo_Post_Phase6.md`):

| Criterion | Invariant | Current Runtime State | Pass? |
|---|---|---|---|
| Single whitelist version per evaluation run | INV-ECA-001 | `WHITELIST_INDEX` is a module-level dict loaded once at adapter import. It is immutable for the lifetime of any evaluation request. | **PASS** |
| Unknown ECA IDs rejected fail-closed | INV-ECA-002 | `physique_session` path: halt → `UNKNOWN_EXERCISE_ID`. `day_slots` path: `_resolution_error=True` → `MCC_ECA_SLOT_UNRESOLVABLE` (HARDFAIL, no override). | **PASS** |
| DCC authority overrides all | INV-AUTH-001 | `run_physique_dcc_gates()` runs in Pass 1 (LAW mode) before any MCC gate. DCC violations are structurally upstream of MCC arbitration. | **PASS** |
| ECA canonical fields are authoritative for gate decisions | INV-AUTH-002 | `_resolved_*` prefix convention enforces this. D1, B2, N-cluster gates read only resolver-injected fields. Caller-supplied `node_max`/`h_node` values are silently unused by permission gates. | **PASS** |
| horiz_vert normalization applied before gate evaluation | Shell §4.3 rule 4 | `HORIZ_VERT_MAP` applied in `run_physique_adapter()` for both `normalized_exercises` and `normalized_slots` before either is returned. Gates receive only normalized values. | **PASS** |

**Known divergences (not criterion failures):**

**Authoring-contract key (`eca_id` vs `exercise_id`):** Shell SPEC §4.1 uses `eca_id` as the exercise identifier in the authoring-layer contract. The runtime MCC schema (`mcc-v1-0-1-patchpack.json` EXERCISE definition) requires `exercise_id`. The adapter's `_resolve_slot_exercises()` accepts `eca_id` as a fallback precisely to bridge this authoring-vs-runtime gap. Both values inhabit the same `canonical_id` namespace. This is an authoring-vs-runtime architectural boundary, not a contradiction.

**`prepass/eca_resolver.py` reference:** Shell INVARIANTS reference this module as the ECA resolution implementation. This module does not exist in the kernel. It is a declared-architecture artifact from the Shell's "DECLARED ARCHITECTURE" scope, which the disclaimer blocks in both Shell documents correctly identify as not-yet-implemented.

**Verdict: KEEP. No version bump required.**

All five INV- invariants are satisfied by the current runtime kernel. The "DECLARED ARCHITECTURE — NOT CURRENT IMPLEMENTATION" disclaimer blocks in the Shell SPEC and INVARIANTS documents remain accurate and sufficient to distinguish authoring-layer concepts from runtime implementations. No Shell invariant is violated. No Shell section makes a false claim about current implementation state.

A VERSION BUMP REQUIRED verdict would apply only if: (a) an invariant were violated, (b) a Shell section required correction to avoid misleading future implementors, or (c) the Shell needed to declare new architectural commitments. None of these conditions apply.

---

## §9 Implementation Completeness Map

| DCC-Physique v1.2.1 Section | Gate Group | Implementation Status |
|---|---|---|
| §2 Band–Node–H-Node system | D1 (node permission), B2 (h_node) | **ENFORCED** |
| §3.1 DAY A architecture | L1 (DAY_A frequency) | **ENFORCED** |
| §3.2 DAY B architecture | L2 (DAY_B frequency) | **ENFORCED** |
| §3.3 DAY C architecture | Day-C gates (pattern repetition, meso rotation) | **ENFORCED** |
| §3.4 DAY D architecture | Day-D intent gate | **ENFORCED** |
| §4.2 Day-role allocation matrix (A≤1, B≤1 at 3-5×, D-minimum) | L1, L2, L5 | **ENFORCED** |
| §4.2 6× B≤2 (Patch F) | L2 with adjacency dependency | **ENFORCED** |
| §4.5 Adjacency rules (B→B, A_BAND3→B, 3+ consecutive NODE3) | A-gates | **ENFORCED** |
| §4.7 H3 aggregate cap (≤3 sessions/week, ≤2 archetypes/session) | H-gates | **ENFORCED** |
| §4.8 Density ledger (BAND2+NODE3 thresholds) | DN-gates | **ENFORCED** |
| §5 Session structure (volume, duration, WORK block) | SS-gates | **ENFORCED** |
| §6 Training routes (route saturation) | R-gates | **ENFORCED** |
| §7.1–7.2 Readiness states (BAND cap, volume reduction) | RD-gates | **ENFORCED** |
| §7.3 Chronic YELLOW guard (≥3 YELLOW/RED in 7 days) | L3 gate | **ENFORCED** |
| §8 Volume classification (immutability, landmark counting) | VL-gates | **ENFORCED** |
| Tempo Governance v1.1.2 (DCC pass 1A+1B) | `run_physique_dcc_gates()` | **ENFORCED** |
| Tempo Governance v1.1.2 (MCC pass 2 downgrade/escalation) | `run_physique_mcc_gates()` | **ENFORCED** |
| ECA whitelist enforcement — physique_session path | Adapter halt | **ENFORCED** |
| ECA whitelist enforcement — day_slots path | Pre-scan + MCC_ECA_SLOT_UNRESOLVABLE | **ENFORCED** (post-patch) |
| e4_clearance — PHYSIQUE layer | — | **GAP: PHYSIQUE-GATE-GAP-001** (Phase 8) |
| DCC_TEMPO_GOVERNANCE_UNAVAILABLE | — | **GAP: unregistered** (Phase 10) |
| MESO/MACRO Physique-specific gate logic | — | **STUB** (not in scope for Physique phases) |

---

## §10 Non-Goals

This document does not cover and Phase 7 has not produced:

- Code changes of any kind
- Frozen spec file edits (no registryHash or documentHash recomputation)
- Violation code registration in any frozen spec or VIOLATION_REGISTRY
- New gate functions
- SQLite operational provider implementation (Phase 10)
- FastAPI or HTTP service layer changes
- Builder or training program generation logic
- GOVERNANCE module gate logic or spec
- MESO or MACRO Physique-specific gate logic (those modules are stubbed; this spec does not change that)
- Frontend, tenancy, or PostgreSQL migration path
- Phase 8 gate implementation (e4_clearance PHYSIQUE gate)
- Phase 9 handshake spec
- Phase 10 `DCC_TEMPO_GOVERNANCE_UNAVAILABLE` registration and implementation

---

## §11 References

| Document | Path |
|---|---|
| DCC-Physique v1.2.1 | `C:\EFL-Kernel\Physique\DCC-Physique-v1.2.1-PATCHED.md` |
| Tempo Governance v1.1.2 | `C:\EFL-Kernel\Physique\efl_tempo_governance_v1_1_2_ENFORCEMENT_CLEAN.json` |
| ECA Whitelist v1.0.3 | `C:\EFL-Kernel\Physique\efl_whitelist_v1_0_3.json` |
| MCC PatchPack v1.0.1 | `C:\EFL-Kernel\Physique\mcc-v1-0-1-patchpack.json` |
| Global Reason Codes v1.0 | `C:\EFL-Kernel\Physique\global_reason_codes_v1_0.json` |
| Project State Memo Post-Phase6 | `C:\EFL-Kernel\Physique\Physique_Project_State_Memo_Post_Phase6.md` |
| Shell SPEC v1.0 | `C:\EFL-Kernel\Physique\Minimal_Runtime_Shell_v1_0_SPEC.md` |
| Shell INVARIANTS v1.0 | `C:\EFL-Kernel\Physique\Minimal_Runtime_Shell_v1_0_INVARIANTS.md` |
| Physique Adapter | `C:\EFL-Kernel\efl_kernel\kernel\physique_adapter.py` |
| Gates Physique | `C:\EFL-Kernel\efl_kernel\kernel\gates_physique.py` |
| Registry | `C:\EFL-Kernel\efl_kernel\kernel\registry.py` |
| RAL | `C:\EFL-Kernel\efl_kernel\kernel\ral.py` |
| Operational Schema | `C:\EFL-Kernel\efl_kernel\docs\operational_schema.md` |
| EFL Kernel README | `C:\EFL-Kernel\efl_kernel\README.md` |
| CLAUDE.md | `C:\EFL-Kernel\CLAUDE.md` |
