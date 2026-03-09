from __future__ import annotations

from datetime import date, datetime, timedelta

from .dependency_provider import KernelDependencyProvider
from .pg_audit_store import PgAuditStore
from .pg_operational_store import PgOperationalStore
from .ral import WINDOW_SEMANTICS

# Fail-closed sentinels — identical to SqliteDependencyProvider.
_MISSING_ATHLETE_SENTINEL = {
    "maxDailyContactLoad": 0.0,
    "minimumRestIntervalHours": 24.0,
    "e4_clearance": False,
}
_MISSING_SEASON_SENTINEL = {
    "competitionWeeks": 1,
    "gppWeeks": 0,
}


class PgDependencyProvider(KernelDependencyProvider):
    """Production KernelDependencyProvider backed by PgOperationalStore and PgAuditStore.

    Same interface and fail-closed sentinel behaviour as SqliteDependencyProvider.
    """

    def __init__(self, operational_store: PgOperationalStore, audit_store: PgAuditStore):
        self.operational_store = operational_store
        self.audit_store = audit_store

    def get_athlete_profile(self, athlete_id: str) -> dict:
        row = self.operational_store.get_athlete(athlete_id)
        if row is None:
            return dict(_MISSING_ATHLETE_SENTINEL)
        return {
            "maxDailyContactLoad": row["max_daily_contact_load"],
            "minimumRestIntervalHours": row["minimum_rest_interval_hours"],
            "e4_clearance": bool(row["e4_clearance"]),
        }

    def get_prior_session(self, athlete_id: str, before_date: datetime) -> dict | None:
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
        semantics = WINDOW_SEMANTICS.get(window_type)
        if semantics is None:
            raise ValueError(f"Unknown window type: {window_type!r}")
        window_days = semantics["days"]

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
        return self.audit_store.get_override_history(lineage_key, module_id, window_days)

    def get_readiness_history(
        self, athlete_id: str, anchor_date: date, window_days: int = 7
    ) -> list[str]:
        anchor_date_str = anchor_date.isoformat() + "T23:59:59.999999+00:00"
        window_start_str = (anchor_date - timedelta(days=window_days)).isoformat()
        return self.operational_store.get_readiness_history(
            athlete_id, window_start_str, anchor_date_str
        )

    def get_collapse_count(
        self, athlete_id: str, anchor_date: date, window_days: int = 7
    ) -> int:
        anchor_date_str = anchor_date.isoformat() + "T23:59:59.999999+00:00"
        window_start_str = (anchor_date - timedelta(days=window_days)).isoformat()
        return self.operational_store.get_collapse_count(
            athlete_id, window_start_str, anchor_date_str
        )

    def get_weekly_totals(self, athlete_id: str, anchor_date: date) -> dict:
        raise NotImplementedError(
            "get_weekly_totals has no live gate consumer and is not implemented. "
            "It will be implemented when a gate requires it. "
            "Do not call this method in the current runtime."
        )
