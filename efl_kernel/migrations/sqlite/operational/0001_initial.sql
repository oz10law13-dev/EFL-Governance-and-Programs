-- SQLite operational domain baseline: op_athletes, op_sessions, op_seasons,
-- artifact_versions, artifact_kdo_links, review_records

CREATE TABLE IF NOT EXISTS op_athletes (
    athlete_id                   TEXT PRIMARY KEY NOT NULL,
    max_daily_contact_load       REAL NOT NULL,
    minimum_rest_interval_hours  REAL NOT NULL,
    e4_clearance                 INTEGER NOT NULL,
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
    is_collapsed    INTEGER NOT NULL DEFAULT 0
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

CREATE TABLE IF NOT EXISTS artifact_versions (
    version_id     TEXT PRIMARY KEY NOT NULL,
    artifact_id    TEXT NOT NULL,
    module_id      TEXT NOT NULL,
    object_id      TEXT NOT NULL,
    content_json   TEXT NOT NULL,
    content_hash   TEXT NOT NULL,
    lifecycle      TEXT NOT NULL DEFAULT 'DRAFT',
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_av_artifact_id
    ON artifact_versions(artifact_id);

CREATE INDEX IF NOT EXISTS idx_av_lifecycle
    ON artifact_versions(lifecycle);

CREATE TABLE IF NOT EXISTS artifact_kdo_links (
    link_id              TEXT PRIMARY KEY NOT NULL,
    version_id           TEXT NOT NULL,
    decision_hash        TEXT NOT NULL,
    content_hash_at_eval TEXT NOT NULL,
    linked_at            TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_akl_version_id
    ON artifact_kdo_links(version_id);

CREATE TABLE IF NOT EXISTS review_records (
    review_id           TEXT PRIMARY KEY NOT NULL,
    artifact_version_id TEXT NOT NULL,
    decision_hash       TEXT NOT NULL,
    reviewer_id         TEXT NOT NULL,
    reviewed_at         TEXT NOT NULL,
    reason              TEXT NOT NULL,
    decision            TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rr_version_id
    ON review_records(artifact_version_id);
