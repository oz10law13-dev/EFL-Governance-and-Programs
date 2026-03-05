from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone

from .ral import canonicalize_and_hash

_DDL = """
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
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ArtifactStore:
    def __init__(self, db_path: str = "efl_audit.db"):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_DDL)
        self._conn.commit()

    def commit_artifact_version(
        self,
        artifact_id: str,
        module_id: str,
        object_id: str,
        content: dict,
    ) -> dict:
        """Create a new immutable artifact version in DRAFT state.

        Always inserts a new row with a new version_id. Never updates
        existing content or content_hash (INV-1).
        """
        content_hash = canonicalize_and_hash(content)
        version_id = str(uuid.uuid4())
        now = _now()
        self._conn.execute(
            "INSERT INTO artifact_versions "
            "(version_id, artifact_id, module_id, object_id, content_json, "
            "content_hash, lifecycle, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 'DRAFT', ?, ?)",
            (version_id, artifact_id, module_id, object_id,
             json.dumps(content), content_hash, now, now),
        )
        self._conn.commit()
        row = self._conn.execute(
            "SELECT * FROM artifact_versions WHERE version_id = ?", (version_id,)
        ).fetchone()
        return dict(row)

    def link_kdo(
        self,
        version_id: str,
        decision_hash: str,
        content_hash_at_eval: str,
    ) -> dict:
        """Link a KDO decision_hash to a version.

        Does not verify promotion eligibility — that is promote_to_live's job.
        """
        link_id = str(uuid.uuid4())
        now = _now()
        self._conn.execute(
            "INSERT INTO artifact_kdo_links "
            "(link_id, version_id, decision_hash, content_hash_at_eval, linked_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (link_id, version_id, decision_hash, content_hash_at_eval, now),
        )
        self._conn.commit()
        row = self._conn.execute(
            "SELECT * FROM artifact_kdo_links WHERE link_id = ?", (link_id,)
        ).fetchone()
        return dict(row)

    def add_review_record(
        self,
        artifact_version_id: str,
        decision_hash: str,
        reviewer_id: str,
        reason: str,
        decision: str,
    ) -> dict:
        """Add a review record for an artifact version.

        decision must be "APPROVE" or "REJECT".
        """
        if decision not in ("APPROVE", "REJECT"):
            raise ValueError(f"decision must be 'APPROVE' or 'REJECT', got {decision!r}")
        review_id = str(uuid.uuid4())
        now = _now()
        self._conn.execute(
            "INSERT INTO review_records "
            "(review_id, artifact_version_id, decision_hash, reviewer_id, "
            "reviewed_at, reason, decision) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (review_id, artifact_version_id, decision_hash, reviewer_id,
             now, reason, decision),
        )
        self._conn.commit()
        row = self._conn.execute(
            "SELECT * FROM review_records WHERE review_id = ?", (review_id,)
        ).fetchone()
        return dict(row)

    def promote_to_live(self, version_id: str, get_kdo_fn) -> dict:
        """Promote a DRAFT artifact version to LIVE.

        Enforces all four invariants:
        INV-1: content immutability verified by hash comparison
        INV-2: content_hash_at_eval must match version.content_hash
        INV-3: KDO publish state must be LEGALREADY/REQUIRESREVIEW/LEGALOVERRIDE
        INV-4: REQUIRESREVIEW/LEGALOVERRIDE require an APPROVE review record

        get_kdo_fn: callable(decision_hash) -> dict | None
                    Use audit_store.get_kdo. Injected to avoid hard dependency.
        """
        # 1. Fetch artifact_version row
        row = self._conn.execute(
            "SELECT * FROM artifact_versions WHERE version_id = ?", (version_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"artifact version {version_id!r} not found")
        version = dict(row)

        # 2. Idempotent for already-LIVE
        if version["lifecycle"] == "LIVE":
            return version

        # 3. RETIRED cannot be promoted
        if version["lifecycle"] == "RETIRED":
            raise ValueError("cannot promote RETIRED artifact")

        # 4. Fetch latest KDO link (most recently linked)
        link_row = self._conn.execute(
            "SELECT * FROM artifact_kdo_links "
            "WHERE version_id = ? ORDER BY linked_at DESC LIMIT 1",
            (version_id,),
        ).fetchone()
        if link_row is None:
            raise ValueError("no KDO linked")
        link = dict(link_row)

        # 5. Fetch KDO via injected callable
        kdo = get_kdo_fn(link["decision_hash"])
        if kdo is None:
            raise ValueError("KDO not found")

        # 6. Verify content hash (INV-2)
        if link["content_hash_at_eval"] != version["content_hash"]:
            raise ValueError("content hash mismatch: artifact mutated after evaluation")

        # 7. Read finalPublishState
        final_publish_state = kdo["resolution"]["finalPublishState"]

        # 8. Apply promotion rules (INV-3, INV-4)
        if final_publish_state == "LEGALREADY":
            pass  # direct promotion, no review required
        elif final_publish_state in ("REQUIRESREVIEW", "LEGALOVERRIDE"):
            review_row = self._conn.execute(
                "SELECT * FROM review_records "
                "WHERE artifact_version_id = ? ORDER BY reviewed_at DESC LIMIT 1",
                (version_id,),
            ).fetchone()
            if review_row is None:
                raise ValueError("review required")
            review = dict(review_row)
            if review["decision"] != "APPROVE":
                raise ValueError("review decision is not APPROVE")
        else:
            raise ValueError(
                f"publish state {final_publish_state!r} is not eligible for LIVE"
            )

        # 9. Promote
        now = _now()
        self._conn.execute(
            "UPDATE artifact_versions SET lifecycle='LIVE', updated_at=? "
            "WHERE version_id=?",
            (now, version_id),
        )
        self._conn.commit()

        # 10. Return updated row
        updated = self._conn.execute(
            "SELECT * FROM artifact_versions WHERE version_id = ?", (version_id,)
        ).fetchone()
        return dict(updated)

    def retire(self, version_id: str) -> dict:
        """Retire an artifact version (DRAFT or LIVE → RETIRED).

        Raises ValueError if already RETIRED or not found.
        """
        row = self._conn.execute(
            "SELECT * FROM artifact_versions WHERE version_id = ?", (version_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"artifact version {version_id!r} not found")
        version = dict(row)
        if version["lifecycle"] == "RETIRED":
            raise ValueError(f"artifact version {version_id!r} is already RETIRED")
        now = _now()
        self._conn.execute(
            "UPDATE artifact_versions SET lifecycle='RETIRED', updated_at=? "
            "WHERE version_id=?",
            (now, version_id),
        )
        self._conn.commit()
        updated = self._conn.execute(
            "SELECT * FROM artifact_versions WHERE version_id = ?", (version_id,)
        ).fetchone()
        return dict(updated)

    def get_version(self, version_id: str) -> dict | None:
        """Return artifact_versions row as dict, or None."""
        row = self._conn.execute(
            "SELECT * FROM artifact_versions WHERE version_id = ?", (version_id,)
        ).fetchone()
        return dict(row) if row is not None else None

    def get_live_versions(self, artifact_id: str) -> list[dict]:
        """Return all LIVE versions for artifact_id, ordered by created_at DESC."""
        rows = self._conn.execute(
            "SELECT * FROM artifact_versions "
            "WHERE artifact_id = ? AND lifecycle = 'LIVE' "
            "ORDER BY created_at DESC",
            (artifact_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_versions(self, artifact_id: str) -> list[dict]:
        """Return all versions for artifact_id (all lifecycle states), ordered by created_at DESC."""
        rows = self._conn.execute(
            "SELECT * FROM artifact_versions "
            "WHERE artifact_id = ? "
            "ORDER BY created_at DESC",
            (artifact_id,),
        ).fetchall()
        return [dict(r) for r in rows]
