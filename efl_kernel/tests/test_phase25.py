"""Phase 25 — Governed Spec Bump CLI tests.

16 tests always run. No PG-gated tests in this phase.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from efl_kernel.kernel.ral import canonicalize_and_hash


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_module_spec(tmp_path, name="TESTMOD", version="1.0.0",
                      filename=None, corrupt_doc=False, corrupt_reg=False):
    """Create a minimal module spec with violationRegistry + documentHash."""
    spec = {
        "moduleID": name,
        "version": version,
        "moduleVersion": version,
        "moduleViolationRegistryVersion": version,
        "documentHash": "",
        "violationRegistry": {
            "registryHash": "",
            "violations": [
                {
                    "moduleID": name,
                    "code": f"{name}.CODE1",
                    "severity": "WARNING",
                    "overridePossible": False,
                    "allowedOverrideReasonCodes": [],
                    "violationCap": None,
                    "reviewOverrideThreshold28D": None,
                }
            ],
        },
    }
    # Compute valid hashes
    vr = spec["violationRegistry"]
    vr["registryHash"] = ""
    vr["registryHash"] = canonicalize_and_hash(vr)
    spec["documentHash"] = canonicalize_and_hash(spec, "documentHash")

    if corrupt_doc:
        spec["documentHash"] = "0" * 64
    if corrupt_reg:
        spec["violationRegistry"]["registryHash"] = "0" * 64

    fname = filename or f"EFL_{name}_v{'_'.join(version.split('.'))}_frozen.json"
    path = tmp_path / fname
    path.write_text(json.dumps(spec, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return path, spec


def _make_ral_like_spec(tmp_path):
    """Spec with documentHash but no violationRegistry."""
    spec = {
        "specID": "RAL_LIKE",
        "version": "1.0.0",
        "documentHash": "",
        "someData": {"key": "value"},
    }
    spec["documentHash"] = canonicalize_and_hash(spec, "documentHash")
    path = tmp_path / "EFL_RAL_LIKE_v1_0_0_frozen.json"
    path.write_text(json.dumps(spec, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return path, spec


def _make_cl_like_spec(tmp_path):
    """Spec with CLVIOLATIONREGISTRY instead of violationRegistry."""
    spec = {
        "moduleID": "CL_LIKE",
        "version": "1.0.0",
        "documentHash": "",
        "CLVIOLATIONREGISTRY": {
            "registryHash": "",
            "violations": [
                {
                    "moduleID": "CL_LIKE",
                    "code": "CL.TEST",
                    "severity": "WARNING",
                    "overridePossible": False,
                    "allowedOverrideReasonCodes": [],
                    "violationCap": None,
                    "reviewOverrideThreshold28D": None,
                }
            ],
        },
    }
    cl = spec["CLVIOLATIONREGISTRY"]
    cl["registryHash"] = ""
    cl["registryHash"] = canonicalize_and_hash(cl)
    spec["documentHash"] = canonicalize_and_hash(spec, "documentHash")
    path = tmp_path / "EFL_CL_LIKE_v1_0_0_frozen.json"
    path.write_text(json.dumps(spec, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return path, spec


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRehash:
    def test_rehash_module_spec(self, tmp_path):
        """Create spec with wrong hashes, rehash, verify hashes are now correct."""
        from efl_kernel.tools.spec_bump import cmd_rehash, cmd_verify

        path, _ = _make_module_spec(tmp_path, corrupt_doc=True, corrupt_reg=True)

        class Args:
            spec = str(path)
            force = True

        assert cmd_rehash(Args()) == 0

        class VerifyArgs:
            spec = str(path)

        assert cmd_verify(VerifyArgs()) == 0

    def test_rehash_ral_like_spec(self, tmp_path):
        """Spec with documentHash but no violationRegistry."""
        from efl_kernel.tools.spec_bump import cmd_rehash, cmd_verify

        path, spec = _make_ral_like_spec(tmp_path)
        # Corrupt the documentHash
        spec["documentHash"] = "0" * 64
        path.write_text(json.dumps(spec, sort_keys=True, indent=2) + "\n", encoding="utf-8")

        class Args:
            spec = str(path)
            force = True

        assert cmd_rehash(Args()) == 0

        class VerifyArgs:
            spec = str(path)

        assert cmd_verify(VerifyArgs()) == 0

    def test_rehash_cl_like_spec(self, tmp_path):
        """Spec with CLVIOLATIONREGISTRY."""
        from efl_kernel.tools.spec_bump import cmd_rehash, cmd_verify

        path, spec = _make_cl_like_spec(tmp_path)
        # Corrupt both hashes
        spec["CLVIOLATIONREGISTRY"]["registryHash"] = "0" * 64
        spec["documentHash"] = "0" * 64
        path.write_text(json.dumps(spec, sort_keys=True, indent=2) + "\n", encoding="utf-8")

        class Args:
            spec = str(path)
            force = True

        assert cmd_rehash(Args()) == 0

        class VerifyArgs:
            spec = str(path)

        assert cmd_verify(VerifyArgs()) == 0

    def test_rehash_order_registry_before_document(self, tmp_path):
        """registryHash must be computed before documentHash."""
        from efl_kernel.tools.spec_bump import cmd_rehash

        path, _ = _make_module_spec(tmp_path, name="ORDERTEST",
                                     corrupt_doc=True, corrupt_reg=True)

        class Args:
            spec = str(path)
            force = True

        cmd_rehash(Args())

        result = json.loads(path.read_text(encoding="utf-8"))

        # registryHash verifies independently
        vr = copy.deepcopy(result["violationRegistry"])
        rh = vr["registryHash"]
        vr["registryHash"] = ""
        assert canonicalize_and_hash(vr) == rh

        # documentHash verifies independently (covers the registryHash value)
        assert canonicalize_and_hash(result, "documentHash") == result["documentHash"]

    def test_rehash_warns_existing_without_force(self, tmp_path):
        """Overwrite in specs dir without --force returns exit code 1."""
        from efl_kernel.tools.spec_bump import cmd_rehash

        # Create a spec with wrong hashes directly in the real specs dir
        # We'll use a temp dir that we pretend is the specs dir
        # Actually, we need to test the safety check — create a file in
        # a directory that matches specs_dir resolution
        specs_dir = Path(__file__).resolve().parent.parent / "specs"
        # Create a temp spec in the real specs dir (we'll clean up)
        test_path = specs_dir / "_TEST_TEMP_v1_0_0_frozen.json"
        try:
            spec = {"documentHash": "wrong", "testKey": True}
            test_path.write_text(json.dumps(spec) + "\n", encoding="utf-8")

            class Args:
                spec = str(test_path)
                force = False

            result = cmd_rehash(Args())
            assert result == 1  # Should warn and refuse
        finally:
            if test_path.exists():
                test_path.unlink()


class TestVerify:
    def test_verify_valid_spec_passes(self, tmp_path):
        from efl_kernel.tools.spec_bump import cmd_verify

        path, _ = _make_module_spec(tmp_path)

        class Args:
            spec = str(path)

        assert cmd_verify(Args()) == 0

    def test_verify_corrupt_documenthash_fails(self, tmp_path):
        from efl_kernel.tools.spec_bump import cmd_verify

        path, _ = _make_module_spec(tmp_path, corrupt_doc=True)

        class Args:
            spec = str(path)

        assert cmd_verify(Args()) == 1

    def test_verify_corrupt_registryhash_fails(self, tmp_path):
        from efl_kernel.tools.spec_bump import cmd_verify

        path, _ = _make_module_spec(tmp_path, corrupt_reg=True)

        class Args:
            spec = str(path)

        assert cmd_verify(Args()) == 1


class TestNewVersion:
    def test_new_version_creates_file(self, tmp_path):
        from efl_kernel.tools.spec_bump import cmd_new_version

        path, _ = _make_module_spec(tmp_path)

        class Args:
            source = str(path)
            version = "1.0.1"

        assert cmd_new_version(Args()) == 0
        new_path = tmp_path / "EFL_TESTMOD_v1_0_1_frozen.json"
        assert new_path.exists()

    def test_new_version_bumps_version_fields(self, tmp_path):
        from efl_kernel.tools.spec_bump import cmd_new_version

        path, _ = _make_module_spec(tmp_path)

        class Args:
            source = str(path)
            version = "2.0.0"

        cmd_new_version(Args())
        new_path = tmp_path / "EFL_TESTMOD_v2_0_0_frozen.json"
        new_spec = json.loads(new_path.read_text(encoding="utf-8"))
        assert new_spec["version"] == "2.0.0"
        assert new_spec["moduleVersion"] == "2.0.0"
        assert new_spec["moduleViolationRegistryVersion"] == "2.0.0"

    def test_new_version_hashes_valid(self, tmp_path):
        from efl_kernel.tools.spec_bump import cmd_new_version, cmd_verify

        path, _ = _make_module_spec(tmp_path)

        class Args:
            source = str(path)
            version = "1.1.0"

        cmd_new_version(Args())
        new_path = tmp_path / "EFL_TESTMOD_v1_1_0_frozen.json"

        class VerifyArgs:
            spec = str(new_path)

        assert cmd_verify(VerifyArgs()) == 0

    def test_new_version_preserves_violations(self, tmp_path):
        from efl_kernel.tools.spec_bump import cmd_new_version

        path, original = _make_module_spec(tmp_path)

        class Args:
            source = str(path)
            version = "1.0.1"

        cmd_new_version(Args())
        new_path = tmp_path / "EFL_TESTMOD_v1_0_1_frozen.json"
        new_spec = json.loads(new_path.read_text(encoding="utf-8"))
        assert (new_spec["violationRegistry"]["violations"]
                == original["violationRegistry"]["violations"])

    def test_new_version_does_not_modify_source(self, tmp_path):
        from efl_kernel.tools.spec_bump import cmd_new_version

        path, _ = _make_module_spec(tmp_path)
        source_before = path.read_bytes()

        class Args:
            source = str(path)
            version = "1.0.1"

        cmd_new_version(Args())
        assert path.read_bytes() == source_before


class TestCheckAll:
    def test_check_all_passes_on_real_specs(self):
        """All current frozen specs verify."""
        from efl_kernel.tools.spec_bump import cmd_check_all

        class Args:
            specs_dir = None  # defaults to efl_kernel/specs/

        assert cmd_check_all(Args()) == 0


class TestShowRegistration:
    def test_show_registration_output(self, tmp_path, capsys):
        from efl_kernel.tools.spec_bump import cmd_show_registration

        path, _ = _make_module_spec(tmp_path)

        class Args:
            spec = str(path)

        assert cmd_show_registration(Args()) == 0
        output = capsys.readouterr().out
        assert '"TESTMOD"' in output
        assert '"moduleVersion"' in output
        assert '"registryHash"' in output


class TestCLI:
    def test_cli_help_runs(self):
        result = subprocess.run(
            [sys.executable, "-m", "efl_kernel.tools.spec_bump", "--help"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "spec_bump" in result.stdout.lower() or "spec" in result.stdout.lower()
