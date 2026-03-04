# EFL Kernel — Claude Working Rules

## 1. Always show a diff summary before making any edits.

Before touching any file, describe exactly what will change: which file, which lines, and why. Do not make the edit until that summary has been stated.

## 2. No silent refactors — every change must be explained before it is made.

Every modification — including whitespace, import reordering, or comment updates — must be described and justified before the edit tool is called. "Cleaning up" or "while I'm here" changes are not permitted.

## 3. Frozen spec files are immutable.

Files matching `efl_kernel/specs/*.json` must never be edited in place. If a spec change is required:
1. Create a new versioned frozen file (e.g. `EFL_RAL_v1_3_0_frozen.json`).
2. Recompute `documentHash` and any affected `registryHash` values using `canonicalize_and_hash` from `efl_kernel/kernel/ral.py`.
3. Update all `moduleRegistration` entries in the new spec to reflect the new versions and hashes.
4. Update the import path in `efl_kernel/kernel/ral.py` (`SPEC_PATH`) to point to the new file.

## 4. After every change: run tests, then commit.

```
cd C:\EFL-Kernel
python -m pytest -q
```

All tests must pass before committing. Commit message format:

```
<phase>: <what changed>
```

Examples: `conformance: fix step 9 cap breach logic`, `spec: add RAL.NEWCODE to v1.3.0 frozen spec`

## 5. Never source aggregates from the input payload.

Load totals, prior session timestamps, and season phase counts must always be fetched from the dependency provider (`KernelDependencyProvider`). These values must never be read from `raw_input` or any caller-supplied dict. This applies to all gate implementations and any future kernel steps.

## 6. KDOValidator allowed sets must be sourced from the frozen RAL spec at runtime.

Allowed values for fields such as `finalEffectiveLabel`, `finalSeverity`, and `finalPublishState` must be derived from `RAL_SPEC` at import time (e.g. from `RALPrecedenceRule`, `RALPublishStateDerivation`). They must not be hardcoded as Python literals in `kdo.py` or any validator.
