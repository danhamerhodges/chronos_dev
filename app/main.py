"""FastAPI entrypoint for Chronos Phase 2 foundation."""

from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.era_detection import router as era_detection_router
from app.api.fidelity import router as fidelity_router
from app.api.health import router as health_router
from app.api.internal_workers import router as internal_workers_router
from app.api.jobs import router as jobs_router
from app.api.deletion_proofs import router as deletion_proofs_router
from app.api.logs import router as logs_router
from app.api.manifests import router as manifests_router
from app.api.metrics import router as metrics_router
from app.api.ops import router as ops_router
from app.api.problem_details import (
    http_exception_handler,
    problem_exception_handler,
    request_validation_exception_handler,
    ProblemException,
)
from app.api.uploads import router as uploads_router
from app.api.users import router as users_router
from app.api.version import router as version_router
from app.config import settings
from app.observability.logging import configure_logging
from app.observability.monitoring import record_http_request


def create_app() -> FastAPI:
    app = FastAPI(title="ChronosRefine", version=settings.build_version)
    configure_logging()
    logger = logging.getLogger("chronos.request")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        record_http_request(request.url.path)
        logger.info(
            "request-complete method=%s path=%s status_code=%s",
            request.method,
            request.url.path,
            response.status_code,
            extra={"request_id": request_id},
        )
        return response

    app.add_exception_handler(ProblemException, problem_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)

    app.include_router(health_router, tags=["health"])
    app.include_router(internal_workers_router, tags=["internal-workers"])
    app.include_router(metrics_router, tags=["metrics"])
    app.include_router(ops_router, tags=["ops"])
    app.include_router(version_router, tags=["version"])
    app.include_router(uploads_router, tags=["uploads"])
    app.include_router(fidelity_router, tags=["fidelity"])
    app.include_router(era_detection_router, tags=["era-detection"])
    app.include_router(jobs_router, tags=["jobs"])
    app.include_router(deletion_proofs_router, tags=["deletion-proofs"])
    app.include_router(manifests_router, tags=["manifests"])
    app.include_router(users_router, tags=["users"])
    app.include_router(logs_router, tags=["security"])

    if settings.test_auth_override:
        from app.api.testing import router as testing_router

        app.include_router(testing_router, tags=["testing"])

    return app


app = create_app()
