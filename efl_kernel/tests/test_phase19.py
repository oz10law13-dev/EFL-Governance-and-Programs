"""Phase 19 — PostgreSQL Migration tests.

6 SQLite backward-compat tests always run.
18 PostgreSQL tests are skipped when EFL_TEST_DATABASE_URL is not set.
"""
from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient

from efl_kernel.kernel.audit_store import AuditStore
from efl_kernel.kernel.artifact_store import ArtifactStore
from efl_kernel.kernel.operational_store import OperationalStore
from efl_kernel.kernel.sqlite_audit_store import SqliteAuditStore
from efl_kernel.kernel.sqlite_artifact_store import SqliteArtifactStore
from efl_kernel.kernel.sqlite_operational_store import SqliteOperationalStore
from efl_kernel.service import create_app

_PG_URL = os.environ.get("EFL_TEST_DATABASE_URL")
requires_pg = pytest.mark.skipif(
    not _PG_URL,
    reason="EFL_TEST_DATABASE_URL not set — PostgreSQL tests skipped",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uid(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:8]}"


def _minimal_session_payload(athlete_id: str, session_id: str) -> dict:
    """Minimal SESSION eval payload that passes all gates for a permissive athlete."""
    return {
        "moduleVersion": "1.0.0",
        "moduleViolationRegistryVersion": "1.0.0",
        "registryHash": "ignored-in-test",
        "objectID": session_id,
        "evaluationContext": {
            "athleteID": athlete_id,
            "sessionID": session_id,
            "sessionDate": "2026-01-15",
            "contactLoad": 50.0,
        },
        "windowContext": [
            {
                "windowType": "ROLLING7DAYS",
                "anchorDate": "2026-01-15",
                "startDate": "2026-01-08",
                "endDate": "2026-01-15",
                "timezone": "UTC",
            }
        ],
        "session": {
            "exercises": [],
            "sessionType": "STRENGTH",
        },
    }


# ---------------------------------------------------------------------------
# SQLite backward-compat (always run)
# ---------------------------------------------------------------------------

def test_sqlite_shim_audit_store():
    """AuditStore shim re-exports SqliteAuditStore under the AuditStore name."""
    assert AuditStore is SqliteAuditStore


def test_sqlite_shim_operational_store():
    """OperationalStore shim re-exports SqliteOperationalStore under the OperationalStore name."""
    assert OperationalStore is SqliteOperationalStore


def test_sqlite_shim_artifact_store():
    """ArtifactStore shim re-exports SqliteArtifactStore under the ArtifactStore name."""
    assert ArtifactStore is SqliteArtifactStore


def test_create_app_no_pg_url_uses_sqlite(tmp_path):
    """create_app() with no PG URL → audit_store is SqliteAuditStore."""
    app = create_app(
        db_path=str(tmp_path / "audit.db"),
        op_db_path=str(tmp_path / "op.db"),
    )
    assert isinstance(app.state.audit_store, SqliteAuditStore)
    assert isinstance(app.state.op_store, SqliteOperationalStore)
    assert isinstance(app.state.artifact_store, SqliteArtifactStore)


def test_create_app_version_bumped():
    """Service version is at least 19.0.0 (bumped in subsequent phases)."""
    app = create_app()
    major = int(app.version.split(".")[0])
    assert major >= 19


def test_sqlite_evaluate_session_still_works(tmp_path):
    """SQLite-backed /evaluate/session round-trip still works after Phase 19 refactor."""
    from efl_kernel.kernel.ral import RAL_SPEC
    reg = RAL_SPEC["moduleRegistration"]["SESSION"]
    app = create_app(
        db_path=str(tmp_path / "audit.db"),
        op_db_path=str(tmp_path / "op.db"),
    )
    app.state.op_store.upsert_athlete({
        "athlete_id": "ATH-P19-SQLITE",
        "max_daily_contact_load": 999.0,
        "minimum_rest_interval_hours": 0.0,
        "e4_clearance": 1,
    })
    client = TestClient(app)
    payload = {
        "moduleVersion": reg["moduleVersion"],
        "moduleViolationRegistryVersion": reg["moduleViolationRegistryVersion"],
        "registryHash": reg["registryHash"],
        "objectID": "OBJ-P19-S1",
        "evaluationContext": {
            "athleteID": "ATH-P19-SQLITE",
            "sessionID": "SES-P19-S1",
            "sessionDate": "2026-01-15",
            "contactLoad": 50.0,
        },
        "windowContext": [
            {
                "windowType": "ROLLING7DAYS",
                "anchorDate": "2026-01-15",
                "startDate": "2026-01-08",
                "endDate": "2026-01-15",
                "timezone": "UTC",
            }
        ],
        "session": {"exercises": [], "sessionType": "STRENGTH"},
    }
    r = client.post("/evaluate/session", json=payload)
    assert r.status_code == 200
    assert "resolution" in r.json()


# ---------------------------------------------------------------------------
# PG fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def pg_audit_store():
    """PgAuditStore backed by EFL_TEST_DATABASE_URL. Truncates tables after test."""
    from efl_kernel.kernel.pg_pool import open_pg
    from efl_kernel.kernel.pg_audit_store import PgAuditStore
    conn = open_pg(_PG_URL)
    store = PgAuditStore(conn)
    yield store
    conn.execute("TRUNCATE kdo_log, override_ledger")
    conn.commit()
    conn.close()


@pytest.fixture(scope="function")
def pg_op_store():
    """PgOperationalStore backed by EFL_TEST_DATABASE_URL. Truncates tables after test."""
    from efl_kernel.kernel.pg_pool import open_pg
    from efl_kernel.kernel.pg_operational_store import PgOperationalStore
    conn = open_pg(_PG_URL)
    store = PgOperationalStore(conn)
    yield store
    conn.execute("TRUNCATE op_athletes, op_sessions, op_seasons")
    conn.commit()
    conn.close()


@pytest.fixture(scope="function")
def pg_artifact_store():
    """PgArtifactStore backed by EFL_TEST_DATABASE_URL. Truncates tables after test."""
    from efl_kernel.kernel.pg_pool import open_pg
    from efl_kernel.kernel.pg_artifact_store import PgArtifactStore
    conn = open_pg(_PG_URL)
    store = PgArtifactStore(conn)
    yield store
    conn.execute("TRUNCATE artifact_versions, artifact_kdo_links, review_records")
    conn.commit()
    conn.close()


@pytest.fixture(scope="function")
def pg_svc():
    """Full service backed by PG. Truncates all tables after test."""
    from efl_kernel.kernel.pg_pool import open_pg
    from efl_kernel.kernel.pg_audit_store import PgAuditStore
    from efl_kernel.kernel.pg_operational_store import PgOperationalStore
    from efl_kernel.kernel.pg_artifact_store import PgArtifactStore

    app = create_app(database_url=_PG_URL)
    client = TestClient(app)

    yield client, app

    conn = open_pg(_PG_URL)
    for table in ("kdo_log", "override_ledger", "op_athletes", "op_sessions",
                  "op_seasons", "artifact_versions", "artifact_kdo_links", "review_records"):
        try:
            conn.execute(f"TRUNCATE {table}")
        except Exception:
            conn.rollback()
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# PgAuditStore tests
# ---------------------------------------------------------------------------

@requires_pg
def test_pg_audit_store_commit_kdo(pg_audit_store):
    """commit_kdo returns a decision_hash and persists the record."""
    from efl_kernel.kernel.kdo import KDO
    kdo = KDO(
        module_id="SESSION",
        module_version="1.0.0",
        object_id="OBJ-P19-001",
        ral_version="1.0.0",
        evaluation_context={"athleteID": "A1", "sessionID": "S1"},
        window_context=[{
            "windowType": "ROLLING7DAYS", "anchorDate": "2026-01-15",
            "startDate": "2026-01-08", "endDate": "2026-01-15", "timezone": "UTC",
        }],
        violations=[],
        resolution={"finalPublishState": "LEGALREADY", "finalEffectiveLabel": "PASS",
                    "finalSeverity": "PASS"},
        reason_summary="",
        timestamp_normalized="2026-01-15T00:00:00+00:00",
        audit={"decisionHash": ""},
    )
    decision_hash = pg_audit_store.commit_kdo(kdo)
    assert isinstance(decision_hash, str)
    assert len(decision_hash) > 0


@requires_pg
def test_pg_audit_store_get_kdo_returns_dict(pg_audit_store):
    """get_kdo returns a Python dict (JSONB decoded)."""
    from efl_kernel.kernel.kdo import KDO
    kdo = KDO(
        module_id="SESSION",
        module_version="1.0.0",
        object_id="OBJ-P19-002",
        ral_version="1.0.0",
        evaluation_context={"athleteID": "A2", "sessionID": "S2"},
        window_context=[{
            "windowType": "ROLLING7DAYS", "anchorDate": "2026-01-15",
            "startDate": "2026-01-08", "endDate": "2026-01-15", "timezone": "UTC",
        }],
        violations=[],
        resolution={"finalPublishState": "LEGALREADY", "finalEffectiveLabel": "PASS",
                    "finalSeverity": "PASS"},
        reason_summary="",
        timestamp_normalized="2026-01-15T00:00:00+00:00",
        audit={"decisionHash": ""},
    )
    decision_hash = pg_audit_store.commit_kdo(kdo)
    result = pg_audit_store.get_kdo(decision_hash)
    assert isinstance(result, dict)
    assert result["module_id"] == "SESSION"
    assert result["resolution"]["finalPublishState"] == "LEGALREADY"


@requires_pg
def test_pg_audit_store_commit_kdo_idempotent(pg_audit_store):
    """Duplicate commit_kdo call is silently ignored — returns same hash."""
    from efl_kernel.kernel.kdo import KDO
    kdo = KDO(
        module_id="SESSION",
        module_version="1.0.0",
        object_id="OBJ-P19-003",
        ral_version="1.0.0",
        evaluation_context={"athleteID": "A3", "sessionID": "S3"},
        window_context=[{
            "windowType": "ROLLING7DAYS", "anchorDate": "2026-01-15",
            "startDate": "2026-01-08", "endDate": "2026-01-15", "timezone": "UTC",
        }],
        violations=[],
        resolution={"finalPublishState": "LEGALREADY", "finalEffectiveLabel": "PASS",
                    "finalSeverity": "PASS"},
        reason_summary="",
        timestamp_normalized="2026-01-15T00:00:00+00:00",
        audit={"decisionHash": ""},
    )
    h1 = pg_audit_store.commit_kdo(kdo)
    h2 = pg_audit_store.commit_kdo(kdo)
    assert h1 == h2


@requires_pg
def test_pg_audit_store_get_metrics(pg_audit_store):
    """get_metrics returns kdo_total, by_module, by_publish_state."""
    from efl_kernel.kernel.kdo import KDO
    for i in range(3):
        kdo = KDO(
            module_id="SESSION",
            module_version="1.0.0",
            object_id=f"OBJ-P19-MET-{i}",
            ral_version="1.0.0",
            evaluation_context={"athleteID": f"AM{i}", "sessionID": f"SM{i}"},
            window_context=[{
                "windowType": "ROLLING7DAYS", "anchorDate": "2026-01-15",
                "startDate": "2026-01-08", "endDate": "2026-01-15", "timezone": "UTC",
            }],
            violations=[],
            resolution={"finalPublishState": "LEGALREADY", "finalEffectiveLabel": "PASS",
                        "finalSeverity": "PASS"},
            reason_summary="",
            timestamp_normalized=f"2026-01-1{i+5}T00:00:00+00:00",
            audit={"decisionHash": ""},
        )
        pg_audit_store.commit_kdo(kdo)
    metrics = pg_audit_store.get_metrics()
    assert metrics["kdo_total"] >= 3
    assert "SESSION" in metrics["by_module"]
    assert "LEGALREADY" in metrics["by_publish_state"]


# ---------------------------------------------------------------------------
# PgOperationalStore tests
# ---------------------------------------------------------------------------

@requires_pg
def test_pg_op_store_upsert_and_get_athlete(pg_op_store):
    """upsert_athlete stores data; get_athlete returns it."""
    aid = _uid("ATH-P19-")
    pg_op_store.upsert_athlete({
        "athlete_id": aid,
        "max_daily_contact_load": 150.0,
        "minimum_rest_interval_hours": 12.0,
        "e4_clearance": 1,
    })
    row = pg_op_store.get_athlete(aid)
    assert row is not None
    assert row["athlete_id"] == aid
    assert row["max_daily_contact_load"] == 150.0
    assert bool(row["e4_clearance"]) is True


@requires_pg
def test_pg_op_store_upsert_session_and_window(pg_op_store):
    """upsert_session stores data; get_sessions_in_window returns it."""
    aid = _uid("ATH-P19-")
    sid = _uid("SES-P19-")
    pg_op_store.upsert_athlete({
        "athlete_id": aid,
        "max_daily_contact_load": 999.0,
        "minimum_rest_interval_hours": 0.0,
        "e4_clearance": 0,
    })
    pg_op_store.upsert_session({
        "session_id": sid,
        "athlete_id": aid,
        "session_date": "2026-01-10",
        "contact_load": 80.0,
    })
    rows = pg_op_store.get_sessions_in_window(
        aid, "2026-01-01", "2026-01-31T23:59:59+00:00"
    )
    assert any(r["session_id"] == sid for r in rows)


@requires_pg
def test_pg_op_store_upsert_season(pg_op_store):
    """upsert_season stores data; get_season returns it."""
    aid = _uid("ATH-P19-")
    pg_op_store.upsert_athlete({
        "athlete_id": aid,
        "max_daily_contact_load": 999.0,
        "minimum_rest_interval_hours": 0.0,
        "e4_clearance": 0,
    })
    pg_op_store.upsert_season({
        "athlete_id": aid,
        "season_id": "S2026",
        "competition_weeks": 8,
        "gpp_weeks": 4,
        "start_date": "2026-01-01",
        "end_date": "2026-06-30",
    })
    row = pg_op_store.get_season(aid, "S2026")
    assert row is not None
    assert row["competition_weeks"] == 8
    assert row["gpp_weeks"] == 4


@requires_pg
def test_pg_op_store_get_athlete_missing_returns_none(pg_op_store):
    """get_athlete returns None for an unknown athlete_id."""
    result = pg_op_store.get_athlete("DOES-NOT-EXIST-P19")
    assert result is None


# ---------------------------------------------------------------------------
# PgArtifactStore tests
# ---------------------------------------------------------------------------

@requires_pg
def test_pg_artifact_store_commit_returns_draft(pg_artifact_store):
    """commit_artifact_version returns a DRAFT version dict."""
    aid = _uid("ART-P19-")
    result = pg_artifact_store.commit_artifact_version(
        artifact_id=aid,
        module_id="SESSION",
        object_id="OBJ-P19",
        content={"key": "value"},
    )
    assert result["lifecycle"] == "DRAFT"
    assert result["artifact_id"] == aid
    assert "version_id" in result
    assert "content_hash" in result


@requires_pg
def test_pg_artifact_store_promote_to_live(pg_artifact_store, pg_audit_store):
    """promote_to_live works with a LEGALREADY KDO."""
    from efl_kernel.kernel.kdo import KDO
    # Commit KDO
    kdo = KDO(
        module_id="SESSION",
        module_version="1.0.0",
        object_id="OBJ-P19-PROMO",
        ral_version="1.0.0",
        evaluation_context={"athleteID": "APROMO", "sessionID": "SPROMO"},
        window_context=[{
            "windowType": "ROLLING7DAYS", "anchorDate": "2026-01-15",
            "startDate": "2026-01-08", "endDate": "2026-01-15", "timezone": "UTC",
        }],
        violations=[],
        resolution={"finalPublishState": "LEGALREADY", "finalEffectiveLabel": "PASS",
                    "finalSeverity": "PASS"},
        reason_summary="",
        timestamp_normalized="2026-01-15T00:00:00+00:00",
        audit={"decisionHash": ""},
    )
    decision_hash = pg_audit_store.commit_kdo(kdo)

    # Commit artifact
    content = {"key": "promo-test"}
    version = pg_artifact_store.commit_artifact_version(
        artifact_id=_uid("ART-P19-"),
        module_id="SESSION",
        object_id="OBJ-P19-PROMO",
        content=content,
    )
    version_id = version["version_id"]
    content_hash = version["content_hash"]

    # Link KDO
    pg_artifact_store.link_kdo(version_id, decision_hash, content_hash)

    # Promote
    promoted = pg_artifact_store.promote_to_live(version_id, pg_audit_store.get_kdo)
    assert promoted["lifecycle"] == "LIVE"


@requires_pg
def test_pg_artifact_store_retire(pg_artifact_store):
    """retire transitions lifecycle to RETIRED."""
    version = pg_artifact_store.commit_artifact_version(
        artifact_id=_uid("ART-P19-"),
        module_id="SESSION",
        object_id="OBJ-P19-RET",
        content={"retire": True},
    )
    retired = pg_artifact_store.retire(version["version_id"])
    assert retired["lifecycle"] == "RETIRED"


@requires_pg
def test_pg_artifact_store_link_kdo(pg_artifact_store):
    """link_kdo creates a link record with correct fields."""
    version = pg_artifact_store.commit_artifact_version(
        artifact_id=_uid("ART-P19-"),
        module_id="SESSION",
        object_id="OBJ-P19-LINK",
        content={"link": True},
    )
    link = pg_artifact_store.link_kdo(
        version["version_id"],
        decision_hash="fake-hash-p19",
        content_hash_at_eval=version["content_hash"],
    )
    assert link["version_id"] == version["version_id"]
    assert link["decision_hash"] == "fake-hash-p19"


# ---------------------------------------------------------------------------
# Service-level PG tests
# ---------------------------------------------------------------------------

@requires_pg
def test_create_app_pg_url_uses_pg_stores():
    """create_app(database_url=...) → stores are PG-backed."""
    from efl_kernel.kernel.pg_audit_store import PgAuditStore
    from efl_kernel.kernel.pg_operational_store import PgOperationalStore
    from efl_kernel.kernel.pg_artifact_store import PgArtifactStore
    app = create_app(database_url=_PG_URL)
    assert isinstance(app.state.audit_store, PgAuditStore)
    assert isinstance(app.state.op_store, PgOperationalStore)
    assert isinstance(app.state.artifact_store, PgArtifactStore)


@requires_pg
def test_pg_evaluate_session(pg_svc):
    """POST /evaluate/session works with PG-backed service."""
    from efl_kernel.kernel.ral import RAL_SPEC
    reg = RAL_SPEC["moduleRegistration"]["SESSION"]
    client, app = pg_svc
    app.state.op_store.upsert_athlete({
        "athlete_id": "ATH-P19-PG1",
        "max_daily_contact_load": 999.0,
        "minimum_rest_interval_hours": 0.0,
        "e4_clearance": 1,
    })
    payload = {
        "moduleVersion": reg["moduleVersion"],
        "moduleViolationRegistryVersion": reg["moduleViolationRegistryVersion"],
        "registryHash": reg["registryHash"],
        "objectID": "OBJ-P19-PG1",
        "evaluationContext": {
            "athleteID": "ATH-P19-PG1",
            "sessionID": "SES-P19-PG1",
            "sessionDate": "2026-01-20",
            "contactLoad": 60.0,
        },
        "windowContext": [
            {
                "windowType": "ROLLING7DAYS",
                "anchorDate": "2026-01-20",
                "startDate": "2026-01-13",
                "endDate": "2026-01-20",
                "timezone": "UTC",
            }
        ],
        "session": {"exercises": [], "sessionType": "STRENGTH"},
    }
    r = client.post("/evaluate/session", json=payload)
    assert r.status_code == 200
    assert "resolution" in r.json()


@requires_pg
def test_pg_athlete_create_and_get(pg_svc):
    """POST /athletes + GET /athletes/{id} round-trip via PG."""
    client, _ = pg_svc
    aid = _uid("ATH-P19-API-")
    r = client.post("/athletes", json={
        "athlete_id": aid,
        "max_daily_contact_load": 200.0,
        "minimum_rest_interval_hours": 8.0,
        "e4_clearance": 1,
    })
    assert r.status_code == 200
    r2 = client.get(f"/athletes/{aid}")
    assert r2.status_code == 200
    assert r2.json()["athlete_id"] == aid


@requires_pg
def test_pg_pipeline_physique(pg_svc):
    """POST /pipeline/physique end-to-end via PG."""
    client, app = pg_svc
    aid = _uid("ATH-P19-PP-")
    app.state.op_store.upsert_athlete({
        "athlete_id": aid,
        "max_daily_contact_load": 999.0,
        "minimum_rest_interval_hours": 0.0,
        "e4_clearance": 1,
    })
    r = client.post("/pipeline/physique", json={
        "constraints": {
            "athlete_id": aid,
            "session_id": _uid("SES-P19-"),
            "day_role": "A",
            "target_exercise_count": 2,
        },
        "artifact_id": _uid("ART-P19-"),
        "object_id": _uid("OBJ-P19-"),
    })
    assert r.status_code == 200
    body = r.json()
    assert "proposal" in body
    assert "lifecycle" in body


@requires_pg
def test_pg_dependency_provider_fail_closed_sentinel():
    """PgDependencyProvider returns fail-closed sentinel for unknown athlete."""
    from efl_kernel.kernel.pg_pool import open_pg
    from efl_kernel.kernel.pg_audit_store import PgAuditStore
    from efl_kernel.kernel.pg_operational_store import PgOperationalStore
    from efl_kernel.kernel.pg_dependency_provider import PgDependencyProvider

    audit_conn = open_pg(_PG_URL)
    op_conn = open_pg(_PG_URL)
    try:
        audit_store = PgAuditStore(audit_conn)
        op_store = PgOperationalStore(op_conn)
        provider = PgDependencyProvider(op_store, audit_store)
        profile = provider.get_athlete_profile("DOES-NOT-EXIST-P19-SENTINEL")
        assert profile["maxDailyContactLoad"] == 0.0
        assert profile["minimumRestIntervalHours"] == 24.0
        assert profile["e4_clearance"] is False
    finally:
        audit_conn.close()
        op_conn.close()


@requires_pg
def test_pg_audit_store_override_history(pg_audit_store):
    """get_override_history returns empty counts when no overrides exist."""
    result = pg_audit_store.get_override_history(
        lineage_key="LK-P19-NONE",
        module_id="SESSION",
        window_days=28,
    )
    assert result["byReasonCode"] == {}
    assert result["byViolationCode"] == {}
