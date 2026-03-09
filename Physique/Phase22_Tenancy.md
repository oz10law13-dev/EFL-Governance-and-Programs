# Phase 22 — Tenancy (org_id Isolation) (BINDING)

**Status:** BINDING
**Phase:** 22
**Date:** 2026-03-08
**Predecessor:** Phase21_Backup_Restore_Strategy.md (Phase 21, BINDING)

---

## §1 Scope

Phase 22 closes gap 4.1 from `docs/EFL_Kernel_OS_Roadmap.md`.

**This phase delivers:**
- `org_id TEXT NOT NULL DEFAULT 'default'` column on 6 tables: `kdo_log`, `override_ledger`, `op_athletes`, `op_sessions`, `op_seasons`, `artifact_versions`
- WHERE-clause isolation on all store read/write methods (every `org_id` param defaults to `"default"`)
- 4 migration files (`0002_add_org_id.sql`) for SQLite audit, SQLite operational, PG audit, PG operational
- `OrgScopedSqliteProvider` / `OrgScopedPgProvider` — transparent proxy that injects `org_id` into every store method call
- `APIKeyMiddleware` rewritten with multi-key support (`EFL_API_KEYS` JSON dict maps API keys to org_ids)
- All routes pass `org_id` through evaluate, CRUD, artifact, and author flows
- `efl_kernel/tools/seed.py` gains `--org-id` flag
- `efl_kernel/tests/test_phase22.py` — 30 tests covering store isolation, middleware, provider delegation, route passthrough

**Explicit non-goals for this phase:**
- No composite primary keys — `athlete_id` remains globally unique (no two orgs can share the same athlete_id)
- No gate or kernel changes — `org_id` never appears in evaluation logic
- No `InMemoryDependencyProvider` changes — test double unaffected
- No frozen spec changes
- No UI for org management

---

## §2 Database Schema Changes

### New column on 6 tables

```sql
org_id TEXT NOT NULL DEFAULT 'default'
```

Added to: `kdo_log`, `override_ledger`, `op_athletes`, `op_sessions`, `op_seasons`, `artifact_versions`.

**Not added to:** `artifact_kdo_links`, `review_records` (scoped via FK chain through `artifact_versions`).

### Migration files

| File | Dialect | Domain |
|---|---|---|
| `migrations/sqlite/audit/0002_add_org_id.sql` | SQLite | audit |
| `migrations/sqlite/operational/0002_add_org_id.sql` | SQLite | operational |
| `migrations/pg/audit/0002_add_org_id.sql` | PG | audit |
| `migrations/pg/operational/0002_add_org_id.sql` | PG | operational |

### DDL interaction

- `_DDL` strings in store files are **not modified** — they remain the original schema without `org_id`
- Store constructors call `_migrate_org_id()` unconditionally (idempotent via try/except on "duplicate column name")
- Migration runner's `_execute_migration_sqlite` catches "duplicate column name" per-statement
- PG migrations use `ADD COLUMN IF NOT EXISTS`

---

## §3 Store Method Changes

All store methods gain `org_id: str = "default"` parameter. Every INSERT includes `org_id` in values. Every SELECT/UPDATE/DELETE includes `AND org_id = ?` in WHERE clause.

**Exception:** `get_kdo(decision_hash)` — no `org_id` filter (hash is globally unique).

### SQLite stores modified
- `sqlite_audit_store.py` — `commit_kdo`, `get_override_history`, `get_metrics`
- `sqlite_operational_store.py` — `upsert_athlete`, `upsert_session`, `upsert_season`, `get_athlete`, `get_sessions_in_window`, `get_season`, `get_all_seasons`, `get_active_season`
- `sqlite_artifact_store.py` — `commit_artifact_version`, `get_versions`, `get_versions_by_artifact_id`, `get_live_version`, `promote_to_live`, `retire`

### PG stores modified
- `pg_audit_store.py`, `pg_operational_store.py`, `pg_artifact_store.py` — same methods as SQLite equivalents

---

## §4 Org-Scoped Providers

**File:** `efl_kernel/kernel/org_scoped_provider.py`

### `_OrgScopedStoreProxy`
Transparent proxy that intercepts all method calls on a store object and injects `org_id=<value>` via `kwargs.setdefault`. Non-callable attributes pass through unchanged.

### `OrgScopedSqliteProvider(op_store, audit_store, org_id)`
Wraps `SqliteDependencyProvider` with proxied stores. The kernel and gates see the standard `KernelDependencyProvider` interface — no `org_id` leaks into evaluation logic.

### `OrgScopedPgProvider(op_store, audit_store, org_id)`
Same pattern for PostgreSQL stores.

---

## §5 Middleware + Route Wiring

### APIKeyMiddleware (rewritten)

Priority order:
1. `EFL_API_KEYS` env var (JSON dict `{key: org_id}`) → multi-key mode, sets `request.state.org_id`
2. `EFL_API_KEY` env var (single string) → single-key mode, `org_id="default"`
3. Neither set → no auth, `org_id="default"`

`/health` is always exempt from auth.

### Route changes

- `_make_runner(app, org_id)` — returns `app.state.runner` when `org_id=="default"` (preserves test monkeypatching), creates `OrgScoped*Provider` + `KernelRunner` otherwise
- `_evaluate_and_commit` gains `org_id="default"` param, passes to `audit_store.commit_kdo(kdo, org_id=org_id)`
- All evaluate routes: use `_make_runner(request.app, org_id)` and pass `org_id`
- All CRUD routes: pass `org_id=request.state.org_id` to store methods
- All artifact routes: pass `org_id` to commit, promote, retire, get_versions
- All author/pipeline routes: pass `org_id` throughout
- `/metrics`: passes `org_id=request.state.org_id`
- Version bumped to `"22.0.0"`

---

## §6 Seed Tool

`efl_kernel/tools/seed.py` gains `--org-id` argument (default `"default"`). Passed to all `upsert_athlete`, `upsert_session`, `upsert_season` calls.

---

## §7 DO NOT — Carry-Forward Constraints

1. Do not add `org_id` to `KernelDependencyProvider` abstract methods — tenancy is a persistence concern, not an evaluation concern
2. Do not modify `InMemoryDependencyProvider` — test double must remain org-unaware
3. Do not change primary keys — `athlete_id` remains globally unique
4. Do not change any gate file, kernel.py, kdo.py, ral.py, registry.py, or adapter
5. Do not change any frozen spec file
6. Do not modify applied migration files (0001) — frozen migration discipline
7. Do not call `logging.basicConfig()`
8. Do not make PG tests fail when `EFL_TEST_DATABASE_URL` is not set

---

## §8 Suite State

| Metric | Value |
|---|---|
| Passed | 486 |
| Skipped | 23 (18 PG Phase 19 + 3 PG Phase 20 + 1 PG Phase 21 + 1 pre-existing) |
| Failed | 0 |
| Commit | `9166695` |
