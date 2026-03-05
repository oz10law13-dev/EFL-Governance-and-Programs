from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from efl_kernel.kernel.audit_store import AuditStore
from efl_kernel.kernel.kdo import KDOValidator
from efl_kernel.kernel.kernel import KernelRunner
from efl_kernel.kernel.operational_store import OperationalStore
from efl_kernel.kernel.ral import RAL_SPEC
from efl_kernel.kernel.sqlite_dependency_provider import SqliteDependencyProvider

SESSION_REG = RAL_SPEC["moduleRegistration"]["SESSION"]
MESO_REG = RAL_SPEC["moduleRegistration"]["MESO"]
MACRO_REG = RAL_SPEC["moduleRegistration"]["MACRO"]


# ------------------------------------------------------------------ #
# Infrastructure helpers                                              #
# ------------------------------------------------------------------ #

def _make_provider(db_path):
    op_store = OperationalStore(str(db_path))
    audit_store = AuditStore(str(db_path))
    return SqliteDependencyProvider(op_store, audit_store), op_store, audit_store


def _make_runner(db_path):
    provider, op_store, audit_store = _make_provider(db_path)
    return KernelRunner(provider), op_store, audit_store


# ------------------------------------------------------------------ #
# Conformance base dicts — copied from test_conformance._*_input()   #
# moduleVersion / registryHash read from RAL_SPEC; never hardcoded.  #
# ------------------------------------------------------------------ #

def _conformance_session_base() -> dict:
    return {
        "moduleVersion": SESSION_REG["moduleVersion"],
        "moduleViolationRegistryVersion": SESSION_REG["moduleViolationRegistryVersion"],
        "registryHash": SESSION_REG["registryHash"],
        "objectID": "obj-session-1",
        "evaluationContext": {"athleteID": "a1", "sessionID": "s1"},
        "windowContext": [
            {
                "windowType": "ROLLING7DAYS",
                "anchorDate": "2026-01-01",
                "startDate": "2025-12-26",
                "endDate": "2026-01-01",
                "timezone": "UTC",
            },
            {
                "windowType": "ROLLING28DAYS",
                "anchorDate": "2026-01-01",
                "startDate": "2025-12-05",
                "endDate": "2026-01-01",
                "timezone": "UTC",
            },
        ],
    }


def _conformance_meso_base() -> dict:
    return {
        "moduleVersion": MESO_REG["moduleVersion"],
        "moduleViolationRegistryVersion": MESO_REG["moduleViolationRegistryVersion"],
        "registryHash": MESO_REG["registryHash"],
        "objectID": "obj-meso-1",
        "evaluationContext": {"athleteID": "a1", "mesoID": "m1"},
        "windowContext": [
            {
                "windowType": "MESOCYCLE",
                "anchorDate": "2026-01-01",
                "startDate": "2025-12-05",
                "endDate": "2026-01-01",
                "timezone": "UTC",
            },
        ],
    }


def _conformance_macro_base() -> dict:
    return {
        "moduleVersion": MACRO_REG["moduleVersion"],
        "moduleViolationRegistryVersion": MACRO_REG["moduleViolationRegistryVersion"],
        "registryHash": MACRO_REG["registryHash"],
        "objectID": "obj-macro-1",
        "evaluationContext": {"athleteID": "a1", "seasonID": "season-1"},
        "windowContext": [
            {
                "windowType": "SEASON",
                "anchorDate": "2026-01-01",
                "startDate": "2025-01-01",
                "endDate": "2026-01-01",
                "timezone": "UTC",
            },
        ],
    }


# ------------------------------------------------------------------ #
# Payload builders                                                     #
# ------------------------------------------------------------------ #

def _session_payload(
    athlete_id: str,
    session_id: str,
    session_date: str,
    contact_load: float,
    exercises=None,
    anchor_date: str | None = None,
) -> dict:
    """Build a SESSION payload starting from the conformance base dict.

    Overrides objectID, evaluationContext, and session fields.
    If anchor_date is provided, windowContext dates are updated
    consistently so the window covers the intended session date.
    """
    payload = _conformance_session_base()
    payload["objectID"] = session_id
    payload["evaluationContext"] = {"athleteID": athlete_id, "sessionID": session_id}
    payload["session"] = {
        "sessionDate": session_date,
        "contactLoad": contact_load,
        "exercises": exercises if exercises is not None else [],
    }
    if anchor_date is not None:
        anchor = date.fromisoformat(anchor_date)
        for entry in payload["windowContext"]:
            if entry["windowType"] == "ROLLING28DAYS":
                entry["anchorDate"] = anchor_date
                entry["startDate"] = (anchor - timedelta(days=28)).isoformat()
                entry["endDate"] = anchor_date
            elif entry["windowType"] == "ROLLING7DAYS":
                entry["anchorDate"] = anchor_date
                entry["startDate"] = (anchor - timedelta(days=7)).isoformat()
                entry["endDate"] = anchor_date
    return payload


def _meso_payload(athlete_id: str, meso_id: str, anchor_date: str) -> dict:
    """Build a MESO payload starting from the conformance base dict.

    Overrides objectID, evaluationContext, and MESOCYCLE window dates.
    anchor_date drives the ROLLING28DAYS window in gates_meso.py.
    """
    payload = _conformance_meso_base()
    payload["objectID"] = meso_id
    payload["evaluationContext"] = {"athleteID": athlete_id, "mesoID": meso_id}
    anchor = date.fromisoformat(anchor_date)
    entry = payload["windowContext"][0]
    entry["anchorDate"] = anchor_date
    entry["startDate"] = (anchor - timedelta(days=28)).isoformat()
    entry["endDate"] = anchor_date
    entry["timezone"] = "UTC"
    return payload


def _macro_payload(athlete_id: str, season_id: str, anchor_date: str) -> dict:
    """Build a MACRO payload starting from the conformance base dict.

    Overrides objectID, evaluationContext, and SEASON window dates.
    """
    payload = _conformance_macro_base()
    payload["objectID"] = season_id
    payload["evaluationContext"] = {"athleteID": athlete_id, "seasonID": season_id}
    anchor = date.fromisoformat(anchor_date)
    entry = payload["windowContext"][0]
    entry["anchorDate"] = anchor_date
    entry["startDate"] = (anchor - timedelta(days=365)).isoformat()
    entry["endDate"] = anchor_date
    entry["timezone"] = "UTC"
    return payload


# ------------------------------------------------------------------ #
# GROUP 1 — SCM gates                                                 #
# ------------------------------------------------------------------ #

def test_scm_maxdailyload_fires_from_persisted_athlete(tmp_path):
    db = tmp_path / "scm_max.db"
    runner, op_store, audit_store = _make_runner(db)

    op_store.upsert_athlete({
        "athlete_id": "ATH-SCM-01",
        "max_daily_contact_load": 50.0,
        "minimum_rest_interval_hours": 24.0,
        "e4_clearance": 0,
    })

    payload = _session_payload(
        athlete_id="ATH-SCM-01",
        session_id="S-SCM-MAX-01",
        session_date="2026-01-15T10:00:00+00:00",
        contact_load=100.0,
        exercises=[],
        anchor_date="2026-01-15",
    )

    kdo = runner.evaluate(payload, "SESSION")
    codes = {v["code"] for v in kdo.violations}

    assert "SCM.MAXDAILYLOAD" in codes
    assert kdo.resolution["finalPublishState"] == "ILLEGALQUARANTINED"

    audit_store.commit_kdo(kdo)
    conn = sqlite3.connect(str(db))
    count = conn.execute("SELECT COUNT(*) FROM kdo_log").fetchone()[0]
    conn.close()
    assert count == 1


def test_scm_maxdailyload_clean_when_load_within_cap(tmp_path):
    db = tmp_path / "scm_max_clean.db"
    runner, op_store, _ = _make_runner(db)

    op_store.upsert_athlete({
        "athlete_id": "ATH-SCM-01B",
        "max_daily_contact_load": 200.0,
        "minimum_rest_interval_hours": 24.0,
        "e4_clearance": 0,
    })
    # No prior sessions.

    payload = _session_payload(
        athlete_id="ATH-SCM-01B",
        session_id="S-SCM-MAX-CLEAN-01",
        session_date="2026-01-15T10:00:00+00:00",
        contact_load=50.0,
        exercises=[],
        anchor_date="2026-01-15",
    )

    kdo = runner.evaluate(payload, "SESSION")
    codes = {v["code"] for v in kdo.violations}

    assert "SCM.MAXDAILYLOAD" not in codes


def test_scm_minrest_fires_from_persisted_prior_session(tmp_path):
    db = tmp_path / "scm_rest.db"
    runner, op_store, _ = _make_runner(db)

    op_store.upsert_athlete({
        "athlete_id": "ATH-SCM-02",
        "max_daily_contact_load": 500.0,
        "minimum_rest_interval_hours": 24.0,
        "e4_clearance": 0,
    })
    op_store.upsert_session({
        "session_id": "PRIOR-01",
        "athlete_id": "ATH-SCM-02",
        "session_date": "2026-01-15T10:00:00+00:00",
        "contact_load": 10.0,
    })

    # New session 10 hours after prior — less than 24h minimum rest.
    payload = _session_payload(
        athlete_id="ATH-SCM-02",
        session_id="S-SCM-REST-01",
        session_date="2026-01-15T20:00:00+00:00",
        contact_load=10.0,
        exercises=[],
        anchor_date="2026-01-15",
    )

    kdo = runner.evaluate(payload, "SESSION")
    codes = {v["code"] for v in kdo.violations}

    assert "SCM.MINREST" in codes


def test_scm_minrest_clean_when_rest_sufficient(tmp_path):
    db = tmp_path / "scm_rest_clean.db"
    runner, op_store, _ = _make_runner(db)

    op_store.upsert_athlete({
        "athlete_id": "ATH-SCM-03",
        "max_daily_contact_load": 500.0,
        "minimum_rest_interval_hours": 24.0,
        "e4_clearance": 0,
    })
    op_store.upsert_session({
        "session_id": "PRIOR-02",
        "athlete_id": "ATH-SCM-03",
        "session_date": "2026-01-10T10:00:00+00:00",
        "contact_load": 10.0,
    })

    # New session 120 hours after prior — well above 24h minimum rest.
    payload = _session_payload(
        athlete_id="ATH-SCM-03",
        session_id="S-SCM-REST-CLEAN-01",
        session_date="2026-01-15T10:00:00+00:00",
        contact_load=10.0,
        exercises=[],
        anchor_date="2026-01-15",
    )

    kdo = runner.evaluate(payload, "SESSION")
    codes = {v["code"] for v in kdo.violations}

    assert "SCM.MINREST" not in codes


def test_scm_minrest_clean_when_no_prior_session(tmp_path):
    db = tmp_path / "scm_no_prior.db"
    runner, op_store, _ = _make_runner(db)

    op_store.upsert_athlete({
        "athlete_id": "ATH-SCM-04",
        "max_daily_contact_load": 500.0,
        "minimum_rest_interval_hours": 24.0,
        "e4_clearance": 0,
    })
    # No sessions inserted — get_prior_session returns None.

    payload = _session_payload(
        athlete_id="ATH-SCM-04",
        session_id="S-SCM-NOPRIOR-01",
        session_date="2026-01-15T10:00:00+00:00",
        contact_load=0.0,
        exercises=[],
        anchor_date="2026-01-15",
    )

    kdo = runner.evaluate(payload, "SESSION")
    codes = {v["code"] for v in kdo.violations}

    assert "SCM.MINREST" not in codes


# ------------------------------------------------------------------ #
# GROUP 2 — CL gate                                                   #
# ------------------------------------------------------------------ #

def test_cl_clearance_fires_from_persisted_athlete_profile(tmp_path):
    db = tmp_path / "cl_deny.db"
    runner, op_store, _ = _make_runner(db)

    op_store.upsert_athlete({
        "athlete_id": "ATH-CL-01",
        "max_daily_contact_load": 500.0,
        "minimum_rest_interval_hours": 1.0,
        "e4_clearance": 0,
    })

    # isometric_mid_thigh_pull_max confirmed as E4 exercise in
    # test_all_gates_functional.py (session_2, line 97).
    # exercises under "session" key, each entry has "exerciseID" field.
    payload = _session_payload(
        athlete_id="ATH-CL-01",
        session_id="S-CL-DENY-01",
        session_date="2026-03-01T10:00:00+00:00",
        contact_load=0,
        exercises=[{"exerciseID": "isometric_mid_thigh_pull_max"}],
        anchor_date="2026-03-01",
    )

    kdo = runner.evaluate(payload, "SESSION")
    codes = {v["code"] for v in kdo.violations}

    assert "CL.CLEARANCEMISSING" in codes


def test_cl_clearance_clean_when_athlete_has_clearance(tmp_path):
    db = tmp_path / "cl_allow.db"
    runner, op_store, _ = _make_runner(db)

    op_store.upsert_athlete({
        "athlete_id": "ATH-CL-02",
        "max_daily_contact_load": 500.0,
        "minimum_rest_interval_hours": 1.0,
        "e4_clearance": 1,
    })

    payload = _session_payload(
        athlete_id="ATH-CL-02",
        session_id="S-CL-ALLOW-01",
        session_date="2026-03-01T10:00:00+00:00",
        contact_load=0,
        exercises=[{"exerciseID": "isometric_mid_thigh_pull_max"}],
        anchor_date="2026-03-01",
    )

    kdo = runner.evaluate(payload, "SESSION")
    codes = {v["code"] for v in kdo.violations}

    assert "CL.CLEARANCEMISSING" not in codes


# ------------------------------------------------------------------ #
# GROUP 3 — Fail-closed sentinel behavior                             #
# ------------------------------------------------------------------ #

def test_missing_athlete_fails_closed_scm(tmp_path):
    db = tmp_path / "sentinel_athlete.db"
    runner, _, _ = _make_runner(db)

    # No athlete row inserted.
    # SqliteDependencyProvider returns _MISSING_ATHLETE_SENTINEL:
    # maxDailyContactLoad=0.0, so any nonzero contactLoad fires immediately.
    payload = _session_payload(
        athlete_id="DOES-NOT-EXIST",
        session_id="S-SENTINEL-01",
        session_date="2026-01-15T10:00:00+00:00",
        contact_load=1.0,
        exercises=[],
        anchor_date="2026-01-15",
    )

    kdo = runner.evaluate(payload, "SESSION")
    codes = {v["code"] for v in kdo.violations}

    assert "SCM.MAXDAILYLOAD" in codes


def test_missing_season_fails_closed_macro(tmp_path):
    db = tmp_path / "sentinel_season.db"
    runner, op_store, _ = _make_runner(db)

    op_store.upsert_athlete({
        "athlete_id": "ATH-NOSEA-01",
        "max_daily_contact_load": 200.0,
        "minimum_rest_interval_hours": 24.0,
        "e4_clearance": 0,
    })
    # No season row inserted.
    # SqliteDependencyProvider returns _MISSING_SEASON_SENTINEL:
    # competitionWeeks=1, gppWeeks=0 → MACRO.PHASEMISMATCH fires immediately.

    payload = _macro_payload(
        athlete_id="ATH-NOSEA-01",
        season_id="SEASON-MISSING",
        anchor_date="2026-12-31",
    )

    kdo = runner.evaluate(payload, "MACRO")
    codes = {v["code"] for v in kdo.violations}

    assert "MACRO.PHASEMISMATCH" in codes


# ------------------------------------------------------------------ #
# GROUP 4 — MESO gate                                                 #
# ------------------------------------------------------------------ #

def test_meso_loadimbalance_fires_from_persisted_sessions(tmp_path):
    """Violation from persisted session rows. No injected window totals."""
    db = tmp_path / "meso_spike.db"
    runner, op_store, _ = _make_runner(db)

    op_store.upsert_athlete({
        "athlete_id": "ATH-MESO-01",
        "max_daily_contact_load": 9999.0,
        "minimum_rest_interval_hours": 0.0,
        "e4_clearance": 0,
    })
    for sid, sdate, load in [
        ("M-S1", "2026-01-05T10:00:00+00:00", 30.0),
        ("M-S2", "2026-01-12T10:00:00+00:00", 35.0),
        ("M-S3", "2026-01-19T10:00:00+00:00", 30.0),
        ("M-S4", "2026-01-26T10:00:00+00:00", 150.0),
    ]:
        op_store.upsert_session({
            "session_id": sid,
            "athlete_id": "ATH-MESO-01",
            "session_date": sdate,
            "contact_load": load,
        })

    # anchor_date="2026-02-01" → ROLLING28DAYS covers 2026-01-04 to 2026-02-01.
    # All four sessions fall within the window.
    # avg=(30+35+30+150)/4=61.25, max=150.0, 150.0 > 122.5 → fires.
    payload = _meso_payload(
        athlete_id="ATH-MESO-01",
        meso_id="MESO-SPIKE-01",
        anchor_date="2026-02-01",
    )

    kdo = runner.evaluate(payload, "MESO")
    codes = {v["code"] for v in kdo.violations}

    assert "MESO.LOADIMBALANCE" in codes


def test_meso_clean_when_load_balanced(tmp_path):
    db = tmp_path / "meso_balanced.db"
    runner, op_store, _ = _make_runner(db)

    op_store.upsert_athlete({
        "athlete_id": "ATH-MESO-02",
        "max_daily_contact_load": 9999.0,
        "minimum_rest_interval_hours": 0.0,
        "e4_clearance": 0,
    })
    for sid, sdate in [
        ("B-S1", "2026-01-05T10:00:00+00:00"),
        ("B-S2", "2026-01-12T10:00:00+00:00"),
        ("B-S3", "2026-01-19T10:00:00+00:00"),
        ("B-S4", "2026-01-26T10:00:00+00:00"),
    ]:
        op_store.upsert_session({
            "session_id": sid,
            "athlete_id": "ATH-MESO-02",
            "session_date": sdate,
            "contact_load": 30.0,
        })

    payload = _meso_payload(
        athlete_id="ATH-MESO-02",
        meso_id="MESO-BAL-01",
        anchor_date="2026-02-01",
    )

    kdo = runner.evaluate(payload, "MESO")
    codes = {v["code"] for v in kdo.violations}

    # avg=30.0, max=30.0, 30.0 > 60.0 is False → no violation.
    assert "MESO.LOADIMBALANCE" not in codes


def test_meso_clean_when_empty_window(tmp_path):
    db = tmp_path / "meso_empty.db"
    runner, op_store, _ = _make_runner(db)

    op_store.upsert_athlete({
        "athlete_id": "ATH-MESO-03",
        "max_daily_contact_load": 9999.0,
        "minimum_rest_interval_hours": 0.0,
        "e4_clearance": 0,
    })
    # No sessions inserted.

    payload = _meso_payload(
        athlete_id="ATH-MESO-03",
        meso_id="MESO-EMPTY-01",
        anchor_date="2026-02-01",
    )

    kdo = runner.evaluate(payload, "MESO")
    codes = {v["code"] for v in kdo.violations}

    # len(daily) == 0 < 2 → gate suppresses.
    # Empty-window neutral shape confirmed end-to-end.
    assert "MESO.LOADIMBALANCE" not in codes


def test_meso_clean_when_only_one_session_in_window(tmp_path):
    db = tmp_path / "meso_one.db"
    runner, op_store, _ = _make_runner(db)

    op_store.upsert_athlete({
        "athlete_id": "ATH-MESO-04",
        "max_daily_contact_load": 9999.0,
        "minimum_rest_interval_hours": 0.0,
        "e4_clearance": 0,
    })
    op_store.upsert_session({
        "session_id": "ONE-S1",
        "athlete_id": "ATH-MESO-04",
        "session_date": "2026-01-15T10:00:00+00:00",
        "contact_load": 200.0,
    })

    payload = _meso_payload(
        athlete_id="ATH-MESO-04",
        meso_id="MESO-ONE-01",
        anchor_date="2026-02-01",
    )

    kdo = runner.evaluate(payload, "MESO")
    codes = {v["code"] for v in kdo.violations}

    # len(daily) == 1 < 2 → gate suppresses.
    assert "MESO.LOADIMBALANCE" not in codes


def test_meso_exclude_session_id_prevents_self_inclusion(tmp_path):
    """Exclusion driven by evaluationContext['mesoID'].

    gates_meso.py passes eval_ctx.get("mesoID", "") as exclude_session_id
    to get_window_totals (gates_meso.py line 14). Sessions whose
    session_id == mesoID are excluded from the window query.

    S3 session_id == "MESO-EXCL-01" == meso_id → excluded from totals.

    With S3 excluded:  daily=[30.0, 30.0], avg=30.0, max=30.0
                       30.0 > 60.0 is False → no violation.
    Bug path (S3 in):  daily=[30.0, 30.0, 150.0], avg=70.0, max=150.0
                       150.0 > 140.0 → violation would fire.
    """
    db = tmp_path / "meso_excl.db"
    runner, op_store, _ = _make_runner(db)

    op_store.upsert_athlete({
        "athlete_id": "ATH-MESO-EXCL",
        "max_daily_contact_load": 9999.0,
        "minimum_rest_interval_hours": 0.0,
        "e4_clearance": 0,
    })
    for sid, sdate, load in [
        ("M-EXCL-S1",  "2026-01-10T10:00:00+00:00", 30.0),
        ("M-EXCL-S2",  "2026-01-17T10:00:00+00:00", 30.0),
        ("MESO-EXCL-01", "2026-01-24T10:00:00+00:00", 150.0),  # excluded
    ]:
        op_store.upsert_session({
            "session_id": sid,
            "athlete_id": "ATH-MESO-EXCL",
            "session_date": sdate,
            "contact_load": load,
        })

    payload = _meso_payload(
        athlete_id="ATH-MESO-EXCL",
        meso_id="MESO-EXCL-01",
        anchor_date="2026-02-01",
    )

    kdo = runner.evaluate(payload, "MESO")
    codes = {v["code"] for v in kdo.violations}

    assert "MESO.LOADIMBALANCE" not in codes


# ------------------------------------------------------------------ #
# GROUP 5 — MACRO gate                                                #
# ------------------------------------------------------------------ #

def test_macro_phasemismatch_fires_from_persisted_season(tmp_path):
    """From persisted season row. Not a sentinel."""
    db = tmp_path / "macro_mismatch.db"
    runner, op_store, _ = _make_runner(db)

    op_store.upsert_athlete({
        "athlete_id": "ATH-MAC-01",
        "max_daily_contact_load": 200.0,
        "minimum_rest_interval_hours": 24.0,
        "e4_clearance": 0,
    })
    op_store.upsert_season({
        "athlete_id": "ATH-MAC-01",
        "season_id": "SEASON-BAD",
        "competition_weeks": 10,
        "gpp_weeks": 2,
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
    })

    payload = _macro_payload(
        athlete_id="ATH-MAC-01",
        season_id="SEASON-BAD",
        anchor_date="2026-12-31",
    )

    kdo = runner.evaluate(payload, "MACRO")
    codes = {v["code"] for v in kdo.violations}

    # Ratio = 10/2 = 5.0 > 2.0 → fires.
    assert "MACRO.PHASEMISMATCH" in codes


def test_macro_clean_when_season_ratio_valid(tmp_path):
    db = tmp_path / "macro_clean.db"
    runner, op_store, _ = _make_runner(db)

    op_store.upsert_athlete({
        "athlete_id": "ATH-MAC-02",
        "max_daily_contact_load": 200.0,
        "minimum_rest_interval_hours": 24.0,
        "e4_clearance": 0,
    })
    op_store.upsert_season({
        "athlete_id": "ATH-MAC-02",
        "season_id": "SEASON-GOOD",
        "competition_weeks": 4,
        "gpp_weeks": 8,
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
    })

    payload = _macro_payload(
        athlete_id="ATH-MAC-02",
        season_id="SEASON-GOOD",
        anchor_date="2026-12-31",
    )

    kdo = runner.evaluate(payload, "MACRO")
    codes = {v["code"] for v in kdo.violations}

    # Ratio = 4/8 = 0.5 ≤ 2.0 → no violation.
    assert "MACRO.PHASEMISMATCH" not in codes


# ------------------------------------------------------------------ #
# GROUP 6 — KDO invariants and audit persistence                      #
# ------------------------------------------------------------------ #

def test_kdo_persisted_to_audit_store(tmp_path):
    db = tmp_path / "kdo_persist.db"
    runner, op_store, audit_store = _make_runner(db)

    op_store.upsert_athlete({
        "athlete_id": "ATH-KDO-01",
        "max_daily_contact_load": 999.0,
        "minimum_rest_interval_hours": 0.0,
        "e4_clearance": 1,
    })
    # No prior sessions — clean path, no violations expected.

    payload = _session_payload(
        athlete_id="ATH-KDO-01",
        session_id="S-KDO-01",
        session_date="2026-01-15T10:00:00+00:00",
        contact_load=0,
        exercises=[],
        anchor_date="2026-01-15",
    )

    kdo = runner.evaluate(payload, "SESSION")

    # Invariants that hold before freeze.
    assert kdo.violations == []
    assert kdo.resolution["finalPublishState"] == "LEGALREADY"

    # KDOValidator passes (does not require non-empty decisionHash).
    errors = KDOValidator().validate(kdo)
    assert errors == []

    # commit_kdo freezes the KDO in-place before persisting.
    audit_store.commit_kdo(kdo)

    # decisionHash is populated after freeze via commit_kdo.
    assert isinstance(kdo.audit.get("decisionHash"), str)
    assert len(kdo.audit["decisionHash"]) > 0

    # Verify persistence.
    # kdo_log schema (from audit_store.py):
    #   decision_hash(0), timestamp_normalized(1),
    #   module_id(2), object_id(3), kdo_json(4)
    conn = sqlite3.connect(str(db))
    rows = conn.execute("SELECT * FROM kdo_log").fetchall()
    conn.close()

    assert len(rows) == 1
    assert rows[0][3] == "S-KDO-01"
