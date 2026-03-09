"""Seed tool — writes athlete, session, and season records to the operational SQLite store.

Usage:
    python -m efl_kernel.tools.seed --fixture <path> [--db <path>]

This tool only inserts data. It does not call the kernel, evaluate sessions,
or generate programs. Its sole purpose is test-data insertion for Phase 12+.
"""
from __future__ import annotations

import argparse
import json
import sys

from efl_kernel.kernel.operational_store import OperationalStore

_ATHLETE_REQUIRED = {"athlete_id", "max_daily_contact_load", "minimum_rest_interval_hours", "e4_clearance"}
_SESSION_REQUIRED = {"session_id", "athlete_id", "session_date", "contact_load"}
_SEASON_REQUIRED = {"athlete_id", "season_id", "competition_weeks", "gpp_weeks", "start_date", "end_date"}


def _validate(records: list[dict], required: set[str], entity: str) -> None:
    for i, rec in enumerate(records):
        missing = required - rec.keys()
        if missing:
            raise ValueError(
                f"{entity}[{i}] is missing required fields: {sorted(missing)}"
            )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="EFL Kernel operational data seed tool")
    parser.add_argument("--fixture", required=True, help="Path to JSON fixture file")
    parser.add_argument(
        "--db", "--op-db",
        default="efl_audit.db",
        dest="db_path",
        help="Path to operational SQLite database to seed"
    )
    parser.add_argument(
        "--org-id",
        default="default",
        dest="org_id",
        help="Organization ID for tenant isolation (default: 'default')"
    )
    args = parser.parse_args(argv)

    # Load fixture
    try:
        with open(args.fixture, encoding="utf-8") as f:
            fixture = json.load(f)
    except FileNotFoundError:
        print(f"Error: fixture file not found: {args.fixture}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON in {args.fixture}: {exc}", file=sys.stderr)
        sys.exit(1)

    athletes = fixture.get("athletes", [])
    sessions = fixture.get("sessions", [])
    seasons = fixture.get("seasons", [])

    # Validate required fields before any DB writes
    try:
        _validate(athletes, _ATHLETE_REQUIRED, "athletes")
        _validate(sessions, _SESSION_REQUIRED, "sessions")
        _validate(seasons, _SEASON_REQUIRED, "seasons")
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    # Write to store
    try:
        store = OperationalStore(args.db_path)
        for athlete in athletes:
            store.upsert_athlete(athlete, org_id=args.org_id)
        for session in sessions:
            store.upsert_session(session, org_id=args.org_id)
        for season in seasons:
            store.upsert_season(season, org_id=args.org_id)
    except Exception as exc:
        print(f"Error: DB write failed: {exc}", file=sys.stderr)
        sys.exit(1)

    print(
        f"Seeded: {len(athletes)} athletes, {len(sessions)} sessions, "
        f"{len(seasons)} seasons → {args.db_path}"
    )


if __name__ == "__main__":
    main()
