# Phase 15 — KDO Query, Structured Logging, and Metrics (BINDING)

**Status:** BINDING
**Phase:** 15
**Date:** 2026-03-08
**Predecessor:** Phase14_Operational_CRUD_Routes.md (Phase 14, BINDING)

---

## §1 Scope

Phase 15 closes gap 3.4 from `docs/EFL_Kernel_OS_Roadmap.md` and adds structured logging + operational metrics:

- **Gap 3.4** — `GET /kdo/{decision_hash}` audit query route: KDOs were persisted to `kdo_log` but no HTTP route retrieved a specific KDO by its hash.
- **Structured logging** — `_evaluate_and_commit` now emits a structured INFO log entry after each successful KDO commit.
- **`GET /metrics`** — Aggregate counts from `kdo_log` (total KDOs, by module, by publish state).

**This phase:**
- Adds `GET /kdo/{decision_hash}` and `GET /metrics` routes to `service.py`
- Adds `import logging` + `_logger = logging.getLogger(__name__)` to `service.py`
- Adds `_logger.info("kdo_committed", extra={...})` call in `_evaluate_and_commit`
- Adds `AuditStore.get_metrics()` to `audit_store.py`
- Adds 6 tests in `efl_kernel/tests/test_phase15.py`

**This phase does NOT:**
- Change any gate logic, violation codes, or frozen specs
- Change existing routes or `_evaluate_and_commit` behavior
- Call `logging.basicConfig()` — logger configuration is the caller's responsibility

---

## §2 Route Contracts

### `GET /kdo/{decision_hash}`

| Property | Value |
|---|---|
| Path parameter | `decision_hash` (str) — never `hash` (Python builtin) |
| 200 response | Full KDO dict as stored in `kdo_log.kdo_json` |
| 404 response | `{"detail": "KDO '<hash>' not found"}` |
| Implementation | `audit_store.get_kdo(decision_hash)` — returns `dict | None` |

### `GET /metrics`

| Property | Value |
|---|---|
| 200 response | `{"kdo_total": int, "by_module": {...}, "by_publish_state": {...}}` |
| Implementation | `audit_store.get_metrics()` |
| `by_module` | SQL `GROUP BY module_id` — keyed by `module_id` string |
| `by_publish_state` | Python grouping over `kdo_json → resolution.finalPublishState` |

---

## §3 Structured Logging Contract

**Logger name:** `efl_kernel.service` (from `logging.getLogger(__name__)`)

**Log point:** After `audit_store.commit_kdo(kdo)` returns, before `return dataclasses.asdict(kdo)` in `_evaluate_and_commit`.

**Level:** INFO

**Message:** `"kdo_committed"`

**Extra fields:**

| Field | Source |
|---|---|
| `module_id` | `kdo.module_id` |
| `object_id` | `kdo.object_id` |
| `decision_hash` | `kdo.audit["decisionHash"]` |
| `final_publish_state` | `kdo.resolution["finalPublishState"]` |
| `violation_count` | `len(kdo.violations)` |

`decision_hash` is only available after `commit_kdo` calls `freeze_kdo` — log placement after commit is mandatory.

---

## §4 Phase 16 Must Deliver

1. **Authentication middleware (API key)** — all HTTP routes are currently open. Any caller can evaluate any athlete, read any KDO, or modify any artifact. API key middleware required before any non-local deployment.

---

## §5 DO NOT — Carry-Forward Constraints

*(Copied verbatim from `Phase14_Operational_CRUD_Routes.md §6`)*

1. Do not create a `weekly_totals` table — `get_weekly_totals` has no live gate consumer
2. Do not create a second SQLite database file — share the same database path
3. Do not reuse `kdo_log` or `override_ledger` table names — owned by `audit_store.py`
4. Do not join operational and audit tables in provider queries
5. Do not change `InMemoryDependencyProvider` — it remains the test double
6. No new frozen spec required for Phase 15 — `EFL_PHYSIQUE_v1_0_4_frozen.json` remains current

---

## §6 Suite State

| Metric | Value |
|---|---|
| Passed | 400 |
| Skipped | 1 |
| Failed | 0 |
| Commits this phase | 2: `67aaf30`, `48bfec8` |
