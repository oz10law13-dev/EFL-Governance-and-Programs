-- SQLite audit domain baseline: kdo_log + override_ledger

CREATE TABLE IF NOT EXISTS kdo_log (
    decision_hash        TEXT PRIMARY KEY,
    timestamp_normalized TEXT NOT NULL,
    module_id            TEXT NOT NULL,
    object_id            TEXT NOT NULL,
    kdo_json             TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS override_ledger (
    lineage_key          TEXT NOT NULL,
    module_id            TEXT NOT NULL,
    violation_code       TEXT NOT NULL,
    reason_code          TEXT NOT NULL,
    timestamp_normalized TEXT NOT NULL,
    PRIMARY KEY (lineage_key, module_id, violation_code, reason_code, timestamp_normalized)
);
