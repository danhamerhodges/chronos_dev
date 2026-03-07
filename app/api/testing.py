"""Test-only helpers."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import AuthenticatedUser, get_current_user
from app.api.problem_details import ProblemException
from app.config import settings
from app.services.job_runtime import configure_reproducibility_failures, configure_segment_failures, drain_job_queue
from app.services.rate_limits import reset_rate_limits

router = APIRouter()


class SegmentFailureRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    failures: list[str] = Field(default_factory=list)


class ReproducibilityFailureRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    failures: int = Field(default=0, ge=0)


def _require_testing_mode(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    if settings.environment != "test":
        raise ProblemException(
            title="Not Found",
            detail="Testing helpers are only available in the test environment.",
            status_code=404,
        )
    return user


@router.post("/v1/testing/reset-rate-limits")
def reset_rate_limit_state(user: AuthenticatedUser = Depends(_require_testing_mode)) -> dict[str, str]:
    _ = user
    return reset_rate_limits()


@router.post("/v1/testing/jobs/run-dispatcher")
def run_dispatcher_once(user: AuthenticatedUser = Depends(_require_testing_mode)) -> dict[str, object]:
    _ = user
    processed = drain_job_queue()
    return {"processed_jobs": processed}


@router.post("/v1/testing/jobs/{job_id}/segments/{segment_index}/failures")
def set_segment_failures(
    job_id: str,
    segment_index: int,
    payload: SegmentFailureRequest,
    user: AuthenticatedUser = Depends(_require_testing_mode),
) -> dict[str, object]:
    _ = user
    configure_segment_failures(job_id, segment_index, payload.failures)
    return {"job_id": job_id, "segment_index": segment_index, "failures": payload.failures}


@router.post("/v1/testing/jobs/{job_id}/segments/{segment_index}/reproducibility-failures")
def set_reproducibility_failures(
    job_id: str,
    segment_index: int,
    payload: ReproducibilityFailureRequest,
    user: AuthenticatedUser = Depends(_require_testing_mode),
) -> dict[str, object]:
    _ = user
    configure_reproducibility_failures(job_id, segment_index, payload.failures)
    return {"job_id": job_id, "segment_index": segment_index, "failures": payload.failures}
