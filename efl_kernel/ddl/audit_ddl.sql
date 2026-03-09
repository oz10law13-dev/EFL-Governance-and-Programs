-- PostgreSQL DDL for audit store tables.
-- kdo_json uses JSONB for native JSON storage and indexing.
-- timestamp_normalized is TEXT (ISO 8601 string) — not TIMESTAMPTZ.

CREATE TABLE IF NOT EXISTS kdo_log (
    decision_hash        TEXT PRIMARY KEY,
    timestamp_normalized TEXT NOT NULL,
    module_id            TEXT NOT NULL,
    object_id            TEXT NOT NULL,
    kdo_json             JSONB NOT NULL,
    org_id               TEXT NOT NULL DEFAULT 'default'
);

CREATE INDEX IF NOT EXISTS idx_kdo_log_org ON kdo_log(org_id);

CREATE TABLE IF NOT EXISTS override_ledger (
    lineage_key          TEXT NOT NULL,
    module_id            TEXT NOT NULL,
    violation_code       TEXT NOT NULL,
    reason_code          TEXT NOT NULL,
    timestamp_normalized TEXT NOT NULL,
    org_id               TEXT NOT NULL DEFAULT 'default',
    PRIMARY KEY (lineage_key, module_id, violation_code, reason_code, timestamp_normalized)
);

CREATE INDEX IF NOT EXISTS idx_override_org ON override_ledger(org_id);
