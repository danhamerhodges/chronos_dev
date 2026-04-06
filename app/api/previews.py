"""Packet 4F preview session routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from app.api.contracts import (
    JobCreateResponse,
    PreviewCreateRequest,
    PreviewLaunchRequest,
    PreviewReviewRequest,
    PreviewSessionResponse,
)
from app.api.dependencies import AuthenticatedUser, apply_rate_limit, require_permission
from app.services.preview_generation import PreviewGenerationService

router = APIRouter()
_preview_service = PreviewGenerationService()


@router.post("/v1/previews", response_model=PreviewSessionResponse)
def create_preview(
    payload: PreviewCreateRequest,
    response: Response,
    user: AuthenticatedUser = Depends(require_permission("jobs:write")),
) -> PreviewSessionResponse:
    apply_rate_limit(user, "/v1/previews")
    response.headers["Cache-Control"] = "private, no-store"
    preview = _preview_service.create_preview(
        upload_id=payload.upload_id,
        owner_user_id=user.user_id,
        plan_tier=user.plan_tier,
        access_token=user.access_token,
    )
    return PreviewSessionResponse.model_validate(preview)


@router.get("/v1/previews/{preview_id}", response_model=PreviewSessionResponse)
def get_preview(
    preview_id: str,
    response: Response,
    user: AuthenticatedUser = Depends(require_permission("jobs:read")),
) -> PreviewSessionResponse:
    apply_rate_limit(user, "/v1/previews/{preview_id}")
    response.headers["Cache-Control"] = "private, max-age=1"
    preview = _preview_service.get_preview(
        preview_id,
        owner_user_id=user.user_id,
        access_token=user.access_token,
    )
    return PreviewSessionResponse.model_validate(preview)


@router.post("/v1/previews/{preview_id}/review", response_model=PreviewSessionResponse)
def review_preview(
    preview_id: str,
    payload: PreviewReviewRequest,
    response: Response,
    user: AuthenticatedUser = Depends(require_permission("jobs:write")),
) -> PreviewSessionResponse:
    apply_rate_limit(user, "/v1/previews/{preview_id}/review")
    response.headers["Cache-Control"] = "private, no-store"
    preview = _preview_service.review_preview(
        preview_id,
        owner_user_id=user.user_id,
        access_token=user.access_token,
        review_status=payload.review_status,
    )
    return PreviewSessionResponse.model_validate(preview)


@router.post(
    "/v1/previews/{preview_id}/launch",
    response_model=JobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def launch_preview(
    preview_id: str,
    payload: PreviewLaunchRequest,
    response: Response,
    user: AuthenticatedUser = Depends(require_permission("jobs:write")),
) -> JobCreateResponse:
    apply_rate_limit(user, "/v1/previews/{preview_id}/launch")
    response.headers["Cache-Control"] = "private, no-store"
    job = _preview_service.launch_preview(
        preview_id,
        owner_user_id=user.user_id,
        org_id=user.org_id,
        plan_tier=user.plan_tier,
        access_token=user.access_token,
        configuration_fingerprint_value=payload.configuration_fingerprint,
    )
    return JobCreateResponse.model_validate(job)
