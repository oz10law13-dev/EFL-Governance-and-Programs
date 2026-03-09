# Phase 24 — Session Intake Workflow (BINDING)

**Status:** BINDING
**Phase:** 24
**Date:** 2026-03-09
**Predecessor:** Phase23_Review_Queue_Surface.md (Phase 23, BINDING)

---

## §1 Scope

Phase 24 closes gap 3.1 from `docs/EFL_Kernel_OS_Roadmap.md`.

**This phase delivers:**
- `_build_session_eval_payload` helper in `service.py` — builds conformant SESSION evaluation envelope from simplified coach intake data
- `POST /intake/session` route — compound endpoint: validates athlete, records session in op_sessions, evaluates via SESSION gates, commits KDO, returns combined result
- `efl_kernel/tests/test_phase24.py` — 18 tests (17 always-run + 1 PG-gated)

**Explicit non-goals for this phase:**
- No new database tables or columns
- No gate or kernel changes
- No frozen spec changes
- No new store methods
- No `InMemoryDependencyProvider` changes

---

## §2 The Four Session Paths

| Path | Route | Purpose |
|---|---|---|
| Raw CRUD | `POST /sessions` | Record session data only, no evaluation |
| Stateless eval | `POST /evaluate/session` | Evaluate a payload, no recording |
| Author | `POST /author/session` | Artifact + eval + promote pipeline |
| **Intake** | `POST /intake/session` | **Record + evaluate in one call** |

Intake is the governed path for real coaching use. The coach says "athlete X did this session today" and the system both records it (for future rolling windows) and evaluates it (for immediate legality feedback).

---

## §3 Route Contract

### `POST /intake/session`

**Request:**
```json
{
  "athlete_id": "ATH-001",
  "session_id": "S-001",
  "session_date": "2026-03-09T10:00:00+00:00",
  "contact_load": 50.0,
  "exercises": [{"exerciseID": "back_squat"}],
  "readiness_state": "GREEN",
  "is_collapsed": false
}
```

Required: `athlete_id`, `session_id`, `session_date`, `contact_load`.
Optional: `exercises` (default `[]`), `readiness_state` (default `null`), `is_collapsed` (default `false`).

**Response (200):**
```json
{
  "status": "recorded",
  "session_id": "S-001",
  "athlete_id": "ATH-001",
  "evaluation": {
    "decision_hash": "abc123...",
    "publish_state": "LEGALREADY",
    "violations": [],
    "violation_count": 0,
    "module_id": "SESSION"
  }
}
```

**Error cases:**
- 400: Missing required field
- 404: Athlete not found (with guidance to create via `POST /athletes`)

---

## §4 Payload Builder Design

`_build_session_eval_payload` constructs the full 7-key SESSION evaluation envelope:

1. `moduleVersion` — from `RAL_SPEC["moduleRegistration"]["SESSION"]`
2. `moduleViolationRegistryVersion` — from same registration
3. `registryHash` — from same registration
4. `objectID` — session_id
5. `evaluationContext` — athleteID, sessionID, sessionDate, contactLoad
6. `windowContext` — ROLLING7DAYS and ROLLING28DAYS anchored on session date
7. `session` — sessionDate, contactLoad, exercises

The function reads `RAL_SPEC` at call time — never hardcodes moduleVersion or registryHash.

---

## §5 Ordering: Session Recorded Before Evaluation

The session is recorded in `op_sessions` BEFORE the evaluation runs. This is intentional:

- Future evaluations of OTHER sessions will see it in their rolling windows
- Self-inclusion is prevented by `exclude_session_id` in `get_sessions_in_window` and strict less-than in `get_prior_session`
- This enables `SCM.MINREST` and other time-dependent gates to fire from real accumulated data

---

## §6 Athlete Verification

The intake route verifies athlete existence BEFORE recording the session. If the athlete is not found, the route returns 404 with a guidance message directing the caller to create the athlete first via `POST /athletes`.

This is a governed check — the system refuses to record training data for unknown athletes.

---

## §7 Phase 25 Must Deliver

**Governed spec bump CLI tool** — bumping a spec version currently requires hand-editing JSON and manually recomputing SHA-256 hashes. Phase 25 adds `python -m efl_kernel.tools.spec_bump` that autocomputes hashes and validates round-trips.

---

## §8 DO NOT — Carry-Forward Constraints

1. Do not change `InMemoryDependencyProvider` — SACRED
2. Do not change any gate file, `kernel.py`, `kdo.py`, `ral.py`, `registry.py`
3. Do not change any frozen spec file
4. Do not change any EXISTING store method
5. Do not call `logging.basicConfig()`
6. Do not modify applied migration files — frozen migration discipline
7. PG tests must skip when `EFL_TEST_DATABASE_URL` is not set
8. New routes must respect `request.state.org_id` (Phase 22 tenancy)
9. `_build_session_eval_payload` must read `RAL_SPEC` at call time — never hardcode
10. Duplicate session_id is allowed (upsert behavior) — each intake produces a new KDO

---

## §9 Suite State

| Metric | Value |
|---|---|
| Passed | 524 |
| Skipped | 25 (18 PG Phase 19 + 3 PG Phase 20 + 1 PG Phase 21 + 1 PG Phase 23 + 1 PG Phase 24 + 1 pre-existing) |
| Failed | 0 |
| Commit | `b8caf22` |
