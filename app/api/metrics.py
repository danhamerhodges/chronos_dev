"""Prometheus-compatible metrics endpoint for OPS-001/OPS-002."""

from fastapi import APIRouter, Response

from app.config import settings
from app.observability.monitoring import metrics_payload

router = APIRouter()


@router.get("/v1/metrics")
def metrics() -> Response:
    payload = metrics_payload(namespace=settings.metrics_namespace)
    return Response(content=payload, media_type="text/plain; version=0.0.4")
