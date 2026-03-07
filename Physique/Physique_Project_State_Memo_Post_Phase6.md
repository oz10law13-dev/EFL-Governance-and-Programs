# EFL Kernel / Physique Project State Memo
## Post-Authority Cleanup, Pre-Runtime Integration

## Current status
The Physique authority cleanup series is complete through Phase 6.

Completed:
- Phase 1: authority text normalization
- Phase 2: reason-code canonicalization and alias governance
- Phase 3: strict JSON hygiene
- Phase 4: taxonomy cleanup and whitelist/MCC boundary clarification
- Phase 5: support-file drift cleanup
- Phase 6: runtime integration truth map

## Key conclusion from Phase 6
Physique is currently a governance-stable policy/spec pack, not a runtime-bound pack.

Runtime is currently bound to:
- frozen EFL_* specs in `efl_kernel/specs`
- kernel registry / RAL / kernel dispatch
- current runtime exercise library path

Physique artifacts currently classified as:
- active policy authority but not runtime-bound:
  - `Physique/DCC-Physique-v1.2.1-PATCHED.md`
  - `Physique/efl_tempo_governance_v1_1_2_ENFORCEMENT_CLEAN.json`
- future integration targets:
  - `Physique/efl_whitelist_v1_0_3.json`
  - `Physique/mcc-v1-0-1-patchpack.json`
- support/spec only:
  - `Physique/adult_physique_v1_0_2.json`
  - `Physique/efl_physique_framework_v2_1_tempo_validated.json`
  - `Physique/Minimal_Runtime_Shell_v1_0_SPEC.md`
  - `Physique/Minimal_Runtime_Shell_v1_0_INVARIANTS.md`
  - `Physique/EFL_Physique_Program_Framework_v2_1.md`

## Whitelist governance conclusion
The whitelist review showed that the project currently has:
- a richer authoring/planning whitelist shape
- a flatter transitional/runtime-adjacent whitelist shape
- a separate MCC runtime schema shape

Best governance answer:
- formalize one canonical authoring whitelist contract
- formalize one runtime exercise contract
- define one deterministic pre-pass adapter between them
- do not flatten authoring richness into MCC shape directly
- fail closed if normalization mapping is missing

Best current authoring candidate:
- `adult_physique_v1_0_2.json` style

Best treatment of `efl_whitelist_v1_0_3.json`:
- transitional or derived artifact until explicitly bound by runtime spec

## Runtime shell conclusion
Minimal Runtime Shell v1 docs should be reviewed, but not automatically replaced only because they are v1.

Review standard:
- do they still accurately describe fail-closed runtime behavior?
- do they accurately describe canonical field injection and normalization boundaries?
- do they distinguish authoring contract vs runtime contract?
- do they reflect current truth that Physique is not yet runtime-bound?
- do they accurately describe implemented vs declarative coupling?

If yes:
- keep active and patch minimally if needed

If materially outdated:
- issue a controlled version bump after review

## Post-Phase-6 roadmap
Track A — Physique runtime integration specs
- Phase 7: Physique Runtime Binding Spec
- Phase 8: Physique Runtime Manifest
- Phase 9: Physique Pre-Pass Adapter Spec

Track B — runtime implementation
- Phase 10: Physique Loader/Registry Hook
- Phase 11: Physique Validation Bridge
- Phase 12: Operational Data Schema
- Phase 13: SQLite Operational Store
- Phase 14: Real Dependency Provider
- Phase 15: Persisted Evaluation Path
- Phase 16: Thin HTTP Service
- Phase 17: Artifact Lifecycle Runtime
- Phase 18: Governed Authoring / Builder Prep

## Non-negotiable architectural constraints
- deterministic legality
- validation precedes publish
- default deny / quarantine on missing dependencies
- frozen specs remain frozen
- append-only registry discipline
- no builder before real runtime
- LLM optional, never authoritative

## LLM policy
The system must run with or without an LLM.

LLM may assist with:
- proposal generation
- summarization
- UI interaction
- constrained draft generation

LLM may not decide:
- legality
- state transition
- reason-code truth
- publish eligibility
