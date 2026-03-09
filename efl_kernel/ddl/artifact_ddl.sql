-- PostgreSQL DDL for artifact store tables.
-- content_json uses JSONB for native JSON storage.
-- All timestamp columns are TEXT (ISO 8601 strings), not TIMESTAMPTZ.

CREATE TABLE IF NOT EXISTS artifact_versions (
    version_id     TEXT PRIMARY KEY NOT NULL,
    artifact_id    TEXT NOT NULL,
    module_id      TEXT NOT NULL,
    object_id      TEXT NOT NULL,
    content_json   JSONB NOT NULL,
    content_hash   TEXT NOT NULL,
    lifecycle      TEXT NOT NULL DEFAULT 'DRAFT',
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL,
    org_id         TEXT NOT NULL DEFAULT 'default'
);

CREATE INDEX IF NOT EXISTS idx_av_artifact_id
    ON artifact_versions(artifact_id);

CREATE INDEX IF NOT EXISTS idx_av_lifecycle
    ON artifact_versions(lifecycle);

CREATE INDEX IF NOT EXISTS idx_av_org
    ON artifact_versions(org_id);

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
