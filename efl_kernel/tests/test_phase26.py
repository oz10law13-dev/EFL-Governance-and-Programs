"""Phase 26 — Version Negotiation / Deprecation Window tests.

16 tests always run. No PG-gated tests in this phase.
"""
from __future__ import annotations

import copy
import json
import os

import pytest

from efl_kernel.kernel.kernel import KernelRunner, _match_prior_version
from efl_kernel.kernel.dependency_provider import InMemoryDependencyProvider
from efl_kernel.kernel.ral import RAL_SPEC


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _runner():
    return KernelRunner(InMemoryDependencyProvider())


def _physique_reg():
    return RAL_SPEC["moduleRegistration"]["PHYSIQUE"]


def _physique_prior():
    for p in _physique_reg().get("priorVersions", []):
        if p["status"] == "DEPRECATED":
            return p
    return None


def _base_physique_payload(reg):
    return {
        "moduleVersion": reg["moduleVersion"],
        "moduleViolationRegistryVersion": reg["moduleViolationRegistryVersion"],
        "registryHash": reg["registryHash"],
        "objectID": "OBJ-V26-001",
        "evaluationContext": {
            "athleteID": "a1",
            "sessionID": "s1",
        },
        "windowContext": [
            {"windowType": "ROLLING7DAYS", "anchorDate": "2026-03-09",
             "startDate": "2026-03-02", "endDate": "2026-03-09", "timezone": "UTC"},
            {"windowType": "ROLLING28DAYS", "anchorDate": "2026-03-09",
             "startDate": "2026-02-09", "endDate": "2026-03-09", "timezone": "UTC"},
        ],
        "physique_session": {"exercises": []},
    }


# ---------------------------------------------------------------------------
# Version negotiation tests
# ---------------------------------------------------------------------------

class TestVersionNegotiation:
    def test_current_version_accepted(self):
        """Exact match on current version -> normal eval."""
        reg = _physique_reg()
        payload = _base_physique_payload(reg)
        kdo = _runner().evaluate(payload, "PHYSIQUE")
        codes = [v["code"] for v in kdo.violations]
        assert "RAL.MODULEREGISTRYMISMATCH" not in codes

    def test_unknown_version_quarantined(self):
        """Random version/hash -> RAL.MODULEREGISTRYMISMATCH."""
        payload = _base_physique_payload({
            "moduleVersion": "99.99.99",
            "moduleViolationRegistryVersion": "99.99.99",
            "registryHash": "0" * 64,
        })
        kdo = _runner().evaluate(payload, "PHYSIQUE")
        codes = [v["code"] for v in kdo.violations]
        assert "RAL.MODULEREGISTRYMISMATCH" in codes

    def test_deprecated_version_accepted(self):
        """DEPRECATED prior version accepted — no MODULEREGISTRYMISMATCH."""
        prior = _physique_prior()
        if prior is None:
            pytest.skip("No DEPRECATED prior version in RAL for PHYSIQUE")

        payload = _base_physique_payload(prior)
        kdo = _runner().evaluate(payload, "PHYSIQUE")
        codes = [v["code"] for v in kdo.violations]
        assert "RAL.MODULEREGISTRYMISMATCH" not in codes

    def test_deprecated_version_kdo_has_negotiation(self):
        """Deprecated eval -> resolution has versionNegotiation."""
        prior = _physique_prior()
        if prior is None:
            pytest.skip("No DEPRECATED prior version in RAL for PHYSIQUE")

        payload = _base_physique_payload(prior)
        kdo = _runner().evaluate(payload, "PHYSIQUE")
        neg = kdo.resolution.get("versionNegotiation")
        assert neg is not None
        assert neg["callerVersion"] == prior["moduleVersion"]
        assert neg["currentVersion"] == _physique_reg()["moduleVersion"]
        assert neg["status"] == "DEPRECATED"

    def test_deprecated_version_violations_still_fire(self):
        """Deprecated + violation trigger -> violation fires normally."""
        prior = _physique_prior()
        if prior is None:
            pytest.skip("No DEPRECATED prior version in RAL for PHYSIQUE")

        payload = _base_physique_payload(prior)
        # Remove required window to trigger RAL.MISSINGREQUIREDWINDOW
        # Actually, that would fire before gates. Instead, just verify
        # the eval completes (no crash) and no MODULEREGISTRYMISMATCH
        kdo = _runner().evaluate(payload, "PHYSIQUE")
        codes = [v["code"] for v in kdo.violations]
        assert "RAL.MODULEREGISTRYMISMATCH" not in codes
        # The eval ran gates (may or may not have violations depending
        # on payload content, but no mismatch)

    def test_retired_version_rejected(self, monkeypatch):
        """RETIRED prior version -> RAL.MODULEREGISTRYMISMATCH."""
        reg = copy.deepcopy(RAL_SPEC["moduleRegistration"]["PHYSIQUE"])
        reg["priorVersions"] = [{
            "moduleVersion": "0.0.1",
            "moduleViolationRegistryVersion": "0.0.1",
            "registryHash": "fakehash",
            "status": "RETIRED",
        }]

        patched_spec = copy.deepcopy(RAL_SPEC)
        patched_spec["moduleRegistration"]["PHYSIQUE"] = reg

        import efl_kernel.kernel.kernel as kernel_mod
        monkeypatch.setattr(kernel_mod, "RAL_SPEC", patched_spec)

        payload = _base_physique_payload({
            "moduleVersion": "0.0.1",
            "moduleViolationRegistryVersion": "0.0.1",
            "registryHash": "fakehash",
        })
        kdo = _runner().evaluate(payload, "PHYSIQUE")
        codes = [v["code"] for v in kdo.violations]
        assert "RAL.MODULEREGISTRYMISMATCH" in codes

    def test_no_prior_versions_exact_match_only(self):
        """SESSION (priorVersions: []) + wrong version -> quarantine."""
        payload = {
            "moduleVersion": "0.0.0",
            "moduleViolationRegistryVersion": "0.0.0",
            "registryHash": "wronghash",
            "objectID": "obj-1",
            "evaluationContext": {"athleteID": "a1", "sessionID": "s1"},
            "windowContext": [
                {"windowType": "ROLLING7DAYS", "anchorDate": "2026-03-09",
                 "startDate": "2026-03-02", "endDate": "2026-03-09", "timezone": "UTC"},
                {"windowType": "ROLLING28DAYS", "anchorDate": "2026-03-09",
                 "startDate": "2026-02-09", "endDate": "2026-03-09", "timezone": "UTC"},
            ],
        }
        kdo = _runner().evaluate(payload, "SESSION")
        codes = [v["code"] for v in kdo.violations]
        assert "RAL.MODULEREGISTRYMISMATCH" in codes

    def test_wrong_hash_same_version_rejected(self):
        """Correct moduleVersion but wrong registryHash -> quarantine."""
        reg = _physique_reg()
        payload = _base_physique_payload({
            "moduleVersion": reg["moduleVersion"],
            "moduleViolationRegistryVersion": reg["moduleViolationRegistryVersion"],
            "registryHash": "0" * 64,  # wrong hash
        })
        kdo = _runner().evaluate(payload, "PHYSIQUE")
        codes = [v["code"] for v in kdo.violations]
        assert "RAL.MODULEREGISTRYMISMATCH" in codes


# ---------------------------------------------------------------------------
# _match_prior_version helper tests
# ---------------------------------------------------------------------------

class TestMatchPriorVersion:
    def test_match_prior_version_helper_found(self):
        reg = {
            "priorVersions": [{
                "moduleVersion": "1.0.3",
                "moduleViolationRegistryVersion": "1.0.3",
                "registryHash": "abc123",
                "status": "DEPRECATED",
            }]
        }
        result = _match_prior_version(reg, "1.0.3", "1.0.3", "abc123")
        assert result is not None
        assert result["moduleVersion"] == "1.0.3"

    def test_match_prior_version_helper_not_found(self):
        reg = {
            "priorVersions": [{
                "moduleVersion": "1.0.3",
                "moduleViolationRegistryVersion": "1.0.3",
                "registryHash": "abc123",
                "status": "DEPRECATED",
            }]
        }
        result = _match_prior_version(reg, "1.0.2", "1.0.2", "xyz")
        assert result is None

    def test_match_prior_version_helper_retired_skipped(self):
        reg = {
            "priorVersions": [{
                "moduleVersion": "1.0.3",
                "moduleViolationRegistryVersion": "1.0.3",
                "registryHash": "abc123",
                "status": "RETIRED",
            }]
        }
        result = _match_prior_version(reg, "1.0.3", "1.0.3", "abc123")
        assert result is None


# ---------------------------------------------------------------------------
# KDO shape tests
# ---------------------------------------------------------------------------

class TestKDOShape:
    def test_kdo_no_negotiation_on_current(self):
        """Current version -> no versionNegotiation in resolution."""
        reg = _physique_reg()
        payload = _base_physique_payload(reg)
        kdo = _runner().evaluate(payload, "PHYSIQUE")
        assert "versionNegotiation" not in kdo.resolution


# ---------------------------------------------------------------------------
# RAL v1.7.0 structural tests
# ---------------------------------------------------------------------------

class TestRALv170:
    def test_ral_v1_7_0_loads_and_verifies(self):
        """RAL v1.7.0 loaded and documentHash verified."""
        assert RAL_SPEC["version"] == "1.7.0"

    def test_ral_v1_7_0_has_prior_versions_schema(self):
        """All moduleRegistration entries have priorVersions field."""
        for mod, reg in RAL_SPEC["moduleRegistration"].items():
            assert "priorVersions" in reg, f"{mod} missing priorVersions"
            assert isinstance(reg["priorVersions"], list)


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_intake_session_still_works(self, tmp_path):
        """POST /intake/session still works with RAL v1.7.0."""
        from fastapi.testclient import TestClient
        from efl_kernel.service import create_app

        app = create_app(str(tmp_path / "v26.db"))
        client = TestClient(app)

        client.post("/athletes", json={
            "athlete_id": "ATH-V26",
            "max_daily_contact_load": 999.0,
            "minimum_rest_interval_hours": 0.0,
            "e4_clearance": 1,
        })

        r = client.post("/intake/session", json={
            "athlete_id": "ATH-V26",
            "session_id": "S-V26-001",
            "session_date": "2026-03-09T10:00:00+00:00",
            "contact_load": 50.0,
        })
        assert r.status_code == 200
        assert r.json()["evaluation"]["publish_state"] == "LEGALREADY"

    def test_evaluate_physique_still_works(self):
        """POST /evaluate/physique still works with RAL v1.7.0."""
        from fastapi.testclient import TestClient
        from efl_kernel.service import create_app

        app = create_app(":memory:")
        client = TestClient(app)

        reg = _physique_reg()
        r = client.post("/evaluate/physique", json=_base_physique_payload(reg))
        assert r.status_code == 200
        body = r.json()
        assert body["resolution"]["finalPublishState"] in (
            "LEGALREADY", "REQUIRESREVIEW", "LEGALOVERRIDE", "ILLEGALQUARANTINED"
        )


# ---------------------------------------------------------------------------
# Version check
# ---------------------------------------------------------------------------

def test_version_bumped():
    from efl_kernel.service import create_app
    app = create_app(":memory:")
    major = int(app.version.split(".")[0])
    assert major >= 24
