# Phase 16 — Authentication Middleware (BINDING)

**Status:** BINDING
**Phase:** 16
**Date:** 2026-03-08
**Predecessor:** Phase15_KDO_Query_Logging_Metrics.md (Phase 15, BINDING)

---

## §1 Scope

Phase 16 closes gap 2.2 from `docs/EFL_Kernel_OS_Roadmap.md`:

- **Gap 2.2** — No authentication: all HTTP routes were open. Any caller could evaluate any athlete, read any KDO, or modify any artifact.

**This phase:**
- Adds `APIKeyMiddleware` class to `efl_kernel/service.py` using `starlette.middleware.base.BaseHTTPMiddleware`
- Registers the middleware in `create_app` via `app.add_middleware(APIKeyMiddleware)`
- Adds `from starlette.middleware.base import BaseHTTPMiddleware` and `from fastapi.responses import JSONResponse` to `service.py` imports
- Adds 6 tests in `efl_kernel/tests/test_phase16.py`

**This phase does NOT:**
- Change any gate logic, violation codes, or frozen specs
- Change existing routes or `_evaluate_and_commit` behavior
- Add role-based authorization — this is API key only (single shared key)
- Add key rotation or multi-key support

---

## §2 Middleware Contract

| Property | Value |
|---|---|
| Middleware class | `APIKeyMiddleware(BaseHTTPMiddleware)` |
| Env var | `EFL_API_KEY` |
| Env var read point | Inside `dispatch` at request time (NOT `__init__`, NOT `create_app`) |
| No-op condition | `EFL_API_KEY` unset → all requests pass through |
| Exempt routes | `/health` only (exact path match) |
| Header name | `x-api-key` (Starlette normalizes to lowercase) |
| Rejection status | 401 |
| Rejection body | `{"detail": "unauthorized"}` |
| Acceptance | `request.headers.get("x-api-key") == api_key` → pass through |

The env var is read inside `dispatch` — not at `__init__` or `create_app` time — so that `monkeypatch.setenv` / `monkeypatch.delenv` in tests correctly affects request-time behavior after the app is already created.

---

## §3 Implementation

```python
class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        api_key = os.environ.get("EFL_API_KEY")
        if api_key is None:
            return await call_next(request)
        if request.url.path == "/health":
            return await call_next(request)
        if request.headers.get("x-api-key") != api_key:
            return JSONResponse(status_code=401, content={"detail": "unauthorized"})
        return await call_next(request)
```

Registered in `create_app` immediately after `app = FastAPI(...)`:
```python
app.add_middleware(APIKeyMiddleware)
```

---

## §4 Phase 17 Must Deliver

1. **Audit/operational DB separation** — `AuditStore` and `OperationalStore` share one SQLite file (`efl_audit.db`). Corrupting operational data can corrupt the legal audit record. Separate file paths required.

---

## §5 DO NOT — Carry-Forward Constraints

*(Copied verbatim from `Phase15_KDO_Query_Logging_Metrics.md §5`)*

1. Do not create a `weekly_totals` table — `get_weekly_totals` has no live gate consumer
2. Do not create a second SQLite database file — share the same database path
3. Do not reuse `kdo_log` or `override_ledger` table names — owned by `audit_store.py`
4. Do not join operational and audit tables in provider queries
5. Do not change `InMemoryDependencyProvider` — it remains the test double
6. No new frozen spec required for Phase 16 — `EFL_PHYSIQUE_v1_0_4_frozen.json` remains current

---

## §6 Suite State

| Metric | Value |
|---|---|
| Passed | 406 |
| Skipped | 1 |
| Failed | 0 |
| Commit | `377a73a` |
