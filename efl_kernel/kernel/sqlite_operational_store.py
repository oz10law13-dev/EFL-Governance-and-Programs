from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

# Operational table DDL.
# Tables are prefixed op_ to avoid collision with audit tables
# (kdo_log, override_ledger) owned by audit_store.py.
# All FK relationships are logical only — enforced by the application,
# not by SQLite PRAGMA foreign_keys.
_DDL = """
CREATE TABLE IF NOT EXISTS op_athletes (
    athlete_id                   TEXT PRIMARY KEY NOT NULL,
    max_daily_contact_load       REAL NOT NULL,
    minimum_rest_interval_hours  REAL NOT NULL,
    e4_clearance                 INTEGER NOT NULL,
    created_at                   TEXT NOT NULL,
    updated_at                   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS op_sessions (
    session_id    TEXT PRIMARY KEY NOT NULL,
    athlete_id    TEXT NOT NULL,
    session_date  TEXT NOT NULL,
    contact_load  REAL NOT NULL,
    created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_op_sessions_athlete_date
    ON op_sessions(athlete_id, session_date);
CREATE TABLE IF NOT EXISTS op_seasons (
    athlete_id         TEXT NOT NULL,
    season_id          TEXT NOT NULL,
    competition_weeks  INTEGER NOT NULL,
    gpp_weeks          INTEGER NOT NULL,
    start_date         TEXT NOT NULL,
    end_date           TEXT NOT NULL,
    created_at         TEXT NOT NULL,
    updated_at         TEXT NOT NULL,
    PRIMARY KEY (athlete_id, season_id)
);
"""

_ATHLETE_COLS = (
    "athlete_id", "max_daily_contact_load", "minimum_rest_interval_hours",
    "e4_clearance", "created_at", "updated_at",
)
_SESSION_COLS = (
    "session_id", "athlete_id", "session_date", "contact_load", "created_at",
    "readiness_state", "is_collapsed",
)
_SEASON_COLS = (
    "athlete_id", "season_id", "competition_weeks", "gpp_weeks",
    "start_date", "end_date", "created_at", "updated_at",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SqliteOperationalStore:
    """Owns DDL and read/write access for the three operational tables.

    Shares the same SQLite database file as AuditStore (audit_store.py).
    Follows audit_store.py's initialization pattern: executescript for DDL,
    explicit commit after each write operation, check_same_thread=False.
    """

    def __init__(self, db_path: str = "efl_audit.db"):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_tables()
        self._migrate_schema()

    def _init_tables(self) -> None:
        self._conn.executescript(_DDL)
        self._conn.commit()

    def _migrate_schema(self) -> None:
        """Idempotent migration: add new columns to op_sessions if they don't exist."""
        for stmt in [
            "ALTER TABLE op_sessions ADD COLUMN readiness_state TEXT",
            "ALTER TABLE op_sessions ADD COLUMN is_collapsed INTEGER NOT NULL DEFAULT 0",
        ]:
            try:
                self._conn.execute(stmt)
            except sqlite3.OperationalError:
                pass  # column already exists
        self._conn.commit()

    # ------------------------------------------------------------------ #
    # Athletes                                                             #
    # ------------------------------------------------------------------ #

    def upsert_athlete(self, athlete: dict) -> None:
        """Insert or replace an op_athletes row.

        created_at is preserved from the existing row on update.
        updated_at defaults to current UTC time if not provided.
        """
        now = _now()
        existing = self.get_athlete(athlete["athlete_id"])
        created_at = existing["created_at"] if existing else athlete.get("created_at", now)
        updated_at = athlete.get("updated_at", now)
        self._conn.execute(
            "INSERT OR REPLACE INTO op_athletes "
            "(athlete_id, max_daily_contact_load, minimum_rest_interval_hours, "
            "e4_clearance, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                athlete["athlete_id"],
                athlete["max_daily_contact_load"],
                athlete["minimum_rest_interval_hours"],
                athlete["e4_clearance"],
                created_at,
                updated_at,
            ),
        )
        self._conn.commit()

    def get_athlete(self, athlete_id: str) -> dict | None:
        """Return the op_athletes row as a dict, or None if not found."""
        row = self._conn.execute(
            "SELECT athlete_id, max_daily_contact_load, minimum_rest_interval_hours, "
            "e4_clearance, created_at, updated_at "
            "FROM op_athletes WHERE athlete_id = ?",
            (athlete_id,),
        ).fetchone()
        return dict(row) if row is not None else None

    # ------------------------------------------------------------------ #
    # Sessions                                                             #
    # ------------------------------------------------------------------ #

    def upsert_session(self, session: dict) -> None:
        """Insert or replace an op_sessions row.

        created_at defaults to current UTC time if not provided.
        athlete_id is a logical FK to op_athletes.athlete_id — not enforced
        by SQLite; enforced by the caller (seed tool / Phase 11 provider).
        """
        created_at = session.get("created_at", _now())
        self._conn.execute(
            "INSERT OR REPLACE INTO op_sessions "
            "(session_id, athlete_id, session_date, contact_load, created_at, "
            "readiness_state, is_collapsed) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                session["session_id"],
                session["athlete_id"],
                session["session_date"],
                session["contact_load"],
                created_at,
                session.get("readiness_state"),
                int(session.get("is_collapsed", False)),
            ),
        )
        self._conn.commit()

    def get_sessions_in_window(
        self,
        athlete_id: str,
        window_start: str,
        anchor_date: str,
        exclude_session_id: str = "",
    ) -> list[dict]:
        """Return op_sessions rows within [window_start, anchor_date] inclusive.

        Excludes the row matching exclude_session_id (self-exclusion for
        rolling-window calculations). Ordered by session_date ASC.
        ISO 8601 string comparison is lexicographically correct.
        """
        rows = self._conn.execute(
            "SELECT session_id, athlete_id, session_date, contact_load "
            "FROM op_sessions "
            "WHERE athlete_id = ? "
            "  AND session_date >= ? "
            "  AND session_date <= ? "
            "  AND session_id != ? "
            "ORDER BY session_date ASC",
            (athlete_id, window_start, anchor_date, exclude_session_id),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_prior_session(self, athlete_id: str, before_date: str) -> dict | None:
        """Return the most recent op_sessions row with session_date < before_date.

        Strict less-than — the boundary date itself is excluded.
        Returns None if no qualifying row exists.
        """
        row = self._conn.execute(
            "SELECT session_id, athlete_id, session_date, contact_load "
            "FROM op_sessions "
            "WHERE athlete_id = ? AND session_date < ? "
            "ORDER BY session_date DESC "
            "LIMIT 1",
            (athlete_id, before_date),
        ).fetchone()
        return dict(row) if row is not None else None

    def get_readiness_history(
        self, athlete_id: str, window_start: str, anchor_date: str
    ) -> list[str]:
        """Return readiness_state values for sessions in window, ASC order.

        NULL readiness_state rows are excluded.
        """
        rows = self._conn.execute(
            "SELECT readiness_state FROM op_sessions "
            "WHERE athlete_id = ? AND session_date >= ? AND session_date <= ? "
            "  AND readiness_state IS NOT NULL "
            "ORDER BY session_date ASC",
            (athlete_id, window_start, anchor_date),
        ).fetchall()
        return [r[0] for r in rows]

    def get_collapse_count(
        self, athlete_id: str, window_start: str, anchor_date: str
    ) -> int:
        """Return count of collapsed (is_collapsed=1) sessions in window."""
        row = self._conn.execute(
            "SELECT COUNT(*) FROM op_sessions "
            "WHERE athlete_id = ? AND session_date >= ? AND session_date <= ? "
            "  AND is_collapsed = 1",
            (athlete_id, window_start, anchor_date),
        ).fetchone()
        return row[0] if row else 0

    # ------------------------------------------------------------------ #
    # Seasons                                                              #
    # ------------------------------------------------------------------ #

    def upsert_season(self, season: dict) -> None:
        """Insert or replace an op_seasons row.

        created_at is preserved from the existing row on update.
        updated_at defaults to current UTC time if not provided.
        athlete_id is a logical FK to op_athletes.athlete_id — not enforced
        by SQLite; enforced by the caller.
        """
        now = _now()
        existing = self.get_season(season["athlete_id"], season["season_id"])
        created_at = existing["created_at"] if existing else season.get("created_at", now)
        updated_at = season.get("updated_at", now)
        self._conn.execute(
            "INSERT OR REPLACE INTO op_seasons "
            "(athlete_id, season_id, competition_weeks, gpp_weeks, "
            "start_date, end_date, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                season["athlete_id"],
                season["season_id"],
                season["competition_weeks"],
                season["gpp_weeks"],
                season["start_date"],
                season["end_date"],
                created_at,
                updated_at,
            ),
        )
        self._conn.commit()

    def get_season(self, athlete_id: str, season_id: str) -> dict | None:
        """Return the op_seasons row for (athlete_id, season_id), or None."""
        row = self._conn.execute(
            "SELECT athlete_id, season_id, competition_weeks, gpp_weeks, "
            "start_date, end_date, created_at, updated_at "
            "FROM op_seasons "
            "WHERE athlete_id = ? AND season_id = ?",
            (athlete_id, season_id),
        ).fetchone()
        return dict(row) if row is not None else None
