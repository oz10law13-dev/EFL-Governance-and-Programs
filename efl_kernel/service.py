from __future__ import annotations

import dataclasses
import logging
import os

_logger = logging.getLogger(__name__)

from fastapi import FastAPI, HTTPException, Request

from efl_kernel.kernel.audit_store import AuditStore
from efl_kernel.kernel.kernel import KernelRunner
from efl_kernel.kernel.operational_store import OperationalStore
from efl_kernel.kernel.sqlite_dependency_provider import SqliteDependencyProvider
from efl_kernel.kernel.artifact_store import ArtifactStore
from efl_kernel.kernel.exercise_catalog import ExerciseCatalog


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

    app = FastAPI(title="EFL Kernel Service", version="18.0.0")
    app.state.db_path = resolved_path
    app.state.op_store = OperationalStore(resolved_path)
    app.state.audit_store = AuditStore(resolved_path)
    app.state.provider = SqliteDependencyProvider(
        app.state.op_store, app.state.audit_store
    )
    app.state.runner = KernelRunner(app.state.provider)
    app.state.artifact_store = ArtifactStore(resolved_path)
    app.state.catalog = ExerciseCatalog()

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
    _logger.info(
        "kdo_committed",
        extra={
            "module_id": kdo.module_id,
            "object_id": kdo.object_id,
            "decision_hash": kdo.audit["decisionHash"],
            "final_publish_state": kdo.resolution["finalPublishState"],
            "violation_count": len(kdo.violations),
        },
    )
    return dataclasses.asdict(kdo)


def _register_routes(app: FastAPI) -> None:

    @app.get("/health")
    def health():
        return {"status": "ok", "db_path": app.state.db_path}

    @app.get("/kdo/{decision_hash}")
    def get_kdo(decision_hash: str, request: Request):
        result = request.app.state.audit_store.get_kdo(decision_hash)
        if result is None:
            raise HTTPException(status_code=404, detail=f"KDO {decision_hash!r} not found")
        return result

    @app.get("/metrics")
    def get_metrics(request: Request):
        return request.app.state.audit_store.get_metrics()

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

    @app.post("/evaluate/physique")
    def evaluate_physique(payload: dict, request: Request):
        return _evaluate_and_commit(
            request.app.state.runner,
            request.app.state.audit_store,
            payload,
            "PHYSIQUE",
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
        if request.app.state.artifact_store.get_version(version_id) is None:
            raise HTTPException(status_code=404, detail=f"version {version_id!r} not found")
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

    @app.get("/artifacts")
    def list_artifact_versions(artifact_id: str, request: Request):
        return request.app.state.artifact_store.get_versions_by_artifact_id(artifact_id)

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

    @app.get("/exercises")
    def list_exercises(
        request: Request,
        movement_family: str | None = None,
        h_node: str | None = None,
        day_role: str | None = None,
        node_max: int | None = None,
        band_max: int | None = None,
        volume_class: str | None = None,
        equipment: str | None = None,
    ):
        filters: dict = {}
        if h_node is not None:
            filters["h_node"] = h_node
        if day_role is not None:
            filters["day_role"] = day_role
        if movement_family is not None:
            filters["movement_family"] = movement_family
        if node_max is not None:
            filters["node_max"] = node_max
        if band_max is not None:
            filters["band_max"] = band_max
        if volume_class is not None:
            filters["volume_class"] = volume_class
        if equipment is not None:
            filters["equipment"] = equipment
        return request.app.state.catalog.list_exercises(filters or None)

    @app.get("/exercises/{canonical_id}")
    def get_exercise(canonical_id: str, request: Request):
        ex = request.app.state.catalog.get_exercise(canonical_id)
        if ex is None:
            raise HTTPException(status_code=404, detail=f"Exercise {canonical_id!r} not found")
        return ex

    @app.post("/check/exercise")
    def check_exercise(payload: dict, request: Request):
        return request.app.state.catalog.check_exercise(payload)

    # ── Operational CRUD ──────────────────────────────────────────────

    @app.post("/athletes")
    def create_athlete(payload: dict, request: Request):
        for field in ("athlete_id", "max_daily_contact_load", "minimum_rest_interval_hours", "e4_clearance"):
            if field not in payload:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        op_store = request.app.state.op_store
        op_store.upsert_athlete(payload)
        return op_store.get_athlete(payload["athlete_id"])

    @app.get("/athletes/{athlete_id}")
    def get_athlete(athlete_id: str, request: Request):
        row = request.app.state.op_store.get_athlete(athlete_id)
        if row is None:
            raise HTTPException(status_code=404, detail=f"Athlete {athlete_id!r} not found")
        return row

    @app.post("/sessions")
    def create_session(payload: dict, request: Request):
        for field in ("session_id", "athlete_id", "session_date", "contact_load"):
            if field not in payload:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        request.app.state.op_store.upsert_session(payload)
        return {"status": "ok", "session_id": payload["session_id"]}

    @app.post("/seasons")
    def create_season(payload: dict, request: Request):
        for field in ("athlete_id", "season_id", "competition_weeks", "gpp_weeks", "start_date", "end_date"):
            if field not in payload:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        op_store = request.app.state.op_store
        op_store.upsert_season(payload)
        return op_store.get_season(payload["athlete_id"], payload["season_id"])

    @app.get("/seasons/{athlete_id}/{season_id}")
    def get_season(athlete_id: str, season_id: str, request: Request):
        row = request.app.state.op_store.get_season(athlete_id, season_id)
        if row is None:
            raise HTTPException(status_code=404, detail=f"Season {season_id!r} for athlete {athlete_id!r} not found")
        return row

    @app.post("/author/physique")
    def author_physique(payload: dict, request: Request):
        try:
            artifact_store = request.app.state.artifact_store
            audit_store = request.app.state.audit_store
            runner = request.app.state.runner

            # 1. Commit artifact version
            version_result = artifact_store.commit_artifact_version(
                artifact_id=payload["artifact_id"],
                module_id="PHYSIQUE",
                object_id=payload["object_id"],
                content=payload["content"],
            )
            version_id = version_result["version_id"]
            content_hash = version_result["content_hash"]

            # 2. Evaluate and commit KDO
            kdo_dict = _evaluate_and_commit(runner, audit_store, payload["evaluation_payload"], "PHYSIQUE")
            decision_hash = kdo_dict["audit"]["decisionHash"]
            final_publish_state = kdo_dict["resolution"]["finalPublishState"]

            # 3. Route by publish state
            if final_publish_state in ("BLOCKED", "ILLEGALQUARANTINED"):
                return {
                    "version_id": version_id,
                    "lifecycle": "DRAFT",
                    "publish_state": final_publish_state,
                    "decision_hash": decision_hash,
                    "promoted": False,
                    "requires_review": False,
                }
            elif final_publish_state == "LEGALREADY":
                artifact_store.link_kdo(version_id, decision_hash, content_hash)
                artifact_store.promote_to_live(version_id, audit_store.get_kdo)
                return {
                    "version_id": version_id,
                    "lifecycle": "LIVE",
                    "publish_state": final_publish_state,
                    "decision_hash": decision_hash,
                    "promoted": True,
                    "requires_review": False,
                }
            elif final_publish_state in ("REQUIRESREVIEW", "LEGALOVERRIDE"):
                artifact_store.link_kdo(version_id, decision_hash, content_hash)
                return {
                    "version_id": version_id,
                    "lifecycle": "DRAFT",
                    "publish_state": final_publish_state,
                    "decision_hash": decision_hash,
                    "promoted": False,
                    "requires_review": True,
                }
            else:
                raise ValueError(f"Unexpected publish state: {final_publish_state!r}")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/author/session")
    def author_session(payload: dict, request: Request):
        try:
            artifact_store = request.app.state.artifact_store
            audit_store = request.app.state.audit_store
            runner = request.app.state.runner

            # 1. Commit artifact version
            version_result = artifact_store.commit_artifact_version(
                artifact_id=payload["artifact_id"],
                module_id="SESSION",
                object_id=payload["object_id"],
                content=payload["content"],
            )
            version_id = version_result["version_id"]
            content_hash = version_result["content_hash"]

            # 2. Evaluate and commit KDO
            kdo_dict = _evaluate_and_commit(runner, audit_store, payload["evaluation_payload"], "SESSION")
            decision_hash = kdo_dict["audit"]["decisionHash"]
            final_publish_state = kdo_dict["resolution"]["finalPublishState"]

            # 3. Route by publish state
            if final_publish_state in ("BLOCKED", "ILLEGALQUARANTINED"):
                # Do NOT link — no ILLEGALQUARANTINED/BLOCKED KDO may be linked to an artifact
                return {
                    "version_id": version_id,
                    "lifecycle": "DRAFT",
                    "publish_state": final_publish_state,
                    "decision_hash": decision_hash,
                    "promoted": False,
                    "requires_review": False,
                }
            elif final_publish_state == "LEGALREADY":
                artifact_store.link_kdo(version_id, decision_hash, content_hash)
                artifact_store.promote_to_live(version_id, audit_store.get_kdo)
                return {
                    "version_id": version_id,
                    "lifecycle": "LIVE",
                    "publish_state": final_publish_state,
                    "decision_hash": decision_hash,
                    "promoted": True,
                    "requires_review": False,
                }
            elif final_publish_state in ("REQUIRESREVIEW", "LEGALOVERRIDE"):
                artifact_store.link_kdo(version_id, decision_hash, content_hash)
                return {
                    "version_id": version_id,
                    "lifecycle": "DRAFT",
                    "publish_state": final_publish_state,
                    "decision_hash": decision_hash,
                    "promoted": False,
                    "requires_review": True,
                }
            else:
                raise ValueError(f"Unexpected publish state: {final_publish_state!r}")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


# Module-level app for uvicorn: create_app() with no args
# reads EFL_DB_PATH at runtime. Tests call create_app(str(tmp_db)).
app = create_app()
