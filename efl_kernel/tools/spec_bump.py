"""EFL Kernel — Governed Spec Bump CLI tool.

Subcommands:
    rehash           — Recompute and stamp all hashes in a spec file.
    verify           — Verify all hashes in a spec file without modifying.
    new-version      — Copy spec to new version, bump version fields, rehash.
    check-all        — Verify every spec in the specs directory.
    show-registration — Print the moduleRegistration entry for RAL.

Usage:
    python -m efl_kernel.tools.spec_bump rehash --spec <path> [--force]
    python -m efl_kernel.tools.spec_bump verify --spec <path>
    python -m efl_kernel.tools.spec_bump new-version --source <path> --version <semver>
    python -m efl_kernel.tools.spec_bump check-all [--specs-dir <path>]
    python -m efl_kernel.tools.spec_bump show-registration --spec <path>
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

from efl_kernel.kernel.ral import canonicalize_and_hash


def cmd_rehash(args):
    """Recompute and stamp all hashes in a spec file."""
    path = Path(args.spec)
    if not path.exists():
        print(f"ERROR: {path} not found")
        return 1

    spec = json.loads(path.read_text(encoding="utf-8"))
    changed = False

    # --- registryHash FIRST (documentHash covers it) ---

    # Standard module violation registry
    vr = spec.get("violationRegistry")
    if isinstance(vr, dict) and "registryHash" in vr:
        old = vr["registryHash"]
        vr["registryHash"] = ""
        new = canonicalize_and_hash(vr)
        vr["registryHash"] = new
        print(f"  violationRegistry.registryHash: {old[:16]}... -> {new[:16]}...")
        if old != new:
            changed = True

    # CL-specific violation registry
    cl = spec.get("CLVIOLATIONREGISTRY")
    if isinstance(cl, dict) and "registryHash" in cl:
        old = cl["registryHash"]
        cl["registryHash"] = ""
        new = canonicalize_and_hash(cl)
        cl["registryHash"] = new
        print(f"  CLVIOLATIONREGISTRY.registryHash: {old[:16]}... -> {new[:16]}...")
        if old != new:
            changed = True

    # --- documentHash SECOND ---
    if "documentHash" in spec:
        old = spec["documentHash"]
        new = canonicalize_and_hash(spec, "documentHash")
        spec["documentHash"] = new
        print(f"  documentHash: {old[:16]}... -> {new[:16]}...")
        if old != new:
            changed = True

    if not changed:
        print("All hashes already correct. No changes needed.")
        return 0

    # Safety check: warn if overwriting existing frozen spec without --force
    specs_dir = Path(__file__).resolve().parent.parent / "specs"
    if path.resolve().parent == specs_dir.resolve():
        if not getattr(args, "force", False):
            print(f"WARNING: {path.name} is in the specs directory.")
            print("Frozen specs should not be modified in place (CLAUDE.md Rule 3).")
            print("Use --force to override this warning.")
            return 1

    output = json.dumps(spec, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    path.write_text(output, encoding="utf-8")
    print(f"Wrote: {path}")
    return 0


def cmd_verify(args):
    """Check all hashes in a spec file without modifying."""
    path = Path(args.spec)
    if not path.exists():
        print(f"ERROR: {path} not found")
        return 1

    spec = json.loads(path.read_text(encoding="utf-8"))
    ok = True

    vr = spec.get("violationRegistry")
    if isinstance(vr, dict) and "registryHash" in vr:
        expected = vr["registryHash"]
        check = copy.deepcopy(vr)
        check["registryHash"] = ""
        computed = canonicalize_and_hash(check)
        status = "PASS" if computed == expected else "FAIL"
        if status == "FAIL":
            ok = False
        print(f"  violationRegistry.registryHash: {status}")

    cl = spec.get("CLVIOLATIONREGISTRY")
    if isinstance(cl, dict) and "registryHash" in cl:
        expected = cl["registryHash"]
        check = copy.deepcopy(cl)
        check["registryHash"] = ""
        computed = canonicalize_and_hash(check)
        status = "PASS" if computed == expected else "FAIL"
        if status == "FAIL":
            ok = False
        print(f"  CLVIOLATIONREGISTRY.registryHash: {status}")

    if "documentHash" in spec:
        expected = spec["documentHash"]
        computed = canonicalize_and_hash(spec, "documentHash")
        status = "PASS" if computed == expected else "FAIL"
        if status == "FAIL":
            ok = False
        print(f"  documentHash: {status}")

    return 0 if ok else 1


def cmd_new_version(args):
    """Copy spec to new version, bump version fields, rehash."""
    source = Path(args.source)
    if not source.exists():
        print(f"ERROR: {source} not found")
        return 1

    spec = json.loads(source.read_text(encoding="utf-8"))
    new_ver = args.version
    parts = new_ver.split(".")
    if len(parts) != 3:
        print("ERROR: --version must be MAJOR.MINOR.PATCH (e.g., 1.0.5)")
        return 1

    # Derive new filename from source
    match = re.match(r"^(.+)_v(\d+)_(\d+)_(\d+)(_frozen)?\.json$", source.name)
    if not match:
        print(f"ERROR: Cannot parse version from filename: {source.name}")
        return 1
    prefix = match.group(1)
    suffix = match.group(5) or ""
    new_filename = f"{prefix}_v{'_'.join(parts)}{suffix}.json"
    new_path = source.parent / new_filename

    if new_path.exists():
        print(f"ERROR: {new_path} already exists. Remove it first or choose a different version.")
        return 1

    # Preserve source bytes for safety
    source_bytes = source.read_bytes()

    # Bump version fields
    old_ver = spec.get("version", spec.get("moduleVersion", ""))
    if "version" in spec:
        spec["version"] = new_ver
    if "moduleVersion" in spec:
        spec["moduleVersion"] = new_ver
    if "moduleViolationRegistryVersion" in spec:
        spec["moduleViolationRegistryVersion"] = new_ver

    # Rehash (registry first, then document)
    vr = spec.get("violationRegistry")
    if isinstance(vr, dict) and "registryHash" in vr:
        vr["registryHash"] = ""
        vr["registryHash"] = canonicalize_and_hash(vr)

    cl = spec.get("CLVIOLATIONREGISTRY")
    if isinstance(cl, dict) and "registryHash" in cl:
        cl["registryHash"] = ""
        cl["registryHash"] = canonicalize_and_hash(cl)

    if "documentHash" in spec:
        spec["documentHash"] = canonicalize_and_hash(spec, "documentHash")

    # Write new file
    output = json.dumps(spec, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    new_path.write_text(output, encoding="utf-8")
    print(f"Created: {new_path}")
    print(f"Version: {old_ver} -> {new_ver}")

    # Verify source was not modified
    assert source.read_bytes() == source_bytes, "Source file was modified!"

    # Print registration snippet
    module_id = spec.get("moduleID")
    if module_id and vr and "registryHash" in vr:
        print(f"\nUpdate RAL moduleRegistration for {module_id}:")
        print(f'  "moduleVersion": "{new_ver}",')
        print(f'  "moduleViolationRegistryVersion": "{new_ver}",')
        print(f'  "registryHash": "{vr["registryHash"]}"')

    return 0


def cmd_check_all(args):
    """Verify every spec in the specs directory."""
    specs_dir = Path(args.specs_dir) if args.specs_dir else (
        Path(__file__).resolve().parent.parent / "specs"
    )
    files = sorted(specs_dir.glob("*_frozen.json"))
    if not files:
        print(f"No frozen spec files found in {specs_dir}")
        return 1

    total = 0
    passed = 0
    failed = 0
    for f in files:
        print(f"{f.name}:")

        class FakeArgs:
            spec = str(f)

        result = cmd_verify(FakeArgs())
        total += 1
        if result == 0:
            passed += 1
        else:
            failed += 1

    print(f"\n{total} files checked. {passed} passed, {failed} failed.")
    return 0 if failed == 0 else 1


def cmd_show_registration(args):
    """Print the moduleRegistration entry for RAL."""
    path = Path(args.spec)
    if not path.exists():
        print(f"ERROR: {path} not found")
        return 1

    spec = json.loads(path.read_text(encoding="utf-8"))

    module_id = spec.get("moduleID") or spec.get("specID", "UNKNOWN")
    version = spec.get("moduleVersion") or spec.get("version", "UNKNOWN")
    vr_version = spec.get("moduleViolationRegistryVersion") or version

    registry_hash = None
    vr = spec.get("violationRegistry")
    if isinstance(vr, dict):
        registry_hash = vr.get("registryHash")
    cl = spec.get("CLVIOLATIONREGISTRY")
    if isinstance(cl, dict) and registry_hash is None:
        registry_hash = cl.get("registryHash")

    print(f'"{module_id}": {{')
    print(f'  "moduleVersion": "{version}",')
    print(f'  "moduleViolationRegistryVersion": "{vr_version}",')
    print(f'  "registryHash": "{registry_hash or "N/A"}"')
    print("}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="EFL Kernel — Governed Spec Bump CLI",
    )
    sub = parser.add_subparsers(dest="command")

    # rehash
    p_rehash = sub.add_parser("rehash", help="Recompute and stamp all hashes")
    p_rehash.add_argument("--spec", required=True, help="Path to spec file")
    p_rehash.add_argument("--force", action="store_true",
                          help="Allow overwriting existing frozen spec")

    # verify
    p_verify = sub.add_parser("verify", help="Check hashes without modifying")
    p_verify.add_argument("--spec", required=True, help="Path to spec file")

    # new-version
    p_new = sub.add_parser("new-version", help="Copy to new version + rehash")
    p_new.add_argument("--source", required=True, help="Source spec file")
    p_new.add_argument("--version", required=True, help="New version (MAJOR.MINOR.PATCH)")

    # check-all
    p_all = sub.add_parser("check-all", help="Verify all specs in directory")
    p_all.add_argument("--specs-dir", default=None, help="Specs directory path")

    # show-registration
    p_reg = sub.add_parser("show-registration", help="Print RAL registration entry")
    p_reg.add_argument("--spec", required=True, help="Path to spec file")

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return 1

    dispatch = {
        "rehash": cmd_rehash,
        "verify": cmd_verify,
        "new-version": cmd_new_version,
        "check-all": cmd_check_all,
        "show-registration": cmd_show_registration,
    }
    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
