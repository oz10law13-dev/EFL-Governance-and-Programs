from __future__ import annotations

import json
from pathlib import Path

from efl_kernel.kernel.ral import canonicalize_and_hash

SPECS_DIR = Path(__file__).resolve().parent.parent / "specs"


def test_all_frozen_spec_hashes_are_valid():
    spec_files = sorted(SPECS_DIR.glob("*.json"))
    assert spec_files, f"No spec files found in {SPECS_DIR}"

    checked = 0
    for path in spec_files:
        doc = json.loads(path.read_text(encoding="utf-8"))

        if not isinstance(doc, dict):
            continue

        if "documentHash" in doc:
            expected = doc["documentHash"]
            computed = canonicalize_and_hash(doc, "documentHash")
            assert computed == expected, (
                f"{path.name}: documentHash mismatch.\n"
                f"  stored:   {expected}\n"
                f"  computed: {computed}"
            )
            checked += 1

        vr = doc.get("violationRegistry")
        if isinstance(vr, dict) and "registryHash" in vr:
            expected = vr["registryHash"]
            computed = canonicalize_and_hash(vr, "registryHash")
            assert computed == expected, (
                f"{path.name}: violationRegistry.registryHash mismatch.\n"
                f"  stored:   {expected}\n"
                f"  computed: {computed}"
            )
            checked += 1

    assert checked >= 4, f"Expected at least 4 hash checks across spec files, got {checked} — check SPECS_DIR path"
