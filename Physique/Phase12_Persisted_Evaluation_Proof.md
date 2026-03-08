# Phase 12 — Persisted Evaluation Proof (BINDING)

**Status:** BINDING
**Phase:** 12
**Date:** 2026-03-07
**Predecessor:** Phase11_Validation_Bridge.md (Phase 11, BINDING)

---

## §1 Scope and Note

Phase 12 delivers three things:

1. **F1 key name patch** — `_verify_authority_versions` now checks the spec-declared envelope keys `whitelist` and `tempo_governance` (previously `whitelist_version` and `tempo_gov_version`). This bug was carried forward undetected through Phases 10 and 11 because the existing F1 tests used the wrong key and still passed.

2. **PHYSIQUE persisted evaluation proof** — `phase12_proof.md` Step 5 documents the first end-to-end evaluation of the PHYSIQUE module against `SqliteDependencyProvider` with a persisted athlete record, producing `PHYSIQUE.CLEARANCEMISSING` via `ECA-PHY-0027`.

3. **PHYSIQUE CLI integration tests** — `test_cli_integration.py` gains `test_cli_physique_clean_payload` and `test_cli_physique_clearance_violation`, closing the CLI coverage gap for PHYSIQUE.

**Note:** Step 6 PHYSIQUE dispatch (`elif module_id == "PHYSIQUE": violations = run_physique_gates(...)`) was present in `kernel.py` from Phase 8. Phase 12 is the first time this path was exercised end-to-end with `SqliteDependencyProvider` and a persisted athlete record. Prior test coverage used `InMemoryDependencyProvider`.

---

## §2 F1 Patch Record

**Bug:** `_verify_authority_versions` in `physique_adapter.py` checked for `whitelist_version` and `tempo_gov_version` as dict keys. The spec-declared authority_versions envelope (§5.2 of `Physique_Pre_Pass_Adapter_Spec_v1_1.md`) declares these keys as `whitelist` and `tempo_governance`. A caller following the spec got no validation — the mismatch was silent.

**Detection:** Step 0 verification in Phase 12 proof script:
```
SPEC KEY (whitelist=wrong): []       ← expected ['AUTHORITY_VERSION_MISMATCH']
IMPL KEY (whitelist_version=wrong): ['AUTHORITY_VERSION_MISMATCH']  ← wrong key was active
```

**Fix:** `_verify_authority_versions` now checks `"whitelist"` and `"tempo_governance"`. Old key `whitelist_version` is silently skipped per validate-if-present (D1 Option A). No breaking change to existing caller behavior.

**Commit:** `39baf20` — `phase12-patch: F1 authority_version key names fixed (spec-declared: whitelist/tempo_governance)`

---

## §3 PHYSIQUE Persisted Proof

**Exercise:** `ECA-PHY-0027` — Rest-Pause Set (Technique), `e4_requires_clearance=True` in `efl_whitelist_v1_0_4.json`.

**Athlete:** ATH001, `e4_clearance=0`, sourced from persisted `op_athletes` row via `SqliteDependencyProvider.get_athlete_profile`.

**Expected violation:** `PHYSIQUE.CLEARANCEMISSING`

**Expected publish state:** `ILLEGALQUARANTINED`

**Module registry values at time of proof:**
- `moduleVersion`: `1.0.4`
- `moduleViolationRegistryVersion`: `1.0.4`
- `registryHash`: `7140d801e3194e0bbc74adc7f3c6d03bb503edc3124c3f0dfc0b71a02c185ec0`

**Proof command (see `phase12_proof.md` Step 5):**
```
python -m efl_kernel.cli \
  --module PHYSIQUE \
  --input physique_payload.json \
  --db efl_audit.db
```

**Commit:** `b2353a5` — `phase12: PHYSIQUE persisted evaluation proof (Step 5 — CLEARANCEMISSING via SqliteDependencyProvider)`

---

## §4 CLI Integration Tests

Two tests added to `efl_kernel/tests/test_cli_integration.py`:

| Test | Exercise | Athlete | Expected outcome |
|---|---|---|---|
| `test_cli_physique_clean_payload` | `ECA-PHY-0001` (Back Squat), tempo `3:0:1:0` | ATH-CLI-PHY-001 (unseeded → fail-closed, no E4 exercise) | Valid publish state, KDO persisted |
| `test_cli_physique_clearance_violation` | `ECA-PHY-0027`, tempo `3:0:1:0` | ATH-CLI-PHY-002 (`e4_clearance=0`, seeded via OperationalStore) | `PHYSIQUE.CLEARANCEMISSING`, `ILLEGALQUARANTINED` |

`ECA-PHY-0027` is hardcoded — confirmed in Step B1 of Phase 12 proof as the first E4-restricted exercise in `WHITELIST_INDEX` iteration order.

---

## §5 Phase 13 Must Deliver

1. **Declared input envelope (§5.1 of `Physique_Pre_Pass_Adapter_Spec_v1_1.md`)** — top-level field names `evaluation_context` and `session` must be accepted alongside the transitional wire shape (`evaluationContext` and `physique_session`). The adapter must map both shapes to the same internal representation. Backward compatibility with the transitional shape is required — no existing tests may be broken.
2. **Missing Phase 12 deliverable** — none; Phase 12 is fully closed by this document.

---

## §6 DO NOT — Carry-Forward Constraints

*(Copied verbatim from `Phase11_Validation_Bridge.md §6`)*

1. Do not create a `weekly_totals` table — `get_weekly_totals` has no live gate consumer
2. Do not create a second SQLite database file — share the same database path
3. Do not reuse `kdo_log` or `override_ledger` table names — owned by `audit_store.py`
4. Do not join operational and audit tables in provider queries
5. Do not change `InMemoryDependencyProvider` — it remains the test double
6. No new frozen spec required for Phase 11 — `EFL_PHYSIQUE_v1_0_4_frozen.json` remains current

---

## §7 Suite State

| Metric | Value |
|---|---|
| Passed | 361 |
| Skipped | 1 |
| Failed | 0 |
| Commits this phase | 4 total: `39baf20`, `b2353a5`, + 2 from this prompt |
