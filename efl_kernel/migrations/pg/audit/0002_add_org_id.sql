ALTER TABLE kdo_log ADD COLUMN IF NOT EXISTS org_id TEXT NOT NULL DEFAULT 'default';
ALTER TABLE override_ledger ADD COLUMN IF NOT EXISTS org_id TEXT NOT NULL DEFAULT 'default';
CREATE INDEX IF NOT EXISTS idx_kdo_log_org ON kdo_log(org_id);
CREATE INDEX IF NOT EXISTS idx_override_org ON override_ledger(org_id);
