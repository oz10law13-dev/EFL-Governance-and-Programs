"""Phase 21 — Backup/Restore Strategy + WAL Configuration tests.

16 SQLite/backup tests always run.
1 PostgreSQL test is skipped when EFL_TEST_DATABASE_URL is not set.
"""
from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from efl_kernel.tools.backup import (
    backup_sqlite,
    backup_pg,
    verify_sqlite_backup,
    verify_pg_backup,
    _sha256_file,
    _write_metadata,
)

_PG_URL = os.environ.get("EFL_TEST_DATABASE_URL")
requires_pg = pytest.mark.skipif(
    not _PG_URL,
    reason="EFL_TEST_DATABASE_URL not set — PostgreSQL tests skipped",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_test_db(db_path: str, table: str = "kdo_log") -> None:
    """Create a minimal SQLite DB with one table and one row."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute(f"CREATE TABLE IF NOT EXISTS {table} (id TEXT PRIMARY KEY, data TEXT)")
    conn.execute(f"INSERT INTO {table} VALUES ('test-1', 'hello')")
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Test 1 — WAL mode on SqliteAuditStore (file-backed)
# ---------------------------------------------------------------------------

def test_wal_mode_audit_store(tmp_path):
    """SqliteAuditStore enables WAL on file-backed databases."""
    from efl_kernel.kernel.sqlite_audit_store import SqliteAuditStore
    db = str(tmp_path / "audit_wal.db")
    store = SqliteAuditStore(db)
    mode = store._conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode == "wal"


# ---------------------------------------------------------------------------
# Test 2 — WAL mode on SqliteOperationalStore (file-backed)
# ---------------------------------------------------------------------------

def test_wal_mode_operational_store(tmp_path):
    """SqliteOperationalStore enables WAL on file-backed databases."""
    from efl_kernel.kernel.sqlite_operational_store import SqliteOperationalStore
    db = str(tmp_path / "op_wal.db")
    store = SqliteOperationalStore(db)
    mode = store._conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode == "wal"


# ---------------------------------------------------------------------------
# Test 3 — WAL mode on SqliteArtifactStore (file-backed)
# ---------------------------------------------------------------------------

def test_wal_mode_artifact_store(tmp_path):
    """SqliteArtifactStore enables WAL on file-backed databases."""
    from efl_kernel.kernel.sqlite_artifact_store import SqliteArtifactStore
    db = str(tmp_path / "art_wal.db")
    store = SqliteArtifactStore(db)
    mode = store._conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode == "wal"


# ---------------------------------------------------------------------------
# Test 4 — :memory: does NOT get WAL
# ---------------------------------------------------------------------------

def test_memory_no_wal():
    """In-memory databases do not attempt WAL mode."""
    from efl_kernel.kernel.sqlite_audit_store import SqliteAuditStore
    store = SqliteAuditStore(":memory:")
    mode = store._conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode == "memory"


# ---------------------------------------------------------------------------
# Test 5 — backup_sqlite produces a valid copy
# ---------------------------------------------------------------------------

def test_backup_sqlite_produces_copy(tmp_path):
    """backup_sqlite creates a backup that contains the source data."""
    src = str(tmp_path / "src.db")
    _create_test_db(src)

    dest = str(tmp_path / "backups")
    entry = backup_sqlite(src, dest, label="test")

    assert entry["type"] == "sqlite"
    assert entry["label"] == "test"
    assert entry["size_bytes"] > 0
    assert "sha256" in entry

    # Verify backup contains the data
    conn = sqlite3.connect(entry["backup_path"], check_same_thread=False)
    row = conn.execute("SELECT data FROM kdo_log WHERE id='test-1'").fetchone()
    conn.close()
    assert row[0] == "hello"


# ---------------------------------------------------------------------------
# Test 6 — backup_sqlite writes metadata file
# ---------------------------------------------------------------------------

def test_backup_sqlite_writes_metadata(tmp_path):
    """backup_sqlite creates .last_backup.json in dest dir."""
    src = str(tmp_path / "src.db")
    _create_test_db(src)

    dest = str(tmp_path / "backups")
    entry = backup_sqlite(src, dest, label="audit")

    meta_path = os.path.join(dest, ".last_backup.json")
    assert os.path.exists(meta_path)
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    assert meta["last_backup"]["label"] == "audit"
    assert len(meta["backups"]) == 1


# ---------------------------------------------------------------------------
# Test 7 — multiple backups append to metadata
# ---------------------------------------------------------------------------

def test_backup_sqlite_appends_metadata(tmp_path):
    """Two sequential backups → two entries in metadata."""
    src = str(tmp_path / "src.db")
    _create_test_db(src)
    dest = str(tmp_path / "backups")

    backup_sqlite(src, dest, label="first")
    backup_sqlite(src, dest, label="second")

    meta_path = os.path.join(dest, ".last_backup.json")
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    assert len(meta["backups"]) == 2
    assert meta["last_backup"]["label"] == "second"


# ---------------------------------------------------------------------------
# Test 8 — verify_sqlite_backup passes on good backup
# ---------------------------------------------------------------------------

def test_verify_sqlite_backup_good(tmp_path):
    """verify_sqlite_backup returns OK for a valid backup."""
    src = str(tmp_path / "src.db")
    _create_test_db(src)
    dest = str(tmp_path / "backups")
    entry = backup_sqlite(src, dest)

    result = verify_sqlite_backup(entry["backup_path"])
    assert result["status"] == "ok"
    assert "kdo_log" in result["tables"]
    assert result["sha256"] == entry["sha256"]


# ---------------------------------------------------------------------------
# Test 9 — verify_sqlite_backup fails on corrupt file
# ---------------------------------------------------------------------------

def test_verify_sqlite_backup_corrupt(tmp_path):
    """verify_sqlite_backup raises on a corrupt file."""
    bad_path = str(tmp_path / "corrupt.db")
    with open(bad_path, "wb") as f:
        f.write(b"this is not a sqlite database")

    with pytest.raises(Exception):
        verify_sqlite_backup(bad_path)


# ---------------------------------------------------------------------------
# Test 10 — sha256 checksum consistency
# ---------------------------------------------------------------------------

def test_sha256_consistency(tmp_path):
    """_sha256_file returns consistent results."""
    f = tmp_path / "test.txt"
    f.write_text("hello world", encoding="utf-8")
    h1 = _sha256_file(str(f))
    h2 = _sha256_file(str(f))
    assert h1 == h2
    assert len(h1) == 64  # hex digest length


# ---------------------------------------------------------------------------
# Test 11 — backup dest dir auto-created
# ---------------------------------------------------------------------------

def test_backup_creates_dest_dir(tmp_path):
    """backup_sqlite creates the destination directory if it doesn't exist."""
    src = str(tmp_path / "src.db")
    _create_test_db(src)
    dest = str(tmp_path / "nested" / "deep" / "backups")
    entry = backup_sqlite(src, dest)
    assert os.path.exists(entry["backup_path"])


# ---------------------------------------------------------------------------
# Test 12 — health/backup not configured
# ---------------------------------------------------------------------------

def test_health_backup_not_configured():
    """GET /health/backup returns not_configured when EFL_BACKUP_DIR not set."""
    from efl_kernel.service import create_app
    app = create_app(db_path=":memory:", op_db_path=":memory:")
    client = TestClient(app)
    # Ensure EFL_BACKUP_DIR is not set
    old = os.environ.pop("EFL_BACKUP_DIR", None)
    try:
        resp = client.get("/health/backup")
        assert resp.status_code == 200
        assert resp.json()["status"] == "not_configured"
    finally:
        if old is not None:
            os.environ["EFL_BACKUP_DIR"] = old


# ---------------------------------------------------------------------------
# Test 13 — health/backup no backups yet
# ---------------------------------------------------------------------------

def test_health_backup_no_backups(tmp_path):
    """GET /health/backup returns no_backups when dir exists but no metadata."""
    from efl_kernel.service import create_app
    app = create_app(db_path=":memory:", op_db_path=":memory:")
    client = TestClient(app)
    backup_dir = str(tmp_path / "empty_backups")
    os.makedirs(backup_dir, exist_ok=True)
    old = os.environ.get("EFL_BACKUP_DIR")
    os.environ["EFL_BACKUP_DIR"] = backup_dir
    try:
        resp = client.get("/health/backup")
        assert resp.status_code == 200
        assert resp.json()["status"] == "no_backups"
    finally:
        if old is not None:
            os.environ["EFL_BACKUP_DIR"] = old
        else:
            os.environ.pop("EFL_BACKUP_DIR", None)


# ---------------------------------------------------------------------------
# Test 14 — health/backup with backup metadata
# ---------------------------------------------------------------------------

def test_health_backup_with_metadata(tmp_path):
    """GET /health/backup returns metadata when .last_backup.json exists."""
    from efl_kernel.service import create_app
    app = create_app(db_path=":memory:", op_db_path=":memory:")
    client = TestClient(app)

    backup_dir = str(tmp_path / "backups")
    os.makedirs(backup_dir, exist_ok=True)
    # Write a metadata file
    meta = {
        "backups": [{"label": "test", "timestamp": "2026-03-08T00:00:00Z"}],
        "last_backup": {"label": "test", "timestamp": "2026-03-08T00:00:00Z"},
    }
    with open(os.path.join(backup_dir, ".last_backup.json"), "w") as f:
        json.dump(meta, f)

    old = os.environ.get("EFL_BACKUP_DIR")
    os.environ["EFL_BACKUP_DIR"] = backup_dir
    try:
        resp = client.get("/health/backup")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["last_backup"]["label"] == "test"
    finally:
        if old is not None:
            os.environ["EFL_BACKUP_DIR"] = old
        else:
            os.environ.pop("EFL_BACKUP_DIR", None)


# ---------------------------------------------------------------------------
# Test 15 — verify_pg_backup good file
# ---------------------------------------------------------------------------

def test_verify_pg_backup_good(tmp_path):
    """verify_pg_backup returns OK for a non-empty SQL file."""
    f = tmp_path / "test.sql"
    f.write_text("-- PostgreSQL dump\nCREATE TABLE test (id int);", encoding="utf-8")
    result = verify_pg_backup(str(f), "")
    assert result["status"] == "ok"
    assert result["size_bytes"] > 0


# ---------------------------------------------------------------------------
# Test 16 — verify_pg_backup missing file
# ---------------------------------------------------------------------------

def test_verify_pg_backup_missing(tmp_path):
    """verify_pg_backup raises on missing file."""
    with pytest.raises(RuntimeError, match="not found"):
        verify_pg_backup(str(tmp_path / "nonexistent.sql"), "")


# ---------------------------------------------------------------------------
# Test 17 — PG backup (requires pg_dump + EFL_TEST_DATABASE_URL)
# ---------------------------------------------------------------------------

@requires_pg
def test_backup_pg_creates_dump(tmp_path):
    """backup_pg produces a .sql dump file."""
    import shutil
    if shutil.which("pg_dump") is None:
        pytest.skip("pg_dump not on PATH")
    dest = str(tmp_path / "pg_backups")
    entry = backup_pg(_PG_URL, dest, label="test_pg")
    assert entry["type"] == "pg"
    assert entry["size_bytes"] > 0
    assert os.path.exists(entry["backup_path"])
