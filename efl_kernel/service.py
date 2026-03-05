from __future__ import annotations

import dataclasses
import os

from fastapi import FastAPI, HTTPException, Request

from efl_kernel.kernel.audit_store import AuditStore
from efl_kernel.kernel.kernel import KernelRunner
from efl_kernel.kernel.operational_store import OperationalStore
from efl_kernel.kernel.sqlite_dependency_provider import SqliteDependencyProvider
from efl_kernel.kernel.artifact_store import ArtifactStore


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
    app.state.artifact_store = ArtifactStore(resolved_path)

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

    @app.post("/artifacts", status_code=201)
    def commit_artifact(payload: dict, request: Request):
        result = request.app.state.artifact_store.commit_artifact_version(
            artifact_id=payload["artifact_id"],
            module_id=payload["module_id"],
            object_id=payload["object_id"],
            content=payload["content"],
        )
        return result

    @app.post("/artifacts/{version_id}/link-kdo")
    def link_artifact_kdo(version_id: str, payload: dict, request: Request):
        result = request.app.state.artifact_store.link_kdo(
            version_id=version_id,
            decision_hash=payload["decision_hash"],
            content_hash_at_eval=payload["content_hash_at_eval"],
        )
        return result

    @app.post("/artifacts/{version_id}/review")
    def add_artifact_review(version_id: str, payload: dict, request: Request):
        try:
            result = request.app.state.artifact_store.add_review_record(
                artifact_version_id=version_id,
                decision_hash=payload["decision_hash"],
                reviewer_id=payload["reviewer_id"],
                reason=payload["reason"],
                decision=payload["decision"],
            )
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
        return result

    @app.post("/artifacts/{version_id}/promote")
    def promote_artifact(version_id: str, request: Request):
        try:
            result = request.app.state.artifact_store.promote_to_live(
                version_id=version_id,
                get_kdo_fn=request.app.state.audit_store.get_kdo,
            )
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))
        return result

    @app.get("/artifacts/{version_id}")
    def get_artifact_version(version_id: str, request: Request):
        result = request.app.state.artifact_store.get_version(version_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"version {version_id!r} not found")
        return result

    @app.post("/artifacts/{version_id}/retire")
    def retire_artifact(version_id: str, request: Request):
        try:
            result = request.app.state.artifact_store.retire(version_id)
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))
        return result


# Module-level app for uvicorn: create_app() with no args
# reads EFL_DB_PATH at runtime. Tests call create_app(str(tmp_db)).
app = create_app()
