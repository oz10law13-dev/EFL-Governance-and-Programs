from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import psycopg

from .pg_pool import apply_ddl

_DDL_PATH = Path(__file__).parent.parent / "ddl" / "op_ddl.sql"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PgOperationalStore:
    """OperationalStore backed by PostgreSQL.

    Uses BOOLEAN for e4_clearance and is_collapsed (replaces SQLite INTEGER 0/1).
    Parameterized with %s (psycopg3 style). ON CONFLICT upserts preserve created_at.
    Shares the same interface as SqliteOperationalStore.
    """

    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn
        apply_ddl(conn, _DDL_PATH)

    # ------------------------------------------------------------------ #
    # Athletes                                                             #
    # ------------------------------------------------------------------ #

    def upsert_athlete(self, athlete: dict) -> None:
        """Insert or replace an op_athletes row.

        created_at is preserved for existing rows (not in DO UPDATE SET).
        updated_at defaults to current UTC time if not provided.
        """
        now = _now()
        created_at = athlete.get("created_at", now)
        updated_at = athlete.get("updated_at", now)
        self._conn.execute(
            "INSERT INTO op_athletes "
            "(athlete_id, max_daily_contact_load, minimum_rest_interval_hours, "
            "e4_clearance, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (athlete_id) DO UPDATE SET "
            "    max_daily_contact_load = EXCLUDED.max_daily_contact_load, "
            "    minimum_rest_interval_hours = EXCLUDED.minimum_rest_interval_hours, "
            "    e4_clearance = EXCLUDED.e4_clearance, "
            "    updated_at = EXCLUDED.updated_at",
            (
                athlete["athlete_id"],
                athlete["max_daily_contact_load"],
                athlete["minimum_rest_interval_hours"],
                bool(athlete["e4_clearance"]),
                created_at,
                updated_at,
            ),
        )
        self._conn.commit()

    def get_athlete(self, athlete_id: str) -> dict | None:
        """Return the op_athletes row as a dict, or None if not found."""
        return self._conn.execute(
            "SELECT athlete_id, max_daily_contact_load, minimum_rest_interval_hours, "
            "e4_clearance, created_at, updated_at "
            "FROM op_athletes WHERE athlete_id = %s",
            (athlete_id,),
        ).fetchone()

    # ------------------------------------------------------------------ #
    # Sessions                                                             #
    # ------------------------------------------------------------------ #

    def upsert_session(self, session: dict) -> None:
        """Insert or replace an op_sessions row.

        created_at defaults to current UTC time if not provided.
        """
        created_at = session.get("created_at", _now())
        self._conn.execute(
            "INSERT INTO op_sessions "
            "(session_id, athlete_id, session_date, contact_load, created_at, "
            "readiness_state, is_collapsed) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (session_id) DO UPDATE SET "
            "    athlete_id = EXCLUDED.athlete_id, "
            "    session_date = EXCLUDED.session_date, "
            "    contact_load = EXCLUDED.contact_load, "
            "    readiness_state = EXCLUDED.readiness_state, "
            "    is_collapsed = EXCLUDED.is_collapsed",
            (
                session["session_id"],
                session["athlete_id"],
                session["session_date"],
                session["contact_load"],
                created_at,
                session.get("readiness_state"),
                bool(session.get("is_collapsed", False)),
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

        Excludes the row matching exclude_session_id. Ordered by session_date ASC.
        """
        return self._conn.execute(
            "SELECT session_id, athlete_id, session_date, contact_load "
            "FROM op_sessions "
            "WHERE athlete_id = %s "
            "  AND session_date >= %s "
            "  AND session_date <= %s "
            "  AND session_id != %s "
            "ORDER BY session_date ASC",
            (athlete_id, window_start, anchor_date, exclude_session_id),
        ).fetchall()

    def get_prior_session(self, athlete_id: str, before_date: str) -> dict | None:
        """Return the most recent op_sessions row with session_date < before_date."""
        return self._conn.execute(
            "SELECT session_id, athlete_id, session_date, contact_load "
            "FROM op_sessions "
            "WHERE athlete_id = %s AND session_date < %s "
            "ORDER BY session_date DESC "
            "LIMIT 1",
            (athlete_id, before_date),
        ).fetchone()

    def get_readiness_history(
        self, athlete_id: str, window_start: str, anchor_date: str
    ) -> list[str]:
        """Return readiness_state values for sessions in window, ASC order."""
        rows = self._conn.execute(
            "SELECT readiness_state FROM op_sessions "
            "WHERE athlete_id = %s AND session_date >= %s AND session_date <= %s "
            "  AND readiness_state IS NOT NULL "
            "ORDER BY session_date ASC",
            (athlete_id, window_start, anchor_date),
        ).fetchall()
        return [row["readiness_state"] for row in rows]

    def get_collapse_count(
        self, athlete_id: str, window_start: str, anchor_date: str
    ) -> int:
        """Return count of collapsed sessions in window."""
        row = self._conn.execute(
            "SELECT COUNT(*) AS cnt FROM op_sessions "
            "WHERE athlete_id = %s AND session_date >= %s AND session_date <= %s "
            "  AND is_collapsed = TRUE",
            (athlete_id, window_start, anchor_date),
        ).fetchone()
        return row["cnt"] if row else 0

    # ------------------------------------------------------------------ #
    # Seasons                                                              #
    # ------------------------------------------------------------------ #

    def upsert_season(self, season: dict) -> None:
        """Insert or replace an op_seasons row.

        created_at is preserved for existing rows (not in DO UPDATE SET).
        updated_at defaults to current UTC time if not provided.
        """
        now = _now()
        created_at = season.get("created_at", now)
        updated_at = season.get("updated_at", now)
        self._conn.execute(
            "INSERT INTO op_seasons "
            "(athlete_id, season_id, competition_weeks, gpp_weeks, "
            "start_date, end_date, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (athlete_id, season_id) DO UPDATE SET "
            "    competition_weeks = EXCLUDED.competition_weeks, "
            "    gpp_weeks = EXCLUDED.gpp_weeks, "
            "    start_date = EXCLUDED.start_date, "
            "    end_date = EXCLUDED.end_date, "
            "    updated_at = EXCLUDED.updated_at",
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
        return self._conn.execute(
            "SELECT athlete_id, season_id, competition_weeks, gpp_weeks, "
            "start_date, end_date, created_at, updated_at "
            "FROM op_seasons "
            "WHERE athlete_id = %s AND season_id = %s",
            (athlete_id, season_id),
        ).fetchone()
