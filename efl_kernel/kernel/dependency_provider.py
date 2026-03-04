from __future__ import annotations

from datetime import date, datetime


class KernelDependencyProvider:
    def get_window_totals(self, athlete_id: str, window_type: str, anchor_date: date, exclude_session_id: str) -> dict:
        raise NotImplementedError

    def get_weekly_totals(self, athlete_id: str, anchor_date: date) -> dict:
        raise NotImplementedError

    def get_prior_session(self, athlete_id: str, before_date: datetime) -> dict | None:
        raise NotImplementedError

    def get_season_phases(self, athlete_id: str, season_id: str) -> dict:
        raise NotImplementedError

    def get_override_history(self, lineage_key: str, module_id: str, window_days: int = 28) -> dict:
        raise NotImplementedError

    def get_athlete_profile(self, athlete_id: str) -> dict:
        raise NotImplementedError


class InMemoryDependencyProvider(KernelDependencyProvider):
    def __init__(self, **datasets):
        self.datasets = datasets

    def get_window_totals(self, athlete_id: str, window_type: str, anchor_date: date, exclude_session_id: str) -> dict:
        return self.datasets.get("window_totals", {}).get((athlete_id, window_type), {"totalContactLoad": 0.0, "dailyContactLoads": []})

    def get_weekly_totals(self, athlete_id: str, anchor_date: date) -> dict:
        return self.datasets.get("weekly_totals", {}).get(
            athlete_id,
            {f"week{i}": {"totalContactLoad": 0.0} for i in [1, 2, 3, 4]},
        )

    def get_prior_session(self, athlete_id: str, before_date: datetime) -> dict | None:
        return self.datasets.get("prior_session", {}).get(athlete_id)

    def get_season_phases(self, athlete_id: str, season_id: str) -> dict:
        return self.datasets.get("season_phases", {}).get((athlete_id, season_id), {"competitionWeeks": 0, "gppWeeks": 0})

    def get_override_history(self, lineage_key: str, module_id: str, window_days: int = 28) -> dict:
        return self.datasets.get("override_history", {}).get(
            (lineage_key, module_id, window_days),
            {"byReasonCode": {}, "byViolationCode": {}},
        )

    def get_athlete_profile(self, athlete_id: str) -> dict:
        return self.datasets.get("athlete_profile", {}).get(athlete_id, {})
