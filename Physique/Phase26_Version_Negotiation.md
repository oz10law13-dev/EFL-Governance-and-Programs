# Phase 26 — Version Negotiation / Deprecation Window (BINDING)

**Status:** BINDING
**Phase:** 26
**Date:** 2026-03-09
**Predecessor:** Phase25_Spec_Bump_CLI.md (Phase 25, BINDING)

---

## §1 Scope

Phase 26 closes gap 4.3 from `docs/EFL_Kernel_OS_Roadmap.md` — the LAST gap.

**This phase delivers:**
- `EFL_RAL_v1_7_0_frozen.json` — RAL spec with `priorVersions` in moduleRegistration
- `_match_prior_version` helper in `kernel.py`
- Updated kernel Step 0b — version negotiation (exact match → prior version → reject)
- `versionNegotiation` field in KDO resolution for deprecated callers
- `efl_kernel/tests/test_phase26.py` — 17 tests

**Explicit non-goals for this phase:**
- No gate changes — gates never see version numbers
- No store, provider, adapter, or route changes
- No new database tables or columns

---

## §2 Version Negotiation Design

The kernel now accepts three outcomes at Step 0b:

| Outcome | Condition | Result |
|---|---|---|
| **Current** | Caller version matches moduleRegistration | Normal evaluation |
| **Deprecated** | Caller version matches a `priorVersions` entry with `status: "DEPRECATED"` | Evaluation proceeds; `versionNegotiation` added to KDO resolution |
| **Rejected** | No match found | `RAL.MODULEREGISTRYMISMATCH` quarantine |

Gates run identically regardless of which version the caller sent. Version is an integrity check, not a feature toggle.

---

## §3 RAL moduleRegistration Extension

Each module's registration now includes an optional `priorVersions` array:

```json
"PHYSIQUE": {
    "moduleVersion": "1.0.4",
    "moduleViolationRegistryVersion": "1.0.4",
    "registryHash": "7140d801...",
    "priorVersions": [
        {
            "moduleVersion": "1.0.3",
            "moduleViolationRegistryVersion": "1.0.3",
            "registryHash": "da6f7d3e...",
            "status": "DEPRECATED",
            "deprecatedAt": "2026-03-09T00:00:00+00:00"
        }
    ]
}
```

- `priorVersions` absent or `[]` means exact match only
- Only `status: "DEPRECATED"` entries are accepted
- `status: "RETIRED"` entries are rejected (same as unknown)

---

## §4 Kernel Step 0b Change

Before (exact match only):
```
if version mismatch → MODULEREGISTRYMISMATCH
```

After (negotiation):
```
if exact match → proceed
elif deprecated prior match → proceed + record negotiation
else → MODULEREGISTRYMISMATCH
```

The `_match_prior_version` helper checks all three fields: moduleVersion, moduleViolationRegistryVersion, registryHash. All must match.

---

## §5 Deprecation in KDO

When a deprecated version is accepted, the KDO resolution includes:

```json
"resolution": {
    "finalPublishState": "LEGALREADY",
    "versionNegotiation": {
        "callerVersion": "1.0.3",
        "currentVersion": "1.0.4",
        "status": "DEPRECATED"
    }
}
```

`versionNegotiation` is absent when the caller uses the current version.

---

## §6 Backward Compatibility Guarantees

- Callers using the current version see zero behavior change
- `priorVersions: []` (SESSION, MESO, MACRO, GOVERNANCE) behaves identically to the pre-Phase-26 exact-match check
- The KDO resolution dict is a plain dict — adding the optional `versionNegotiation` key does not break existing consumers
- `_version_deprecated`, `_version_negotiated_from`, `_version_negotiated_to` are private keys on `raw_input` (underscore prefix) — never serialized into KDO evaluation_context

---

## §7 Complete Spec Governance Lifecycle

With Phases 25 and 26, the full spec governance lifecycle is now tooled:

1. **Create** — `spec_bump new-version` copies + bumps + rehashes
2. **Deprecate** — Add old version to `priorVersions` with `status: "DEPRECATED"`
3. **Grace period** — Deprecated callers still get evaluated, with a deprecation notice in KDO
4. **Retire** — Change `status` to `"RETIRED"` — callers are now rejected

---

## §8 ROADMAP CLOSED

All 26 phases delivered. Tiers A, B, and C are complete.

| Tier | Phases | Status |
|------|--------|--------|
| A — Kernel Correctness | 7–18 | COMPLETE |
| B — Production Infrastructure | 19–21 | COMPLETE |
| C — Multi-User Operational System | 22–26 | COMPLETE |

---

## §9 Suite State

| Metric | Value |
|---|---|
| Passed | 557 |
| Skipped | 25 (18 PG Phase 19 + 3 PG Phase 20 + 1 PG Phase 21 + 1 PG Phase 23 + 1 PG Phase 24 + 1 pre-existing) |
| Failed | 0 |
| Commit | `5eae2f4` |
