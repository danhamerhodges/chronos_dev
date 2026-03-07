"""Trusted worker entrypoint and progress publishing boundary."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.api.problem_details import ProblemException
from app.config import settings
from app.db.client import SupabaseClient
from app.observability.monitoring import record_job_runtime_event

_PROGRESS_EVENTS: dict[str, list[dict[str, Any]]] = defaultdict(list)
_TEST_TRUSTED_TOKEN = "chronos-test-worker-token"


def default_trusted_worker_token() -> str:
    if settings.job_worker_trusted_token:
        return settings.job_worker_trusted_token
    if settings.environment == "test":
        return _TEST_TRUSTED_TOKEN
    raise RuntimeError("JOB_WORKER_TRUSTED_TOKEN is required for trusted worker execution outside test mode.")


def authorize_trusted_worker(trusted_token: str | None) -> str:
    expected = default_trusted_worker_token()
    if trusted_token != expected:
        raise ProblemException(
            title="Forbidden",
            detail="Trusted worker token is required for background job execution.",
            status_code=403,
        )
    return expected


def reset_worker_state() -> None:
    _PROGRESS_EVENTS.clear()


def progress_events_for_job(job_id: str) -> list[dict[str, Any]]:
    return [dict(event) for event in _PROGRESS_EVENTS.get(job_id, [])]


def publish_progress_event(
    *,
    trusted_token: str,
    payload: dict[str, Any],
) -> None:
    authorize_trusted_worker(trusted_token)
    _PROGRESS_EVENTS[str(payload["job_id"])].append(dict(payload))
    if settings.job_progress_mode.lower() == "supabase":
        SupabaseClient().broadcast_realtime_service_role(
            topic=str(payload["channel"]),
            event=str(payload["event"]),
            payload=payload,
        )
    record_job_runtime_event("progress_published")


def run_worker_message(
    message: dict[str, Any],
    *,
    trusted_token: str | None = None,
) -> dict[str, Any] | None:
    authorize_trusted_worker(trusted_token)
    from app.services.job_runtime import process_job

    record_job_runtime_event("worker_invoked")
    return process_job(str(message["job_id"]), trusted_token=trusted_token)
