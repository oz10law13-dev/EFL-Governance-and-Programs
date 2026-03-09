# Phase 19 — PostgreSQL Migration (BINDING)

**Status:** BINDING
**Phase:** 19
**Date:** 2026-03-08
**Predecessor:** Phase18_Governed_Authoring.md (Phase 18, BINDING)

---

## §1 Scope

Phase 19 closes gap 2.1 from `docs/EFL_Kernel_OS_Roadmap.md`.

**This phase delivers:**
- `efl_kernel/kernel/sqlite_audit_store.py` — `SqliteAuditStore` (renamed from `AuditStore`)
- `efl_kernel/kernel/sqlite_operational_store.py` — `SqliteOperationalStore` (renamed from `OperationalStore`)
- `efl_kernel/kernel/sqlite_artifact_store.py` — `SqliteArtifactStore` (renamed from `ArtifactStore`)
- `efl_kernel/kernel/audit_store.py` — backward-compat shim re-exporting `AuditStore = SqliteAuditStore`
- `efl_kernel/kernel/operational_store.py` — backward-compat shim re-exporting `OperationalStore = SqliteOperationalStore`
- `efl_kernel/kernel/artifact_store.py` — backward-compat shim re-exporting `ArtifactStore = SqliteArtifactStore`
- `efl_kernel/ddl/audit_ddl.sql` — PostgreSQL DDL for `kdo_log`, `override_ledger`
- `efl_kernel/ddl/op_ddl.sql` — PostgreSQL DDL for `op_athletes`, `op_sessions`, `op_seasons`
- `efl_kernel/ddl/artifact_ddl.sql` — PostgreSQL DDL for `artifact_versions`, `artifact_kdo_links`, `review_records`
- `efl_kernel/kernel/pg_pool.py` — `open_pg()` + `apply_ddl()` helpers
- `efl_kernel/kernel/pg_audit_store.py` — `PgAuditStore`
- `efl_kernel/kernel/pg_operational_store.py` — `PgOperationalStore`
- `efl_kernel/kernel/pg_artifact_store.py` — `PgArtifactStore`
- `efl_kernel/kernel/pg_dependency_provider.py` — `PgDependencyProvider`
- `service.py` updated — `create_app` gains `database_url` / `op_database_url` params; PG branch; version bumped to `19.0.0`
- `efl_kernel/tests/test_phase19.py` — 24 tests (6 SQLite compat + 18 PG-gated)

**Explicit non-goals for this phase:**
- No schema migration versioning (Alembic or custom) — Phase 20
- No WAL configuration or backup strategy — Phase 21
- No multi-tenancy (org_id) — Phase 22
- No changes to any gate file
- No frozen spec changes
- No LLM integration

---

## §2 Store Rename Contract

The three SQLite store classes are renamed and their canonical implementations moved to `sqlite_*.py` files. The original module paths become shim re-exports so all existing imports remain valid with zero callers changed.

| Original name | New canonical file | New class name | Shim at |
|---|---|---|---|
| `AuditStore` | `sqlite_audit_store.py` | `SqliteAuditStore` | `audit_store.py` |
| `OperationalStore` | `sqlite_operational_store.py` | `SqliteOperationalStore` | `operational_store.py` |
| `ArtifactStore` | `sqlite_artifact_store.py` | `SqliteArtifactStore` | `artifact_store.py` |

`sqlite_dependency_provider.py` imports updated to reference the `sqlite_*.py` files directly (not through shims).

---

## §3 PostgreSQL Store Contract

### Driver
- **psycopg3 (sync)** — `psycopg.connect(database_url, row_factory=dict_row)`
- All results returned as Python dicts (dict_row factory)

### Type mapping (SQLite → PostgreSQL)

| Column | SQLite type | PostgreSQL type | Notes |
|---|---|---|---|
| `kdo_json` | `TEXT` (json.dumps) | `JSONB` | Auto-decoded to dict on read |
| `content_json` | `TEXT` (json.dumps) | `JSONB` | Auto-decoded to dict on read |
| `e4_clearance` | `INTEGER` (0/1) | `BOOLEAN` | Pass Python `bool` |
| `is_collapsed` | `INTEGER` (0/1) | `BOOLEAN` | Pass Python `bool`, default `FALSE` |

### Parameter style
- `%s` positional parameters (not `?`)

### Upsert semantics

| Store | Pattern | Preserved on conflict |
|---|---|---|
| `PgAuditStore.commit_kdo` | `ON CONFLICT DO NOTHING` | — (append-only) |
| `PgOperationalStore.upsert_athlete` | `ON CONFLICT (athlete_id) DO UPDATE` | `created_at` |
| `PgOperationalStore.upsert_session` | `ON CONFLICT (session_id) DO UPDATE` | `created_at` |
| `PgOperationalStore.upsert_season` | `ON CONFLICT (athlete_id, season_id) DO UPDATE` | `created_at` |

### JSONB writes
Use `psycopg.types.json.Jsonb(dict)` wrapper for all JSONB column inserts to ensure correct type adaptation.

### JSONB reads
psycopg3 automatically decodes JSONB columns to Python dicts. No `json.loads` calls on JSONB results.

### DDL application
Each `Pg*Store.__init__` calls `apply_ddl(conn, _DDL_PATH)` which splits the `.sql` file on `;` and executes each statement, then commits. `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS` make DDL application idempotent.

---

## §4 create_app Backend Selection

```
EFL_DATABASE_URL set (or database_url param)?
  YES → PostgreSQL branch
  NO  → SQLite branch (fully preserved, unchanged behavior)
```

`database_url` → audit PG connection
`op_database_url` (or `EFL_OP_DATABASE_URL`) → op/artifact PG connection; falls back to `database_url`

---

## §5 Test Contract

| Category | Count | Skip condition |
|---|---|---|
| SQLite backward-compat | 6 | Never skipped |
| PostgreSQL (requires_pg) | 18 | Skipped when `EFL_TEST_DATABASE_URL` is unset |
| **Total** | **24** | |

To run PG tests: `EFL_TEST_DATABASE_URL=postgresql://... pytest efl_kernel/tests/test_phase19.py`

---

## §6 DO NOT — Carry-Forward Constraints

*(Items 1–14 copied from Phase18_Governed_Authoring.md §6)*

1. Do not create a `weekly_totals` table
2. Do not create a second SQLite database file — route through `create_app` path resolution
3. Do not reuse `kdo_log` or `override_ledger` as table names
4. Do not join operational and audit tables in provider queries
5. Do not change `InMemoryDependencyProvider` — it remains the test double
6. No new frozen spec required for Phase 19
7. Do not write LLM calls in any store or provider (CLAUDE.md §8)
8. Do not hardcode `moduleVersion`, `moduleViolationRegistryVersion`, or `registryHash`
9. Do not add randomness to `propose()` — determinism is non-negotiable
10. Do not read from `OperationalStore` or `AuditStore` inside `propose()`
11. Do not pass `band_max` or `node_max` as keys to `list_exercises()` for upper-bound caps
12. Do not commit route-only changes without tests (CLAUDE.md §9)
13. Do not call `logging.basicConfig()`
14. Do not rename `db_path` or `op_db_path` in `create_app`
15. Do not use async psycopg3 — synchronous API only in this phase
16. Do not call `json.loads()` on JSONB column results — psycopg3 returns native dicts
17. Do not use SQLite-style `?` parameter placeholders in PG queries — use `%s`
18. Do not use `INSERT OR REPLACE` or `INSERT OR IGNORE` syntax in PG — use `ON CONFLICT` clauses

---

## §7 Suite State

| Metric | Value |
|---|---|
| Passed | 426 |
| Skipped | 19 (18 PG-gated + 1 pre-existing) |
| Failed | 0 |
| Commit | `4d35947` |
