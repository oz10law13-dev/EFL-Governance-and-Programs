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
