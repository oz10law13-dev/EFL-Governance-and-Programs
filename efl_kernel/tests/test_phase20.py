"""Phase 20 — Schema Migration Versioning tests.

14 SQLite/runner tests always run.
3 PostgreSQL tests are skipped when EFL_TEST_DATABASE_URL is not set.
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

import pytest

from efl_kernel.migrations.runner import MigrationRunner, MigrationError

_PG_URL = os.environ.get("EFL_TEST_DATABASE_URL")
requires_pg = pytest.mark.skipif(
    not _PG_URL,
    reason="EFL_TEST_DATABASE_URL not set — PostgreSQL tests skipped",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sqlite_conn(db_path: str = ":memory:") -> sqlite3.Connection:
    return sqlite3.connect(db_path, check_same_thread=False)


def _table_exists_sqlite(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def _write_migration(base_dir: Path, filename: str, sql: str) -> Path:
    """Write a migration file and return the path."""
    filepath = base_dir / filename
    filepath.write_text(sql, encoding="utf-8")
    return filepath


def _runner_with_custom_dir(conn, dialect: str, domain: str, migration_dir: Path) -> MigrationRunner:
    """Create a runner that uses a custom migration directory."""
    runner = MigrationRunner(conn, dialect, domain)
    # Override the migration directory method
    runner._migration_dir = lambda: migration_dir
    return runner


# ---------------------------------------------------------------------------
# Test 1 — tracking table creation
# ---------------------------------------------------------------------------

def test_runner_creates_tracking_table_sqlite():
    """_schema_migrations table exists after ensure_current() on fresh SQLite."""
    conn = _sqlite_conn()
    runner = MigrationRunner(conn, "sqlite", "audit")
    runner._migration_dir = lambda: Path(tempfile.mkdtemp())  # empty dir
    runner.ensure_current()
    assert _table_exists_sqlite(conn, "_schema_migrations")
    conn.close()


# ---------------------------------------------------------------------------
# Test 2 — fresh install audit
# ---------------------------------------------------------------------------

def test_runner_fresh_install_creates_tables_sqlite(tmp_path):
    """Audit domain: kdo_log + override_ledger created from migration 0001."""
    db = str(tmp_path / "test_audit.db")
    conn = _sqlite_conn(db)
    runner = MigrationRunner(conn, "sqlite", "audit")
    result = runner.ensure_current()
    assert 1 in result["applied"]
    assert _table_exists_sqlite(conn, "kdo_log")
    assert _table_exists_sqlite(conn, "override_ledger")
    conn.close()


# ---------------------------------------------------------------------------
# Test 3 — fresh install operational
# ---------------------------------------------------------------------------

def test_runner_fresh_install_operational_sqlite(tmp_path):
    """Operational domain: all 6 tables created from migration 0001."""
    db = str(tmp_path / "test_op.db")
    conn = _sqlite_conn(db)
    runner = MigrationRunner(conn, "sqlite", "operational")
    result = runner.ensure_current()
    assert 1 in result["applied"]
    for table in ("op_athletes", "op_sessions", "op_seasons",
                  "artifact_versions", "artifact_kdo_links", "review_records"):
        assert _table_exists_sqlite(conn, table), f"Table {table} not found"
    conn.close()


# ---------------------------------------------------------------------------
# Test 4 — idempotent
# ---------------------------------------------------------------------------

def test_runner_idempotent_sqlite(tmp_path):
    """Second ensure_current() returns applied=[]."""
    db = str(tmp_path / "idem.db")
    conn = _sqlite_conn(db)
    runner = MigrationRunner(conn, "sqlite", "audit")
    r1 = runner.ensure_current()
    assert 1 in r1["applied"]
    r2 = runner.ensure_current()
    assert r2["applied"] == []
    assert r2["current_version"] >= 1
    conn.close()


# ---------------------------------------------------------------------------
# Test 5 — bootstrap existing DB
# ---------------------------------------------------------------------------

def test_runner_bootstrap_existing_db_sqlite(tmp_path):
    """Create tables via old DDL path, then run runner → 0001 recorded but NOT re-executed."""
    from efl_kernel.kernel.sqlite_audit_store import _DDL
    db = str(tmp_path / "bootstrap.db")
    conn = _sqlite_conn(db)
    conn.executescript(_DDL)
    conn.commit()
    # Insert a row so we can verify it's preserved
    conn.execute(
        "INSERT INTO kdo_log (decision_hash, timestamp_normalized, module_id, object_id, kdo_json) "
        "VALUES ('BOOT-HASH', '2026-01-01', 'SESSION', 'OBJ1', '{}')"
    )
    conn.commit()

    runner = MigrationRunner(conn, "sqlite", "audit")
    result = runner.ensure_current()
    assert result["bootstrapped"] is True
    assert 1 not in result["applied"]  # 0001 was recorded, not executed
    assert result["current_version"] >= 1
    # Data is still there
    row = conn.execute("SELECT * FROM kdo_log WHERE decision_hash='BOOT-HASH'").fetchone()
    assert row is not None
    conn.close()


# ---------------------------------------------------------------------------
# Test 6 — checksum mismatch
# ---------------------------------------------------------------------------

def test_runner_checksum_mismatch_raises(tmp_path):
    """Apply 0001, modify the file, run again → MigrationError."""
    db = str(tmp_path / "cs.db")
    conn = _sqlite_conn(db)

    # Create a custom migration dir with one migration
    mdir = tmp_path / "migrations"
    mdir.mkdir()
    _write_migration(mdir, "0001_initial.sql",
                     "CREATE TABLE IF NOT EXISTS _test_t1 (id TEXT PRIMARY KEY);")

    runner = _runner_with_custom_dir(conn, "sqlite", "audit", mdir)
    runner.ensure_current()

    # Tamper with the file
    _write_migration(mdir, "0001_initial.sql",
                     "CREATE TABLE IF NOT EXISTS _test_t1 (id TEXT PRIMARY KEY, extra TEXT);")

    runner2 = _runner_with_custom_dir(conn, "sqlite", "audit", mdir)
    with pytest.raises(MigrationError, match="Checksum mismatch"):
        runner2.ensure_current()
    conn.close()


# ---------------------------------------------------------------------------
# Test 7 — incremental migration
# ---------------------------------------------------------------------------

def test_runner_incremental_migration(tmp_path):
    """Write a 0002 migration file, run → only 0002 applies."""
    db = str(tmp_path / "incr.db")
    conn = _sqlite_conn(db)

    # Copy real migration 0001
    mdir = tmp_path / "migrations"
    mdir.mkdir()
    real_0001 = Path(__file__).parent.parent / "migrations" / "sqlite" / "audit" / "0001_initial.sql"
    shutil.copy2(real_0001, mdir / "0001_initial.sql")

    runner = _runner_with_custom_dir(conn, "sqlite", "audit", mdir)
    r1 = runner.ensure_current()
    assert r1["applied"] == [1]

    # Add 0002
    _write_migration(mdir, "0002_add_test_column.sql",
                     "ALTER TABLE kdo_log ADD COLUMN _test_col TEXT;")

    runner2 = _runner_with_custom_dir(conn, "sqlite", "audit", mdir)
    r2 = runner2.ensure_current()
    assert r2["applied"] == [2]
    assert r2["current_version"] == 2
    conn.close()


# ---------------------------------------------------------------------------
# Test 8 — skips already applied
# ---------------------------------------------------------------------------

def test_runner_skips_already_applied(tmp_path):
    """0001 already applied, add 0002 → only 0002 executes."""
    db = str(tmp_path / "skip.db")
    conn = _sqlite_conn(db)

    mdir = tmp_path / "migrations"
    mdir.mkdir()
    real_0001 = Path(__file__).parent.parent / "migrations" / "sqlite" / "audit" / "0001_initial.sql"
    shutil.copy2(real_0001, mdir / "0001_initial.sql")

    runner = _runner_with_custom_dir(conn, "sqlite", "audit", mdir)
    runner.ensure_current()

    _write_migration(mdir, "0002_add_col.sql",
                     "ALTER TABLE kdo_log ADD COLUMN _skip_test TEXT;")

    runner2 = _runner_with_custom_dir(conn, "sqlite", "audit", mdir)
    r = runner2.ensure_current()
    assert 1 not in r["applied"]
    assert 2 in r["applied"]
    conn.close()


# ---------------------------------------------------------------------------
# Test 9 — status reports pending
# ---------------------------------------------------------------------------

def test_runner_status_reports_pending(tmp_path):
    """status() shows pending versions without applying."""
    db = str(tmp_path / "status.db")
    conn = _sqlite_conn(db)
    runner = MigrationRunner(conn, "sqlite", "audit")
    st = runner.status()
    assert st["current_version"] is None
    assert 1 in st["pending"]
    assert st["total_applied"] == 0
    # Tables should NOT be created
    assert not _table_exists_sqlite(conn, "kdo_log")
    conn.close()


# ---------------------------------------------------------------------------
# Test 10 — verify clean
# ---------------------------------------------------------------------------

def test_runner_verify_clean(tmp_path):
    """verify() passes when no files tampered."""
    db = str(tmp_path / "verify.db")
    conn = _sqlite_conn(db)
    runner = MigrationRunner(conn, "sqlite", "audit")
    runner.ensure_current()
    runner.verify()  # should not raise
    conn.close()


# ---------------------------------------------------------------------------
# Test 11 — missing file raises
# ---------------------------------------------------------------------------

def test_runner_missing_file_raises(tmp_path):
    """Delete an applied migration file → verify() raises MigrationError."""
    db = str(tmp_path / "missing.db")
    conn = _sqlite_conn(db)

    mdir = tmp_path / "migrations"
    mdir.mkdir()
    f = _write_migration(mdir, "0001_initial.sql",
                         "CREATE TABLE IF NOT EXISTS _miss_t (id TEXT PRIMARY KEY);")

    runner = _runner_with_custom_dir(conn, "sqlite", "audit", mdir)
    runner.ensure_current()

    # Delete the file
    f.unlink()

    runner2 = _runner_with_custom_dir(conn, "sqlite", "audit", mdir)
    with pytest.raises(MigrationError, match="no corresponding file"):
        runner2.verify()
    conn.close()


# ---------------------------------------------------------------------------
# Test 12 — domain isolation
# ---------------------------------------------------------------------------

def test_runner_domain_isolation(tmp_path):
    """Audit and operational domains track independently in same DB."""
    db = str(tmp_path / "iso.db")
    conn = _sqlite_conn(db)

    audit_runner = MigrationRunner(conn, "sqlite", "audit")
    op_runner = MigrationRunner(conn, "sqlite", "operational")

    r_audit = audit_runner.ensure_current()
    assert r_audit["current_version"] >= 1

    st_op = op_runner.status()
    assert st_op["current_version"] is None
    assert 1 in st_op["pending"]

    r_op = op_runner.ensure_current()
    assert r_op["current_version"] >= 1

    # Both domains independently tracked
    assert audit_runner.status()["current_version"] >= 1
    assert op_runner.status()["current_version"] >= 1
    conn.close()


# ---------------------------------------------------------------------------
# Test 13 — create_app file-backed has tracking table
# ---------------------------------------------------------------------------

def test_create_app_file_backed_has_tracking_table(tmp_path):
    """create_app(str(db)) → _schema_migrations exists in the DB file."""
    from efl_kernel.service import create_app
    db = str(tmp_path / "fb_audit.db")
    op = str(tmp_path / "fb_op.db")
    create_app(db_path=db, op_db_path=op)

    conn = sqlite3.connect(db, check_same_thread=False)
    assert _table_exists_sqlite(conn, "_schema_migrations")
    conn.close()

    conn2 = sqlite3.connect(op, check_same_thread=False)
    assert _table_exists_sqlite(conn2, "_schema_migrations")
    conn2.close()


# ---------------------------------------------------------------------------
# Test 14 — create_app :memory: has no tracking table
# ---------------------------------------------------------------------------

def test_create_app_memory_has_no_tracking_table():
    """create_app() with default :memory: → no _schema_migrations (old path used)."""
    from efl_kernel.service import create_app
    app = create_app(db_path=":memory:", op_db_path=":memory:")
    # The stores' internal connections should NOT have _schema_migrations
    assert not _table_exists_sqlite(app.state.audit_store._conn, "_schema_migrations")


# ---------------------------------------------------------------------------
# PG tests
# ---------------------------------------------------------------------------

@requires_pg
def test_runner_pg_creates_tracking(tmp_path):
    """PG _schema_migrations created + baseline applied."""
    from efl_kernel.kernel.pg_pool import open_pg
    conn = open_pg(_PG_URL)
    try:
        runner = MigrationRunner(conn, "pg", "audit")
        result = runner.ensure_current()
        assert result["current_version"] == 1
        row = conn.execute(
            "SELECT * FROM _schema_migrations WHERE domain=%s AND version=%s",
            ("audit", 1),
        ).fetchone()
        assert row is not None
    finally:
        conn.execute("DROP TABLE IF EXISTS _schema_migrations")
        conn.commit()
        conn.close()


@requires_pg
def test_runner_pg_bootstrap():
    """Existing PG tables → bootstrap recorded without execution."""
    from efl_kernel.kernel.pg_pool import open_pg
    conn = open_pg(_PG_URL)
    try:
        # Tables already exist from Phase 19 PgAuditStore usage
        # The runner should detect kdo_log and bootstrap
        runner = MigrationRunner(conn, "pg", "audit")
        # Drop _schema_migrations so we start fresh
        conn.execute("DROP TABLE IF EXISTS _schema_migrations")
        conn.commit()

        result = runner.ensure_current()
        # kdo_log exists (created by PgAuditStore), so bootstrap should trigger
        assert result["bootstrapped"] is True
        assert result["current_version"] == 1
    finally:
        conn.execute("DROP TABLE IF EXISTS _schema_migrations")
        conn.commit()
        conn.close()


@requires_pg
def test_runner_pg_incremental():
    """0002 migration applies on PG."""
    from efl_kernel.kernel.pg_pool import open_pg
    conn = open_pg(_PG_URL)
    try:
        # Set up custom dir with 0001 + 0002
        mdir = Path(tempfile.mkdtemp())
        real_0001 = Path(__file__).parent.parent / "migrations" / "pg" / "audit" / "0001_initial.sql"
        shutil.copy2(real_0001, mdir / "0001_initial.sql")

        # Drop tracking table for fresh start
        conn.execute("DROP TABLE IF EXISTS _schema_migrations")
        conn.commit()

        runner = _runner_with_custom_dir(conn, "pg", "audit", mdir)
        runner.ensure_current()  # bootstrap or apply 0001

        # Add 0002
        _write_migration(mdir, "0002_add_test_column.sql",
                         "ALTER TABLE kdo_log ADD COLUMN IF NOT EXISTS _test_col TEXT;")

        runner2 = _runner_with_custom_dir(conn, "pg", "audit", mdir)
        r2 = runner2.ensure_current()
        assert 2 in r2["applied"]
        assert r2["current_version"] == 2

        # Clean up the test column
        conn.execute("ALTER TABLE kdo_log DROP COLUMN IF EXISTS _test_col")
        conn.commit()
        shutil.rmtree(mdir)
    finally:
        conn.execute("DROP TABLE IF EXISTS _schema_migrations")
        conn.commit()
        conn.close()
