# Phase 14 — Operational CRUD Routes (BINDING)

**Status:** BINDING
**Phase:** 14 (includes 14B)
**Date:** 2026-03-08
**Predecessor:** Phase13B_Author_Physique_Route.md (Phase 13B, BINDING)

---

## §1 Scope

Phase 14 closes gaps 1.3 and 1.4 from `docs/EFL_Kernel_OS_Roadmap.md`:

- **Gap 1.3** — Athlete/session/season CRUD API routes: athletes previously entered the system only via seed tool or direct `upsert_athlete` test calls. Five new routes added to `service.py` close the enrollment gap.
- **Gap 1.4** — `ExerciseCatalog` whitelist path: `exercise_catalog.py` was confirmed to already load `efl_whitelist_v1_0_4.json` (updated in Phase 9). No change required.

**This phase:**
- Adds 5 operational CRUD routes to `service.py`
- Adds 15 tests in `efl_kernel/tests/test_crud_routes.py`

**This phase does NOT:**
- Change any gate logic, violation codes, or frozen specs
- Implement `GET /sessions` or session list routes
- Add `DELETE` for any entity
- Add athlete FK enforcement at `/sessions` or `/seasons`

---

## §2 Route Table

| Method | Route | Required Fields | Response | FK check |
|---|---|---|---|---|
| `POST` | `/athletes` | `athlete_id`, `max_daily_contact_load`, `minimum_rest_interval_hours`, `e4_clearance` | stored row | N/A |
| `GET` | `/athletes/{athlete_id}` | — | stored row, 404 if absent | N/A |
| `POST` | `/sessions` | `session_id`, `athlete_id`, `session_date`, `contact_load` | `{"status": "ok", "session_id": ...}` | None |
| `POST` | `/seasons` | `athlete_id`, `season_id`, `competition_weeks`, `gpp_weeks`, `start_date`, `end_date` | stored row | None |
| `GET` | `/seasons/{athlete_id}/{season_id}` | — | stored row, 404 if absent | N/A |

Optional session fields: `readiness_state` (str), `is_collapsed` (int).

---

## §3 Validation Contract

**400 on missing required field:** Each POST route iterates required fields in declared order and raises `HTTPException(status_code=400, detail=f"Missing required field: {field}")` on the first absent field. Missing fields never reach `upsert_*` as a `KeyError` → 500.

**No FK enforcement at the API layer:** `/sessions` and `/seasons` accept any `athlete_id` without verifying it exists in `op_athletes`. Rationale: the `SqliteDependencyProvider` uses fail-closed sentinels for missing athlete records at evaluation time. Enforcing FK at the API layer would add coupling with no gate benefit — the sentinel is the correct enforcement point.

---

## §4 Whitelist Path Fix (14B)

`efl_kernel/kernel/exercise_catalog.py` default path was confirmed to already reference `efl_whitelist_v1_0_4.json` (line 26). Both v1.0.3 and v1.0.4 contain **30 exercises** — `test_catalog_loads_all_exercises` required no update.

---

## §5 Phase 15 Must Deliver

1. **`GET /kdo/{decision_hash}` audit query route** — KDOs are persisted to `kdo_log` but no HTTP route retrieves a specific KDO by its hash.
2. **Structured logging** — currently `print(json.dumps(kdo))` is the only output path for CLI; no log aggregation or alerting.

---

## §6 DO NOT — Carry-Forward Constraints

*(Copied verbatim from `Phase13B_Author_Physique_Route.md §6`)*

1. Do not create a `weekly_totals` table — `get_weekly_totals` has no live gate consumer
2. Do not create a second SQLite database file — share the same database path
3. Do not reuse `kdo_log` or `override_ledger` table names — owned by `audit_store.py`
4. Do not join operational and audit tables in provider queries
5. Do not change `InMemoryDependencyProvider` — it remains the test double
6. No new frozen spec required for Phase 14 — `EFL_PHYSIQUE_v1_0_4_frozen.json` remains current

---

## §7 Suite State

| Metric | Value |
|---|---|
| Passed | 394 |
| Skipped | 1 |
| Failed | 0 |
| Commits this phase | 1: `30f99ea` |
