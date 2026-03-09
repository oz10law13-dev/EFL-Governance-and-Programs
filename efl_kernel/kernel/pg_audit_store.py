from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from .kdo import KDO, freeze_kdo
from .pg_pool import apply_ddl

_DDL_PATH = Path(__file__).parent.parent / "ddl" / "audit_ddl.sql"


class PgAuditStore:
    """AuditStore backed by PostgreSQL.

    Uses JSONB for kdo_json. Parameterized with %s (psycopg3 style).
    Shares the same interface as SqliteAuditStore.
    """

    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn
        apply_ddl(conn, _DDL_PATH)

    def commit_kdo(self, kdo: KDO) -> str:
        """Freeze the KDO (if not already), persist it, and append override ledger entries.

        Append-only: a duplicate decision_hash is silently ignored and no override
        records are written for it a second time.
        """
        if not kdo.audit.get("decisionHash"):
            freeze_kdo(kdo)
        decision_hash = kdo.audit["decisionHash"]

        cur = self._conn.execute(
            "INSERT INTO kdo_log "
            "(decision_hash, timestamp_normalized, module_id, object_id, kdo_json) "
            "VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (
                decision_hash,
                kdo.timestamp_normalized,
                kdo.module_id,
                kdo.object_id,
                Jsonb(kdo.__dict__),
            ),
        )

        if cur.rowcount > 0:
            lineage_key = kdo.evaluation_context.get("lineageKey", "")
            if lineage_key:
                for v in kdo.violations:
                    if v.get("overrideUsed"):
                        self._conn.execute(
                            "INSERT INTO override_ledger "
                            "(lineage_key, module_id, violation_code, reason_code, timestamp_normalized) "
                            "VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                            (
                                lineage_key,
                                kdo.module_id,
                                v["code"],
                                v.get("overrideReasonCode") or "",
                                kdo.timestamp_normalized,
                            ),
                        )

        self._conn.commit()
        return decision_hash

    def get_kdo(self, decision_hash: str) -> dict | None:
        """Return the full KDO as a dict, or None if not found.

        JSONB column is returned as a native Python dict by psycopg3.
        """
        row = self._conn.execute(
            "SELECT kdo_json FROM kdo_log WHERE decision_hash = %s", (decision_hash,)
        ).fetchone()
        if row is None:
            return None
        val = row["kdo_json"]
        return val if isinstance(val, dict) else json.loads(val)

    def get_override_history(self, lineage_key: str, module_id: str, window_days: int = 28) -> dict:
        """Return rolling-window override counts in InMemoryDependencyProvider-compatible shape."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=window_days)).isoformat()
        rows = self._conn.execute(
            "SELECT violation_code, reason_code, COUNT(*) AS cnt "
            "FROM override_ledger "
            "WHERE lineage_key = %s AND module_id = %s AND timestamp_normalized >= %s "
            "GROUP BY violation_code, reason_code",
            (lineage_key, module_id, cutoff),
        ).fetchall()

        by_reason: dict[str, int] = {}
        by_violation: dict[str, int] = {}
        for row in rows:
            v_code = row["violation_code"]
            r_code = row["reason_code"]
            cnt = row["cnt"]
            by_violation[v_code] = by_violation.get(v_code, 0) + cnt
            if r_code:
                by_reason[r_code] = by_reason.get(r_code, 0) + cnt

        return {"byReasonCode": by_reason, "byViolationCode": by_violation}

    def get_metrics(self) -> dict:
        """Return aggregate counts from kdo_log using JSONB path operators."""
        total_row = self._conn.execute("SELECT COUNT(*) AS cnt FROM kdo_log").fetchone()
        kdo_total = total_row["cnt"] if total_row else 0

        by_module: dict[str, int] = {}
        for row in self._conn.execute(
            "SELECT module_id, COUNT(*) AS cnt FROM kdo_log GROUP BY module_id"
        ).fetchall():
            by_module[row["module_id"]] = row["cnt"]

        by_publish_state: dict[str, int] = {}
        for row in self._conn.execute(
            "SELECT kdo_json->'resolution'->>'finalPublishState' AS state, COUNT(*) AS cnt "
            "FROM kdo_log GROUP BY state"
        ).fetchall():
            state = row["state"]
            by_publish_state[state] = by_publish_state.get(state, 0) + row["cnt"]

        return {
            "kdo_total": kdo_total,
            "by_module": by_module,
            "by_publish_state": by_publish_state,
        }
