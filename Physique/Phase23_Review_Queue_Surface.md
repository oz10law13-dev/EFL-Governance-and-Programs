# Phase 23 — Review Queue Surface (API) (BINDING)

**Status:** BINDING
**Phase:** 23
**Date:** 2026-03-09
**Predecessor:** Phase22_Tenancy.md (Phase 22, BINDING)

---

## §1 Scope

Phase 23 closes gap 3.2 from `docs/EFL_Kernel_OS_Roadmap.md`.

**This phase delivers:**
- `get_pending_reviews(get_kdo_fn, org_id)` on both `SqliteArtifactStore` and `PgArtifactStore`
- `get_review_detail(version_id, get_kdo_fn, org_id)` on both artifact stores
- Two private helpers: `_get_latest_link`, `_get_review_records`
- 5 new HTTP routes: `GET /review-queue`, `GET /review-queue/stats`, `GET /review-queue/{version_id}`, `POST /review-queue/{version_id}/approve`, `POST /review-queue/{version_id}/reject`
- `efl_kernel/tests/test_phase23.py` — 21 tests (20 always-run + 1 PG-gated)

**Explicit non-goals for this phase:**
- No HTML UI — API only
- No new database tables or columns
- No gate or kernel changes
- No frozen spec changes
- No `InMemoryDependencyProvider` changes
- No weekly_totals aggregation table

---

## §2 New Store Methods

### `get_pending_reviews(get_kdo_fn, org_id="default") -> list[dict]`

Finds artifact versions in pending review state:
- `lifecycle = 'DRAFT'`
- Has at least one `artifact_kdo_links` entry
- No `review_records` entry with `decision = 'APPROVE'`
- Linked KDO has `finalPublishState` of `REQUIRESREVIEW` or `LEGALOVERRIDE`
- Scoped by `org_id`

Returns list of dicts with: `version_id`, `artifact_id`, `module_id`, `object_id`, `created_at`, `org_id`, `decision_hash`, `publish_state`, `violation_count`.

### `get_review_detail(version_id, get_kdo_fn, org_id="default") -> dict | None`

Returns full detail for a single review item:
- `version`: full artifact_versions row
- `kdo`: full KDO dict from audit store
- `violations`: list of violation dicts from KDO
- `publish_state`: `finalPublishState` from KDO
- `reviews`: list of review_records rows (newest first)

Returns `None` if version not found, org_id mismatch, or no KDO link.

---

## §3 Cross-DB Pattern

Both new methods accept `get_kdo_fn: callable(decision_hash) -> dict | None`. This is injected from the route handler as `audit_store.get_kdo` to cross the audit/operational database boundary without joining across stores.

---

## §4 Route Contracts

### `GET /review-queue`
```json
{"pending": [...], "count": 0}
```

### `GET /review-queue/stats`
```json
{
  "total_pending": 2,
  "by_module": {"SESSION": 1, "PHYSIQUE": 1},
  "by_publish_state": {"REQUIRESREVIEW": 1, "LEGALOVERRIDE": 1},
  "oldest_pending_hours": 48.3
}
```

### `GET /review-queue/{version_id}`
Returns full detail dict. 404 if not found or wrong org.

### `POST /review-queue/{version_id}/approve`
Request: `{"reviewer_id": "...", "reason": "..."}`
Response: `{"version_id": "...", "lifecycle": "LIVE", "promoted": true}`
- Creates APPROVE review record
- Promotes artifact to LIVE
- 400 if missing fields, 404 if not found, 409 if promotion fails

### `POST /review-queue/{version_id}/reject`
Request: `{"reviewer_id": "...", "reason": "..."}`
Response: `{"version_id": "...", "review_id": "...", "decision": "REJECT", "lifecycle": "DRAFT"}`
- Creates REJECT review record
- Artifact stays DRAFT
- 400 if missing fields, 404 if not found

---

## §5 Approve Workflow

The approve endpoint is a compound operation:
1. Validate version exists and has a linked KDO
2. Add APPROVE review record via `add_review_record`
3. Call `promote_to_live` which enforces all 4 invariants (INV-1 through INV-4)
4. Return promoted status

This reuses the existing `add_review_record` and `promote_to_live` methods — no new promotion logic.

---

## §6 DO NOT — Carry-Forward Constraints

1. Do not change `InMemoryDependencyProvider` — SACRED
2. Do not change any gate file, `kernel.py`, `kdo.py`, `ral.py`, `registry.py`
3. Do not change any frozen spec file
4. Do not change any EXISTING store method
5. Do not join operational and audit tables in SQL — use `get_kdo_fn` injection
6. Do not call `logging.basicConfig()`
7. Do not modify applied migration files — frozen migration discipline
8. Do not add HTML templates — API only
9. PG tests must skip when `EFL_TEST_DATABASE_URL` is not set
10. New routes must respect `request.state.org_id` (Phase 22 tenancy)

---

## §7 Suite State

| Metric | Value |
|---|---|
| Passed | 507 |
| Skipped | 24 (18 PG Phase 19 + 3 PG Phase 20 + 1 PG Phase 21 + 1 PG Phase 23 + 1 pre-existing) |
| Failed | 0 |
| Commit | `d50cb8f` |
