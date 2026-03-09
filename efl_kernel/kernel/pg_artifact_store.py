from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from .pg_pool import apply_ddl
from .ral import canonicalize_and_hash

_DDL_PATH = Path(__file__).parent.parent / "ddl" / "artifact_ddl.sql"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PgArtifactStore:
    """ArtifactStore backed by PostgreSQL.

    Uses JSONB for content_json. Parameterized with %s (psycopg3 style).
    Shares the same interface as SqliteArtifactStore.
    content_json column returns a native Python dict from JSONB reads.
    """

    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn
        apply_ddl(conn, _DDL_PATH)

    def commit_artifact_version(
        self,
        artifact_id: str,
        module_id: str,
        object_id: str,
        content: dict,
        org_id: str = "default",
    ) -> dict:
        """Create a new immutable artifact version in DRAFT state."""
        content_hash = canonicalize_and_hash(content)
        version_id = str(uuid.uuid4())
        now = _now()
        self._conn.execute(
            "INSERT INTO artifact_versions "
            "(version_id, artifact_id, module_id, object_id, content_json, "
            "content_hash, lifecycle, created_at, updated_at, org_id) "
            "VALUES (%s, %s, %s, %s, %s, %s, 'DRAFT', %s, %s, %s)",
            (version_id, artifact_id, module_id, object_id,
             Jsonb(content), content_hash, now, now, org_id),
        )
        self._conn.commit()
        return self._conn.execute(
            "SELECT * FROM artifact_versions WHERE version_id = %s", (version_id,)
        ).fetchone()

    def link_kdo(
        self,
        version_id: str,
        decision_hash: str,
        content_hash_at_eval: str,
    ) -> dict:
        """Link a KDO decision_hash to a version."""
        link_id = str(uuid.uuid4())
        now = _now()
        self._conn.execute(
            "INSERT INTO artifact_kdo_links "
            "(link_id, version_id, decision_hash, content_hash_at_eval, linked_at) "
            "VALUES (%s, %s, %s, %s, %s)",
            (link_id, version_id, decision_hash, content_hash_at_eval, now),
        )
        self._conn.commit()
        return self._conn.execute(
            "SELECT * FROM artifact_kdo_links WHERE link_id = %s", (link_id,)
        ).fetchone()

    def add_review_record(
        self,
        artifact_version_id: str,
        decision_hash: str,
        reviewer_id: str,
        reason: str,
        decision: str,
    ) -> dict:
        """Add a review record. decision must be 'APPROVE' or 'REJECT'."""
        if decision not in ("APPROVE", "REJECT"):
            raise ValueError(f"decision must be 'APPROVE' or 'REJECT', got {decision!r}")
        review_id = str(uuid.uuid4())
        now = _now()
        self._conn.execute(
            "INSERT INTO review_records "
            "(review_id, artifact_version_id, decision_hash, reviewer_id, "
            "reviewed_at, reason, decision) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (review_id, artifact_version_id, decision_hash, reviewer_id,
             now, reason, decision),
        )
        self._conn.commit()
        return self._conn.execute(
            "SELECT * FROM review_records WHERE review_id = %s", (review_id,)
        ).fetchone()

    def promote_to_live(self, version_id: str, get_kdo_fn, org_id: str = "default") -> dict:
        """Promote a DRAFT artifact version to LIVE.

        Enforces INV-1 through INV-4. get_kdo_fn is injected to avoid
        a hard dependency on the audit store.
        """
        version = self._conn.execute(
            "SELECT * FROM artifact_versions WHERE version_id = %s", (version_id,)
        ).fetchone()
        if version is None:
            raise ValueError(f"artifact version {version_id!r} not found")

        if version.get("org_id", "default") != org_id:
            raise ValueError("org_id mismatch")

        if version["lifecycle"] == "LIVE":
            return version

        if version["lifecycle"] == "RETIRED":
            raise ValueError("cannot promote RETIRED artifact")

        link = self._conn.execute(
            "SELECT * FROM artifact_kdo_links "
            "WHERE version_id = %s ORDER BY linked_at DESC LIMIT 1",
            (version_id,),
        ).fetchone()
        if link is None:
            raise ValueError("no KDO linked")

        kdo = get_kdo_fn(link["decision_hash"])
        if kdo is None:
            raise ValueError("KDO not found")

        if link["content_hash_at_eval"] != version["content_hash"]:
            raise ValueError("content hash mismatch: artifact mutated after evaluation")

        final_publish_state = kdo["resolution"]["finalPublishState"]

        if final_publish_state == "LEGALREADY":
            pass
        elif final_publish_state in ("REQUIRESREVIEW", "LEGALOVERRIDE"):
            review = self._conn.execute(
                "SELECT * FROM review_records "
                "WHERE artifact_version_id = %s ORDER BY reviewed_at DESC LIMIT 1",
                (version_id,),
            ).fetchone()
            if review is None:
                raise ValueError("review required")
            if review["decision"] != "APPROVE":
                raise ValueError("review decision is not APPROVE")
        else:
            raise ValueError(
                f"publish state {final_publish_state!r} is not eligible for LIVE"
            )

        now = _now()
        self._conn.execute(
            "UPDATE artifact_versions SET lifecycle='LIVE', updated_at=%s "
            "WHERE version_id=%s",
            (now, version_id),
        )
        self._conn.commit()
        return self._conn.execute(
            "SELECT * FROM artifact_versions WHERE version_id = %s", (version_id,)
        ).fetchone()

    def retire(self, version_id: str, org_id: str = "default") -> dict:
        """Retire an artifact version (DRAFT or LIVE → RETIRED)."""
        version = self._conn.execute(
            "SELECT * FROM artifact_versions WHERE version_id = %s", (version_id,)
        ).fetchone()
        if version is None:
            raise ValueError(f"artifact version {version_id!r} not found")
        if version.get("org_id", "default") != org_id:
            raise ValueError("org_id mismatch")
        if version["lifecycle"] == "RETIRED":
            raise ValueError(f"artifact version {version_id!r} is already RETIRED")
        now = _now()
        self._conn.execute(
            "UPDATE artifact_versions SET lifecycle='RETIRED', updated_at=%s "
            "WHERE version_id=%s",
            (now, version_id),
        )
        self._conn.commit()
        return self._conn.execute(
            "SELECT * FROM artifact_versions WHERE version_id = %s", (version_id,)
        ).fetchone()

    def get_version(self, version_id: str) -> dict | None:
        """Return artifact_versions row as dict, or None."""
        return self._conn.execute(
            "SELECT * FROM artifact_versions WHERE version_id = %s", (version_id,)
        ).fetchone()

    def get_live_versions(self, artifact_id: str, org_id: str = "default") -> list[dict]:
        """Return all LIVE versions for artifact_id, ordered by created_at DESC."""
        return self._conn.execute(
            "SELECT * FROM artifact_versions "
            "WHERE artifact_id = %s AND lifecycle = 'LIVE' AND org_id = %s "
            "ORDER BY created_at DESC",
            (artifact_id, org_id),
        ).fetchall()

    def get_versions(self, artifact_id: str, org_id: str = "default") -> list[dict]:
        """Return all versions for artifact_id, ordered by created_at DESC."""
        return self._conn.execute(
            "SELECT * FROM artifact_versions "
            "WHERE artifact_id = %s AND org_id = %s ORDER BY created_at DESC",
            (artifact_id, org_id),
        ).fetchall()

    def get_versions_by_artifact_id(self, artifact_id: str, org_id: str = "default") -> list[dict]:
        """Return all versions for artifact_id, ordered by created_at DESC. Never raises."""
        return self._conn.execute(
            "SELECT * FROM artifact_versions "
            "WHERE artifact_id = %s AND org_id = %s ORDER BY created_at DESC",
            (artifact_id, org_id),
        ).fetchall()

    def _get_latest_link(self, version_id: str) -> dict | None:
        return self._conn.execute(
            "SELECT * FROM artifact_kdo_links "
            "WHERE version_id = %s ORDER BY linked_at DESC LIMIT 1",
            (version_id,),
        ).fetchone()

    def _get_review_records(self, version_id: str) -> list[dict]:
        return self._conn.execute(
            "SELECT * FROM review_records "
            "WHERE artifact_version_id = %s ORDER BY reviewed_at DESC",
            (version_id,),
        ).fetchall()

    def get_pending_reviews(self, get_kdo_fn, org_id: str = "default") -> list[dict]:
        """Return artifact versions pending review.

        get_kdo_fn: callable(decision_hash) -> dict | None
                    Injected to cross the audit/operational DB boundary.
        """
        rows = self._conn.execute(
            "SELECT av.version_id, av.artifact_id, av.module_id, av.object_id, "
            "       av.created_at, av.org_id, "
            "       akl.decision_hash "
            "FROM artifact_versions av "
            "JOIN artifact_kdo_links akl ON akl.version_id = av.version_id "
            "WHERE av.lifecycle = 'DRAFT' "
            "  AND av.org_id = %s "
            "  AND NOT EXISTS ( "
            "    SELECT 1 FROM review_records rr "
            "    WHERE rr.artifact_version_id = av.version_id "
            "      AND rr.decision = 'APPROVE' "
            "  ) "
            "ORDER BY av.created_at ASC",
            (org_id,),
        ).fetchall()

        results = []
        for r in rows:
            kdo = get_kdo_fn(r["decision_hash"])
            if kdo is None:
                continue
            state = kdo.get("resolution", {}).get("finalPublishState", "")
            if state in ("REQUIRESREVIEW", "LEGALOVERRIDE"):
                results.append({
                    "version_id": r["version_id"],
                    "artifact_id": r["artifact_id"],
                    "module_id": r["module_id"],
                    "object_id": r["object_id"],
                    "created_at": r["created_at"],
                    "org_id": r["org_id"],
                    "decision_hash": r["decision_hash"],
                    "publish_state": state,
                    "violation_count": len(kdo.get("violations", [])),
                })
        return results

    def get_review_detail(self, version_id: str, get_kdo_fn,
                          org_id: str = "default") -> dict | None:
        """Return full review detail for a version, or None if not found / wrong org."""
        version = self.get_version(version_id)
        if version is None:
            return None
        if version.get("org_id", "default") != org_id:
            return None

        link = self._get_latest_link(version_id)
        if link is None:
            return None

        kdo = get_kdo_fn(link["decision_hash"])
        reviews = self._get_review_records(version_id)

        return {
            "version": version,
            "kdo": kdo,
            "violations": kdo.get("violations", []) if kdo else [],
            "publish_state": kdo["resolution"]["finalPublishState"] if kdo else None,
            "reviews": reviews,
        }
