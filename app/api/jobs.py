"""Async restoration job routes for Packet 3A."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.contracts import (
    ExportVariant,
    JobCancelResponse,
    JobCreateRequest,
    JobCreateResponse,
    JobDetailResponse,
    JobEstimateResponse,
    JobExportResponse,
    JobListResponse,
    JobUncertaintyCalloutsResponse,
)
from app.api.dependencies import AuthenticatedUser, apply_rate_limit, require_permission
from app.services.job_service import JobService

router = APIRouter()
_job_service = JobService()


@router.post("/v1/jobs/estimate", response_model=JobEstimateResponse)
def estimate_job(
    payload: JobCreateRequest,
    user: AuthenticatedUser = Depends(require_permission("jobs:write")),
) -> JobEstimateResponse:
    apply_rate_limit(user, "/v1/jobs/estimate")
    estimate = _job_service.estimate_job(
        user_id=user.user_id,
        plan_tier=user.plan_tier,
        payload=payload.model_dump(),
        access_token=user.access_token,
    )
    return JobEstimateResponse.model_validate(estimate)


@router.post(
    "/v1/jobs",
    response_model=JobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_job(
    payload: JobCreateRequest,
    user: AuthenticatedUser = Depends(require_permission("jobs:write")),
) -> JobCreateResponse:
    apply_rate_limit(user, "/v1/jobs")
    job = _job_service.create_job(
        user_id=user.user_id,
        plan_tier=user.plan_tier,
        org_id=user.org_id,
        payload=payload.model_dump(),
        access_token=user.access_token,
    )
    return JobCreateResponse.model_validate(job)


@router.get("/v1/jobs/{job_id}", response_model=JobDetailResponse)
def get_job(
    job_id: str,
    response: Response,
    user: AuthenticatedUser = Depends(require_permission("jobs:read")),
) -> JobDetailResponse:
    apply_rate_limit(user, "/v1/jobs/{job_id}")
    response.headers["Cache-Control"] = "private, max-age=1"
    job = _job_service.get_job(job_id, owner_user_id=user.user_id, access_token=user.access_token)
    return JobDetailResponse.model_validate(job)


@router.get("/v1/jobs/{job_id}/uncertainty-callouts", response_model=JobUncertaintyCalloutsResponse)
def get_uncertainty_callouts(
    job_id: str,
    response: Response,
    user: AuthenticatedUser = Depends(require_permission("jobs:read")),
) -> JobUncertaintyCalloutsResponse:
    apply_rate_limit(user, "/v1/jobs/{job_id}/uncertainty-callouts")
    response.headers["Cache-Control"] = "private, max-age=1"
    payload = _job_service.get_uncertainty_callouts(job_id, owner_user_id=user.user_id, access_token=user.access_token)
    return JobUncertaintyCalloutsResponse.model_validate(payload)


@router.get("/v1/jobs/{job_id}/export", response_model=JobExportResponse)
def get_export(
    job_id: str,
    response: Response,
    variant: ExportVariant = Query(default=ExportVariant.AV1),
    retention_days: int = Query(default=7, ge=1, le=90),
    user: AuthenticatedUser = Depends(require_permission("jobs:read")),
) -> JobExportResponse:
    apply_rate_limit(user, "/v1/jobs/{job_id}/export")
    response.headers["Cache-Control"] = "private, no-store"
    payload = _job_service.get_export(
        job_id,
        owner_user_id=user.user_id,
        plan_tier=user.plan_tier,
        variant=variant.value,
        retention_days=retention_days,
        access_token=user.access_token,
    )
    return JobExportResponse.model_validate(payload)


@router.get("/v1/jobs", response_model=JobListResponse)
def list_jobs(user: AuthenticatedUser = Depends(require_permission("jobs:read"))) -> JobListResponse:
    apply_rate_limit(user, "/v1/jobs")
    jobs = _job_service.list_jobs(owner_user_id=user.user_id, access_token=user.access_token)
    return JobListResponse.model_validate({"jobs": jobs})


@router.delete("/v1/jobs/{job_id}", response_model=JobCancelResponse)
def cancel_job(
    job_id: str,
    user: AuthenticatedUser = Depends(require_permission("jobs:write")),
) -> JobCancelResponse:
    apply_rate_limit(user, "/v1/jobs/{job_id}")
    job = _job_service.request_cancellation(job_id, owner_user_id=user.user_id, access_token=user.access_token)
    return JobCancelResponse(
        job_id=job["job_id"],
        status=job["status"],
        cancel_requested_at=job["cancel_requested_at"],
    )
