from __future__ import annotations

import dataclasses
import os

from fastapi import FastAPI, HTTPException, Request

from efl_kernel.kernel.audit_store import AuditStore
from efl_kernel.kernel.kernel import KernelRunner
from efl_kernel.kernel.operational_store import OperationalStore
from efl_kernel.kernel.sqlite_dependency_provider import SqliteDependencyProvider


def create_app(db_path: str | None = None) -> FastAPI:
    """
    Create and return a configured FastAPI application.

    db_path: path to the shared SQLite database file.
             If None, reads EFL_DB_PATH env var.
             Falls back to "efl_audit.db" if neither is set.

    Stores, provider, and runner are initialized here and
    attached to app.state for use in request handlers.
    """
    resolved_path = db_path or os.environ.get("EFL_DB_PATH", "efl_audit.db")

    app = FastAPI(title="EFL Kernel Service", version="14.0.0")
    app.state.db_path = resolved_path
    app.state.op_store = OperationalStore(resolved_path)
    app.state.audit_store = AuditStore(resolved_path)
    app.state.provider = SqliteDependencyProvider(
        app.state.op_store, app.state.audit_store
    )
    app.state.runner = KernelRunner(app.state.provider)

    _register_routes(app)
    return app


def _evaluate_and_commit(runner, audit_store, payload: dict, module_id: str) -> dict:
    """
    Evaluate payload against module_id via KernelRunner.
    Commit the resulting KDO to AuditStore regardless of
    violation presence or publish state.
    Return KDO as dict via dataclasses.asdict.

    Commit semantics:
    - runner.evaluate() returns a KDO (even quarantined) → commit it
    - If commit raises → raise HTTPException(500)
    - JSON parse failures never reach this function (FastAPI handles them)

    Never return a KDO that was not successfully committed.
    """
    kdo = runner.evaluate(payload, module_id)
    try:
        audit_store.commit_kdo(kdo)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"KDO commit failed: {e}",
        )
    return dataclasses.asdict(kdo)


def _register_routes(app: FastAPI) -> None:

    @app.get("/health")
    def health():
        return {"status": "ok", "db_path": app.state.db_path}

    @app.post("/evaluate/session")
    def evaluate_session(payload: dict, request: Request):
        return _evaluate_and_commit(
            request.app.state.runner,
            request.app.state.audit_store,
            payload,
            "SESSION",
        )

    @app.post("/evaluate/meso")
    def evaluate_meso(payload: dict, request: Request):
        return _evaluate_and_commit(
            request.app.state.runner,
            request.app.state.audit_store,
            payload,
            "MESO",
        )

    @app.post("/evaluate/macro")
    def evaluate_macro(payload: dict, request: Request):
        return _evaluate_and_commit(
            request.app.state.runner,
            request.app.state.audit_store,
            payload,
            "MACRO",
        )


# Module-level app for uvicorn: create_app() with no args
# reads EFL_DB_PATH at runtime. Tests call create_app(str(tmp_db)).
app = create_app()
