# Phase 25 — Governed Spec Bump CLI (BINDING)

**Status:** BINDING
**Phase:** 25
**Date:** 2026-03-09
**Predecessor:** Phase24_Session_Intake_Workflow.md (Phase 24, BINDING)

---

## §1 Scope

Phase 25 closes gap 4.2 from `docs/EFL_Kernel_OS_Roadmap.md`.

**This phase delivers:**
- `efl_kernel/tools/spec_bump.py` — CLI tool with 5 subcommands
- `efl_kernel/tests/test_phase25.py` — 16 tests

**Explicit non-goals for this phase:**
- No changes to any existing file
- No gate, kernel, store, provider, or route changes
- No frozen spec modifications
- No new database tables or columns

---

## §2 Subcommands

| Subcommand | Purpose |
|---|---|
| `rehash` | Recompute and stamp all hashes in a spec file |
| `verify` | Check all hashes without modifying |
| `new-version` | Copy spec to new version, bump version fields, rehash |
| `check-all` | Verify every frozen spec in the specs directory |
| `show-registration` | Print the RAL moduleRegistration entry for a spec |

Usage:
```
python -m efl_kernel.tools.spec_bump rehash --spec <path> [--force]
python -m efl_kernel.tools.spec_bump verify --spec <path>
python -m efl_kernel.tools.spec_bump new-version --source <path> --version <semver>
python -m efl_kernel.tools.spec_bump check-all [--specs-dir <path>]
python -m efl_kernel.tools.spec_bump show-registration --spec <path>
```

---

## §3 Hash Computation Order

**registryHash is computed BEFORE documentHash.** The `documentHash` covers the entire document including the `registryHash` value. Computing them in the wrong order produces a spec that fails verification.

Order:
1. `violationRegistry.registryHash` (if present)
2. `CLVIOLATIONREGISTRY.registryHash` (if present)
3. `documentHash` (if present)

The tool uses `canonicalize_and_hash` from `efl_kernel.kernel.ral` — the same function the runtime verifiers use. No reimplementation.

---

## §4 Safety

- `rehash` warns and refuses (exit code 1) when the target file is in the `efl_kernel/specs/` directory without `--force`. This enforces CLAUDE.md Rule 3 (frozen specs are immutable).
- `new-version` never modifies the source file. It reads the source, creates a new file at the derived path, and verifies source bytes are unchanged.
- `new-version` refuses if the target file already exists.

---

## §5 Example Workflow — Bump PHYSIQUE v1.0.4 to v1.0.5

```bash
# 1. Create new version from existing
python -m efl_kernel.tools.spec_bump new-version \
  --source efl_kernel/specs/EFL_PHYSIQUE_v1_0_4_frozen.json \
  --version 1.0.5

# 2. Verify the new file
python -m efl_kernel.tools.spec_bump verify \
  --spec efl_kernel/specs/EFL_PHYSIQUE_v1_0_5_frozen.json

# 3. Print the RAL registration snippet
python -m efl_kernel.tools.spec_bump show-registration \
  --spec efl_kernel/specs/EFL_PHYSIQUE_v1_0_5_frozen.json

# 4. Update RAL moduleRegistration with the printed values
# 5. Update registry.py PHYSIQUE_SPEC path
# 6. Run tests
```

---

## §6 Phase 26 Must Deliver

**Version negotiation / deprecation window** — `moduleVersion` in the payload must currently exactly match the RAL registration. Any spec version bump immediately breaks all existing callers with no grace period. Phase 26 adds version range acceptance policy in kernel Step 1 and a deprecation window mechanism.

---

## §7 DO NOT — Carry-Forward Constraints

1. Do not change `InMemoryDependencyProvider` — SACRED
2. Do not change any gate, kernel, store, provider, adapter, or route file
3. Do not change any existing frozen spec file (CLAUDE.md Rule 3)
4. Do not change `ral.py` or `registry.py`
5. Do not change any existing test file
6. Do not call `logging.basicConfig()`
7. Must use `canonicalize_and_hash` from `efl_kernel.kernel.ral` — NO reimplementation
8. Hash computation order: registryHash BEFORE documentHash — ALWAYS
9. `cmd_*` functions must return int exit codes (0 = success, 1 = failure)

---

## §8 Suite State

| Metric | Value |
|---|---|
| Passed | 540 |
| Skipped | 25 (18 PG Phase 19 + 3 PG Phase 20 + 1 PG Phase 21 + 1 PG Phase 23 + 1 PG Phase 24 + 1 pre-existing) |
| Failed | 0 |
| Commit | `05bfe30` |
