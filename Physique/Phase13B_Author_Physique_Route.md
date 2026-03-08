# Phase 13B — `/author/physique` Route (BINDING)

**Status:** BINDING
**Phase:** 13B
**Date:** 2026-03-08
**Predecessor:** Phase13_Declared_Input_Envelope.md (Phase 13, BINDING)

---

## §1 Scope

Phase 13B closes gap 1.2 from `docs/EFL_Kernel_OS_Roadmap.md`. `POST /author/session` existed; PHYSIQUE had no equivalent single-call author path. This phase adds `POST /author/physique` to `service.py` with the same commit → evaluate → promote lifecycle.

**This phase:**
- Adds `POST /author/physique` route to `service.py`
- Adds 6 tests to `efl_kernel/tests/test_authoring.py`

**This phase does NOT:**
- Change any gate logic, frozen specs, or violation codes
- Change `author_session`, `_evaluate_and_commit`, or any existing route
- Implement athlete CRUD routes (Phase 14)
- Fix the `ExerciseCatalog` whitelist path (Phase 14B)

---

## §2 Route Contract

### Request shape

```json
{
  "artifact_id": "<string>",
  "object_id": "<string>",
  "content": { "<any>": "<any>" },
  "evaluation_payload": { "<PHYSIQUE KDO payload>" }
}
```

`evaluation_payload` may use declared (§5.1) or transitional field names. The Phase 13 normalization at `KernelRunner.evaluate` handles both shapes identically.

### Response shape

```json
{
  "version_id": "<string>",
  "lifecycle": "DRAFT" | "LIVE",
  "publish_state": "<finalPublishState>",
  "decision_hash": "<string>",
  "promoted": true | false,
  "requires_review": true | false
}
```

### Four publish-state branches

| `finalPublishState` | `lifecycle` | `promoted` | `requires_review` | KDO linked? |
|---|---|---|---|---|
| `BLOCKED`, `ILLEGALQUARANTINED` | `DRAFT` | `false` | `false` | No |
| `LEGALREADY` | `LIVE` | `true` | `false` | Yes |
| `REQUIRESREVIEW`, `LEGALOVERRIDE` | `DRAFT` | `false` | `true` | Yes |

---

## §3 Equivalence Guarantee

The `author_physique` route body is structurally identical to `author_session`. The only difference is `module_id="PHYSIQUE"` in the `commit_artifact_version` and `_evaluate_and_commit` calls. There is no PHYSIQUE-specific branching at the lifecycle layer.

`_evaluate_and_commit` is shared and works for both modules without modification.

---

## §4 Declared Envelope

`evaluation_payload` in the request body may use either:
- **Declared names** (`evaluation_context`, `session`) per `Physique_Pre_Pass_Adapter_Spec_v1_1.md §5.1`
- **Transitional names** (`evaluationContext`, `physique_session`)

The Phase 13 normalization (`_normalize_physique_envelope`) runs at `KernelRunner.evaluate` entry before Step 0, so both shapes produce identical outcomes. `test_author_physique_declared_envelope_accepted` confirms this end-to-end.

---

## §5 Phase 14 Must Deliver

1. **Athlete/session/season CRUD API routes** — athletes currently enter via seed tool or direct `upsert_athlete` test calls. No governed `POST /athletes`, `POST /sessions`, `POST /seasons`.
2. **`ExerciseCatalog` whitelist path fix** — `exercise_catalog.py` still hardcodes `efl_whitelist_v1_0_3.json`; whitelist is at v1.0.4.

---

## §6 DO NOT — Carry-Forward Constraints

*(Copied verbatim from `Phase13_Declared_Input_Envelope.md §6`)*

1. Do not create a `weekly_totals` table — `get_weekly_totals` has no live gate consumer
2. Do not create a second SQLite database file — share the same database path
3. Do not reuse `kdo_log` or `override_ledger` table names — owned by `audit_store.py`
4. Do not join operational and audit tables in provider queries
5. Do not change `InMemoryDependencyProvider` — it remains the test double
6. No new frozen spec required for Phase 13B — `EFL_PHYSIQUE_v1_0_4_frozen.json` remains current

---

## §7 Suite State

| Metric | Value |
|---|---|
| Passed | 379 |
| Skipped | 1 |
| Failed | 0 |
| Commits this phase | 2: `ce518a7`, `612d082` |
