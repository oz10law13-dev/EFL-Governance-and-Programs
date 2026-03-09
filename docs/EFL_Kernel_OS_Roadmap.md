# EFL-Kernel — Full Roadmap to True OS
**Document:** EFL_Kernel_OS_Roadmap.md  
**Status:** LIVING DOCUMENT  
**Date:** 2026-03-09
**Suite at time of writing:** 507 passed, 24 skipped
**Last completed phase:** Phase 23 (commit d50cb8f)

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

### Layer 3 — HTTP Service ✅ COMPLETE

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
| `POST /author/physique` | Complete — Phase 13B |
| `POST /athletes`, `GET /athletes/{id}`, `POST /sessions`, `POST /seasons`, `GET /seasons/{athlete_id}/{season_id}` | Complete — Phase 14 |
| `GET /kdo/{decision_hash}` audit query | Complete — Phase 15 |

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
| 2.1 | **19** | ✅ **COMPLETE** — `PgAuditStore`, `PgOperationalStore`, `PgArtifactStore`, `PgDependencyProvider` added. `create_app` selects PG via `EFL_DATABASE_URL` / `database_url` param. SQLite path fully preserved via shims. psycopg3 sync API. 24 tests (18 PG-gated). | — | — |
| 2.2 | **16** | ✅ **COMPLETE** — `APIKeyMiddleware` added to `service.py`. Reads `EFL_API_KEY` at request time. No-op when unset. `/health` exempt. 401 on missing/wrong key. | — | — |
| 2.3 | **20** | ✅ **COMPLETE** — Custom numbered-migration runner added. Dialect-specific (SQLite/PG) × domain-specific (audit/operational) migration files. SHA-256 checksum verification (frozen migration discipline). Bootstrap mode for pre-existing databases. `create_app` runs migrations at startup for file-backed and PG databases. | — | — |
| 2.4 | **17** | ✅ **COMPLETE** — `AuditStore` routes to `EFL_AUDIT_DB_PATH`; `OperationalStore` + `ArtifactStore` route to `EFL_OP_DB_PATH`; backward compat preserved via `resolved_audit` fallback. | — | — |
| 2.5 | **21** | ✅ **COMPLETE** — SQLite WAL mode on all 3 file-backed stores. Backup CLI tool (`efl_kernel/tools/backup.py`) with `sqlite`, `pg`, `verify` subcommands. `GET /health/backup` route. `docs/backup_restore.md` operational documentation. | — | — |

---

### TRACK 3 — OPERATIONAL GAPS
*Blocking real coaching use. System works in isolation; can't be used by a real team.*

| # | Phase | Item | Impact | Effort |
|---|---|---|---|---|
| 3.1 | **21** | **No real session intake path** — session data enters only via seed fixtures or direct API evaluation calls. No governed intake workflow for real training data (athlete submits session → system records it → evaluation can reference it). | Coaches can't submit real session data through a normal workflow | Medium — intake API with validation layer separate from evaluation |
| 3.2 | **23** | ✅ **COMPLETE** — Review queue API: `GET /review-queue`, `GET /review-queue/stats`, `GET /review-queue/{id}`, `POST .../approve`, `POST .../reject`. `get_pending_reviews` + `get_review_detail` on both artifact stores. Cross-DB KDO lookup via `get_kdo_fn` injection. 21 tests. | — | — |
| 3.3 | **15** | ✅ **COMPLETE** — Structured logging added to `_evaluate_and_commit` (logger `efl_kernel.service`, INFO after each KDO commit). `GET /metrics` endpoint added to `service.py`. `AuditStore.get_metrics()` returns `kdo_total`, `by_module`, `by_publish_state`. | — | — |
| 3.4 | **15** | ✅ **COMPLETE** — `GET /kdo/{decision_hash}` route added to `service.py`. Returns full KDO dict from `audit_store.get_kdo(decision_hash)`. 404 if not found. | — | — |
| 3.5 | **18** | ✅ **COMPLETE** — `PhysiqueProposalEngine` added. `POST /propose/physique` + `POST /pipeline/physique` wired. Deterministic proposal → evaluate → LIVE pipeline complete. | — | — |

---

### TRACK 4 — GOVERNANCE GAPS
*Blocking institutional trust. System is deterministic; it is not yet institutionally governed.*

| # | Phase | Item | Impact | Effort |
|---|---|---|---|---|
| 4.1 | **22** | ✅ **COMPLETE** — `org_id TEXT NOT NULL DEFAULT 'default'` on 6 tables. WHERE-clause isolation on all store methods. `OrgScopedSqliteProvider` / `OrgScopedPgProvider` inject org_id transparently. `APIKeyMiddleware` supports multi-key (`EFL_API_KEYS` JSON dict). All routes pass org_id. 30 tests. | — | — |
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
| ~~15~~ | ~~`GET /kdo/{hash}` + structured logging + `/metrics`~~ | ~~1~~ | ✅ COMPLETE |
| ~~16~~ | ~~Authentication middleware (API key)~~ | ~~1~~ | ✅ COMPLETE |
| ~~17~~ | ~~Audit/operational DB separation~~ | ~~1~~ | ✅ COMPLETE |
| ~~18~~ | ~~Governed authoring / builder prep~~ | ~~3–4~~ | ✅ COMPLETE |

*Tier A complete. Tiers B and C pending.*

### Tier B — Production Infrastructure
*~8–10 weeks. Makes the system deployable to a real environment.*

| Phase | Title | Weeks | Dependency |
|---|---|---|---|
| ~~19~~ | ~~PostgreSQL migration~~ | ~~3–4~~ | ✅ COMPLETE |
| ~~20~~ | ~~Schema migration versioning (Alembic or custom)~~ | ~~1~~ | ✅ COMPLETE |
| ~~21~~ | ~~Backup/restore strategy + WAL configuration~~ | ~~1~~ | ✅ COMPLETE |

### Tier C — Multi-User Operational System
*~10–12 weeks. Makes the system usable by a real coaching organization.*

| Phase | Title | Weeks | Dependency |
|---|---|---|---|
| ~~22~~ | ~~Tenancy (org_id isolation)~~ | ~~2–3~~ | ✅ COMPLETE |
| ~~23~~ | ~~Review queue surface (API + minimal UI)~~ | ~~2–3~~ | ✅ COMPLETE |
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
