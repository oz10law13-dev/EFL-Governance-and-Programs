from __future__ import annotations

from pathlib import Path

import psycopg
from psycopg.rows import dict_row


def open_pg(database_url: str) -> psycopg.Connection:
    """Open a psycopg3 synchronous connection with dict_row factory."""
    return psycopg.connect(database_url, row_factory=dict_row)


def apply_ddl(conn: psycopg.Connection, ddl_path: Path) -> None:
    """Apply a DDL SQL file to the connection and commit.

    Splits on semicolons. Skips empty statements.
    CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS are idempotent.
    """
    ddl = ddl_path.read_text()
    for stmt in ddl.split(";"):
        stmt = stmt.strip()
        if stmt:
            conn.execute(stmt)
    conn.commit()
