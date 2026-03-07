# Minimal Runtime Shell v1.0
## Formal Invariants Specification

**Status:** ENFORCEMENT-READY  
**Version:** 1.0.0  
**Date:** 2026-01-25  
**Parent Document:** Minimal Runtime Shell v1.0 Specification

---

## Purpose

This document defines **mechanically-checkable invariants** that bridge the Runtime Shell specification to enforcement-complete implementation. Each invariant:

1. Has a unique identifier (INV-XXX-###)
2. States an assertion that must never be violated
3. Specifies where enforcement occurs in the stack
4. Defines violation behavior (error code + halt condition)
5. Provides test requirements for validation

These invariants are **implementation contracts**, not suggestions.

These invariants are subordinate to controlling `Physique/DCC-Physique-v1.2.1-PATCHED.md` and active tempo authority `Physique/efl_tempo_governance_v1_1_2_ENFORCEMENT_CLEAN.json`; they do not define parallel legality.

---

## Table of Contents

1. [Hash Determinism Invariants (INV-HASH-###)](#1-hash-determinism-invariants)
2. [Reason Code Scoping Invariants (INV-CODE-###)](#2-reason-code-scoping-invariants)
3. [Ledger Concurrency Invariants (INV-LEDGER-###)](#3-ledger-concurrency-invariants)
4. [MCC Restriction-Only Invariants (INV-MCC-###)](#4-mcc-restriction-only-invariants)
5. [Pass 3 Non-Hypothetical Invariants (INV-ADV-###)](#5-pass-3-non-hypothetical-invariants)
6. [Authority Hierarchy Invariants (INV-AUTH-###)](#6-authority-hierarchy-invariants)
7. [Mode-Locking Invariants (INV-MODE-###)](#7-mode-locking-invariants)
8. [Commit Atomicity Invariants (INV-COMMIT-###)](#8-commit-atomicity-invariants)
9. [Rollback Determinism Invariants (INV-ROLLBACK-###)](#9-rollback-determinism-invariants)
10. [ECA Resolution Invariants (INV-ECA-###)](#10-eca-resolution-invariants)

---

## 1. Hash Determinism Invariants

### INV-HASH-001: Canonical JSON Serialization

**Assertion:**  
All JSON inputs to the canonical hash function MUST be serialized using RFC 8785 (I-JSON canonical form) or an equivalent deterministic serializer that guarantees:
- Lexicographic key ordering
- No whitespace variations
- Consistent numeric representation
- Stable array ordering

**Enforcement Location:**  
`trace/hash.py` — hash computation function

**Violation Behavior:**  
- If non-canonical JSON is detected → reject with `HASH_SERIALIZATION_ERROR`
- Hash function must fail-closed (reject input rather than produce non-deterministic hash)

**Test Requirement:**
```python
def test_hash_determinism():
    # Same semantic input with different key order
    input_a = {"b": 1, "a": 2}
    input_b = {"a": 2, "b": 1}
    # Must produce identical hash
    assert hash_canonical(input_a) == hash_canonical(input_b)

    # Different whitespace
    input_c = '{"a": 2, "b": 1}'
    input_d = '{"a":2,"b":1}'
    assert hash_canonical(input_c) == hash_canonical(input_d)
```

**Implementation Note:**  
Python: use `json.dumps(obj, sort_keys=True, separators=(',', ':'))`  
TypeScript: use `canonicalize` from `@stablelib/canonical-json` or `json-canonicalize`

---

### INV-HASH-002: Hash Reproducibility

**Assertion:**  
Given identical:
1. `normalized_input`
2. `authority_versions`
3. `pass1_json`
4. `pass2_json` (or null if not executed)
5. `pass3_json` (or null if not executed)

The canonical hash MUST be identical across all runs, systems, and time periods.

**Enforcement Location:**  
`trace/hash.py` — hash computation  
`trace/store.py` — hash storage validation

**Violation Behavior:**  
- If stored hash ≠ recomputed hash → flag as `HASH_MISMATCH` (audit event, not blocking)
- Used for drift detection, not runtime blocking

**Test Requirement:**
```python
def test_hash_reproducibility():
    # Run same inputs through pipeline twice
    result_1 = full_pipeline(input_bundle)
    result_2 = full_pipeline(input_bundle)

    assert result_1.canonical_hash == result_2.canonical_hash

    # Verify hash can be recomputed from trace
    stored_trace = load_trace(result_1.session_id)
    recomputed_hash = compute_hash(stored_trace)
    assert recomputed_hash == result_1.canonical_hash
```

---

## 2. Reason Code Scoping Invariants

### INV-CODE-001: Pass-Scoped Reason Codes

**Assertion:**  
Reason codes MUST be scoped by namespace and enforced per pass:

- **Pass 1 (LAW):** DCC namespace only (codes starting with `DCC_*` or `MCC_BAND_*`, `MCC_SESSION_*`, etc. from DCC law)
- **Pass 2 (CONTROL):** MCC namespace only (codes starting with `MCC_ROUTE_*`, `MCC_FAMILY_*`, `MCC_C_DAY_*`, `MCC_DENSITY_*`, etc. from MCC restrictions)
- **Pass 3 (ADVISORY):** Advisory namespace only (codes like `SFI_ELEVATED`, `PATTERN_BALANCE_WARNING`, `CHRONIC_YELLOW_GUARD`)

**Enforcement Location:**  
`postpass/validate_output.py` — reason code validator  
`postpass/reason_registry.py` — registry with namespace metadata

**Violation Behavior:**  
- If Pass 1 emits MCC/Advisory code → reject with `REASON_CODE_NAMESPACE_VIOLATION`
- If Pass 2 emits DCC/Advisory code → reject with `REASON_CODE_NAMESPACE_VIOLATION`
- If Pass 3 emits DCC/MCC code → reject with `REASON_CODE_NAMESPACE_VIOLATION`

**Test Requirement:**
```python
def test_reason_code_namespace_enforcement():
    # Pass 1 with MCC code should fail
    pass1_output = {
        "mode": "LAW",
        "pass": 1,
        "dcc_status": "ILLEGAL",
        "dcc_reason_codes": ["MCC_ROUTE_SATURATION_VIOLATION"]  # Wrong namespace
    }
    with pytest.raises(ValidationError, match="REASON_CODE_NAMESPACE_VIOLATION"):
        validate_pass_output(pass1_output, expected_mode="LAW", expected_pass=1)
```

**reason_codes.json Structure:**
```json
{
  "codes": [
    {
      "code": "MCC_BAND_NODE_ILLEGAL_COMBINATION",
      "namespace": "DCC",
      "allowed_passes": [1],
      "severity": 5
    },
    {
      "code": "MCC_ROUTE_SATURATION_VIOLATION",
      "namespace": "MCC",
      "allowed_passes": [2],
      "severity": 3
    },
    {
      "code": "SFI_ELEVATED",
      "namespace": "ADVISORY",
      "allowed_passes": [3],
      "severity": 2
    }
  ]
}
```

---

### INV-CODE-002: Unknown Reason Codes

**Assertion:**  
All reason codes emitted by any pass MUST exist in `reason_codes.json` registry.

**Enforcement Location:**  
`postpass/validate_output.py`

**Violation Behavior:**  
- If code not in registry → reject with `UNKNOWN_REASON_CODE`
- Include code value in error for debugging

**Test Requirement:**
```python
def test_unknown_reason_code_rejection():
    pass1_output = {
        "mode": "LAW",
        "pass": 1,
        "dcc_status": "ILLEGAL",
        "dcc_reason_codes": ["INVENTED_CODE_XYZ"]
    }
    with pytest.raises(ValidationError, match="UNKNOWN_REASON_CODE.*INVENTED_CODE_XYZ"):
        validate_pass_output(pass1_output, expected_mode="LAW", expected_pass=1)
```

---

## 3. Ledger Concurrency Invariants

### INV-LEDGER-001: Linearizable Commits Per Subject

**Assertion:**  
Commits for the same subject (athlete/program) MUST be serialized such that no two commits overlap in their critical section (delta computation + ledger write).

This can be achieved via:
- **Advisory lock:** `SELECT pg_advisory_lock(subject_id)` before commit
- **Optimistic concurrency:** Store `ledger_version` with each ledger row; reject commit if version changed

**Enforcement Location:**  
`ledger/commit.py` — transaction start

**Violation Behavior:**  
- If commit detects concurrent modification → rollback transaction and return `LEDGER_CONFLICT`
- Client should retry with fresh ledger state

**Test Requirement:**
```python
def test_concurrent_commit_rejection():
    # Simulate two concurrent commits for same subject
    proposal_1 = create_proposal(subject_id="athlete-123", node3_sets=15)
    proposal_2 = create_proposal(subject_id="athlete-123", node3_sets=15)

    # Start both transactions
    commit_1_started = start_commit(proposal_1)
    commit_2_started = start_commit(proposal_2)

    # First commit should succeed
    result_1 = complete_commit(commit_1_started)
    assert result_1.status == "COMMITTED"

    # Second commit should fail (ledger changed)
    result_2 = complete_commit(commit_2_started)
    assert result_2.status == "LEDGER_CONFLICT"
```

**Implementation Recommendation:**  
Advisory lock (simpler for v1):
```python
def commit_session(subject_id, delta_bundle):
    with db.transaction():
        db.execute("SELECT pg_advisory_xact_lock(%s)", [hash(subject_id)])
        # Now safe to read ledgers, compute constraints, apply deltas
        apply_deltas(delta_bundle)
        db.commit()
```

---

### INV-LEDGER-002: Density Validation at Commit Time

**Assertion:**  
MCC density constraints (e.g., `total_node3_sets ≤ 20` in 7-day window) MUST be validated against current ledger state **at commit time**, not proposal time.

**Enforcement Location:**  
`ledger/commit.py` — after acquiring lock, before applying deltas

**Violation Behavior:**  
- If density constraint violated after recomputing with fresh ledger state → return `DENSITY_LEDGER_EXCEEDED` and rollback
- Pass 2 validation is advisory; commit-time check is authoritative

**Test Requirement:**
```python
def test_commit_time_density_validation():
    # Session validated with node3_sets = 18 (under limit)
    # But between validation and commit, another session added 5 sets

    session_1 = validate_and_commit(node3_sets=5)  # total now 5
    session_2_proposal = validate_session(node3_sets=18)  # Pass 2 says OK (5+18=23, but uses stale ledger)

    # Commit should recheck and fail
    with pytest.raises(CommitError, match="DENSITY_LEDGER_EXCEEDED"):
        commit_session(session_2_proposal)
```

---

## 4. MCC Restriction-Only Invariants

### INV-MCC-001: No Introduction of New Elements

**Assertion:**  
Pass 2 (CONTROL) outputs MUST only:
- Remove exercises from proposal
- Downgrade existing exercises (reduce band/node/h_node)
- Defer existing exercises to later week
- Rotate existing exercises to alternative ECA ID (same movement family)
- Suppress advanced techniques (H4→H3, H3→H2)

Pass 2 MUST NOT:
- Add new exercises not in original proposal
- Add new sets to existing exercises
- Increase band/node/h_node
- Add new session blocks

**Enforcement Location:**  
`postpass/validate_output.py` — Pass 2 validator

**Violation Behavior:**  
- If Pass 2 introduces new exercise → reject with `MCC_EXPANSION_VIOLATION`
- If Pass 2 increases any magnitude → reject with `MCC_EXPANSION_VIOLATION`

**Test Requirement:**
```python
def test_mcc_cannot_add_exercises():
    proposal = {
        "exercises": [
            {"eca_id": "ECA-001", "band": 2, "node": 2}
        ]
    }

    pass2_output = {
        "mode": "CONTROL",
        "pass": 2,
        "mcc_status": "RESTRICTED",
        "restricted_plan": {
            "exercises": [
                {"eca_id": "ECA-001", "band": 2, "node": 2},
                {"eca_id": "ECA-002", "band": 1, "node": 1}  # NEW - illegal
            ]
        }
    }

    with pytest.raises(ValidationError, match="MCC_EXPANSION_VIOLATION"):
        validate_pass2(pass2_output, original_proposal=proposal)

def test_mcc_cannot_increase_magnitude():
    proposal = {"exercises": [{"eca_id": "ECA-001", "band": 2, "node": 2}]}

    pass2_output = {
        "restricted_plan": {
            "exercises": [{"eca_id": "ECA-001", "band": 3, "node": 2}]  # Increased band - illegal
        }
    }

    with pytest.raises(ValidationError, match="MCC_EXPANSION_VIOLATION"):
        validate_pass2(pass2_output, original_proposal=proposal)
```

**Implementation Note:**  
Validator must compare Pass 2 `restricted_plan` against original `proposal`:
- Check all ECA IDs in restricted_plan exist in proposal
- Check all magnitude fields (band/node/h_node/sets) are ≤ original
- Check total session duration is ≤ original

---

## 5. Pass 3 Non-Hypothetical Invariants

### INV-ADV-001: Reference Only Actual Artifacts

**Assertion:**  
Pass 3 (ADVISORY) explanations and warnings MUST reference only:
1. Original proposal (from normalized input)
2. Pass 2 restricted plan (if Pass 2 executed)

Pass 3 MUST NOT:
- Suggest alternative exercises not in proposal or Pass 2 plan
- Describe "what could have been done" unless those elements were actually present
- Generate new training recommendations

**Enforcement Location:**  
`postpass/validate_output.py` — Pass 3 validator

**Violation Behavior:**  
- If Pass 3 references unknown ECA IDs → reject with `ADVISORY_HYPOTHETICAL_VIOLATION`
- Advisory may describe trade-offs within the legal space, but not external alternatives

**Test Requirement:**
```python
def test_advisory_no_hypotheticals():
    proposal = {"exercises": [{"eca_id": "ECA-001"}]}
    pass2 = {"restricted_plan": {"exercises": [{"eca_id": "ECA-001"}]}}

    pass3_output = {
        "mode": "ADVISORY",
        "pass": 3,
        "explanation": "Session is legal. Consider ECA-999 for better results.",  # References unknown ECA
        "warnings": []
    }

    # If strict mode: reject
    # If lenient mode: warn but allow
    # Recommendation: fail-closed (reject)
    with pytest.raises(ValidationError, match="ADVISORY_HYPOTHETICAL_VIOLATION"):
        validate_pass3(pass3_output, proposal=proposal, pass2=pass2)
```

**Implementation Note:**  
Extract all ECA IDs mentioned in Pass 3 text/warnings; verify all exist in proposal or Pass 2 plan.

---

## 6. Authority Hierarchy Invariants

### INV-AUTH-001: DCC Overrides All

**Assertion:**  
If Pass 1 (DCC law) returns `dcc_status = "ILLEGAL"`, no lower authority (MCC, advisory, or LLM output) may override this decision.

**Enforcement Location:**  
`orchestrator/run_pass2.py` — Pass 2 gate  
`orchestrator/run_pass3.py` — Pass 3 gate

**Violation Behavior:**  
- If orchestrator attempts to run Pass 2 after Pass 1 ILLEGAL → return `PASS_OUT_OF_ORDER`
- Pass 3 may run for explanation only, but must not suggest the illegal session is acceptable

**Test Requirement:**
```python
def test_no_pass2_after_illegal():
    pass1_result = {"dcc_status": "ILLEGAL"}

    with pytest.raises(OrchestratorError, match="PASS_OUT_OF_ORDER"):
        run_pass2(pass1_result=pass1_result)
```

---

### INV-AUTH-002: ECA Canonical Fields Are Authoritative

**Assertion:**  
After ECA resolution, canonical fields (name, movement_family, node_max, volume_class, push_pull, horiz_vert) are immutable and override any proposal values.

**Enforcement Location:**  
`prepass/eca_resolver.py`

**Violation Behavior:**  
- If proposal field conflicts with ECA canonical → return `ECA_FIELD_CONFLICT` (fail-closed mode)
- In normalize mode: overwrite proposal with canonical values and log normalization event

**Test Requirement:**
```python
def test_eca_canonical_override():
    proposal = {"eca_id": "ECA-001", "movement_family": "PRESS"}  # User claims PRESS
    eca_canonical = {"eca_id": "ECA-001", "movement_family": "PULL"}  # ECA says PULL

    # Fail-closed mode (v1 recommended)
    with pytest.raises(ValidationError, match="ECA_FIELD_CONFLICT"):
        resolve_eca(proposal, fail_closed=True)

    # Normalize mode (future)
    normalized = resolve_eca(proposal, fail_closed=False)
    assert normalized.movement_family == "PULL"  # ECA wins
```

---

## 7. Mode-Locking Invariants

### INV-MODE-001: Mode Matches Request

**Assertion:**  
LLM response `mode` field MUST exactly match the orchestrator's requested mode.

**Enforcement Location:**  
`postpass/validate_output.py` — first check in validation

**Violation Behavior:**  
- If `response.mode ≠ requested_mode` → reject with `MODE_MISMATCH`

**Test Requirement:**
```python
def test_mode_mismatch_rejection():
    response = {"mode": "CONTROL", "pass": 2}  # LLM claims CONTROL

    with pytest.raises(ValidationError, match="MODE_MISMATCH"):
        validate_pass_output(response, expected_mode="LAW", expected_pass=1)
```

---

### INV-MODE-002: No Shared Context Across Modes

**Assertion:**  
Each pass invocation MUST use fresh context. No chat history, shared memory, or prior pass reasoning may leak into subsequent passes.

**Enforcement Location:**  
`orchestrator/run_pass{1,2,3}.py` — LLM call layer

**Violation Behavior:**  
- Not mechanically detectable at runtime
- Enforcement via architecture (separate LLM calls with fresh context)
- Test via behavioral validation (Pass 2 must not reference Pass 1 reasoning)

**Test Requirement:**
```python
def test_no_context_leakage():
    # Pass 1 sees input_a
    pass1 = run_pass1(input_a)

    # Pass 2 should not be able to reference Pass 1's reasoning
    # (This is harder to test mechanically; relies on orchestrator architecture)
    pass2 = run_pass2(input_a, ledger_state)

    # Validate Pass 2 output doesn't reference Pass 1 internal reasoning
    assert "because Pass 1 said" not in pass2.explanation
```

---

## 8. Commit Atomicity Invariants

### INV-COMMIT-001: All-or-Nothing Delta Application

**Assertion:**  
All ledger deltas for a session MUST be applied in a single database transaction. Either all deltas succeed, or none do (full rollback).

**Enforcement Location:**  
`ledger/commit.py`

**Violation Behavior:**  
- If any delta write fails → rollback entire transaction
- Session row never created if deltas fail

**Test Requirement:**
```python
def test_commit_atomicity():
    delta_bundle = {
        "route_history_delta": [...],
        "density_delta": [...],
        "family_axis_delta": [...],
        "c_focus_delta": [...]
    }

    # Simulate failure on third delta
    with mock.patch('ledger.db.apply_family_axis_delta', side_effect=DBError):
        with pytest.raises(CommitError):
            commit_session(delta_bundle)

    # Verify NO deltas were applied (full rollback)
    assert ledger_route_history.count() == 0
    assert ledger_density.count() == 0
    assert sessions.count() == 0
```

---

### INV-COMMIT-002: Trace Storage Atomicity

**Assertion:**  
Session trace (input_json, pass1_json, pass2_json, pass3_json, delta_bundle) MUST be stored in the same transaction as session creation and delta application.

**Enforcement Location:**  
`ledger/commit.py`

**Violation Behavior:**  
- If trace write fails → rollback session + deltas
- No session may exist without corresponding trace

**Test Requirement:**
```python
def test_trace_storage_atomicity():
    with mock.patch('trace.store.save_trace', side_effect=DBError):
        with pytest.raises(CommitError):
            commit_session(...)

    # Verify session was not created
    assert sessions.count() == 0
```

---

## 9. Rollback Determinism Invariants

### INV-ROLLBACK-001: Inverse Delta Application

**Assertion:**  
Rollback MUST apply exact inverse of stored delta bundle:
- Route history: delete rows where `session_id = S`
- Density: subtract stored delta values (or delete delta rows)
- Family-axis: delete rows where `session_id = S`
- C-day focus: delete rows where `session_id = S`

**Enforcement Location:**  
`ledger/rollback.py`

**Violation Behavior:**  
- If rollback leaves partial state → mark session as `ROLLBACK_FAILED` and alert
- Manual intervention required

**Test Requirement:**
```python
def test_rollback_inverse_deltas():
    # Commit session with known deltas
    session = commit_session(delta_bundle={
        "density_delta": [{"key": "total_node3_sets", "delta": 5}]
    })

    initial_density = get_density("total_node3_sets")
    assert initial_density == 5

    # Rollback
    rollback_session(session.session_id)

    # Verify exact inverse applied
    final_density = get_density("total_node3_sets")
    assert final_density == 0
```

---

### INV-ROLLBACK-002: Trace Immutability

**Assertion:**  
Rollback MUST NOT delete or modify session traces. Traces are immutable audit records.

**Enforcement Location:**  
`ledger/rollback.py`

**Violation Behavior:**  
- Rollback only marks session status as `ROLLED_BACK`
- Trace remains readable for audit

**Test Requirement:**
```python
def test_rollback_preserves_trace():
    session = commit_session(...)
    original_trace = load_trace(session.session_id)

    rollback_session(session.session_id)

    # Trace still exists and unchanged
    rolled_back_trace = load_trace(session.session_id)
    assert rolled_back_trace == original_trace
    assert rolled_back_trace.session.status == "ROLLED_BACK"
```

---

## 10. ECA Resolution Invariants

### INV-ECA-001: Single Version Per Run

**Assertion:**  
All ECA IDs in a single proposal MUST resolve to the same ECA version declared in `authority_versions.eca`.

**Enforcement Location:**  
`prepass/eca_resolver.py`

**Violation Behavior:**  
- If any ECA ID resolves to different version → return `ECA_VERSION_MISMATCH`

**Test Requirement:**
```python
def test_eca_version_pinning():
    proposal = {
        "authority_versions": {"eca": "ECA-v1.2"},
        "exercises": [
            {"eca_id": "ECA-001"},  # v1.2
            {"eca_id": "ECA-002"}   # v1.3 in datastore
        ]
    }

    with pytest.raises(ValidationError, match="ECA_VERSION_MISMATCH"):
        resolve_ecas(proposal)
```

---

### INV-ECA-002: Unknown ECA IDs Rejected

**Assertion:**  
All ECA IDs in proposal MUST exist in the ECA datastore.

**Enforcement Location:**  
`prepass/eca_resolver.py`

**Violation Behavior:**  
- If ECA ID not found → return `UNKNOWN_EXERCISE` with exact ID and index

**Test Requirement:**
```python
def test_unknown_eca_rejection():
    proposal = {"exercises": [{"eca_id": "ECA-FAKE"}]}

    with pytest.raises(ValidationError, match="UNKNOWN_EXERCISE.*ECA-FAKE"):
        resolve_ecas(proposal)
```

---

## Appendix A: Invariant Summary Table

| ID | Category | Assertion | Enforcement Location | Error Code |
|----|----------|-----------|---------------------|-----------|
| INV-HASH-001 | Hash | Canonical JSON serialization required | `trace/hash.py` | `HASH_SERIALIZATION_ERROR` |
| INV-HASH-002 | Hash | Same inputs = same hash | `trace/hash.py` | `HASH_MISMATCH` (audit) |
| INV-CODE-001 | Reason Codes | Pass-scoped namespace enforcement | `postpass/validate_output.py` | `REASON_CODE_NAMESPACE_VIOLATION` |
| INV-CODE-002 | Reason Codes | All codes must exist in registry | `postpass/validate_output.py` | `UNKNOWN_REASON_CODE` |
| INV-LEDGER-001 | Concurrency | Linearizable commits per subject | `ledger/commit.py` | `LEDGER_CONFLICT` |
| INV-LEDGER-002 | Concurrency | Density validated at commit time | `ledger/commit.py` | `DENSITY_LEDGER_EXCEEDED` |
| INV-MCC-001 | MCC | No new elements introduced | `postpass/validate_output.py` | `MCC_EXPANSION_VIOLATION` |
| INV-ADV-001 | Advisory | No hypothetical alternatives | `postpass/validate_output.py` | `ADVISORY_HYPOTHETICAL_VIOLATION` |
| INV-AUTH-001 | Authority | DCC overrides all | `orchestrator/` | `PASS_OUT_OF_ORDER` |
| INV-AUTH-002 | Authority | ECA canonical fields authoritative | `prepass/eca_resolver.py` | `ECA_FIELD_CONFLICT` |
| INV-MODE-001 | Mode | Mode matches request | `postpass/validate_output.py` | `MODE_MISMATCH` |
| INV-MODE-002 | Mode | No shared context | `orchestrator/` | (architectural) |
| INV-COMMIT-001 | Atomicity | All-or-nothing delta application | `ledger/commit.py` | `COMMIT_FAILED` |
| INV-COMMIT-002 | Atomicity | Trace storage atomic with commit | `ledger/commit.py` | `COMMIT_FAILED` |
| INV-ROLLBACK-001 | Rollback | Inverse delta application | `ledger/rollback.py` | `ROLLBACK_FAILED` |
| INV-ROLLBACK-002 | Rollback | Trace immutability | `ledger/rollback.py` | (none) |
| INV-ECA-001 | ECA | Single version per run | `prepass/eca_resolver.py` | `ECA_VERSION_MISMATCH` |
| INV-ECA-002 | ECA | Unknown ECA IDs rejected | `prepass/eca_resolver.py` | `UNKNOWN_EXERCISE` |

---

## Appendix B: Test Coverage Requirements

Every invariant MUST have:

1. **Golden test** — proves invariant holds under normal conditions
2. **Mutation test** — proves invariant catches violations
3. **Boundary test** — tests edge cases (empty arrays, null values, max limits)

Minimum test corpus size: **54 tests** (3 tests × 18 invariants)

---

## Appendix C: Implementation Checklist

For each invariant, implementers must:

- [ ] Add enforcement logic at specified location
- [ ] Return correct error code on violation
- [ ] Write 3 tests (golden, mutation, boundary)
- [ ] Document enforcement in code comments
- [ ] Add invariant ID to error logs for traceability

---

**END OF INVARIANTS SPECIFICATION**

Document Version: 1.0.0  
Last Updated: 2026-01-25  
Status: ENFORCEMENT-READY
