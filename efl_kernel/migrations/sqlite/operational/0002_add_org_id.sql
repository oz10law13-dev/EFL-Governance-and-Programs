ALTER TABLE op_athletes ADD COLUMN org_id TEXT NOT NULL DEFAULT 'default';
ALTER TABLE op_sessions ADD COLUMN org_id TEXT NOT NULL DEFAULT 'default';
ALTER TABLE op_seasons ADD COLUMN org_id TEXT NOT NULL DEFAULT 'default';
ALTER TABLE artifact_versions ADD COLUMN org_id TEXT NOT NULL DEFAULT 'default';
CREATE INDEX IF NOT EXISTS idx_op_athletes_org ON op_athletes(org_id);
CREATE INDEX IF NOT EXISTS idx_op_sessions_org ON op_sessions(org_id, athlete_id, session_date);
CREATE INDEX IF NOT EXISTS idx_op_seasons_org ON op_seasons(org_id, athlete_id);
CREATE INDEX IF NOT EXISTS idx_av_org ON artifact_versions(org_id);
