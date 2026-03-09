from __future__ import annotations

from datetime import date, datetime, timedelta

from .dependency_provider import KernelDependencyProvider
from .sqlite_audit_store import SqliteAuditStore as AuditStore
from .sqlite_operational_store import SqliteOperationalStore as OperationalStore
from .ral import WINDOW_SEMANTICS

# Fail-closed sentinel returned when athlete_id is not found in op_athletes.
# maxDailyContactLoad = 0.0 means any session with nonzero contact load fires
# SCM.MAXDAILYLOAD immediately. e4_clearance = False denies all E4 exercises.
_MISSING_ATHLETE_SENTINEL = {
    "maxDailyContactLoad": 0.0,
    "minimumRestIntervalHours": 24.0,
    "e4_clearance": False,
}

# Fail-closed sentinel returned when (athlete_id, season_id) is not found in op_seasons.
# competitionWeeks = 1 satisfies competition_weeks > 0.
# gppWeeks = 0 satisfies gpp_weeks <= 0.
# Both conditions are simultaneously true, so MACRO.PHASEMISMATCH fires immediately.
_MISSING_SEASON_SENTINEL = {
    "competitionWeeks": 1,
    "gppWeeks": 0,
}


class SqliteDependencyProvider(KernelDependencyProvider):
    """Production KernelDependencyProvider backed by OperationalStore and AuditStore.

    All operational data (athletes, sessions, seasons) is sourced from
    OperationalStore. Override history is sourced from AuditStore.

    There is no fallback to in-memory defaults. Missing records return
    fail-closed sentinels where applicable, raising violations immediately
    rather than silently passing gates.

    Inherits KernelDependencyProvider directly — no InMemoryDependencyProvider
    in the inheritance chain.
    """

    def __init__(self, operational_store: OperationalStore, audit_store: AuditStore):
        self.operational_store = operational_store
        self.audit_store = audit_store

    def get_athlete_profile(self, athlete_id: str) -> dict:
        """Return athlete profile keyed for gate consumption.

        Keys returned: maxDailyContactLoad, minimumRestIntervalHours, e4_clearance.
        Missing athlete returns the fail-closed sentinel (load cap = 0.0).
        """
        row = self.operational_store.get_athlete(athlete_id)
        if row is None:
            return dict(_MISSING_ATHLETE_SENTINEL)
        return {
            "maxDailyContactLoad": row["max_daily_contact_load"],
            "minimumRestIntervalHours": row["minimum_rest_interval_hours"],
            "e4_clearance": bool(row["e4_clearance"]),
        }

    def get_prior_session(self, athlete_id: str, before_date: datetime) -> dict | None:
        """Return the most recent session before before_date, or None.

        before_date is a datetime object (contract); converted to ISO 8601 string
        for the store query. Returns dict with sessionDate key as gates_scm.py
        reads via (prior or {}).get("sessionDate").
        """
        before_date_str = before_date.isoformat()
        row = self.operational_store.get_prior_session(athlete_id, before_date_str)
        if row is None:
            return None
        return {
            "sessionDate": row["session_date"],
            "sessionId": row["session_id"],
            "contactLoad": row["contact_load"],
        }

    def get_window_totals(
        self,
        athlete_id: str,
        window_type: str,
        anchor_date: date,
        exclude_session_id: str,
    ) -> dict:
        """Return totalContactLoad and dailyContactLoads for the rolling window.

        anchor_date is a date object (contract); window_days is read from
        RAL_SPEC RALWindowSemantics. Unknown window_type raises ValueError.
        Empty window returns the neutral shape — valid state, not a deny trigger.
        """
        semantics = WINDOW_SEMANTICS.get(window_type)
        if semantics is None:
            raise ValueError(f"Unknown window type: {window_type!r}")
        window_days = semantics["days"]

        # Build string boundaries. For the anchor upper bound, append end-of-day
        # time so that session datetime strings on the anchor date compare correctly
        # under lexicographic ISO 8601 ordering.
        anchor_date_str = anchor_date.isoformat() + "T23:59:59.999999+00:00"
        window_start_str = (anchor_date - timedelta(days=window_days)).isoformat()

        rows = self.operational_store.get_sessions_in_window(
            athlete_id,
            window_start=window_start_str,
            anchor_date=anchor_date_str,
            exclude_session_id=exclude_session_id,
        )
        daily_loads = [row["contact_load"] for row in rows]
        return {
            "totalContactLoad": sum(daily_loads) if daily_loads else 0.0,
            "dailyContactLoads": daily_loads,
        }

    def get_season_phases(self, athlete_id: str, season_id: str) -> dict:
        """Return competitionWeeks and gppWeeks for the season.

        Missing (athlete_id, season_id) returns the fail-closed sentinel,
        which fires MACRO.PHASEMISMATCH immediately.
        """
        row = self.operational_store.get_season(athlete_id, season_id)
        if row is None:
            return dict(_MISSING_SEASON_SENTINEL)
        return {
            "competitionWeeks": row["competition_weeks"],
            "gppWeeks": row["gpp_weeks"],
        }

    def get_override_history(
        self, lineage_key: str, module_id: str, window_days: int = 28
    ) -> dict:
        """Delegate to AuditStore. Returns byReasonCode and byViolationCode counts."""
        return self.audit_store.get_override_history(lineage_key, module_id, window_days)

    def get_readiness_history(
        self, athlete_id: str, anchor_date: date, window_days: int = 7
    ) -> list[str]:
        """Return readiness_state values for sessions in the rolling window."""
        anchor_date_str = anchor_date.isoformat() + "T23:59:59.999999+00:00"
        window_start_str = (anchor_date - timedelta(days=window_days)).isoformat()
        return self.operational_store.get_readiness_history(
            athlete_id, window_start_str, anchor_date_str
        )

    def get_collapse_count(
        self, athlete_id: str, anchor_date: date, window_days: int = 7
    ) -> int:
        """Return count of collapsed sessions in the rolling window."""
        anchor_date_str = anchor_date.isoformat() + "T23:59:59.999999+00:00"
        window_start_str = (anchor_date - timedelta(days=window_days)).isoformat()
        return self.operational_store.get_collapse_count(
            athlete_id, window_start_str, anchor_date_str
        )

    def get_weekly_totals(self, athlete_id: str, anchor_date: date) -> dict:
        """Not implemented — no live gate consumer exists for this method.

        Raises NotImplementedError explicitly rather than returning fake data.
        This method will be implemented when a gate requires it.
        """
        raise NotImplementedError(
            "get_weekly_totals has no live gate consumer and is not implemented. "
            "It will be implemented when a gate requires it. "
            "Do not call this method in the current runtime."
        )
