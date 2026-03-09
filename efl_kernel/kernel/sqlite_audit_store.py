from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone

from .kdo import KDO, freeze_kdo

_DDL = """
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
"""


class SqliteAuditStore:
    def __init__(self, db_path: str = ":memory:"):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        if db_path != ":memory:":
            self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_DDL)
        self._conn.commit()
        self._migrate_org_id()

    def _migrate_org_id(self) -> None:
        """Idempotent: add org_id columns if they don't exist."""
        for stmt in [
            "ALTER TABLE kdo_log ADD COLUMN org_id TEXT NOT NULL DEFAULT 'default'",
            "ALTER TABLE override_ledger ADD COLUMN org_id TEXT NOT NULL DEFAULT 'default'",
        ]:
            try:
                self._conn.execute(stmt)
            except sqlite3.OperationalError:
                pass
        self._conn.commit()

    def commit_kdo(self, kdo: KDO, org_id: str = "default") -> str:
        """Freeze the KDO (if not already), persist it, and append override ledger entries.

        Append-only: a duplicate decision_hash is silently ignored and no override
        records are written for it a second time.
        """
        if not kdo.audit.get("decisionHash"):
            freeze_kdo(kdo)
        decision_hash = kdo.audit["decisionHash"]

        cur = self._conn.execute(
            "INSERT OR IGNORE INTO kdo_log "
            "(decision_hash, timestamp_normalized, module_id, object_id, kdo_json, org_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                decision_hash,
                kdo.timestamp_normalized,
                kdo.module_id,
                kdo.object_id,
                json.dumps(kdo.__dict__),
                org_id,
            ),
        )

        if cur.rowcount > 0:
            lineage_key = kdo.evaluation_context.get("lineageKey", "")
            if lineage_key:
                for v in kdo.violations:
                    if v.get("overrideUsed"):
                        self._conn.execute(
                            "INSERT OR IGNORE INTO override_ledger "
                            "(lineage_key, module_id, violation_code, reason_code, "
                            "timestamp_normalized, org_id) "
                            "VALUES (?, ?, ?, ?, ?, ?)",
                            (
                                lineage_key,
                                kdo.module_id,
                                v["code"],
                                v.get("overrideReasonCode") or "",
                                kdo.timestamp_normalized,
                                org_id,
                            ),
                        )

        self._conn.commit()
        return decision_hash

    def get_kdo(self, decision_hash: str) -> dict | None:
        """Return the full KDO as a dict, or None if not found."""
        row = self._conn.execute(
            "SELECT kdo_json FROM kdo_log WHERE decision_hash = ?", (decision_hash,)
        ).fetchone()
        return json.loads(row[0]) if row is not None else None

    def get_override_history(self, lineage_key: str, module_id: str, window_days: int = 28, org_id: str = "default") -> dict:
        """Return rolling-window override counts in InMemoryDependencyProvider-compatible shape."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=window_days)).isoformat()
        rows = self._conn.execute(
            "SELECT violation_code, reason_code, COUNT(*) "
            "FROM override_ledger "
            "WHERE lineage_key = ? AND module_id = ? AND timestamp_normalized >= ? "
            "AND org_id = ? "
            "GROUP BY violation_code, reason_code",
            (lineage_key, module_id, cutoff, org_id),
        ).fetchall()

        by_reason: dict[str, int] = {}
        by_violation: dict[str, int] = {}
        for v_code, r_code, cnt in rows:
            by_violation[v_code] = by_violation.get(v_code, 0) + cnt
            if r_code:
                by_reason[r_code] = by_reason.get(r_code, 0) + cnt

        return {"byReasonCode": by_reason, "byViolationCode": by_violation}

    def get_metrics(self, org_id: str | None = None) -> dict:
        """Return aggregate counts from kdo_log.

        If org_id is not None, return counts scoped to that org.
        If org_id is None, return global counts (existing behavior).

        Returns:
            {
                "kdo_total": int,
                "by_module": {module_id: count, ...},
                "by_publish_state": {finalPublishState: count, ...},
            }
        """
        if org_id is not None:
            total_row = self._conn.execute(
                "SELECT COUNT(*) FROM kdo_log WHERE org_id = ?", (org_id,)
            ).fetchone()
            kdo_total = total_row[0] if total_row else 0

            by_module: dict[str, int] = {}
            for row in self._conn.execute(
                "SELECT module_id, COUNT(*) FROM kdo_log WHERE org_id = ? GROUP BY module_id",
                (org_id,),
            ).fetchall():
                by_module[row[0]] = row[1]

            by_publish_state: dict[str, int] = {}
            for row in self._conn.execute(
                "SELECT kdo_json FROM kdo_log WHERE org_id = ?", (org_id,)
            ).fetchall():
                state = json.loads(row[0])["resolution"]["finalPublishState"]
                by_publish_state[state] = by_publish_state.get(state, 0) + 1
        else:
            total_row = self._conn.execute("SELECT COUNT(*) FROM kdo_log").fetchone()
            kdo_total = total_row[0] if total_row else 0

            by_module = {}
            for row in self._conn.execute(
                "SELECT module_id, COUNT(*) FROM kdo_log GROUP BY module_id"
            ).fetchall():
                by_module[row[0]] = row[1]

            by_publish_state = {}
            for row in self._conn.execute("SELECT kdo_json FROM kdo_log").fetchall():
                state = json.loads(row[0])["resolution"]["finalPublishState"]
                by_publish_state[state] = by_publish_state.get(state, 0) + 1

        return {
            "kdo_total": kdo_total,
            "by_module": by_module,
            "by_publish_state": by_publish_state,
        }
