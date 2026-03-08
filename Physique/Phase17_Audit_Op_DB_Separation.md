# Phase 17 — Audit/Operational DB Separation (BINDING)

**Status:** BINDING
**Phase:** 17
**Date:** 2026-03-08
**Predecessor:** Phase16_Authentication_Middleware.md (Phase 16, BINDING)

---

## §1 Scope

Phase 17 closes gap 2.4 from `docs/EFL_Kernel_OS_Roadmap.md`:

- **Gap 2.4** — `AuditStore` and `OperationalStore` both wrote to the same SQLite file. Corrupting operational data could corrupt or lock the file holding the legal KDO record, violating audit integrity separation.

**This phase:**
- Adds `op_db_path: str | None = None` parameter to `create_app` in `efl_kernel/service.py`
- Replaces single `resolved_path` with `resolved_audit` (for `AuditStore`) and `resolved_op` (for `OperationalStore` + `ArtifactStore`)
- Adds `--op-db` argument to `efl_kernel/cli.py` and `"--op-db"` alias to `efl_kernel/tools/seed.py`
- Adds 6 tests in `efl_kernel/tests/test_phase17.py`

**This phase does NOT:**
- Change `AuditStore.__init__`, `OperationalStore.__init__`, or `ArtifactStore.__init__`
- Add SQLite `FOREIGN KEY` or `ATTACH DATABASE` for cross-file references
- Add new DDL, tables, or columns to any store
- Change any gate logic, violation codes, or frozen specs
- Change existing route handlers or `_evaluate_and_commit`

---

## §2 DB Path Resolution Contract

| Calling pattern | resolved_audit | resolved_op |
|---|---|---|
| `create_app(str(db))` | `str(db)` | `str(db)` |
| `create_app(db_path=a, op_db_path=b)` | `a` | `b` |
| `create_app()` + `EFL_AUDIT_DB_PATH=a` + `EFL_OP_DB_PATH=b` | `a` | `b` |
| `create_app()` + `EFL_AUDIT_DB_PATH=a` (no `EFL_OP_DB_PATH`) | `a` | `a` |
| `create_app()` (no env vars) | `"efl_audit.db"` | `"efl_audit.db"` |

Resolution code in `create_app`:
```python
resolved_audit = db_path or os.environ.get("EFL_AUDIT_DB_PATH", "efl_audit.db")
resolved_op    = op_db_path or os.environ.get("EFL_OP_DB_PATH") or resolved_audit
```

---

## §3 Table Ownership

**Audit DB** (resolved from `EFL_AUDIT_DB_PATH` / `db_path` / `"efl_audit.db"`):

| Table | Owner |
|---|---|
| `kdo_log` | `AuditStore` |
| `override_ledger` | `AuditStore` |

**Operational DB** (resolved from `EFL_OP_DB_PATH` / `op_db_path` / falls back to audit path):

| Table | Owner |
|---|---|
| `op_athletes` | `OperationalStore` |
| `op_sessions` | `OperationalStore` |
| `op_seasons` | `OperationalStore` |
| `artifact_versions` | `ArtifactStore` |
| `artifact_kdo_links` | `ArtifactStore` |
| `review_records` | `ArtifactStore` |

`artifact_kdo_links.decision_hash` is an application-level string reference to a KDO in the audit DB. No SQLite cross-file FK. No `ATTACH DATABASE`. `promote_to_live` passes `get_kdo_fn=audit_store.get_kdo` at call time — the audit connection is traversed at that moment only.

---

## §4 Backward Compatibility Contract

`create_app(str(db))` called with a single positional argument and no `op_db_path` resolves `resolved_op = resolved_audit = str(db)`. Both store families write to the same file. All 406 pre-Phase-17 tests pass unchanged.

The `db_path` positional parameter name is preserved exactly. No existing call site requires modification.

`app.state.db_path` is preserved as a backward-compat alias for `app.state.audit_db_path`. The `/health` route returns `app.state.db_path` (the audit path).

---

## §5 Phase 18 Must Deliver

1. **Governed authoring / builder prep** — constraint-aware session proposal generation, proposal → evaluation → artifact → LIVE pipeline, rejection → revision loop. Both Phase 14 (real dependency provider) and Phase 15 (persisted evaluation path) are complete. Phase 18 is unblocked.

---

## §6 DO NOT — Carry-Forward Constraints

*(Items 1–6 copied verbatim from `Phase16_Authentication_Middleware.md §5`)*

1. Do not create a `weekly_totals` table — `get_weekly_totals` has no live gate consumer
2. Do not create a second SQLite database file — share the same database path (unless explicitly routing to separate paths per this spec)
3. Do not reuse `kdo_log` or `override_ledger` as table names
4. Do not join operational and audit tables in provider queries
5. Do not change `InMemoryDependencyProvider` — it remains the test double
6. No new frozen spec required for Phase 17 — `EFL_PHYSIQUE_v1_0_4_frozen.json` remains current
7. Do not rename the `db_path` parameter in `create_app` — existing tests call it positionally
8. Do not add SQLite `FOREIGN KEY` or `ATTACH DATABASE` for cross-file references
9. Do not call `logging.basicConfig()`

---

## §7 Suite State

| Metric | Value |
|---|---|
| Passed | 412 |
| Skipped | 1 |
| Failed | 0 |
| Commit | `87a9046` |
