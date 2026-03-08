# Phase 13 — Declared Input Envelope Normalization (BINDING)

**Status:** BINDING
**Phase:** 13
**Date:** 2026-03-08
**Predecessor:** Phase12_Persisted_Evaluation_Proof.md (Phase 12, BINDING)

---

## §1 Scope

Phase 13 closes gap 1.1 from `docs/EFL_Kernel_OS_Roadmap.md`. The PHYSIQUE adapter spec `Physique_Pre_Pass_Adapter_Spec_v1_1.md §5.1` declares `evaluation_context` and `session` as the canonical top-level field names, but the runtime had only ever accepted the transitional names `evaluationContext` and `physique_session`. A caller following the spec received `RAL.MISSINGORUNDEFINEDREQUIREDSTATE` silently — `kernel.py` Step 1 required `evaluationContext` in `raw_input`, and the declared name `evaluation_context` failed that check before any gate ran.

**This phase:**
- Adds `_normalize_physique_envelope` to `physique_adapter.py`
- Calls the normalization at the top of `KernelRunner.evaluate` for PHYSIQUE payloads only
- Adds 12 tests in `test_phase13_input_envelope.py`

**This phase does NOT:**
- Change any gate logic, violation codes, or frozen specs
- Remove or deprecate the transitional names — they remain valid indefinitely
- Touch SESSION, MESO, MACRO, or GOVERNANCE modules
- Implement `execution` or `module_id` envelope fields (optional, no gate consumers)

---

## §2 Change Table

| File | Change |
|---|---|
| `efl_kernel/kernel/physique_adapter.py` | Added `_normalize_physique_envelope` function (public, importable) |
| `efl_kernel/kernel/kernel.py` | Added normalization call before Step 0 in `KernelRunner.evaluate` for `module_id == "PHYSIQUE"` |
| `efl_kernel/tests/test_phase13_input_envelope.py` | New test file — 12 tests (5 unit, 7 integration) |

---

## §3 Normalization Contract

**Function:** `_normalize_physique_envelope(raw_input: dict) -> dict`

**Location:** `efl_kernel/kernel/physique_adapter.py`

**Rules:**

| Condition | Action |
|---|---|
| `evaluationContext` absent AND `evaluation_context` present | Copy `evaluation_context` → `evaluationContext` |
| `physique_session` absent AND `session` present | Copy `session` → `physique_session` |
| Transitional key present (regardless of declared key) | Transitional value wins; declared key ignored for mapping purposes |
| Neither declared nor transitional key present | No action |

**Invariants:**
- Returns a shallow copy of the input dict — never mutates the caller's dict
- Never removes keys — both declared and transitional names remain in the output dict
- Applied only for `module_id == "PHYSIQUE"` — SESSION's `session` field is unaffected
- Applied before Step 0 so Steps 1/4/5 in `kernel.evaluate` see `evaluationContext` regardless of caller's key choice

---

## §4 Fields In Scope

| Declared name (§5.1) | Transitional name (runtime) | Status |
|---|---|---|
| `evaluation_context` | `evaluationContext` | Implemented — Phase 13 |
| `session` | `physique_session` | Implemented — Phase 13 |
| `execution` | *(no transitional)* | Deferred — optional field, no gate consumer |
| `module_id` | *(no transitional)* | Deferred — optional field, no gate consumer |

---

## §5 Phase 14 Must Deliver

1. **Athlete/session/season CRUD API routes** — athletes currently enter the system only via seed tool or direct `upsert_athlete` calls in tests. No governed `POST /athletes`, `POST /sessions`, `POST /seasons`.
2. **`ExerciseCatalog` whitelist path fix** — `exercise_catalog.py` still hardcodes `efl_whitelist_v1_0_3.json`; whitelist is at v1.0.4.

---

## §6 DO NOT — Carry-Forward Constraints

*(Copied verbatim from `Phase12_Persisted_Evaluation_Proof.md §6`)*

1. Do not create a `weekly_totals` table — `get_weekly_totals` has no live gate consumer
2. Do not create a second SQLite database file — share the same database path
3. Do not reuse `kdo_log` or `override_ledger` table names — owned by `audit_store.py`
4. Do not join operational and audit tables in provider queries
5. Do not change `InMemoryDependencyProvider` — it remains the test double
6. No new frozen spec required for Phase 13 — `EFL_PHYSIQUE_v1_0_4_frozen.json` remains current

---

## §7 Suite State

| Metric | Value |
|---|---|
| Passed | 373 |
| Skipped | 1 |
| Failed | 0 |
| Commits this phase | 2: `cbd24d0`, `3445afd` |
