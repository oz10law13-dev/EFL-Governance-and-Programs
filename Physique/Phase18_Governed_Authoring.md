# Phase 18 — Governed Authoring / Builder Prep (BINDING)

**Status:** BINDING
**Phase:** 18
**Date:** 2026-03-08
**Predecessor:** Phase17_Audit_Op_DB_Separation.md (Phase 17, BINDING)

---

## §1 Scope

Phase 18 closes gap 3.5 from `docs/EFL_Kernel_OS_Roadmap.md` and completes Tier A of the EFL-Kernel roadmap.

**This phase delivers:**
- `PhysiqueProposalEngine` — new class in `efl_kernel/kernel/proposal_engine.py`
- `POST /propose/physique` route in `service.py`
- `POST /pipeline/physique` route in `service.py`
- `app.state.proposal_engine` initialization in `create_app`
- 8 tests in `efl_kernel/tests/test_phase18.py`

**Explicit non-goals for this phase:**
- No LLM integration (CLAUDE.md §8 — deferred to a future phase)
- No changes to any gate file (gates_physique.py, gates_scm.py, etc.)
- No frozen spec changes
- No CLI changes
- No PostgreSQL migration
- No weekly_totals table
- No multi-tenancy changes

---

## §2 ProposalEngine Contract

**File:** `efl_kernel/kernel/proposal_engine.py`
**Class:** `PhysiqueProposalEngine`

### Constructor

```python
def __init__(self, catalog: ExerciseCatalog) -> None
```

Takes an `ExerciseCatalog` instance. No operational store access. No audit store access. No KDO produced.

### `propose(constraints: dict) -> dict`

**Required constraint keys:**

| Key | Type | Description |
|---|---|---|
| `athlete_id` | `str` | Athlete identifier for `evaluationContext.athleteID` |
| `session_id` | `str` | Session identifier for `evaluationContext.sessionID` |
| `day_role` | `str` | Day role filter — single letter ("A", "B", "C") |

**Optional constraint keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `target_exercise_count` | `int` | `3` | Max exercises to include |
| `band_max` | `int` | None | Upper-bound cap: keep exercises where `ex["band_max"] <= cap` |
| `node_max` | `int` | None | Upper-bound cap: keep exercises where `ex["node_max"] <= cap` |
| `movement_families` | `list[str]` | None | Keep only exercises in these families |

**Return shape:**

```python
{
    "candidate_payload": dict,   # complete conformant eval payload (7 keys)
    "pre_validation": list,      # [{canonical_id, violations}] per exercise
    "exercises_selected": int,
    "constraints_applied": dict, # echo of input constraints
}
```

**Determinism guarantee:** `list_exercises({"day_role": ...})` result is sorted by `canonical_id` before slicing to `target_exercise_count`. Same constraints always produce the same exercise list. Window context dates are `date.today()`-relative and vary across calendar days — this is the only non-fixed element.

**Conservative exercise defaults:** `band_count=1`, `node=1`, `tempo="3:0:1:0"`, `set_count=3`.

**`moduleRegistration` sourced at call time:** `reg = RAL_SPEC["moduleRegistration"]["PHYSIQUE"]`. `moduleVersion`, `moduleViolationRegistryVersion`, `registryHash` are never hardcoded.

**`list_exercises` filter semantics (important):** The built-in `band_max` filter means "exercises where `band_max >= value`" (minimum capability). `band_max` and `node_max` upper-bound caps are applied as post-filters on the result list. `day_role` is a membership check against `ex["day_roles"]`.

**On `ValueError`:** Raised on first missing required key (`athlete_id`, then `session_id`, then `day_role`). The route handler converts this to HTTP 422.

---

## §3 Route Contracts

### `POST /propose/physique`

| Property | Value |
|---|---|
| Request body | Constraint dict (see §2) |
| 200 response | `{candidate_payload, pre_validation, exercises_selected, constraints_applied}` |
| 422 response | Missing required constraint key |
| 500 response | Unexpected engine error |
| Implementation | `request.app.state.proposal_engine.propose(payload)` |

### `POST /pipeline/physique`

| Property | Value |
|---|---|
| Required body keys | `constraints` (dict), `artifact_id` (str), `object_id` (str) |
| Optional body keys | `content` (dict, defaults to `candidate_payload`) |
| 200 response | Merged proposal + authoring result (see publish-state branches below) |
| 422/500 | Propagated from proposal engine or inner handlers |

**Publish-state branches:**

| `finalPublishState` | `promoted` | `lifecycle` | `requires_review` |
|---|---|---|---|
| `BLOCKED` / `ILLEGALQUARANTINED` | `False` | `DRAFT` | `False` |
| `LEGALREADY` | `True` | `LIVE` | `False` |
| `REQUIRESREVIEW` / `LEGALOVERRIDE` | `False` | `DRAFT` | `True` |

All four branches include: `proposal`, `version_id`, `lifecycle`, `publish_state`, `decision_hash`, `promoted`, `requires_review`, `violations`.

---

## §4 LLM Boundary

"LLM output is NEVER written to any KDO field, finalPublishState, violation code, frozen spec, or audit store record. The proposal engine is purely deterministic. The gate layer does not know and must not care how a payload was produced."

In this phase, no LLM is wired. `PhysiqueProposalEngine.propose()` is deterministic Python. This rule is encoded here so that when LLM integration is added in a future phase, the boundary is already established and cannot be crossed.

---

## §5 Phase 19 Must Deliver

1. **PostgreSQL migration path** — `AuditStore`, `OperationalStore`, and `ArtifactStore` must support async PostgreSQL drivers for horizontal scale and real concurrent users. Phase 17 separation of audit/op paths is the precursor.
2. **Multi-tenancy considerations** — `org_id` isolation on all operational and audit tables; auth-scoped queries on every provider method.

---

## §6 DO NOT — Carry-Forward Constraints

*(Items 1–6 copied verbatim from `Phase17_Audit_Op_DB_Separation.md §6`)*

1. Do not create a `weekly_totals` table — `get_weekly_totals` has no live gate consumer
2. Do not create a second SQLite database file — route through `create_app` path resolution
3. Do not reuse `kdo_log` or `override_ledger` as table names
4. Do not join operational and audit tables in provider queries
5. Do not change `InMemoryDependencyProvider` — it remains the test double
6. No new frozen spec required for Phase 18 — `EFL_PHYSIQUE_v1_0_4_frozen.json` remains current
7. Do not write LLM calls in `proposal_engine.py` (CLAUDE.md §8)
8. Do not hardcode `moduleVersion`, `moduleViolationRegistryVersion`, or `registryHash`
9. Do not add randomness to `propose()` — determinism is non-negotiable
10. Do not read from `OperationalStore` or `AuditStore` inside `propose()`
11. Do not pass `band_max` or `node_max` as keys to `list_exercises()` for upper-bound caps — apply as post-filters
12. Do not commit route-only changes without tests in the same commit (CLAUDE.md §9)
13. Do not call `logging.basicConfig()`
14. Do not rename `db_path` or `op_db_path` in `create_app`

---

## §7 Suite State

| Metric | Value |
|---|---|
| Passed | 420 |
| Skipped | 1 |
| Failed | 0 |
| Commit | `843e3a6` |
