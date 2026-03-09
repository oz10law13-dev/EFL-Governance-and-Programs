from __future__ import annotations

import hashlib
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_MIGRATIONS_DIR = Path(__file__).parent

_TRACKING_DDL = """
CREATE TABLE IF NOT EXISTS _schema_migrations (
    domain      TEXT NOT NULL,
    version     INTEGER NOT NULL,
    filename    TEXT NOT NULL,
    checksum    TEXT NOT NULL,
    applied_at  TEXT NOT NULL,
    PRIMARY KEY (domain, version)
);
"""

# Table used to detect existing data for bootstrap.
_BOOTSTRAP_TABLES = {
    "audit": "kdo_log",
    "operational": "op_athletes",
}

_MIGRATION_FILENAME_RE = re.compile(r"^(\d{4})_.+\.sql$")


class MigrationError(Exception):
    """Raised on checksum mismatch, missing migration file, or execution failure."""


def _checksum(filepath: Path) -> str:
    content = filepath.read_text(encoding="utf-8").replace("\r\n", "\n")
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MigrationRunner:
    """Dialect- and domain-aware numbered migration runner.

    Supports SQLite and PostgreSQL. Tracks applied migrations in
    _schema_migrations with SHA-256 checksum verification (frozen migration
    discipline). Bootstraps pre-existing databases by recording baseline
    migration without re-executing.
    """

    def __init__(self, conn, dialect: str, domain: str) -> None:
        """
        conn:    sqlite3.Connection or psycopg.Connection
        dialect: "sqlite" or "pg"
        domain:  "audit" or "operational"
        """
        if dialect not in ("sqlite", "pg"):
            raise ValueError(f"Unsupported dialect: {dialect!r}")
        if domain not in ("audit", "operational"):
            raise ValueError(f"Unsupported domain: {domain!r}")
        self._conn = conn
        self.dialect = dialect
        self.domain = domain

    def _migration_dir(self) -> Path:
        return _MIGRATIONS_DIR / self.dialect / self.domain

    def _ensure_tracking_table(self) -> None:
        if self.dialect == "sqlite":
            for stmt in _TRACKING_DDL.split(";"):
                stmt = stmt.strip()
                if stmt:
                    self._conn.execute(stmt)
            self._conn.commit()
        else:
            for stmt in _TRACKING_DDL.split(";"):
                stmt = stmt.strip()
                if stmt:
                    self._conn.execute(stmt)
            self._conn.commit()

    def _discover_migrations(self) -> list[tuple[int, Path]]:
        """Return sorted list of (version, filepath) from migration directory."""
        mdir = self._migration_dir()
        if not mdir.exists():
            return []
        found: list[tuple[int, Path]] = []
        for f in sorted(mdir.iterdir()):
            m = _MIGRATION_FILENAME_RE.match(f.name)
            if m:
                found.append((int(m.group(1)), f))
        return sorted(found, key=lambda x: x[0])

    def _applied_versions(self) -> dict[int, dict]:
        """Return {version: {filename, checksum}} for this domain."""
        if self.dialect == "sqlite":
            rows = self._conn.execute(
                "SELECT version, filename, checksum FROM _schema_migrations WHERE domain = ?",
                (self.domain,),
            ).fetchall()
            return {r[0]: {"filename": r[1], "checksum": r[2]} for r in rows}
        else:
            rows = self._conn.execute(
                "SELECT version, filename, checksum FROM _schema_migrations WHERE domain = %s",
                (self.domain,),
            ).fetchall()
            return {r["version"]: {"filename": r["filename"], "checksum": r["checksum"]} for r in rows}

    def _table_exists(self, table_name: str) -> bool:
        if self.dialect == "sqlite":
            row = self._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,),
            ).fetchone()
            return row is not None
        else:
            row = self._conn.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename=%s",
                (table_name,),
            ).fetchone()
            return row is not None

    def _execute_migration_sqlite(self, sql: str) -> None:
        """Execute migration SQL in SQLite — statement by statement within explicit transaction.

        ALTER TABLE ADD COLUMN that hits 'duplicate column name' is silently
        skipped — this makes migrations idempotent when store constructors
        have already added the column via _migrate_org_id().
        """
        self._conn.execute("BEGIN")
        try:
            for stmt in sql.split(";"):
                stmt = stmt.strip()
                if stmt:
                    try:
                        self._conn.execute(stmt)
                    except sqlite3.OperationalError as e:
                        if "duplicate column name" in str(e):
                            pass  # column already exists — idempotent
                        else:
                            raise
            self._conn.execute("COMMIT")
        except Exception:
            self._conn.execute("ROLLBACK")
            raise

    def _execute_migration_pg(self, sql: str) -> None:
        """Execute migration SQL in PostgreSQL — full content as single execute."""
        self._conn.execute(sql)
        self._conn.commit()

    def _record_migration(self, version: int, filename: str, checksum: str) -> None:
        if self.dialect == "sqlite":
            self._conn.execute(
                "INSERT INTO _schema_migrations (domain, version, filename, checksum, applied_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (self.domain, version, filename, checksum, _now()),
            )
            self._conn.commit()
        else:
            self._conn.execute(
                "INSERT INTO _schema_migrations (domain, version, filename, checksum, applied_at) "
                "VALUES (%s, %s, %s, %s, %s)",
                (self.domain, version, filename, checksum, _now()),
            )
            self._conn.commit()

    def ensure_current(self) -> dict:
        """Apply all pending migrations. Return summary dict."""
        self._ensure_tracking_table()
        migrations = self._discover_migrations()
        applied = self._applied_versions()

        # Bootstrap detection: no rows for this domain but data tables exist
        was_bootstrapped = False
        if not applied and migrations:
            bootstrap_table = _BOOTSTRAP_TABLES.get(self.domain)
            if bootstrap_table and self._table_exists(bootstrap_table):
                # Record 0001 as applied WITHOUT executing
                first_ver, first_path = migrations[0]
                cs = _checksum(first_path)
                self._record_migration(first_ver, first_path.name, cs)
                applied = self._applied_versions()
                was_bootstrapped = True

        # Verify checksums of all already-applied migrations
        self._verify_applied(applied, migrations)

        # Apply pending
        applied_versions: list[int] = []
        for version, filepath in migrations:
            if version in applied:
                continue
            cs = _checksum(filepath)
            sql = filepath.read_text(encoding="utf-8")
            try:
                if self.dialect == "sqlite":
                    self._execute_migration_sqlite(sql)
                else:
                    self._execute_migration_pg(sql)
            except Exception as e:
                raise MigrationError(
                    f"Migration {filepath.name} (version {version}) failed: {e}"
                ) from e
            self._record_migration(version, filepath.name, cs)
            applied_versions.append(version)

        all_applied = self._applied_versions()
        max_version = max(all_applied.keys()) if all_applied else 0

        return {
            "applied": applied_versions,
            "current_version": max_version,
            "bootstrapped": was_bootstrapped,
        }

    def status(self) -> dict:
        """Return current state without applying anything."""
        self._ensure_tracking_table()
        migrations = self._discover_migrations()
        applied = self._applied_versions()
        pending = [v for v, _ in migrations if v not in applied]
        max_version = max(applied.keys()) if applied else None
        return {
            "current_version": max_version,
            "pending": pending,
            "total_applied": len(applied),
        }

    def verify(self) -> None:
        """Verify checksums of all applied migrations.

        Raises MigrationError on mismatch or missing file.
        """
        self._ensure_tracking_table()
        migrations = self._discover_migrations()
        applied = self._applied_versions()
        self._verify_applied(applied, migrations)

    def _verify_applied(self, applied: dict[int, dict], migrations: list[tuple[int, Path]]) -> None:
        """Internal verification — check all applied migrations against files."""
        migration_map = {v: p for v, p in migrations}
        for version, info in applied.items():
            filepath = migration_map.get(version)
            if filepath is None:
                raise MigrationError(
                    f"Applied migration version {version} ({info['filename']}) "
                    f"has no corresponding file in {self._migration_dir()}"
                )
            current_checksum = _checksum(filepath)
            if current_checksum != info["checksum"]:
                raise MigrationError(
                    f"Checksum mismatch for migration {info['filename']} (version {version}): "
                    f"expected {info['checksum']}, got {current_checksum}"
                )
