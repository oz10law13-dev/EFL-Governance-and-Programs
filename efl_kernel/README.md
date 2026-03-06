# EFL Compliance Kernel

Reference implementation of the EFL compliance kernel with frozen JSON specs, a deterministic rule layer, and tests.

## Run tests

```bash
cd <repo-root>
pytest -q
```

## What is covered

- End-to-end kernel flow tests across step 0–10 guard rails.
- Happy-path KDO validation and decision hash freezing.
- Helper derivations for severity, publish state, lineage keys, canonical hashing, and override caps.
- Registry coverage marker validation.
- Override cap enforcement (OC-001): reason-code cap and violation-code cap checks across 28-day windows (step 9).
- REVIEW-OVERRIDE-CLUSTER overlay: upgrades `LEGALREADY`/`LEGALOVERRIDE` to `REQUIRESREVIEW` when override thresholds are met (step 10).

## Evaluation pipeline steps

| Step | Guard / Action |
|------|---------------|
| 0 | Module registration check — unknown module → `RAL.MODULEREGISTRATIONINCOMPLETE` |
| 1 | Required fields + version/hash match → `RAL.MISSINGORUNDEFINEDREQUIREDSTATE` or `RAL.MODULEREGISTRYMISMATCH` |
| 2 | Window entry shape validation → `RAL.MALFORMEDWINDOWENTRY` |
| 3 | Required window types present → `RAL.MISSINGREQUIREDWINDOW` |
| 4 | Lineage context fields present → `RAL.MISSINGLINEAGECONTEXT` |
| 5 | Lineage key derivation |
| 6 | Module gate dispatch (SESSION → SCM + CL, MESO, MACRO, GOVERNANCE) |
| 7 | Kernel-owned field enforcement + unregistered code detection → `RAL.UNREGISTEREDVIOLATIONCODE` |
| 8 | Module ID cross-check → `RAL.MODULEKDOMODULEIDMISMATCH` |
| 9 | Override cap enforcement (OC-001/OC-002a/OC-002b) → `RAL.OVERRIDEREASONCAPBREACH` / `RAL.OVERRIDEVIOLATIONCAPBREACH` |
| 10 | REVIEW-OVERRIDE-CLUSTER overlay → upgrades publish state to `REQUIRESREVIEW` |

## Publish states

| State | Meaning |
|-------|---------|
| `LEGALREADY` | No violations — safe to publish |
| `LEGALOVERRIDE` | Violations present but valid override applied |
| `REQUIRESREVIEW` | Override threshold hit — manual review required |
| `BLOCKED` | Hard-fail violation — cannot publish |
| `ILLEGALQUARANTINED` | Structural/integrity failure — quarantined |

## Gap status

| Gap | Description | Status |
|-----|-------------|--------|
| GAP-001 | Registry hash verification at import | ✅ Closed |
| GAP-004 | Override cap enforcement (step 9) | ✅ Closed |
| GAP-007 | REVIEW-OVERRIDE-CLUSTER overlay (step 10) | ✅ Closed |
| GAP-009 | `RAL.MODULEREGISTRYMISMATCH` / cap breach codes missing from frozen spec | ✅ Closed (RAL v1.2.0 + migration) |

## Spec Governance

### Freeze policy

Frozen spec files in `efl_kernel/specs/` are **never edited in place**. Every change to a spec produces a new versioned file (e.g. `EFL_RAL_v1_3_0_frozen.json`). The old file is kept intact so that any KDO produced against it remains verifiable.

### Creating a new versioned frozen spec

1. Copy the current frozen file to a new name following the convention `EFL_<MODULE>_v<MAJOR>_<MINOR>_<PATCH>_frozen.json`.
2. Make the required content changes in the new file.
3. Recompute `documentHash` (see below) and stamp it into the new file.
4. If the file contains a `violationRegistry`, recompute `registryHash` (see below) and stamp it.
5. Update all `moduleRegistration` entries in the RAL spec that reference this module (see below).
6. Update `SPEC_PATH` in `efl_kernel/kernel/ral.py` to point to the new RAL file if the RAL spec itself changed.

### Recomputing documentHash

`documentHash` covers the entire spec document. Use `canonicalize_and_hash` from `efl_kernel/kernel/ral.py`:

```python
from efl_kernel.kernel.ral import canonicalize_and_hash
import json, pathlib

spec = json.loads(pathlib.Path("efl_kernel/specs/EFL_RAL_v1_3_0_frozen.json").read_text())
spec["documentHash"] = canonicalize_and_hash(spec, "documentHash")
pathlib.Path("efl_kernel/specs/EFL_RAL_v1_3_0_frozen.json").write_text(
    json.dumps(spec, sort_keys=True, indent=2)
)
```

`canonicalize_and_hash(doc, "documentHash")` deep-copies `doc`, zeroes the named field, serialises with `sort_keys=True` and no whitespace, and returns the SHA-256 hex digest. The field must be present (even as an empty string) before calling it.

### Recomputing violationRegistry.registryHash

`registryHash` covers only the `violationRegistry` sub-object. Pass that sub-object as the document:

```python
spec["violationRegistry"]["registryHash"] = canonicalize_and_hash(
    spec["violationRegistry"], "registryHash"
)
```

### Updating moduleRegistration after a module version bump

After publishing a new frozen module spec, update the corresponding entry in `EFL_RAL_vX_Y_Z_frozen.json`:

```json
"moduleRegistration": {
  "SESSION": {
    "moduleVersion": "1.2.0",
    "moduleViolationRegistryVersion": "1.2.0",
    "registryHash": "<recomputed registryHash from new SCM spec>"
  }
}
```

Then recompute and stamp the RAL `documentHash` as described above.

### Historical example

`migrate_ral_spec_gap009.py` (deleted after use) demonstrated this full workflow for the GAP-009 closure: it added `RAL.MODULEREGISTRYMISMATCH`, `RAL.OVERRIDEREASONCAPBREACH`, and `RAL.OVERRIDEVIOLATIONCAPBREACH` to the RAL synthetic violation registry, recomputed `documentHash`, and updated all affected `moduleRegistration` hashes — producing `EFL_RAL_v1_2_0_frozen.json`.
