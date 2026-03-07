from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from efl_kernel.kernel.ral import RAL_SPEC

REPO_ROOT = Path(__file__).resolve().parents[2]  # Prevent cwd-dependent ModuleNotFoundError in subprocess calls.
FIXTURE_PATH = REPO_ROOT / "efl_kernel" / "tools" / "fixtures" / "sample_seed.json"

SESSION_REG = RAL_SPEC["moduleRegistration"]["SESSION"]
MESO_REG = RAL_SPEC["moduleRegistration"]["MESO"]
MACRO_REG = RAL_SPEC["moduleRegistration"]["MACRO"]


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def _seed(db_path: Path) -> None:
    # PYTHONIOENCODING=utf-8: seed.py prints a → (U+2192) character; on Windows
    # the default console encoding (cp1252) cannot encode it. Setting this env
    # variable forces the subprocess stdout to UTF-8 without modifying seed.py.
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONPATH": str(REPO_ROOT)}
    result = subprocess.run(
        [sys.executable, "-m", "efl_kernel.tools.seed",
         "--db", str(db_path),
         "--fixture", str(FIXTURE_PATH)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, f"Seed failed:\n{result.stderr}"


def _run_cli(db_path: Path, module: str, payload_file: Path) -> dict:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONPATH": str(REPO_ROOT)}
    result = subprocess.run(
        [sys.executable, "-m", "efl_kernel.cli",
         "--module", module,
         "--input", str(payload_file),
         "--db", str(db_path)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, (
        f"CLI failed (module={module}):\n{result.stderr}"
    )
    return json.loads(result.stdout)


def _kdo_log_count(db_path: Path) -> int:
    conn = sqlite3.connect(str(db_path))
    count = conn.execute("SELECT COUNT(*) FROM kdo_log").fetchone()[0]
    conn.close()
    return count


# ------------------------------------------------------------------ #
# Smoke Test A — SESSION: CL.CLEARANCEMISSING                        #
# ------------------------------------------------------------------ #

def test_cli_session_cl_clearance(tmp_path):
    db_path = tmp_path / "test.db"
    _seed(db_path)

    # ATH001: e4_clearance=0 (False). isometric_mid_thigh_pull_max
    # requires E4 clearance → CL.CLEARANCEMISSING fires.
    # contactLoad=0 → SCM.MAXDAILYLOAD silent (cap=150).
    # sessionDate 2026-03-01 is 34 days after ATH001's last seeded
    # session (2026-01-26) → SCM.MINREST silent (min_rest=24h).
    payload = {
        "moduleVersion": SESSION_REG["moduleVersion"],
        "moduleViolationRegistryVersion": SESSION_REG["moduleViolationRegistryVersion"],
        "registryHash": SESSION_REG["registryHash"],
        "objectID": "SMOKE-S-001",
        "evaluationContext": {
            "athleteID": "ATH001",
            "sessionID": "SMOKE-S-001",
        },
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
        "session": {
            "sessionDate": "2026-03-01T10:00:00+00:00",
            "contactLoad": 0,
            "exercises": [{"exerciseID": "isometric_mid_thigh_pull_max"}],
        },
    }

    payload_file = tmp_path / "session_payload.json"
    payload_file.write_text(json.dumps(payload), encoding="utf-8")

    kdo = _run_cli(db_path, "SESSION", payload_file)

    violation_codes = [v["code"] for v in kdo["violations"]]
    assert "CL.CLEARANCEMISSING" in violation_codes
    assert any(v["moduleID"] == "SESSION" for v in kdo["violations"])
    assert _kdo_log_count(db_path) >= 1


# ------------------------------------------------------------------ #
# Smoke Test B — MESO: MESO.LOADIMBALANCE                            #
# ------------------------------------------------------------------ #

def test_cli_meso_loadimbalance(tmp_path):
    """Violation produced from ATH002 persisted session rows via SqliteDependencyProvider.
    No injected totals. Spike session contact_load drives the imbalance calculation.
    ATH002 sessions: [30, 35, 30, 150]. avg=61.25, max=150 > 122.5 → MESO.LOADIMBALANCE.
    anchorDate 2026-02-01 places ROLLING28DAYS window over 2026-01-04..2026-02-01,
    capturing all four ATH002 sessions (2026-01-05 through 2026-01-26).
    """
    db_path = tmp_path / "test.db"
    _seed(db_path)

    payload = {
        "moduleVersion": MESO_REG["moduleVersion"],
        "moduleViolationRegistryVersion": MESO_REG["moduleViolationRegistryVersion"],
        "registryHash": MESO_REG["registryHash"],
        "objectID": "SMOKE-MESO-OBJ-001",
        "evaluationContext": {
            "athleteID": "ATH002",
            "mesoID": "SMOKE-MESO-001",
        },
        "windowContext": [
            {
                "windowType": "MESOCYCLE",
                "anchorDate": "2026-02-01",
                "startDate": "2026-01-04",
                "endDate": "2026-02-01",
                "timezone": "UTC",
            },
        ],
    }

    payload_file = tmp_path / "meso_payload.json"
    payload_file.write_text(json.dumps(payload), encoding="utf-8")

    kdo = _run_cli(db_path, "MESO", payload_file)

    violation_codes = [v["code"] for v in kdo["violations"]]
    assert "MESO.LOADIMBALANCE" in violation_codes
    assert any(v["moduleID"] == "MESO" for v in kdo["violations"])
    assert _kdo_log_count(db_path) >= 1


# ------------------------------------------------------------------ #
# Smoke Test C — MACRO: MACRO.PHASEMISMATCH                          #
# ------------------------------------------------------------------ #

def test_cli_macro_phasemismatch(tmp_path):
    """Violation produced from ATH002 persisted season row.
    competition_weeks/gpp_weeks ratio exceeds threshold. Not a sentinel — real season row.
    ATH002 season SEASON-2026: competition_weeks=10, gpp_weeks=2 → ratio=5.0 > 2.0.
    """
    db_path = tmp_path / "test.db"
    _seed(db_path)

    payload = {
        "moduleVersion": MACRO_REG["moduleVersion"],
        "moduleViolationRegistryVersion": MACRO_REG["moduleViolationRegistryVersion"],
        "registryHash": MACRO_REG["registryHash"],
        "objectID": "SMOKE-MACRO-OBJ-001",
        "evaluationContext": {
            "athleteID": "ATH002",
            "seasonID": "SEASON-2026",
        },
        "windowContext": [
            {
                "windowType": "SEASON",
                "anchorDate": "2026-12-31",
                "startDate": "2026-01-01",
                "endDate": "2026-12-31",
                "timezone": "UTC",
            },
        ],
    }

    payload_file = tmp_path / "macro_payload.json"
    payload_file.write_text(json.dumps(payload), encoding="utf-8")

    kdo = _run_cli(db_path, "MACRO", payload_file)

    violation_codes = [v["code"] for v in kdo["violations"]]
    assert "MACRO.PHASEMISMATCH" in violation_codes
    assert any(v["moduleID"] == "MACRO" for v in kdo["violations"])
    assert _kdo_log_count(db_path) >= 1


# ------------------------------------------------------------------ #
# kdo_log increment check                                             #
# ------------------------------------------------------------------ #

def test_kdo_log_increments_across_evaluations(tmp_path):
    """Proves AuditStore appends, not overwrites.
    Two evaluations with different objectIDs produce different decision hashes
    and therefore two distinct rows in kdo_log.
    """
    db_path = tmp_path / "test.db"
    _seed(db_path)

    base = {
        "moduleVersion": MACRO_REG["moduleVersion"],
        "moduleViolationRegistryVersion": MACRO_REG["moduleViolationRegistryVersion"],
        "registryHash": MACRO_REG["registryHash"],
        "evaluationContext": {
            "athleteID": "ATH002",
            "seasonID": "SEASON-2026",
        },
        "windowContext": [
            {
                "windowType": "SEASON",
                "anchorDate": "2026-12-31",
                "startDate": "2026-01-01",
                "endDate": "2026-12-31",
                "timezone": "UTC",
            },
        ],
    }

    payload_1 = {**base, "objectID": "SMOKE-MACRO-INC-001"}
    payload_file_1 = tmp_path / "macro_inc_1.json"
    payload_file_1.write_text(json.dumps(payload_1), encoding="utf-8")
    _run_cli(db_path, "MACRO", payload_file_1)
    assert _kdo_log_count(db_path) == 1

    payload_2 = {**base, "objectID": "SMOKE-MACRO-INC-002"}
    payload_file_2 = tmp_path / "macro_inc_2.json"
    payload_file_2.write_text(json.dumps(payload_2), encoding="utf-8")
    _run_cli(db_path, "MACRO", payload_file_2)
    assert _kdo_log_count(db_path) == 2


# ------------------------------------------------------------------ #
# Import stability check                                              #
# ------------------------------------------------------------------ #

def test_cli_runs_from_non_repo_cwd(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir()
    monkeypatch.chdir(outside_cwd)

    _seed(db_path)

    payload = {
        "moduleVersion": MACRO_REG["moduleVersion"],
        "moduleViolationRegistryVersion": MACRO_REG["moduleViolationRegistryVersion"],
        "registryHash": MACRO_REG["registryHash"],
        "objectID": "SMOKE-MACRO-CWD-001",
        "evaluationContext": {
            "athleteID": "ATH002",
            "seasonID": "SEASON-2026",
        },
        "windowContext": [
            {
                "windowType": "SEASON",
                "anchorDate": "2026-12-31",
                "startDate": "2026-01-01",
                "endDate": "2026-12-31",
                "timezone": "UTC",
            },
        ],
    }

    payload_file = tmp_path / "macro_cwd_payload.json"
    payload_file.write_text(json.dumps(payload), encoding="utf-8")

    kdo = _run_cli(db_path, "MACRO", payload_file)
    violation_codes = [v["code"] for v in kdo["violations"]]
    assert "MACRO.PHASEMISMATCH" in violation_codes
