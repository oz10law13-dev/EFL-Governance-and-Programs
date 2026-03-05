from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from efl_kernel.kernel.audit_store import AuditStore
from efl_kernel.kernel.dependency_provider import InMemoryDependencyProvider
from efl_kernel.kernel.operational_store import OperationalStore
from efl_kernel.kernel.sqlite_dependency_provider import SqliteDependencyProvider


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def _make_provider(tmp_path) -> tuple[SqliteDependencyProvider, OperationalStore]:
    db = str(tmp_path / "test.db")
    audit_store = AuditStore(db)
    op_store = OperationalStore(db)
    provider = SqliteDependencyProvider(op_store, audit_store)
    return provider, op_store


def _athlete(
    athlete_id: str = "ATH001",
    load: float = 150.0,
    min_rest: float = 24.0,
    e4: int = 0,
) -> dict:
    return {
        "athlete_id": athlete_id,
        "max_daily_contact_load": load,
        "minimum_rest_interval_hours": min_rest,
        "e4_clearance": e4,
    }


def _session(session_id: str, athlete_id: str, session_date: str, contact_load: float) -> dict:
    return {
        "session_id": session_id,
        "athlete_id": athlete_id,
        "session_date": session_date,
        "contact_load": contact_load,
    }


# ------------------------------------------------------------------ #
# Inheritance guard                                                   #
# ------------------------------------------------------------------ #

def test_no_inheritance_from_in_memory_provider():
    """Permanent guard: SqliteDependencyProvider must not inherit InMemoryDependencyProvider."""
    assert not issubclass(SqliteDependencyProvider, InMemoryDependencyProvider)


# ------------------------------------------------------------------ #
# get_athlete_profile                                                 #
# ------------------------------------------------------------------ #

def test_get_athlete_profile_returns_real_fields(tmp_path):
    provider, op_store = _make_provider(tmp_path)
    op_store.upsert_athlete(_athlete("A1", load=120.0, min_rest=36.0, e4=1))

    result = provider.get_athlete_profile("A1")

    assert result["maxDailyContactLoad"] == 120.0
    assert result["minimumRestIntervalHours"] == 36.0
    assert result["e4_clearance"] is True
    assert isinstance(result["e4_clearance"], bool)


def test_get_athlete_profile_fail_closed_sentinel(tmp_path):
    provider, _ = _make_provider(tmp_path)

    result = provider.get_athlete_profile("DOES_NOT_EXIST")

    assert result["maxDailyContactLoad"] == 0.0
    assert result["minimumRestIntervalHours"] == 24.0
    assert result["e4_clearance"] is False


# ------------------------------------------------------------------ #
# get_prior_session                                                   #
# ------------------------------------------------------------------ #

def test_get_prior_session_returns_most_recent(tmp_path):
    provider, op_store = _make_provider(tmp_path)
    op_store.upsert_session(_session("S1", "A1", "2026-01-05T10:00:00+00:00", 50.0))
    op_store.upsert_session(_session("S2", "A1", "2026-01-10T10:00:00+00:00", 60.0))
    op_store.upsert_session(_session("S3", "A1", "2026-01-15T10:00:00+00:00", 70.0))

    # before_date after S1 and S2 but before S3 — S2 is the most recent qualifying
    before = datetime(2026, 1, 12, 0, 0, 0, tzinfo=timezone.utc)
    result = provider.get_prior_session("A1", before)

    assert result is not None
    assert result["sessionDate"] == "2026-01-10T10:00:00+00:00"
    assert result["sessionId"] == "S2"
    assert result["contactLoad"] == 60.0


def test_get_prior_session_strict_less_than(tmp_path):
    provider, op_store = _make_provider(tmp_path)
    op_store.upsert_session(_session("S1", "A1", "2026-01-10T10:00:00+00:00", 50.0))

    # before_date exactly equals session_date — must return None (strict <)
    before = datetime(2026, 1, 10, 10, 0, 0, tzinfo=timezone.utc)
    result = provider.get_prior_session("A1", before)

    assert result is None


def test_get_prior_session_none_for_new_athlete(tmp_path):
    provider, _ = _make_provider(tmp_path)
    before = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert provider.get_prior_session("A1", before) is None


# ------------------------------------------------------------------ #
# get_window_totals                                                   #
# ------------------------------------------------------------------ #

def test_get_window_totals_correct_aggregation(tmp_path):
    provider, op_store = _make_provider(tmp_path)
    # Four sessions within 28-day window ending 2026-02-01
    op_store.upsert_session(_session("S1", "A1", "2026-01-05T10:00:00+00:00", 50.0))
    op_store.upsert_session(_session("S2", "A1", "2026-01-12T10:00:00+00:00", 55.0))
    op_store.upsert_session(_session("S3", "A1", "2026-01-19T10:00:00+00:00", 60.0))
    op_store.upsert_session(_session("S4", "A1", "2026-01-26T10:00:00+00:00", 65.0))

    result = provider.get_window_totals(
        "A1", "ROLLING28DAYS", date(2026, 2, 1), exclude_session_id=""
    )

    assert result["totalContactLoad"] == pytest.approx(230.0)
    assert result["dailyContactLoads"] == [50.0, 55.0, 60.0, 65.0]


def test_get_window_totals_excludes_session_id(tmp_path):
    provider, op_store = _make_provider(tmp_path)
    op_store.upsert_session(_session("S1", "A1", "2026-01-05T10:00:00+00:00", 50.0))
    op_store.upsert_session(_session("S2", "A1", "2026-01-12T10:00:00+00:00", 55.0))
    op_store.upsert_session(_session("S3", "A1", "2026-01-19T10:00:00+00:00", 60.0))

    result = provider.get_window_totals(
        "A1", "ROLLING28DAYS", date(2026, 2, 1), exclude_session_id="S2"
    )

    assert len(result["dailyContactLoads"]) == 2
    assert result["totalContactLoad"] == pytest.approx(110.0)


def test_get_window_totals_empty_window_neutral_shape(tmp_path):
    provider, _ = _make_provider(tmp_path)

    result = provider.get_window_totals(
        "A1", "ROLLING28DAYS", date(2026, 2, 1), exclude_session_id=""
    )

    assert result == {"totalContactLoad": 0.0, "dailyContactLoads": []}


def test_get_window_totals_unknown_window_type_raises(tmp_path):
    provider, _ = _make_provider(tmp_path)

    with pytest.raises(ValueError, match="Unknown window type"):
        provider.get_window_totals("A1", "BOGUS_WINDOW", date(2026, 2, 1), "")


# ------------------------------------------------------------------ #
# get_season_phases                                                   #
# ------------------------------------------------------------------ #

def test_get_season_phases_returns_real_values(tmp_path):
    provider, op_store = _make_provider(tmp_path)
    op_store.upsert_season({
        "athlete_id": "A1", "season_id": "S2026",
        "competition_weeks": 4, "gpp_weeks": 8,
        "start_date": "2026-01-01", "end_date": "2026-12-31",
    })

    result = provider.get_season_phases("A1", "S2026")

    assert result["competitionWeeks"] == 4
    assert result["gppWeeks"] == 8


def test_get_season_phases_fail_closed_sentinel(tmp_path):
    provider, _ = _make_provider(tmp_path)

    result = provider.get_season_phases("NOBODY", "S2026")

    assert result["competitionWeeks"] == 1
    assert result["gppWeeks"] == 0
    # Confirm the MACRO gate would fire: competition_weeks > 0 and gpp_weeks <= 0
    assert result["competitionWeeks"] > 0
    assert result["gppWeeks"] <= 0


# ------------------------------------------------------------------ #
# get_override_history                                                #
# ------------------------------------------------------------------ #

def test_get_override_history_delegates_to_audit_store(tmp_path):
    db = str(tmp_path / "test.db")
    audit_store = AuditStore(db)
    op_store = OperationalStore(db)
    provider = SqliteDependencyProvider(op_store, audit_store)

    result = provider.get_override_history("ATH001|S001", "SESSION")

    assert result == {"byReasonCode": {}, "byViolationCode": {}}


# ------------------------------------------------------------------ #
# get_weekly_totals                                                   #
# ------------------------------------------------------------------ #

def test_get_weekly_totals_raises_not_implemented(tmp_path):
    provider, _ = _make_provider(tmp_path)

    with pytest.raises(NotImplementedError, match="no live gate consumer"):
        provider.get_weekly_totals("A1", date(2026, 1, 1))
