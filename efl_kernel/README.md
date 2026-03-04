# EFL Compliance Kernel

Reference implementation of the EFL compliance kernel with frozen JSON specs, a deterministic rule layer, and tests.

## Run tests

```bash
cd efl_kernel
pytest
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
