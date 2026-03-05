from __future__ import annotations

import json
import sqlite3

import pytest

from efl_kernel.kernel.audit_store import AuditStore
from efl_kernel.kernel.operational_store import OperationalStore
from efl_kernel.tools import seed


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def _athlete(athlete_id: str = "ATH001", load: float = 150.0) -> dict:
    return {
        "athlete_id": athlete_id,
        "max_daily_contact_load": load,
        "minimum_rest_interval_hours": 24.0,
        "e4_clearance": 0,
    }


def _session(session_id: str, athlete_id: str, session_date: str, contact_load: float) -> dict:
    return {
        "session_id": session_id,
        "athlete_id": athlete_id,
        "session_date": session_date,
        "contact_load": contact_load,
    }


def _season(athlete_id: str = "ATH001", season_id: str = "S2026") -> dict:
    return {
        "athlete_id": athlete_id,
        "season_id": season_id,
        "competition_weeks": 4,
        "gpp_weeks": 8,
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
    }


# ------------------------------------------------------------------ #
# Initialization                                                      #
# ------------------------------------------------------------------ #

def test_init_creates_tables_idempotently(tmp_path):
    db = str(tmp_path / "test.db")
    OperationalStore(db)
    OperationalStore(db)  # second init must not raise

    conn = sqlite3.connect(db)
    objects = {r[0] for r in conn.execute("SELECT name FROM sqlite_master").fetchall()}
    conn.close()

    assert "op_athletes" in objects
    assert "op_sessions" in objects
    assert "op_seasons" in objects
    assert "idx_op_sessions_athlete_date" in objects


def test_init_coexists_with_audit_tables(tmp_path):
    db = str(tmp_path / "test.db")
    AuditStore(db)
    OperationalStore(db)

    conn = sqlite3.connect(db)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()

    # audit tables present
    assert "kdo_log" in tables
    assert "override_ledger" in tables
    # operational tables present
    assert "op_athletes" in tables
    assert "op_sessions" in tables
    assert "op_seasons" in tables


# ------------------------------------------------------------------ #
# Athletes                                                            #
# ------------------------------------------------------------------ #

def test_upsert_and_get_athlete(tmp_path):
    store = OperationalStore(str(tmp_path / "test.db"))
    store.upsert_athlete(_athlete("A1", load=100.0))

    result = store.get_athlete("A1")
    assert result is not None
    assert result["athlete_id"] == "A1"
    assert result["max_daily_contact_load"] == 100.0
    assert result["minimum_rest_interval_hours"] == 24.0
    assert result["e4_clearance"] == 0

    # update load cap
    store.upsert_athlete(_athlete("A1", load=200.0))
    updated = store.get_athlete("A1")
    assert updated["max_daily_contact_load"] == 200.0


def test_get_athlete_returns_none_for_missing(tmp_path):
    store = OperationalStore(str(tmp_path / "test.db"))
    assert store.get_athlete("NOBODY") is None


def test_upsert_athlete_preserves_created_at_on_update(tmp_path):
    store = OperationalStore(str(tmp_path / "test.db"))
    store.upsert_athlete(_athlete("A1", load=100.0))
    original = store.get_athlete("A1")
    original_created_at = original["created_at"]

    store.upsert_athlete(_athlete("A1", load=200.0))
    updated = store.get_athlete("A1")
    assert updated["created_at"] == original_created_at


# ------------------------------------------------------------------ #
# Sessions — prior session                                            #
# ------------------------------------------------------------------ #

def test_upsert_and_get_prior_session(tmp_path):
    store = OperationalStore(str(tmp_path / "test.db"))
    store.upsert_session(_session("S1", "A1", "2026-01-05T10:00:00+00:00", 50.0))
    store.upsert_session(_session("S2", "A1", "2026-01-10T10:00:00+00:00", 60.0))
    store.upsert_session(_session("S3", "A1", "2026-01-15T10:00:00+00:00", 70.0))

    # before_date is after S1 and S2; S2 is the most recent qualifying
    result = store.get_prior_session("A1", "2026-01-12T00:00:00+00:00")
    assert result is not None
    assert result["session_id"] == "S2"
    assert result["contact_load"] == 60.0


def test_get_prior_session_returns_none_for_no_history(tmp_path):
    store = OperationalStore(str(tmp_path / "test.db"))
    assert store.get_prior_session("A1", "2026-01-01T00:00:00+00:00") is None


def test_get_prior_session_strict_less_than(tmp_path):
    store = OperationalStore(str(tmp_path / "test.db"))
    store.upsert_session(_session("S1", "A1", "2026-01-10T10:00:00+00:00", 50.0))

    # before_date exactly equals session_date — must return None (strict less-than)
    result = store.get_prior_session("A1", "2026-01-10T10:00:00+00:00")
    assert result is None


# ------------------------------------------------------------------ #
# Sessions — window queries                                           #
# ------------------------------------------------------------------ #

def test_get_sessions_in_window(tmp_path):
    store = OperationalStore(str(tmp_path / "test.db"))
    # 5 sessions spanning 30 days; 28-day window ending 2026-01-31 covers 4
    store.upsert_session(_session("S0", "A1", "2026-01-02T10:00:00+00:00", 40.0))  # outside
    store.upsert_session(_session("S1", "A1", "2026-01-05T10:00:00+00:00", 50.0))
    store.upsert_session(_session("S2", "A1", "2026-01-12T10:00:00+00:00", 55.0))
    store.upsert_session(_session("S3", "A1", "2026-01-19T10:00:00+00:00", 50.0))
    store.upsert_session(_session("S4", "A1", "2026-01-26T10:00:00+00:00", 55.0))

    # window_start = 2026-01-04 (28 days before 2026-01-31); anchor = 2026-01-31
    results = store.get_sessions_in_window("A1", "2026-01-04T00:00:00+00:00", "2026-01-31T23:59:59+00:00")
    assert len(results) == 4
    assert [r["session_id"] for r in results] == ["S1", "S2", "S3", "S4"]


def test_get_sessions_in_window_excludes_session_id(tmp_path):
    store = OperationalStore(str(tmp_path / "test.db"))
    store.upsert_session(_session("S1", "A1", "2026-01-05T10:00:00+00:00", 50.0))
    store.upsert_session(_session("S2", "A1", "2026-01-12T10:00:00+00:00", 55.0))
    store.upsert_session(_session("S3", "A1", "2026-01-19T10:00:00+00:00", 60.0))

    results = store.get_sessions_in_window(
        "A1", "2026-01-01T00:00:00+00:00", "2026-01-31T23:59:59+00:00",
        exclude_session_id="S2",
    )
    assert len(results) == 2
    assert all(r["session_id"] != "S2" for r in results)


def test_get_sessions_in_window_empty_returns_neutral(tmp_path):
    store = OperationalStore(str(tmp_path / "test.db"))
    results = store.get_sessions_in_window("A1", "2026-01-01T00:00:00+00:00", "2026-01-31T23:59:59+00:00")
    assert results == []


# ------------------------------------------------------------------ #
# Seasons                                                             #
# ------------------------------------------------------------------ #

def test_upsert_and_get_season(tmp_path):
    store = OperationalStore(str(tmp_path / "test.db"))
    store.upsert_season(_season("A1", "S2026"))

    result = store.get_season("A1", "S2026")
    assert result is not None
    assert result["athlete_id"] == "A1"
    assert result["season_id"] == "S2026"
    assert result["competition_weeks"] == 4
    assert result["gpp_weeks"] == 8
    assert result["start_date"] == "2026-01-01"
    assert result["end_date"] == "2026-12-31"


def test_get_season_returns_none_for_missing(tmp_path):
    store = OperationalStore(str(tmp_path / "test.db"))
    assert store.get_season("NOBODY", "S2026") is None


# ------------------------------------------------------------------ #
# Seed CLI                                                            #
# ------------------------------------------------------------------ #

def _minimal_fixture() -> dict:
    return {
        "athletes": [_athlete("A1", load=100.0)],
        "sessions": [
            _session("S1", "A1", "2026-01-10T10:00:00+00:00", 80.0),
            _session("S2", "A1", "2026-01-15T10:00:00+00:00", 90.0),
        ],
        "seasons": [_season("A1", "S2026")],
    }


def test_seed_cli_inserts_all_entities(tmp_path):
    fixture_file = tmp_path / "fixture.json"
    fixture_file.write_text(json.dumps(_minimal_fixture()), encoding="utf-8")
    db_path = str(tmp_path / "test.db")

    seed.main(["--fixture", str(fixture_file), "--db", db_path])

    store = OperationalStore(db_path)
    assert store.get_athlete("A1") is not None
    sessions = store.get_sessions_in_window("A1", "2026-01-01T00:00:00+00:00", "2026-12-31T23:59:59+00:00")
    assert len(sessions) == 2
    assert store.get_season("A1", "S2026") is not None


def test_seed_cli_is_idempotent(tmp_path):
    fixture_file = tmp_path / "fixture.json"
    fixture_file.write_text(json.dumps(_minimal_fixture()), encoding="utf-8")
    db_path = str(tmp_path / "test.db")

    seed.main(["--fixture", str(fixture_file), "--db", db_path])
    seed.main(["--fixture", str(fixture_file), "--db", db_path])

    conn = sqlite3.connect(db_path)
    athlete_count = conn.execute("SELECT COUNT(*) FROM op_athletes").fetchone()[0]
    session_count = conn.execute("SELECT COUNT(*) FROM op_sessions").fetchone()[0]
    season_count = conn.execute("SELECT COUNT(*) FROM op_seasons").fetchone()[0]
    conn.close()

    assert athlete_count == 1
    assert session_count == 2
    assert season_count == 1


def test_seed_cli_exits_1_on_missing_fixture(tmp_path):
    with pytest.raises(SystemExit) as exc_info:
        seed.main(["--fixture", str(tmp_path / "nonexistent.json"), "--db", str(tmp_path / "test.db")])
    assert exc_info.value.code == 1


def test_seed_cli_exits_1_on_invalid_json(tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("not valid json{{{", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        seed.main(["--fixture", str(bad_file), "--db", str(tmp_path / "test.db")])
    assert exc_info.value.code == 1


def test_seed_cli_exits_1_on_missing_required_field(tmp_path):
    # athlete record missing athlete_id
    fixture = {"athletes": [{"max_daily_contact_load": 100.0, "minimum_rest_interval_hours": 24.0, "e4_clearance": 0}]}
    fixture_file = tmp_path / "fixture.json"
    fixture_file.write_text(json.dumps(fixture), encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        seed.main(["--fixture", str(fixture_file), "--db", str(tmp_path / "test.db")])
    assert exc_info.value.code == 1
