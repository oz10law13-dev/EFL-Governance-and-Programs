# EFL Kernel — Backup & Restore Operations

## Overview

The EFL Kernel audit store (`kdo_log`) is the legal record of every evaluation decision. Loss of this data is catastrophic and unrecoverable. This document describes the backup strategy, tools, and restore procedures.

---

## SQLite Backup

### WAL Mode

All file-backed SQLite stores enable WAL (Write-Ahead Logging) at construction time:

```
PRAGMA journal_mode=WAL
```

WAL provides:
- Concurrent readers during writes
- Crash-safe atomic commits
- Better performance under concurrent access

In-memory databases (`:memory:`) are excluded.

### Backup Command

```bash
python -m efl_kernel.tools.backup sqlite \
    --audit-db /data/efl_audit.db \
    --op-db /data/efl_op.db \
    --dest /backups
```

This uses Python's `sqlite3.Connection.backup()` API for an online, consistent backup. No downtime required.

### Output

Each backup produces:
- A timestamped `.db` file (e.g., `audit_20260308T120000Z.db`)
- An updated `.last_backup.json` metadata file in the destination directory

### Scheduling

Use cron or Task Scheduler:

```cron
# Every 6 hours
0 */6 * * * python -m efl_kernel.tools.backup sqlite --audit-db /data/efl_audit.db --op-db /data/efl_op.db --dest /backups/sqlite
```

---

## PostgreSQL Backup

### Backup Command

```bash
python -m efl_kernel.tools.backup pg \
    --database-url postgresql://user:pass@host:5432/efl \
    --dest /backups/pg
```

Requires `pg_dump` on PATH. Produces a plain-text SQL dump.

### Scheduling

```cron
# Daily at 02:00
0 2 * * * python -m efl_kernel.tools.backup pg --dest /backups/pg
```

The tool reads `EFL_DATABASE_URL` if `--database-url` is not provided.

---

## Verification

### SQLite

```bash
python -m efl_kernel.tools.backup verify --backup-path /backups/sqlite/audit_20260308T120000Z.db
```

Runs `PRAGMA integrity_check` and reports tables and SHA-256 checksum.

### PostgreSQL

```bash
python -m efl_kernel.tools.backup verify --backup-path /backups/pg/pg_20260308T120000Z.sql
```

Validates the file exists and is non-empty.

---

## Restore Procedures

### SQLite Restore

1. Stop the EFL Kernel service.
2. Copy the backup file over the production database:
   ```bash
   cp /backups/sqlite/audit_20260308T120000Z.db /data/efl_audit.db
   ```
3. Restart the service. The migration runner will verify schema checksums on startup.

### PostgreSQL Restore

1. Stop the EFL Kernel service.
2. Drop and recreate the database:
   ```bash
   dropdb efl && createdb efl
   psql efl < /backups/pg/pg_20260308T120000Z.sql
   ```
3. Restart the service.

---

## Health Monitoring

`GET /health/backup` returns the current backup status:

- `EFL_BACKUP_DIR` not set → `{"status": "not_configured"}`
- No backups yet → `{"status": "no_backups"}`
- Backups exist → `{"status": "ok", "last_backup": {...}}`

Use this endpoint for monitoring/alerting on backup freshness.

---

## Retention

The backup tool does not delete old backups. Implement a retention policy externally:

```bash
# Keep last 30 days of SQLite backups
find /backups/sqlite -name "*.db" -mtime +30 -delete
```

---

## Metadata File

`.last_backup.json` in the backup directory tracks all backups:

```json
{
  "backups": [
    {
      "type": "sqlite",
      "label": "audit",
      "backup_path": "/backups/audit_20260308T120000Z.db",
      "timestamp": "2026-03-08T12:00:00+00:00",
      "sha256": "abc123...",
      "size_bytes": 4096
    }
  ],
  "last_backup": { ... }
}
```
