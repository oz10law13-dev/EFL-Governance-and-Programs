from __future__ import annotations

import dataclasses
import json
import logging
import os

_logger = logging.getLogger(__name__)

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from efl_kernel.kernel.audit_store import AuditStore
from efl_kernel.kernel.kernel import KernelRunner
from efl_kernel.kernel.operational_store import OperationalStore
from efl_kernel.kernel.sqlite_dependency_provider import SqliteDependencyProvider
from efl_kernel.kernel.artifact_store import ArtifactStore
from efl_kernel.kernel.exercise_catalog import ExerciseCatalog
from efl_kernel.kernel.proposal_engine import PhysiqueProposalEngine


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


def create_app(
    db_path: str | None = None,
    op_db_path: str | None = None,
    database_url: str | None = None,
    op_database_url: str | None = None,
) -> FastAPI:
    """
    Create and return a configured FastAPI application.

    PostgreSQL branch (preferred for production):
      database_url:    PostgreSQL DSN for the audit store (kdo_log, override_ledger).
                       If None, reads EFL_DATABASE_URL env var.
      op_database_url: PostgreSQL DSN for op/artifact stores.
                       If None, reads EFL_OP_DATABASE_URL env var; falls back to database_url.

    SQLite branch (backward-compatible default):
      db_path:    path to the audit SQLite database. Reads EFL_AUDIT_DB_PATH; falls back to "efl_audit.db".
      op_db_path: path to the operational SQLite database. Reads EFL_OP_DB_PATH; falls back to db_path.

    If database_url (or EFL_DATABASE_URL) is set, the PostgreSQL branch is used and the
    SQLite branch is ignored.
    """
    app = FastAPI(title="EFL Kernel Service", version="21.0.0")
    app.add_middleware(APIKeyMiddleware)

    resolved_db_url = database_url or os.environ.get("EFL_DATABASE_URL")
    resolved_op_url = op_database_url or os.environ.get("EFL_OP_DATABASE_URL") or resolved_db_url

    if resolved_db_url:
        from efl_kernel.kernel.pg_pool import open_pg
        from efl_kernel.kernel.pg_audit_store import PgAuditStore
        from efl_kernel.kernel.pg_operational_store import PgOperationalStore
        from efl_kernel.kernel.pg_artifact_store import PgArtifactStore
        from efl_kernel.kernel.pg_dependency_provider import PgDependencyProvider
        from efl_kernel.migrations.runner import MigrationRunner

        audit_conn = open_pg(resolved_db_url)
        op_conn = open_pg(resolved_op_url) if resolved_op_url != resolved_db_url else audit_conn
        app.state.audit_db_path = resolved_db_url
        app.state.op_db_path    = resolved_op_url or resolved_db_url
        app.state.db_path       = resolved_db_url
        app.state.audit_store   = PgAuditStore(audit_conn)
        app.state.op_store      = PgOperationalStore(op_conn)
        app.state.artifact_store = PgArtifactStore(op_conn)
        app.state.provider      = PgDependencyProvider(app.state.op_store, app.state.audit_store)
        MigrationRunner(audit_conn, "pg", "audit").ensure_current()
        MigrationRunner(op_conn, "pg", "operational").ensure_current()
    else:
        resolved_audit = db_path or os.environ.get("EFL_AUDIT_DB_PATH", "efl_audit.db")
        resolved_op    = op_db_path or os.environ.get("EFL_OP_DB_PATH") or resolved_audit
        app.state.audit_db_path = resolved_audit
        app.state.op_db_path    = resolved_op
        app.state.db_path       = resolved_audit   # backward compat alias
        app.state.op_store      = OperationalStore(resolved_op)
        app.state.audit_store   = AuditStore(resolved_audit)
        app.state.provider      = SqliteDependencyProvider(
            app.state.op_store, app.state.audit_store
        )
        app.state.artifact_store = ArtifactStore(resolved_op)
        # Run migrations for file-backed SQLite (skip for :memory: test stores)
        if resolved_audit != ":memory:":
            from efl_kernel.migrations.runner import MigrationRunner
            MigrationRunner(app.state.audit_store._conn, "sqlite", "audit").ensure_current()
        if resolved_op != ":memory:":
            from efl_kernel.migrations.runner import MigrationRunner
            MigrationRunner(app.state.op_store._conn, "sqlite", "operational").ensure_current()

    app.state.runner = KernelRunner(app.state.provider)
    app.state.catalog = ExerciseCatalog()
    app.state.proposal_engine = PhysiqueProposalEngine(app.state.catalog)

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

    @app.get("/health/backup")
    def health_backup():
        backup_dir = os.environ.get("EFL_BACKUP_DIR")
        if not backup_dir:
            return {"status": "not_configured", "detail": "EFL_BACKUP_DIR not set"}
        meta_path = os.path.join(backup_dir, ".last_backup.json")
        if not os.path.exists(meta_path):
            return {"status": "no_backups", "backup_dir": backup_dir}
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        return {"status": "ok", "backup_dir": backup_dir, **meta}

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

    @app.post("/propose/physique")
    def propose_physique(payload: dict, request: Request):
        try:
            result = request.app.state.proposal_engine.propose(payload)
            return result
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/pipeline/physique")
    def pipeline_physique(payload: dict, request: Request):
        try:
            proposal_engine = request.app.state.proposal_engine
            artifact_store  = request.app.state.artifact_store
            audit_store     = request.app.state.audit_store
            runner          = request.app.state.runner

            # 1. Generate proposal from constraints
            constraints = payload.get("constraints", {})
            proposal = proposal_engine.propose(constraints)
            candidate = proposal["candidate_payload"]

            # 2. Commit artifact version
            version_result = artifact_store.commit_artifact_version(
                artifact_id=payload["artifact_id"],
                module_id="PHYSIQUE",
                object_id=payload["object_id"],
                content=payload.get("content", candidate),
            )
            version_id   = version_result["version_id"]
            content_hash = version_result["content_hash"]

            # 3. Evaluate and commit KDO
            kdo_dict = _evaluate_and_commit(
                runner, audit_store, candidate, "PHYSIQUE"
            )
            decision_hash       = kdo_dict["audit"]["decisionHash"]
            final_publish_state = kdo_dict["resolution"]["finalPublishState"]
            violations          = kdo_dict.get("violations", [])

            # 4. Route by publish state — mirrors author_physique exactly
            if final_publish_state in ("BLOCKED", "ILLEGALQUARANTINED"):
                return {
                    "proposal": proposal,
                    "version_id": version_id,
                    "lifecycle": "DRAFT",
                    "publish_state": final_publish_state,
                    "decision_hash": decision_hash,
                    "promoted": False,
                    "requires_review": False,
                    "violations": violations,
                }
            elif final_publish_state == "LEGALREADY":
                artifact_store.link_kdo(version_id, decision_hash, content_hash)
                artifact_store.promote_to_live(version_id, audit_store.get_kdo)
                return {
                    "proposal": proposal,
                    "version_id": version_id,
                    "lifecycle": "LIVE",
                    "publish_state": final_publish_state,
                    "decision_hash": decision_hash,
                    "promoted": True,
                    "requires_review": False,
                    "violations": [],
                }
            elif final_publish_state in ("REQUIRESREVIEW", "LEGALOVERRIDE"):
                artifact_store.link_kdo(version_id, decision_hash, content_hash)
                return {
                    "proposal": proposal,
                    "version_id": version_id,
                    "lifecycle": "DRAFT",
                    "publish_state": final_publish_state,
                    "decision_hash": decision_hash,
                    "promoted": False,
                    "requires_review": True,
                    "violations": violations,
                }
            else:
                raise ValueError(
                    f"Unexpected publish state: {final_publish_state!r}"
                )
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
