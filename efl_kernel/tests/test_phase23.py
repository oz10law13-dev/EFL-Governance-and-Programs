"""Phase 23 — Review Queue Surface (API) tests.

20 SQLite/route tests always run.
1 PostgreSQL test is skipped when EFL_TEST_DATABASE_URL is not set.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from efl_kernel.kernel.sqlite_audit_store import SqliteAuditStore
from efl_kernel.kernel.sqlite_artifact_store import SqliteArtifactStore
from efl_kernel.service import create_app

PG_URL = os.environ.get("EFL_TEST_DATABASE_URL")
requires_pg = pytest.mark.skipif(not PG_URL, reason="EFL_TEST_DATABASE_URL not set")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _inject_kdo(audit_store, decision_hash, publish_state, module_id="SESSION",
                violations=None):
    """Inject a crafted KDO directly into kdo_log for testing."""
    crafted = {
        "module_id": module_id,
        "resolution": {"finalPublishState": publish_state},
        "violations": violations or [
            {"code": "SCM.MAXDAILYLOAD", "moduleID": module_id,
             "severity": "CLAMP", "overrideUsed": True}
        ],
        "audit": {"decisionHash": decision_hash},
    }
    kdo_json = json.dumps(crafted, sort_keys=True, separators=(",", ":"))
    audit_store._conn.execute(
        "INSERT OR IGNORE INTO kdo_log "
        "(decision_hash, timestamp_normalized, module_id, object_id, kdo_json, org_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (decision_hash, datetime.now(timezone.utc).isoformat(),
         module_id, "OBJ-RQ", kdo_json, "default"),
    )
    audit_store._conn.commit()


def _create_reviewable(client, artifact_store, audit_store,
                       artifact_id, publish_state="REQUIRESREVIEW",
                       module_id="SESSION"):
    """Create a DRAFT artifact linked to a KDO with the given publish state."""
    dh = hashlib.sha256(f"{artifact_id}-{publish_state}".encode()).hexdigest()
    _inject_kdo(audit_store, dh, publish_state, module_id=module_id)

    r = client.post("/artifacts", json={
        "artifact_id": artifact_id,
        "module_id": module_id,
        "object_id": "OBJ-RQ",
        "content": {"review_test": artifact_id},
    })
    assert r.status_code == 201
    version_id = r.json()["version_id"]
    content_hash = r.json()["content_hash"]

    r = client.post(f"/artifacts/{version_id}/link-kdo", json={
        "decision_hash": dh,
        "content_hash_at_eval": content_hash,
    })
    assert r.status_code == 200

    return version_id, dh, content_hash


@pytest.fixture()
def svc():
    app = create_app(db_path=":memory:", op_db_path=":memory:")
    client = TestClient(app)
    return client, app.state.artifact_store, app.state.audit_store


# ---------------------------------------------------------------------------
# Store-level tests
# ---------------------------------------------------------------------------

class TestPendingReviews:
    def test_pending_reviews_empty(self, svc):
        client, art_store, audit_store = svc
        result = art_store.get_pending_reviews(audit_store.get_kdo)
        assert result == []

    def test_pending_reviews_finds_requiresreview(self, svc):
        client, art_store, audit_store = svc
        vid, dh, _ = _create_reviewable(client, art_store, audit_store, "ART-RQ-1")
        result = art_store.get_pending_reviews(audit_store.get_kdo)
        assert len(result) == 1
        assert result[0]["version_id"] == vid
        assert result[0]["publish_state"] == "REQUIRESREVIEW"

    def test_pending_reviews_finds_legaloverride(self, svc):
        client, art_store, audit_store = svc
        vid, dh, _ = _create_reviewable(client, art_store, audit_store, "ART-LO-1",
                                         publish_state="LEGALOVERRIDE")
        result = art_store.get_pending_reviews(audit_store.get_kdo)
        assert len(result) == 1
        assert result[0]["publish_state"] == "LEGALOVERRIDE"

    def test_pending_reviews_excludes_approved(self, svc):
        client, art_store, audit_store = svc
        vid, dh, _ = _create_reviewable(client, art_store, audit_store, "ART-EXCL-1")
        art_store.add_review_record(vid, dh, "coach", "ok", "APPROVE")
        result = art_store.get_pending_reviews(audit_store.get_kdo)
        assert len(result) == 0

    def test_pending_reviews_excludes_legalready(self, svc):
        client, art_store, audit_store = svc
        # Create with LEGALREADY — should not appear in pending
        dh = hashlib.sha256(b"LEGALREADY-test").hexdigest()
        _inject_kdo(audit_store, dh, "LEGALREADY")
        r = client.post("/artifacts", json={
            "artifact_id": "ART-LR-1", "module_id": "SESSION",
            "object_id": "OBJ-LR", "content": {"lr": True},
        })
        vid = r.json()["version_id"]
        client.post(f"/artifacts/{vid}/link-kdo", json={
            "decision_hash": dh, "content_hash_at_eval": r.json()["content_hash"],
        })
        result = art_store.get_pending_reviews(audit_store.get_kdo)
        assert len(result) == 0

    def test_pending_reviews_org_scoped(self, svc):
        client, art_store, audit_store = svc
        _create_reviewable(client, art_store, audit_store, "ART-ORG-1")
        assert len(art_store.get_pending_reviews(audit_store.get_kdo, org_id="default")) == 1
        assert len(art_store.get_pending_reviews(audit_store.get_kdo, org_id="other_org")) == 0


class TestReviewDetail:
    def test_review_detail_returns_full_data(self, svc):
        client, art_store, audit_store = svc
        vid, dh, _ = _create_reviewable(client, art_store, audit_store, "ART-DET-1")
        detail = art_store.get_review_detail(vid, audit_store.get_kdo)
        assert detail is not None
        assert detail["version"]["version_id"] == vid
        assert detail["kdo"] is not None
        assert detail["publish_state"] == "REQUIRESREVIEW"
        assert isinstance(detail["violations"], list)
        assert isinstance(detail["reviews"], list)

    def test_review_detail_wrong_org_returns_none(self, svc):
        client, art_store, audit_store = svc
        vid, _, _ = _create_reviewable(client, art_store, audit_store, "ART-DET-2")
        detail = art_store.get_review_detail(vid, audit_store.get_kdo, org_id="wrong_org")
        assert detail is None


# ---------------------------------------------------------------------------
# Route tests
# ---------------------------------------------------------------------------

class TestReviewQueueRoutes:
    def test_route_review_queue_returns_pending(self, svc):
        client, art_store, audit_store = svc
        _create_reviewable(client, art_store, audit_store, "ART-ROUTE-1")
        r = client.get("/review-queue")
        assert r.status_code == 200
        body = r.json()
        assert body["count"] == 1
        assert len(body["pending"]) == 1

    def test_route_review_queue_empty(self, svc):
        client, _, _ = svc
        r = client.get("/review-queue")
        assert r.status_code == 200
        assert r.json() == {"pending": [], "count": 0}

    def test_route_review_detail(self, svc):
        client, art_store, audit_store = svc
        vid, _, _ = _create_reviewable(client, art_store, audit_store, "ART-ROUTE-2")
        r = client.get(f"/review-queue/{vid}")
        assert r.status_code == 200
        body = r.json()
        assert body["version"]["version_id"] == vid
        assert body["publish_state"] == "REQUIRESREVIEW"

    def test_route_review_detail_404(self, svc):
        client, _, _ = svc
        r = client.get("/review-queue/nonexistent-id")
        assert r.status_code == 404

    def test_route_approve_promotes_to_live(self, svc):
        client, art_store, audit_store = svc
        vid, _, _ = _create_reviewable(client, art_store, audit_store, "ART-APPROVE-1")
        r = client.post(f"/review-queue/{vid}/approve", json={
            "reviewer_id": "coach-01",
            "reason": "verified safe",
        })
        assert r.status_code == 200
        body = r.json()
        assert body["lifecycle"] == "LIVE"
        assert body["promoted"] is True

    def test_route_approve_creates_review_record(self, svc):
        client, art_store, audit_store = svc
        vid, _, _ = _create_reviewable(client, art_store, audit_store, "ART-APPROVE-2")
        client.post(f"/review-queue/{vid}/approve", json={
            "reviewer_id": "coach-02",
            "reason": "reviewed",
        })
        records = art_store._get_review_records(vid)
        assert len(records) == 1
        assert records[0]["decision"] == "APPROVE"
        assert records[0]["reviewer_id"] == "coach-02"

    def test_route_approve_404(self, svc):
        client, _, _ = svc
        r = client.post("/review-queue/nonexistent-id/approve", json={
            "reviewer_id": "coach", "reason": "test",
        })
        assert r.status_code == 404

    def test_route_approve_missing_fields_400(self, svc):
        client, art_store, audit_store = svc
        vid, _, _ = _create_reviewable(client, art_store, audit_store, "ART-APPROVE-3")
        r = client.post(f"/review-queue/{vid}/approve", json={"reviewer_id": "coach"})
        assert r.status_code == 400
        r = client.post(f"/review-queue/{vid}/approve", json={"reason": "test"})
        assert r.status_code == 400

    def test_route_reject_records_rejection(self, svc):
        client, art_store, audit_store = svc
        vid, _, _ = _create_reviewable(client, art_store, audit_store, "ART-REJECT-1")
        r = client.post(f"/review-queue/{vid}/reject", json={
            "reviewer_id": "coach-01",
            "reason": "does not meet standards",
        })
        assert r.status_code == 200
        body = r.json()
        assert body["decision"] == "REJECT"
        assert body["lifecycle"] == "DRAFT"
        # Version stays DRAFT
        version = art_store.get_version(vid)
        assert version["lifecycle"] == "DRAFT"

    def test_route_reject_404(self, svc):
        client, _, _ = svc
        r = client.post("/review-queue/nonexistent-id/reject", json={
            "reviewer_id": "coach", "reason": "test",
        })
        assert r.status_code == 404

    def test_route_stats_returns_counts(self, svc):
        client, art_store, audit_store = svc
        _create_reviewable(client, art_store, audit_store, "ART-STAT-1")
        _create_reviewable(client, art_store, audit_store, "ART-STAT-2",
                           publish_state="LEGALOVERRIDE")
        r = client.get("/review-queue/stats")
        assert r.status_code == 200
        body = r.json()
        assert body["total_pending"] == 2
        assert body["by_module"]["SESSION"] == 2
        assert "REQUIRESREVIEW" in body["by_publish_state"]
        assert "LEGALOVERRIDE" in body["by_publish_state"]
        assert body["oldest_pending_hours"] >= 0

    def test_route_stats_empty(self, svc):
        client, _, _ = svc
        r = client.get("/review-queue/stats")
        assert r.status_code == 200
        body = r.json()
        assert body["total_pending"] == 0
        assert body["by_module"] == {}
        assert body["by_publish_state"] == {}


# ---------------------------------------------------------------------------
# Version check
# ---------------------------------------------------------------------------

def test_version_bumped():
    app = create_app(":memory:")
    major = int(app.version.split(".")[0])
    assert major >= 23


# ---------------------------------------------------------------------------
# PG test
# ---------------------------------------------------------------------------

@requires_pg
def test_pg_pending_reviews():
    from efl_kernel.kernel.pg_pool import open_pg
    from efl_kernel.kernel.pg_audit_store import PgAuditStore
    from efl_kernel.kernel.pg_artifact_store import PgArtifactStore

    conn = open_pg(PG_URL)
    try:
        audit_store = PgAuditStore(conn)
        art_store = PgArtifactStore(conn)
        result = art_store.get_pending_reviews(audit_store.get_kdo)
        assert isinstance(result, list)
    finally:
        conn.close()
