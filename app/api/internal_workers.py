"""Trusted internal worker ingress."""

from __future__ import annotations

import base64
from typing import Any

from fastapi import APIRouter, Header

from app.api.problem_details import ProblemException
from app.services.job_dispatcher import decode_dispatch_message_data
from app.services.job_worker import authorize_trusted_worker, run_worker_message
from app.services.runtime_ops import current_runtime_snapshot, evaluate_runtime_snapshot, reconcile_gpu_pool

router = APIRouter()


def _decode_pubsub_envelope(payload: dict[str, Any]) -> dict[str, Any]:
    message = payload.get("message")
    if not isinstance(message, dict):
        return payload
    encoded_data = message.get("data")
    if not isinstance(encoded_data, str) or not encoded_data:
        raise ProblemException(
            title="Invalid Worker Payload",
            detail="Pub/Sub push payload must include message.data.",
            status_code=400,
        )
    try:
        decoded_bytes = base64.b64decode(encoded_data)
        decoded = decode_dispatch_message_data(decoded_bytes)
    except ValueError as exc:
        raise ProblemException(
            title="Invalid Worker Payload",
            detail="Pub/Sub push payload could not be decoded as JSON.",
            status_code=400,
        ) from exc
    if not isinstance(decoded, dict):
        raise ProblemException(
            title="Invalid Worker Payload",
            detail="Decoded worker payload must be a JSON object.",
            status_code=400,
        )
    attributes = message.get("attributes")
    if isinstance(attributes, dict):
        decoded.setdefault("attributes", attributes)
    return decoded


@router.post("/internal/workers/jobs/run", include_in_schema=False)
def run_worker_job(
    payload: dict[str, Any],
    x_chronos_worker_token: str | None = Header(default=None),
) -> dict[str, Any]:
    trusted_token = authorize_trusted_worker(x_chronos_worker_token)
    message = _decode_pubsub_envelope(payload)
    result = run_worker_message(message, trusted_token=trusted_token)
    return {
        "job_id": message.get("job_id"),
        "status": result["status"] if result else "missing",
    }


@router.post("/internal/ops/runtime/reconcile", include_in_schema=False)
def reconcile_runtime_pool(
    payload: dict[str, Any] | None = None,
    x_chronos_worker_token: str | None = Header(default=None),
) -> dict[str, Any]:
    authorize_trusted_worker(x_chronos_worker_token)
    requested = payload or {}
    queue_depth = int(requested.get("queue_depth", 0) or 0)
    queue_age_seconds = float(requested.get("queue_age_seconds", 0.0) or 0.0)
    return reconcile_gpu_pool(queue_depth=queue_depth, queue_age_seconds=queue_age_seconds)


@router.post("/internal/ops/alerts/evaluate", include_in_schema=False)
def evaluate_runtime_alerts(
    payload: dict[str, Any] | None = None,
    x_chronos_worker_token: str | None = Header(default=None),
) -> dict[str, Any]:
    authorize_trusted_worker(x_chronos_worker_token)
    snapshot = current_runtime_snapshot()
    cache_summary = payload.get("cache_summary", {}) if isinstance(payload, dict) else {}
    incidents = evaluate_runtime_snapshot(snapshot, cache_summary)
    return {
        "snapshot": snapshot,
        "incident_count": len(incidents),
    }
