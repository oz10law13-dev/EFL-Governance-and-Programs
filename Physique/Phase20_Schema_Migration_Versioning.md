# Phase 20 — Schema Migration Versioning (BINDING)

**Status:** BINDING
**Phase:** 20
**Date:** 2026-03-08
**Predecessor:** Phase19_PostgreSQL_Migration.md (Phase 19, BINDING)

---

## §1 Scope

Phase 20 closes gap 2.3 from `docs/EFL_Kernel_OS_Roadmap.md`.

**This phase delivers:**
- `efl_kernel/migrations/runner.py` — `MigrationRunner` class + `MigrationError` exception
- `efl_kernel/migrations/sqlite/audit/0001_initial.sql` — SQLite audit baseline DDL
- `efl_kernel/migrations/sqlite/operational/0001_initial.sql` — SQLite operational baseline DDL (6 tables)
- `efl_kernel/migrations/pg/audit/0001_initial.sql` — PostgreSQL audit baseline DDL
- `efl_kernel/migrations/pg/operational/0001_initial.sql` — PostgreSQL operational baseline DDL (6 tables)
- `service.py` updated — `create_app` runs migrations after store construction for file-backed SQLite and PG
- `efl_kernel/tests/test_phase20.py` — 17 tests (14 always-run + 3 PG-gated)

**Explicit non-goals for this phase:**
- No rollback/down-migration support (forward-only)
- No CLI subcommand for migrations
- No new HTTP routes
- No new store methods
- No gate or provider changes
- No frozen spec changes

---

## §2 MigrationRunner Contract

**File:** `efl_kernel/migrations/runner.py`

### Constructor

```python
def __init__(self, conn, dialect: str, domain: str) -> None
```

- `conn`: `sqlite3.Connection` or `psycopg.Connection`
- `dialect`: `"sqlite"` or `"pg"`
- `domain`: `"audit"` or `"operational"`

### `ensure_current() -> dict`

Apply all pending migrations. Returns:

```python
{
    "applied": [int, ...],      # version numbers applied this run
    "current_version": int,     # max applied version after run
    "bootstrapped": bool,       # True if existing DB was bootstrapped
}
```

Algorithm:
1. Create `_schema_migrations` tracking table (idempotent)
2. Discover migration files from `efl_kernel/migrations/{dialect}/{domain}/`
3. Detect bootstrap: no rows but data tables exist → record 0001 without executing
4. Verify checksums of all already-applied migrations
5. Apply pending migrations in version order
6. Record each applied migration with SHA-256 checksum

### `status() -> dict`

Return current state without applying anything.

### `verify() -> None`

Verify checksums of all applied migrations. Raises `MigrationError` on mismatch or missing file.

---

## §3 Migration File Structure

```
efl_kernel/migrations/
    {dialect}/            # "sqlite" or "pg"
        {domain}/         # "audit" or "operational"
            NNNN_*.sql    # 4-digit version prefix
```

Files are discovered by regex `^(\d{4})_.+\.sql$`, sorted by version ascending.

---

## §4 Frozen Migration Discipline

Once a migration is applied to any database, its file content must never change. The runner stores a SHA-256 checksum (with normalized `\r\n` → `\n` line endings) at apply time and verifies it on every subsequent run. Checksum mismatch raises `MigrationError`.

---

## §5 Bootstrap Behavior

When the runner encounters a database that has data tables (e.g., `kdo_log` for audit, `op_athletes` for operational) but no `_schema_migrations` tracking rows, it records migration 0001 as applied WITHOUT executing it. This allows the runner to be added to pre-existing databases without data loss.

---

## §6 Phase 21 Must Deliver

1. **Backup/restore strategy + WAL configuration** — the KDO log is the legal record of every evaluation decision. No backup/restore procedure exists. Phase 21 delivers a documented strategy, a backup script, and a restore verification procedure.

---

## §7 DO NOT — Carry-Forward Constraints

1. Do not remove `_DDL` strings from any SQLite store — `:memory:` test stores depend on them
2. Do not remove `_migrate_schema()` from `SqliteOperationalStore` — harmless on migrated DBs
3. Do not remove `apply_ddl()` calls from PG stores — fallback for stores constructed without the runner
4. Do not change `InMemoryDependencyProvider` — it remains the test double
5. Do not change any gate file, kernel.py, kdo.py, ral.py, registry.py, or adapter
6. Do not change any frozen spec file
7. Do not change any existing test file
8. Do not call `logging.basicConfig()`
9. Do not make PG tests fail when `EFL_TEST_DATABASE_URL` is not set
10. Do not use `conn.executescript()` for migration execution in SQLite — use `conn.execute()` per statement within explicit BEGIN/COMMIT
11. Do not create a `weekly_totals` table in any migration file
12. Do not add any new HTTP routes — this phase is infrastructure only
13. Do not modify applied migration files — frozen migration discipline

---

## §8 Suite State

| Metric | Value |
|---|---|
| Passed | 440 |
| Skipped | 22 (18 PG Phase 19 + 3 PG Phase 20 + 1 pre-existing) |
| Failed | 0 |
| Commit | `76a7749` |
