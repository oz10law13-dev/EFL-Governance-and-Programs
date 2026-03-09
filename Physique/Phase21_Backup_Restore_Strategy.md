# Phase 21 — Backup/Restore Strategy + WAL Configuration (BINDING)

**Status:** BINDING
**Phase:** 21
**Date:** 2026-03-08
**Predecessor:** Phase20_Schema_Migration_Versioning.md (Phase 20, BINDING)

---

## §1 Scope

Phase 21 closes gap 2.5 from `docs/EFL_Kernel_OS_Roadmap.md`.

**This phase delivers:**
- SQLite WAL mode on all 3 file-backed stores (audit, operational, artifact)
- `efl_kernel/tools/backup.py` — backup CLI tool with `sqlite`, `pg`, `verify` subcommands
- `GET /health/backup` route in `service.py`
- `docs/backup_restore.md` — operational documentation
- `efl_kernel/tests/test_phase21.py` — 17 tests (16 always-run + 1 PG-gated)

**Explicit non-goals for this phase:**
- No automated backup scheduling (use external cron/scheduler)
- No backup retention/rotation (external responsibility)
- No incremental/differential backups
- No new store methods
- No gate or provider changes
- No frozen spec changes

---

## §2 WAL Mode

All three SQLite store constructors add `PRAGMA journal_mode=WAL` after `sqlite3.connect()`, gated on `db_path != ":memory:"`:

- `SqliteAuditStore.__init__` — `sqlite_audit_store.py`
- `SqliteOperationalStore.__init__` — `sqlite_operational_store.py`
- `SqliteArtifactStore.__init__` — `sqlite_artifact_store.py`

WAL provides concurrent read access during writes and crash-safe atomic commits.

---

## §3 Backup CLI Tool

**File:** `efl_kernel/tools/backup.py`

### Functions

| Function | Input | Output |
|---|---|---|
| `backup_sqlite(db_path, dest_dir, label)` | SQLite file path | Metadata dict + backup file |
| `backup_pg(database_url, dest_dir, label)` | PostgreSQL DSN | Metadata dict + SQL dump |
| `verify_sqlite_backup(backup_path)` | Backup file path | Verification dict |
| `verify_pg_backup(backup_path, database_url)` | Backup + DSN | Verification dict |

### CLI Subcommands

- `sqlite --audit-db PATH --op-db PATH --dest DIR`
- `pg --database-url URL --dest DIR [--label LABEL]`
- `verify --backup-path PATH [--database-url URL]`

### Metadata

Each backup writes/appends to `.last_backup.json` in the destination directory. Contains `backups` array and `last_backup` pointer.

---

## §4 Health Endpoint

`GET /health/backup` reads `EFL_BACKUP_DIR` environment variable:

| Condition | Response |
|---|---|
| `EFL_BACKUP_DIR` not set | `{"status": "not_configured"}` |
| Dir exists, no `.last_backup.json` | `{"status": "no_backups"}` |
| Metadata exists | `{"status": "ok", "last_backup": {...}}` |

---

## §5 DO NOT — Carry-Forward Constraints

1. Do not remove WAL pragma — it is required for concurrent access safety
2. Do not change any gate file, kernel.py, kdo.py, ral.py, registry.py, or adapter
3. Do not change any frozen spec file
4. Do not call `logging.basicConfig()`
5. Do not make PG tests fail when `EFL_TEST_DATABASE_URL` is not set
6. Do not modify applied migration files — frozen migration discipline
7. Do not delete `.last_backup.json` — it is the backup tracking record

---

## §6 Suite State

| Metric | Value |
|---|---|
| Passed | 456 |
| Skipped | 23 (18 PG Phase 19 + 3 PG Phase 20 + 1 PG Phase 21 + 1 pre-existing) |
| Failed | 0 |
| Commit | `d71df0c` |
