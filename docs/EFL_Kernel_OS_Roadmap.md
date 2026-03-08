# EFL-Kernel — Full Roadmap to True OS
**Document:** EFL_Kernel_OS_Roadmap.md  
**Status:** LIVING DOCUMENT  
**Date:** 2026-03-08  
**Suite at time of writing:** 394 passed, 1 skipped
**Last completed phase:** Phase 14 (commit 30f99ea)

---

## CURRENT STATE — WHAT IS ACTUALLY BUILT

### Layer 1 — Legality Engine ✅ COMPLETE

| Component | Status | Location |
|---|---|---|
| Frozen spec loading + hash verification | Complete | `registry.py`, `ral.py` |
| SESSION gates (SCM, CL) | Complete | `gates_scm.py`, `gates_cl.py` |
| MESO gate (load imbalance) | Complete | `gates_meso.py` |
| MACRO gate (phase ratio) | Complete | `gates_macro.py` |
| PHYSIQUE gates — DCC Pass 1A/1B (tempo, DCC codes) | Complete | `gates_physique.py` |
| PHYSIQUE gates — MCC all 43 codes | Complete | `gates_physique.py` |
| PHYSIQUE clearance gate (E4) | Complete | `gates_physique.py` |
| KDO assembly + publish state derivation | Complete | `kernel.py`, `kdo.py` |
| Determinism guarantee | Complete | All gates read only dep provider + frozen specs |
| Bidirectional coverage validation | Complete | `registry.py` |

### Layer 2 — Persistence ✅ COMPLETE

| Component | Status | Location |
|---|---|---|
| SQLite audit store (kdo_log, override_ledger) | Complete | `audit_store.py` |
| SQLite operational store (athletes, sessions, seasons) | Complete | `operational_store.py` |
| SqliteDependencyProvider (fail-closed sentinels) | Complete | `sqlite_dependency_provider.py` |
| Seed tool (test/fixture data ingestion) | Complete | `tools/seed.py` |
| Idempotent schema migration | Partial — additive only | `operational_store._migrate_schema()` |

### Layer 3 — HTTP Service ✅ SUBSTANTIALLY COMPLETE

| Route | Status |
|---|---|
| `GET /health` | Complete |
| `POST /evaluate/session` | Complete |
| `POST /evaluate/meso` | Complete |
| `POST /evaluate/macro` | Complete |
| `POST /evaluate/physique` | Complete |
| `POST /artifacts` | Complete |
| `GET /artifacts` | Complete |
| `POST /artifacts/{id}/link-kdo` | Complete |
| `POST /artifacts/{id}/promote` | Complete |
| `POST /artifacts/{id}/retire` | Complete |
| `POST /artifacts/{id}/review` | Complete |
| `GET /exercises` (filterable) | Complete |
| `GET /exercises/{id}` | Complete |
| `POST /check/exercise` (stateless fast-path) | Complete |
| `POST /author/session` (commit + eval + promote) | Complete — SESSION only |
| `POST /author/physique` | **MISSING** |
| Athlete/session/season CRUD routes | **MISSING** |
| `GET /kdo/{decision_hash}` audit query | **MISSING** |

### Layer 4 — Authoring Loop ✅ SUBSTANTIALLY COMPLETE

`test_os_loop.py` proves the full invariant chain is wired:

- INV-1: Any exercise the catalog returns is legal within its own declared envelope
- INV-2: `check_exercise` and `/evaluate/physique` agree on violations
- INV-3: Band violation correlates between stateless check and full governed eval
- INV-4: Readiness history seeded into op_store fires L3 gate via provider path (not payload hint)

The full chain — whitelist → stateless check → governed eval → KDO commit — is coherent and tested.

---

## FULL GAP MAP

---

### TRACK 1 — CORRECTNESS GAPS
*Remaining kernel phases. Blocking correct behavior for spec-compliant callers.*

| # | Phase | Item | Blocking | Scope |
|---|---|---|---|---|
| 1.1 | **13** | ✅ **COMPLETE** — Input envelope normalization — `_normalize_physique_envelope` maps `evaluation_context`→`evaluationContext` and `session`→`physique_session` before kernel Step 0. Transitional names remain valid. | — | — |
| 1.2 | **13B** | ✅ **COMPLETE** — `/author/physique` route added to `service.py`; mirrors `author_session` lifecycle exactly. | — | — |
| 1.3 | **14** | ✅ **COMPLETE** — `POST /athletes`, `GET /athletes/{id}`, `POST /sessions`, `POST /seasons`, `GET /seasons/{athlete_id}/{season_id}` added to `service.py`. | — | — |
| 1.4 | **14B** | ✅ **COMPLETE** — `exercise_catalog.py` already loaded `efl_whitelist_v1_0_4.json` (confirmed Phase 9). No change required. | — | — |
| 1.5 | **15** | **MESO/MACRO Physique-specific gates are stubs** — Phase 7 spec §9 flags these explicitly. General MESO/MACRO gates fire; Physique-specific MESO/MACRO gate logic (density-aware meso evaluation, Physique-specific macro constraints) is not implemented. | No — general gates still enforce; Physique-specific rules absent | `gates_meso.py`, `gates_macro.py` future extension |

---

### TRACK 2 — INFRASTRUCTURE GAPS
*Blocking real deployment. None of these stop the system from passing tests.*

| # | Phase | Item | Impact | Effort |
|---|---|---|---|---|
| 2.1 | **16** | **SQLite → PostgreSQL** — single file, single writer, no horizontal scale. Can't run multiple uvicorn workers against the same db. Can't serve real concurrent users. | Can't deploy to production with any meaningful load | High — new provider implementation, connection pooling, DDL migration, async driver |
| 2.2 | **17** | **No authentication** — all HTTP routes are open. Any caller can evaluate any athlete, read any artifact, promote any KDO. | Unacceptable for any real deployment | Medium — API key or JWT middleware; auth-scoped queries |
| 2.3 | **18** | **No formal schema migration versioning** — `_migrate_schema()` uses idempotent `ALTER TABLE` patches. Works for additive changes, breaks for column renames, type changes, or drops on a running system with real data. | Can't safely deploy schema changes to production | Medium — versioned migration runner (Alembic or custom numbered scripts) |
| 2.4 | **19** | **Audit and operational data share one SQLite file** — `AuditStore` and `OperationalStore` both write to `efl_audit.db`. Corrupting operational data can corrupt the legal audit record. | Violates audit integrity separation principle | Medium — separate db file paths or separate database instances |
| 2.5 | **20** | **No backup/restore strategy** — the KDO log is the legal record of every evaluation decision. No WAL configuration, no scheduled backup, no point-in-time restore. | Losing the audit store is catastrophic and unrecoverable | Medium — WAL mode, scheduled backup script, restore verification procedure |

---

### TRACK 3 — OPERATIONAL GAPS
*Blocking real coaching use. System works in isolation; can't be used by a real team.*

| # | Phase | Item | Impact | Effort |
|---|---|---|---|---|
| 3.1 | **21** | **No real session intake path** — session data enters only via seed fixtures or direct API evaluation calls. No governed intake workflow for real training data (athlete submits session → system records it → evaluation can reference it). | Coaches can't submit real session data through a normal workflow | Medium — intake API with validation layer separate from evaluation |
| 3.2 | **22** | **Review workflow has no UI surface** — `REQUIRESREVIEW` KDOs are committed to the audit log but there is no mechanism for a human reviewer to discover, action, or resolve them. The code path exists; the operational surface does not. | Override/review path is unactionable in practice | Medium-High — review queue API (`GET /review-queue`, `POST /artifacts/{id}/review`) + any front-end |
| 3.3 | **23** | **No structured logging or observability** — `print(json.dumps(kdo))` is the only output path for CLI; no log aggregation, no alerting on repeated quarantines, no health metrics beyond `/health`. | Can't monitor quarantine rates, repeated violations, or system degradation | Low-Medium — structured logger with levels, `/metrics` endpoint, log aggregation integration |
| 3.4 | **24** | **`GET /kdo/{decision_hash}` audit query route missing** — KDOs are persisted to `kdo_log` but there is no HTTP route to retrieve a specific KDO by its hash. Can't produce a verifiable legal record for an external party. | Can't audit or export decisions | Low — single read route on `audit_store.get_kdo()` |
| 3.5 | **25** | **Phase 18 governed authoring not built** — no guided path to create a valid Physique session from scratch. Coaches must hand-craft JSON payloads; there is no builder interface, no proposal generation, no constraint-aware exercise selection workflow. | Coaches can't create a session through any normal interface | High — full Phase 18 scope (see Track 4) |

---

### TRACK 4 — GOVERNANCE GAPS
*Blocking institutional trust. System is deterministic; it is not yet institutionally governed.*

| # | Phase | Item | Impact | Effort |
|---|---|---|---|---|
| 4.1 | **26** | **No tenancy** — all athletes exist in one flat namespace. No org_id or team isolation. Can't run multiple teams or organizations against the same service instance. | Can't serve multiple organizations | High — `org_id` column on all operational and audit tables; auth-scoped queries on every provider method |
| 4.2 | **27** | **Frozen spec update process is manual** — bumping a spec version requires hand-editing JSON, manually recomputing SHA-256 hashes, and updating all reference points. Creates risk of hash corruption on every spec change. | Every spec version bump is a correctness risk | Medium — governed spec bump CLI (`python -m efl_kernel.tools.spec_bump`) that autocomputes hashes and validates round-trips |
| 4.3 | **28** | **No version negotiation** — `moduleVersion` in the payload must exactly match the RAL registration. Any spec version bump immediately breaks all existing callers with no grace period. | Spec updates are breaking changes for all callers simultaneously | Medium — version range acceptance policy in kernel; deprecation window |
| 4.4 | **29** | **Phase 18 — Governed Authoring / Builder Prep** — authoring tools and builder interfaces must not be built before Phase 14 (real dependency provider) and Phase 15 (persisted evaluation path) are complete. Both are done. Phase 18 is now unblocked. Scope: constraint-aware session proposal generation, proposal → evaluation → artifact → LIVE pipeline, rejection → revision loop. | Without this, the system evaluates sessions but cannot help create them | High — 3-4 weeks minimum scope |

---

## PRIORITIZED SEQUENCE TO TRUE OS

### Tier A — Kernel Correctness (complete the original roadmap)
*~5–6 weeks. Finishes what was scoped. System usable by a single trusted operator.*

| Phase | Title | Weeks | Dependency |
|---|---|---|---|
| ~~13~~ | ~~Input envelope normalization~~ | ~~1~~ | ✅ COMPLETE |
| ~~13B~~ | ~~/author/physique route~~ | ~~0.5~~ | ✅ COMPLETE |
| ~~14~~ | ~~Athlete/session/season CRUD API + whitelist path fix~~ | ~~1~~ | ✅ COMPLETE |
| **15** | `GET /kdo/{hash}` + structured logging + `/metrics` | 1 | **NEXT** |
| 16 | Authentication middleware (API key) | 1 | None |
| 17 | Audit/operational DB separation | 1 | 2.1 infra decision |
| 18 | Governed authoring / builder prep | 3–4 | 14, 15 |

### Tier B — Production Infrastructure
*~8–10 weeks. Makes the system deployable to a real environment.*

| Phase | Title | Weeks | Dependency |
|---|---|---|---|
| 19 | PostgreSQL migration | 3–4 | 17 |
| 20 | Schema migration versioning (Alembic or custom) | 1 | 19 |
| 21 | Backup/restore strategy + WAL configuration | 1 | 19 |

### Tier C — Multi-User Operational System
*~10–12 weeks. Makes the system usable by a real coaching organization.*

| Phase | Title | Weeks | Dependency |
|---|---|---|---|
| 22 | Tenancy (org_id isolation) | 2–3 | 19, 20 |
| 23 | Review queue surface (API + minimal UI) | 2–3 | 18 |
| 24 | Session intake workflow | 2 | 22 |
| 25 | Governed spec bump CLI tool | 1 | None |
| 26 | Version negotiation / deprecation window | 1–2 | 25 |

---

## HONEST ASSESSMENT

**The deterministic legality engine is done and trustworthy.**  
Given identical inputs and the same loaded frozen specs, the runtime produces identical outcomes on every invocation. This is Phase 7's non-negotiable constraint and it holds.

**The audit trail is solid.**  
Every evaluation is committed to `kdo_log` with a hash-verified decision record before any result is returned. The legal record is append-only.

**What you don't have yet:**  
The surrounding system that makes those two things useful to an actual organization — real data in, real people acting on results, real infrastructure underneath.

**Tier A** finishes the kernel correctness story. That is the original 18-phase roadmap completed.  
**Tiers B and C** make it an institutional system. That is a second roadmap.  
Phase 18 (governed authoring) is the hardest single piece in Tier A because it is the first time the system must generate valid sessions rather than only evaluate them.

---

## NON-NEGOTIABLE ARCHITECTURAL CONSTRAINTS
*These apply to all remaining phases and may not be relaxed.*

1. **Deterministic legality.** Identical inputs + same loaded authority artifact versions = identical outcomes on every invocation.
2. **Validation precedes publish.** A session may not reach a legal publish state without passing all registered gate checks.
3. **Default deny / quarantine on missing dependencies.** Unknown exercise ID = halt. Missing whitelist field = halt. Missing athlete = fail-closed sentinel.
4. **Frozen specs remain frozen.** No artifact in `efl_kernel/specs/` may be edited in place.
5. **Append-only registry discipline.** Reason codes, violation codes, alias table entries — once registered, never removed or renamed.
6. **No builder before real runtime.** Phase 18 authoring tools must not be built before Phases 14–15 are complete. (They are. Phase 18 is now unblocked.)
7. **LLM optional, never authoritative.** The runtime must produce correct legality outcomes with or without LLM involvement. LLM output is never a dependency for a KDO decision.

---

*End of document. Update this file at the start of each phase with completed items and any new gaps discovered.*
