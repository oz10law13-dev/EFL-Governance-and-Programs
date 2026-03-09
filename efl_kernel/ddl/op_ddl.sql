-- PostgreSQL DDL for operational store tables.
-- e4_clearance uses BOOLEAN (replaces SQLite INTEGER 0/1).
-- is_collapsed uses BOOLEAN DEFAULT FALSE (replaces SQLite INTEGER DEFAULT 0).
-- All timestamp columns are TEXT (ISO 8601 strings), not TIMESTAMPTZ.

CREATE TABLE IF NOT EXISTS op_athletes (
    athlete_id                   TEXT PRIMARY KEY NOT NULL,
    max_daily_contact_load       REAL NOT NULL,
    minimum_rest_interval_hours  REAL NOT NULL,
    e4_clearance                 BOOLEAN NOT NULL,
    created_at                   TEXT NOT NULL,
    updated_at                   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS op_sessions (
    session_id      TEXT PRIMARY KEY NOT NULL,
    athlete_id      TEXT NOT NULL,
    session_date    TEXT NOT NULL,
    contact_load    REAL NOT NULL,
    created_at      TEXT NOT NULL,
    readiness_state TEXT,
    is_collapsed    BOOLEAN NOT NULL DEFAULT FALSE
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
