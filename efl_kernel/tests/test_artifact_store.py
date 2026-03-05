from __future__ import annotations

import pytest

from efl_kernel.kernel.artifact_store import ArtifactStore


@pytest.fixture()
def store():
    return ArtifactStore(db_path=":memory:")


# ------------------------------------------------------------------ #
# Content hash and version creation                                   #
# ------------------------------------------------------------------ #

def test_commit_artifact_version_creates_draft(store):
    content = {"session": {"contactLoad": 100}}
    row = store.commit_artifact_version(
        artifact_id="ART-01",
        module_id="SESSION",
        object_id="OBJ-01",
        content=content,
    )
    assert row["lifecycle"] == "DRAFT"
    assert row["content_hash"] is not None
    assert len(row["content_hash"]) == 64  # sha256 hex
    assert row["version_id"] is not None


def test_content_hash_is_deterministic(store):
    # INV-1: same content → same hash, but two distinct immutable version rows
    content = {"session": {"contactLoad": 100}}
    row_a = store.commit_artifact_version("ART-02", "SESSION", "OBJ", content)
    row_b = store.commit_artifact_version("ART-02", "SESSION", "OBJ", content)
    assert row_a["content_hash"] == row_b["content_hash"]
    assert row_a["version_id"] != row_b["version_id"]


def test_different_content_produces_different_hash(store):
    row_a = store.commit_artifact_version(
        "ART-03", "SESSION", "OBJ", {"contactLoad": 100}
    )
    row_b = store.commit_artifact_version(
        "ART-03", "SESSION", "OBJ", {"contactLoad": 200}
    )
    assert row_a["content_hash"] != row_b["content_hash"]


# ------------------------------------------------------------------ #
# INV-3 / INV-4 — promotion eligibility                              #
# ------------------------------------------------------------------ #

def test_promote_legalready_succeeds_without_review(store):
    # INV-3: LEGALREADY → LIVE eligible without review record
    content = {"x": 1}
    version = store.commit_artifact_version("ART-10", "SESSION", "OBJ", content)
    version_id = version["version_id"]
    content_hash = version["content_hash"]

    store.link_kdo(
        version_id=version_id,
        decision_hash="deadbeef" * 8,
        content_hash_at_eval=content_hash,
    )

    def mock_get_kdo(decision_hash):
        return {"resolution": {"finalPublishState": "LEGALREADY"}}

    result = store.promote_to_live(version_id, mock_get_kdo)
    assert result["lifecycle"] == "LIVE"


def test_promote_requiresreview_without_review_raises(store):
    # INV-4: REQUIRESREVIEW without review record → rejected
    content = {"x": 2}
    version = store.commit_artifact_version("ART-11", "SESSION", "OBJ", content)
    version_id = version["version_id"]

    store.link_kdo(
        version_id=version_id,
        decision_hash="deadbeef" * 8,
        content_hash_at_eval=version["content_hash"],
    )

    def mock_get_kdo(_):
        return {"resolution": {"finalPublishState": "REQUIRESREVIEW"}}

    with pytest.raises(ValueError, match="review required"):
        store.promote_to_live(version_id, mock_get_kdo)


def test_promote_requiresreview_with_approve_succeeds(store):
    # INV-4: REQUIRESREVIEW + APPROVE → LIVE
    content = {"x": 3}
    version = store.commit_artifact_version("ART-12", "SESSION", "OBJ", content)
    version_id = version["version_id"]
    dh = "cafebabe" * 8

    store.link_kdo(version_id, dh, version["content_hash"])
    store.add_review_record(
        artifact_version_id=version_id,
        decision_hash=dh,
        reviewer_id="coach-01",
        reason="manually verified",
        decision="APPROVE",
    )

    def mock_get_kdo(_):
        return {"resolution": {"finalPublishState": "REQUIRESREVIEW"}}

    result = store.promote_to_live(version_id, mock_get_kdo)
    assert result["lifecycle"] == "LIVE"


def test_promote_requiresreview_with_reject_raises(store):
    # INV-4: REQUIRESREVIEW + REJECT → cannot promote
    content = {"x": 4}
    version = store.commit_artifact_version("ART-13", "SESSION", "OBJ", content)
    version_id = version["version_id"]
    dh = "aabbccdd" * 8

    store.link_kdo(version_id, dh, version["content_hash"])
    store.add_review_record(
        artifact_version_id=version_id,
        decision_hash=dh,
        reviewer_id="coach-01",
        reason="does not meet standards",
        decision="REJECT",
    )

    def mock_get_kdo(_):
        return {"resolution": {"finalPublishState": "REQUIRESREVIEW"}}

    with pytest.raises(ValueError, match="APPROVE"):
        store.promote_to_live(version_id, mock_get_kdo)


def test_promote_legaloverride_with_approve_succeeds(store):
    # INV-4: LEGALOVERRIDE follows same gated path as REQUIRESREVIEW
    content = {"x": 5}
    version = store.commit_artifact_version("ART-14", "SESSION", "OBJ", content)
    version_id = version["version_id"]
    dh = "11223344" * 8

    store.link_kdo(version_id, dh, version["content_hash"])
    store.add_review_record(
        artifact_version_id=version_id,
        decision_hash=dh,
        reviewer_id="coach-02",
        reason="override reviewed",
        decision="APPROVE",
    )

    def mock_get_kdo(_):
        return {"resolution": {"finalPublishState": "LEGALOVERRIDE"}}

    result = store.promote_to_live(version_id, mock_get_kdo)
    assert result["lifecycle"] == "LIVE"


def test_promote_illegalquarantined_raises(store):
    # INV-3: ILLEGALQUARANTINED → never LIVE
    content = {"x": 6}
    version = store.commit_artifact_version("ART-15", "SESSION", "OBJ", content)
    version_id = version["version_id"]

    store.link_kdo(version_id, "ff" * 32, version["content_hash"])

    def mock_get_kdo(_):
        return {"resolution": {"finalPublishState": "ILLEGALQUARANTINED"}}

    with pytest.raises(ValueError, match="not eligible"):
        store.promote_to_live(version_id, mock_get_kdo)


# ------------------------------------------------------------------ #
# INV-2 — hash mismatch                                              #
# ------------------------------------------------------------------ #

def test_content_hash_mismatch_rejects_promotion(store):
    # INV-2: content_hash_at_eval != version.content_hash → rejected
    content = {"x": 7}
    version = store.commit_artifact_version("ART-16", "SESSION", "OBJ", content)
    version_id = version["version_id"]

    store.link_kdo(
        version_id=version_id,
        decision_hash="deadbeef" * 8,
        content_hash_at_eval="0000" * 16,  # intentionally wrong
    )

    def mock_get_kdo(_):
        return {"resolution": {"finalPublishState": "LEGALREADY"}}

    with pytest.raises(ValueError, match="content hash mismatch"):
        store.promote_to_live(version_id, mock_get_kdo)


# ------------------------------------------------------------------ #
# Idempotency and lifecycle transitions                               #
# ------------------------------------------------------------------ #

def test_promote_to_live_is_idempotent(store):
    content = {"x": 8}
    version = store.commit_artifact_version("ART-17", "SESSION", "OBJ", content)
    version_id = version["version_id"]

    store.link_kdo(version_id, "deadbeef" * 8, version["content_hash"])

    def mock_get_kdo(_):
        return {"resolution": {"finalPublishState": "LEGALREADY"}}

    store.promote_to_live(version_id, mock_get_kdo)
    result = store.promote_to_live(version_id, mock_get_kdo)  # second call
    assert result["lifecycle"] == "LIVE"


def test_retire_from_live(store):
    version = store.commit_artifact_version("ART-18", "SESSION", "OBJ", {"x": 9})
    version_id = version["version_id"]

    store.link_kdo(version_id, "deadbeef" * 8, version["content_hash"])

    def mock_get_kdo(_):
        return {"resolution": {"finalPublishState": "LEGALREADY"}}

    store.promote_to_live(version_id, mock_get_kdo)

    result = store.retire(version_id)
    assert result["lifecycle"] == "RETIRED"


def test_retire_already_retired_raises(store):
    version = store.commit_artifact_version("ART-19", "SESSION", "OBJ", {"x": 10})
    store.retire(version["version_id"])

    with pytest.raises(ValueError):
        store.retire(version["version_id"])


def test_no_kdo_link_rejects_promotion(store):
    version = store.commit_artifact_version("ART-20", "SESSION", "OBJ", {"x": 11})

    def mock_get_kdo(_):
        return {"resolution": {"finalPublishState": "LEGALREADY"}}

    with pytest.raises(ValueError, match="no KDO linked"):
        store.promote_to_live(version["version_id"], mock_get_kdo)


# ------------------------------------------------------------------ #
# Query methods                                                       #
# ------------------------------------------------------------------ #

def test_get_live_versions_returns_only_live(store):
    art_id = "ART-21"
    v1 = store.commit_artifact_version(art_id, "SESSION", "OBJ", {"v": 1})
    v2 = store.commit_artifact_version(art_id, "SESSION", "OBJ", {"v": 2})

    store.link_kdo(v1["version_id"], "aa" * 32, v1["content_hash"])
    store.link_kdo(v2["version_id"], "bb" * 32, v2["content_hash"])

    def mock_kdo(_):
        return {"resolution": {"finalPublishState": "LEGALREADY"}}

    store.promote_to_live(v1["version_id"], mock_kdo)
    # v2 stays DRAFT

    live = store.get_live_versions(art_id)
    assert len(live) == 1
    assert live[0]["version_id"] == v1["version_id"]


# ------------------------------------------------------------------ #
# Input validation                                                    #
# ------------------------------------------------------------------ #

def test_add_review_record_rejects_invalid_decision(store):
    with pytest.raises(ValueError):
        store.add_review_record(
            artifact_version_id="any-id",
            decision_hash="ff" * 32,
            reviewer_id="coach",
            reason="test",
            decision="MAYBE",
        )
