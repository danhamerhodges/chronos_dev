"""FastAPI entrypoint for Chronos Phase 1 baseline."""

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.metrics import router as metrics_router
from app.observability.logging import configure_logging

app = FastAPI(title="ChronosRefine", version="0.1.0")

configure_logging()

app.include_router(health_router, tags=["health"])
app.include_router(metrics_router, tags=["metrics"])
