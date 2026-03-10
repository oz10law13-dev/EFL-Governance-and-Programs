from __future__ import annotations

import json
import sqlite3

import pytest

from efl_kernel import cli
from efl_kernel.kernel.kdo import KDOValidator
from efl_kernel.kernel.ral import RAL_SPEC


def _session_payload() -> dict:
    reg = RAL_SPEC["moduleRegistration"]["SESSION"]
    return {
        "moduleID": "SESSION",
        "moduleVersion": reg["moduleVersion"],
        "moduleViolationRegistryVersion": reg["moduleViolationRegistryVersion"],
        "registryHash": reg["registryHash"],
        "objectID": "obj-session-cli-test",
        "evaluationContext": {
            "athleteID": "ATH-CLI-001",
            "sessionID": "sess-cli-001",
            "sessionType": "RESISTANCE",
        },
        "windowContext": [
            {
                "windowType": "ROLLING7DAYS",
                "anchorDate": "2025-01-01",
                "startDate": "2024-12-25",
                "endDate": "2025-01-01",
                "timezone": "America/Chicago",
                "totalContactLoad": 0,
            },
            {
                "windowType": "ROLLING28DAYS",
                "anchorDate": "2025-01-01",
                "startDate": "2024-12-04",
                "endDate": "2025-01-01",
                "timezone": "America/Chicago",
                "totalContactLoad": 0,
            },
        ],
        "session": {},
    }


def _meso_payload() -> dict:
    reg = RAL_SPEC["moduleRegistration"]["MESO"]
    return {
        "moduleID": "MESO",
        "moduleVersion": reg["moduleVersion"],
        "moduleViolationRegistryVersion": reg["moduleViolationRegistryVersion"],
        "registryHash": reg["registryHash"],
        "objectID": "obj-meso-cli-test",
        "evaluationContext": {
            "athleteID": "ATH-CLI-001",
            "mesoID": "meso-cli-001",
        },
        "windowContext": [
            {
                "windowType": "MESOCYCLE",
                "anchorDate": "2025-01-01",
                "startDate": "2024-12-01",
                "endDate": "2025-01-31",
                "timezone": "America/Chicago",
                "totalContactLoad": 0,
            },
        ],
    }


def test_cli_session_clean_payload(tmp_path, capsys):
    payload_file = tmp_path / "session_payload.json"
    payload_file.write_text(json.dumps(_session_payload()), encoding="utf-8")
    db_path = str(tmp_path / "test_session.db")

    cli.main(["--module", "SESSION", "--input", str(payload_file), "--db", db_path])

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert "resolution" in result
    assert result["resolution"]["finalPublishState"] in KDOValidator.allowed_publish

    decision_hash = result["audit"]["decisionHash"]
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT decision_hash FROM kdo_log WHERE decision_hash = ?", (decision_hash,)
    ).fetchone()
    conn.close()
    assert row is not None


def test_cli_meso_clean_payload(tmp_path, capsys):
    payload_file = tmp_path / "meso_payload.json"
    payload_file.write_text(json.dumps(_meso_payload()), encoding="utf-8")
    db_path = str(tmp_path / "test_meso.db")

    cli.main(["--module", "MESO", "--input", str(payload_file), "--db", db_path])

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert "resolution" in result
    assert result["resolution"]["finalPublishState"] in KDOValidator.allowed_publish

    decision_hash = result["audit"]["decisionHash"]
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT decision_hash FROM kdo_log WHERE decision_hash = ?", (decision_hash,)
    ).fetchone()
    conn.close()
    assert row is not None


def test_cli_invalid_module_exits_1(tmp_path):
    payload_file = tmp_path / "dummy.json"
    payload_file.write_text("{}", encoding="utf-8")
    db_path = str(tmp_path / "test.db")

    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--module", "BOGUS", "--input", str(payload_file), "--db", db_path])
    assert exc_info.value.code == 1


def test_cli_missing_input_file_exits_1(tmp_path):
    db_path = str(tmp_path / "test.db")

    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--module", "SESSION", "--input", str(tmp_path / "nonexistent.json"), "--db", db_path])
    assert exc_info.value.code == 1


def test_cli_invalid_json_exits_1(tmp_path):
    bad_json_file = tmp_path / "bad.json"
    bad_json_file.write_text("this is not json{{{", encoding="utf-8")
    db_path = str(tmp_path / "test.db")

    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--module", "SESSION", "--input", str(bad_json_file), "--db", db_path])
    assert exc_info.value.code == 1


def _physique_payload(exercises=None) -> dict:
    reg = RAL_SPEC["moduleRegistration"]["PHYSIQUE"]
    return {
        "moduleVersion": reg["moduleVersion"],
        "moduleViolationRegistryVersion": reg["moduleViolationRegistryVersion"],
        "registryHash": reg["registryHash"],
        "objectID": "obj-physique-cli-test",
        "evaluationContext": {
            "athleteID": "ATH-CLI-PHY-001",
            "sessionID": "sess-physique-cli-001",
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
        "physique_session": {"exercises": exercises or []},
    }


def test_cli_physique_clean_payload(tmp_path, capsys):
    """PHYSIQUE CLI: non-E4 exercise, valid tempo → clean KDO, persisted to kdo_log."""
    payload_file = tmp_path / "physique_payload.json"
    payload_file.write_text(
        json.dumps(_physique_payload([{"exercise_id": "ECA-PHY-0001", "tempo": "3:0:1:0"}])),
        encoding="utf-8",
    )
    db_path = str(tmp_path / "test_physique.db")

    cli.main(["--module", "PHYSIQUE", "--input", str(payload_file), "--db", db_path])

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert "resolution" in result
    assert result["resolution"]["finalPublishState"] in KDOValidator.allowed_publish

    decision_hash = result["audit"]["decisionHash"]
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT decision_hash FROM kdo_log WHERE decision_hash = ?", (decision_hash,)
    ).fetchone()
    conn.close()
    assert row is not None


def test_cli_physique_clearance_violation(tmp_path, capsys):
    """PHYSIQUE CLI: ECA-PHY-0135 (e4_requires_clearance=True) + athlete e4_clearance=0 → PHYSIQUE.CLEARANCEMISSING."""
    from efl_kernel.kernel.operational_store import OperationalStore

    db_path = str(tmp_path / "test_physique_clearance.db")
    op = OperationalStore(db_path)
    op.upsert_athlete({
        "athlete_id": "ATH-CLI-PHY-002",
        "max_daily_contact_load": 200.0,
        "minimum_rest_interval_hours": 24.0,
        "e4_clearance": 0,
    })

    reg = RAL_SPEC["moduleRegistration"]["PHYSIQUE"]
    payload = {
        "moduleVersion": reg["moduleVersion"],
        "moduleViolationRegistryVersion": reg["moduleViolationRegistryVersion"],
        "registryHash": reg["registryHash"],
        "objectID": "obj-physique-clearance-cli",
        "evaluationContext": {
            "athleteID": "ATH-CLI-PHY-002",
            "sessionID": "sess-clearance-cli-001",
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
        "physique_session": {
            "exercises": [{"exercise_id": "ECA-PHY-0135", "tempo": "3:0:1:0"}]
        },
    }
    payload_file = tmp_path / "physique_clearance_payload.json"
    payload_file.write_text(json.dumps(payload), encoding="utf-8")

    cli.main(["--module", "PHYSIQUE", "--input", str(payload_file), "--db", db_path])

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    codes = [v["code"] for v in result.get("violations", [])]
    assert "PHYSIQUE.CLEARANCEMISSING" in codes
    assert result["resolution"]["finalPublishState"] == "ILLEGALQUARANTINED"
