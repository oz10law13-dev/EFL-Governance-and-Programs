"""Phase 22 — Tenancy (org_id isolation) tests.

Tests cover:
- Store-level org_id isolation (operational, audit, artifact)
- OrgScopedProvider delegation
- APIKeyMiddleware multi-key support
- Route org_id passthrough
- Seed tool --org-id argument
- Version bump
"""
from __future__ import annotations

import json
import os

import pytest
from fastapi.testclient import TestClient

from efl_kernel.kernel.sqlite_operational_store import SqliteOperationalStore
from efl_kernel.kernel.sqlite_audit_store import SqliteAuditStore
from efl_kernel.kernel.sqlite_artifact_store import SqliteArtifactStore
from efl_kernel.kernel.org_scoped_provider import (
    OrgScopedSqliteProvider,
    _OrgScopedStoreProxy,
)
from efl_kernel.service import create_app


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_athlete(athlete_id: str, load: float = 100.0) -> dict:
    return {
        "athlete_id": athlete_id,
        "max_daily_contact_load": load,
        "minimum_rest_interval_hours": 24.0,
        "e4_clearance": 1,
    }


def _make_session(session_id: str, athlete_id: str, date: str = "2026-01-15", load: float = 50.0) -> dict:
    return {
        "session_id": session_id,
        "athlete_id": athlete_id,
        "session_date": date,
        "contact_load": load,
    }


def _make_season(athlete_id: str, season_id: str) -> dict:
    return {
        "athlete_id": athlete_id,
        "season_id": season_id,
        "competition_weeks": 20,
        "gpp_weeks": 12,
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
    }


# ── Store-level isolation ────────────────────────────────────────────────────

class TestOperationalStoreIsolation:
    def test_athlete_isolation_different_ids(self):
        """Different athlete_ids scoped to different orgs are invisible to each other."""
        store = SqliteOperationalStore(":memory:")
        store.upsert_athlete(_make_athlete("A1_ORG_A"), org_id="org_a")
        store.upsert_athlete(_make_athlete("A1_ORG_B", load=200.0), org_id="org_b")

        assert store.get_athlete("A1_ORG_A", org_id="org_a") is not None
        assert store.get_athlete("A1_ORG_A", org_id="org_b") is None
        assert store.get_athlete("A1_ORG_B", org_id="org_b") is not None
        assert store.get_athlete("A1_ORG_B", org_id="org_a") is None

    def test_athlete_invisible_across_orgs(self):
        store = SqliteOperationalStore(":memory:")
        store.upsert_athlete(_make_athlete("ONLY_A"), org_id="org_a")
        assert store.get_athlete("ONLY_A", org_id="org_a") is not None
        assert store.get_athlete("ONLY_A", org_id="org_b") is None

    def test_session_isolation(self):
        store = SqliteOperationalStore(":memory:")
        store.upsert_session(_make_session("S1", "A1"), org_id="org_a")
        rows_a = store.get_sessions_in_window("A1", "2026-01-01", "2026-12-31", org_id="org_a")
        rows_b = store.get_sessions_in_window("A1", "2026-01-01", "2026-12-31", org_id="org_b")
        assert len(rows_a) == 1
        assert len(rows_b) == 0

    def test_season_isolation(self):
        store = SqliteOperationalStore(":memory:")
        store.upsert_season(_make_season("A1", "S2026"), org_id="org_a")
        assert store.get_season("A1", "S2026", org_id="org_a") is not None
        assert store.get_season("A1", "S2026", org_id="org_b") is None

    def test_prior_session_isolation(self):
        store = SqliteOperationalStore(":memory:")
        store.upsert_session(_make_session("S1", "A1", date="2026-01-10"), org_id="org_a")
        assert store.get_prior_session("A1", "2026-02-01", org_id="org_a") is not None
        assert store.get_prior_session("A1", "2026-02-01", org_id="org_b") is None

    def test_readiness_history_isolation(self):
        store = SqliteOperationalStore(":memory:")
        sess = _make_session("S1", "A1")
        sess["readiness_state"] = "GREEN"
        store.upsert_session(sess, org_id="org_a")
        assert len(store.get_readiness_history("A1", "2026-01-01", "2026-12-31", org_id="org_a")) == 1
        assert len(store.get_readiness_history("A1", "2026-01-01", "2026-12-31", org_id="org_b")) == 0

    def test_collapse_count_isolation(self):
        store = SqliteOperationalStore(":memory:")
        sess = _make_session("S1", "A1")
        sess["is_collapsed"] = True
        store.upsert_session(sess, org_id="org_a")
        assert store.get_collapse_count("A1", "2026-01-01", "2026-12-31", org_id="org_a") == 1
        assert store.get_collapse_count("A1", "2026-01-01", "2026-12-31", org_id="org_b") == 0


class TestAuditStoreIsolation:
    def _make_kdo(self, **overrides):
        from efl_kernel.kernel.kdo import KDO
        defaults = dict(
            module_id="SESSION",
            module_version="1.0.0",
            object_id="OBJ1",
            ral_version="1.0.0",
            timestamp_normalized="2026-01-01T00:00:00Z",
            evaluation_context={"athleteID": "A1", "lineageKey": "LK1"},
            window_context=[],
            violations=[],
            resolution={"finalPublishState": "LEGALREADY"},
            reason_summary="",
            audit={"decisionHash": ""},
        )
        defaults.update(overrides)
        return KDO(**defaults)

    def test_kdo_globally_visible(self):
        """get_kdo uses decision_hash only — no org_id filter."""
        store = SqliteAuditStore(":memory:")
        kdo = self._make_kdo()
        dhash = store.commit_kdo(kdo, org_id="org_a")
        assert store.get_kdo(dhash) is not None

    def test_override_history_isolation(self):
        store = SqliteAuditStore(":memory:")
        kdo = self._make_kdo(
            timestamp_normalized="2026-03-07T00:00:00Z",
            violations=[{"code": "V1", "overrideUsed": True, "overrideReasonCode": "R1"}],
            resolution={"finalPublishState": "LEGALOVERRIDE"},
        )
        store.commit_kdo(kdo, org_id="org_a")
        hist_a = store.get_override_history("LK1", "SESSION", org_id="org_a")
        hist_b = store.get_override_history("LK1", "SESSION", org_id="org_b")
        assert hist_a["byViolationCode"].get("V1", 0) > 0
        assert hist_b["byViolationCode"].get("V1", 0) == 0

    def test_metrics_isolation(self):
        store = SqliteAuditStore(":memory:")
        kdo = self._make_kdo(evaluation_context={"athleteID": "A1"})
        store.commit_kdo(kdo, org_id="org_a")
        assert store.get_metrics(org_id="org_a")["kdo_total"] == 1
        assert store.get_metrics(org_id="org_b")["kdo_total"] == 0


class TestArtifactStoreIsolation:
    def test_artifact_version_isolation(self):
        store = SqliteArtifactStore(":memory:")
        v_a = store.commit_artifact_version("ART1", "SESSION", "OBJ1", {"x": 1}, org_id="org_a")
        v_b = store.commit_artifact_version("ART1", "SESSION", "OBJ1", {"x": 2}, org_id="org_b")
        assert len(store.get_versions("ART1", org_id="org_a")) == 1
        assert len(store.get_versions("ART1", org_id="org_b")) == 1

    def test_promote_org_mismatch(self):
        store = SqliteArtifactStore(":memory:")
        v = store.commit_artifact_version("ART1", "SESSION", "OBJ1", {"x": 1}, org_id="org_a")
        with pytest.raises(ValueError, match="org_id mismatch"):
            store.promote_to_live(v["version_id"], lambda h: None, org_id="org_b")

    def test_retire_org_mismatch(self):
        store = SqliteArtifactStore(":memory:")
        v = store.commit_artifact_version("ART1", "SESSION", "OBJ1", {"x": 1}, org_id="org_a")
        with pytest.raises(ValueError, match="org_id mismatch"):
            store.retire(v["version_id"], org_id="org_b")


# ── OrgScopedProvider ───────────────────────────────────────────────────────

class TestOrgScopedProvider:
    def test_proxy_injects_org_id(self):
        class FakeStore:
            def get_athlete(self, athlete_id, org_id="default"):
                return {"athlete_id": athlete_id, "org_id": org_id}
        proxy = _OrgScopedStoreProxy(FakeStore(), "org_x")
        result = proxy.get_athlete("A1")
        assert result["org_id"] == "org_x"

    def test_proxy_does_not_override_explicit_org_id(self):
        class FakeStore:
            def get_athlete(self, athlete_id, org_id="default"):
                return {"org_id": org_id}
        proxy = _OrgScopedStoreProxy(FakeStore(), "org_x")
        result = proxy.get_athlete("A1", org_id="explicit")
        assert result["org_id"] == "explicit"

    def test_org_scoped_sqlite_provider_reads_scoped_data(self):
        op_store = SqliteOperationalStore(":memory:")
        audit_store = SqliteAuditStore(":memory:")
        # Use different athlete_ids since PK is globally unique
        op_store.upsert_athlete(_make_athlete("A1_ORG_A", load=100.0), org_id="org_a")
        op_store.upsert_athlete(_make_athlete("A1_ORG_B", load=200.0), org_id="org_b")

        provider_a = OrgScopedSqliteProvider(op_store, audit_store, "org_a")
        profile_a = provider_a.get_athlete_profile("A1_ORG_A")
        assert profile_a["maxDailyContactLoad"] == 100.0
        # org_b athlete invisible to org_a provider
        profile_b_via_a = provider_a.get_athlete_profile("A1_ORG_B")
        assert profile_b_via_a["maxDailyContactLoad"] == 0.0  # fail-closed sentinel

    def test_org_scoped_provider_missing_athlete_returns_sentinel(self):
        op_store = SqliteOperationalStore(":memory:")
        audit_store = SqliteAuditStore(":memory:")
        provider = OrgScopedSqliteProvider(op_store, audit_store, "org_a")
        profile = provider.get_athlete_profile("NONEXISTENT")
        # Fail-closed sentinel: maxDailyContactLoad = 0.0
        assert profile["maxDailyContactLoad"] == 0.0


# ── Middleware ───────────────────────────────────────────────────────────────

class TestAPIKeyMiddleware:
    def test_no_auth_sets_default_org(self):
        app = create_app(":memory:")
        client = TestClient(app)
        r = client.get("/health")
        assert r.status_code == 200

    def test_single_key_mode(self, monkeypatch):
        monkeypatch.setenv("EFL_API_KEY", "secret123")
        app = create_app(":memory:")
        client = TestClient(app)
        # No key → 401
        r = client.get("/metrics")
        assert r.status_code == 401
        # Correct key → 200
        r = client.get("/metrics", headers={"x-api-key": "secret123"})
        assert r.status_code == 200

    def test_multi_key_mode(self, monkeypatch):
        keys = {"key_a": "org_a", "key_b": "org_b"}
        monkeypatch.setenv("EFL_API_KEYS", json.dumps(keys))
        app = create_app(":memory:")
        client = TestClient(app)
        # Unknown key → 401
        r = client.get("/metrics", headers={"x-api-key": "bad_key"})
        assert r.status_code == 401
        # Valid key → 200
        r = client.get("/metrics", headers={"x-api-key": "key_a"})
        assert r.status_code == 200

    def test_multi_key_overrides_single_key(self, monkeypatch):
        """EFL_API_KEYS takes precedence over EFL_API_KEY."""
        monkeypatch.setenv("EFL_API_KEY", "old_single_key")
        monkeypatch.setenv("EFL_API_KEYS", json.dumps({"new_key": "org_a"}))
        app = create_app(":memory:")
        client = TestClient(app)
        # Old single key rejected (multi-key mode active)
        r = client.get("/metrics", headers={"x-api-key": "old_single_key"})
        assert r.status_code == 401
        # New multi key accepted
        r = client.get("/metrics", headers={"x-api-key": "new_key"})
        assert r.status_code == 200

    def test_health_skips_auth(self, monkeypatch):
        monkeypatch.setenv("EFL_API_KEY", "secret123")
        app = create_app(":memory:")
        client = TestClient(app)
        r = client.get("/health")
        assert r.status_code == 200


# ── Route org_id passthrough ────────────────────────────────────────────────

class TestRouteOrgIdPassthrough:
    def test_athlete_crud_isolated(self):
        app = create_app(":memory:")
        client = TestClient(app)
        # Create athlete (default org)
        r = client.post("/athletes", json=_make_athlete("ATH1"))
        assert r.status_code == 200
        # Get athlete (default org)
        r = client.get("/athletes/ATH1")
        assert r.status_code == 200

    def test_session_crud(self):
        app = create_app(":memory:")
        client = TestClient(app)
        r = client.post("/sessions", json=_make_session("S1", "A1"))
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_season_crud(self):
        app = create_app(":memory:")
        client = TestClient(app)
        r = client.post("/seasons", json=_make_season("A1", "S2026"))
        assert r.status_code == 200
        r = client.get("/seasons/A1/S2026")
        assert r.status_code == 200

    def test_artifact_crud_with_default_org(self):
        app = create_app(":memory:")
        client = TestClient(app)
        r = client.post("/artifacts", json={
            "artifact_id": "ART1",
            "module_id": "SESSION",
            "object_id": "OBJ1",
            "content": {"plan": "test"},
        })
        assert r.status_code == 201
        version_id = r.json()["version_id"]
        r = client.get(f"/artifacts/{version_id}")
        assert r.status_code == 200

    def test_evaluate_session_with_default_org(self):
        app = create_app(":memory:")
        client = TestClient(app)
        r = client.post("/evaluate/session", json={
            "athleteID": "A1",
            "sessionID": "S1",
            "sessionDate": "2026-01-15",
            "contactLoad": 50.0,
        })
        assert r.status_code == 200
        assert "resolution" in r.json()


# ── Version check ───────────────────────────────────────────────────────────

def test_version_bumped():
    app = create_app(":memory:")
    major = int(app.version.split(".")[0])
    assert major >= 22


# ── Seed tool ───────────────────────────────────────────────────────────────

def test_seed_with_org_id(tmp_path):
    from efl_kernel.tools.seed import main as seed_main
    fixture = {
        "athletes": [_make_athlete("SEED-A1")],
        "sessions": [_make_session("SEED-S1", "SEED-A1")],
        "seasons": [_make_season("SEED-A1", "S2026")],
    }
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps(fixture))
    db_path = str(tmp_path / "seed.db")
    seed_main(["--fixture", str(fixture_path), "--db", db_path, "--org-id", "org_x"])
    store = SqliteOperationalStore(db_path)
    assert store.get_athlete("SEED-A1", org_id="org_x") is not None
    assert store.get_athlete("SEED-A1", org_id="default") is None


def test_seed_default_org(tmp_path):
    from efl_kernel.tools.seed import main as seed_main
    fixture = {
        "athletes": [_make_athlete("SEED-A2")],
        "sessions": [],
        "seasons": [],
    }
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps(fixture))
    db_path = str(tmp_path / "seed.db")
    seed_main(["--fixture", str(fixture_path), "--db", db_path])
    store = SqliteOperationalStore(db_path)
    assert store.get_athlete("SEED-A2", org_id="default") is not None
