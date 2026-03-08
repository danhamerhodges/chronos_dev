"""Upload routes for Packet 4A."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.contracts import (
    UploadCreateRequest,
    UploadFinalizeRequest,
    UploadResumeResponse,
    UploadResponse,
)
from app.api.dependencies import AuthenticatedUser, apply_rate_limit, require_permission
from app.services.upload_service import UploadService

router = APIRouter()
_upload_service = UploadService()


@router.post("/v1/upload", response_model=UploadResponse)
def create_upload(
    payload: UploadCreateRequest,
    user: AuthenticatedUser = Depends(require_permission("jobs:write")),
) -> UploadResponse:
    apply_rate_limit(user, "/v1/upload")
    upload = _upload_service.create_upload(
        user_id=user.user_id,
        org_id=user.org_id,
        payload=payload.model_dump(),
        access_token=user.access_token,
    )
    return UploadResponse.model_validate(upload)


@router.patch("/v1/upload/{upload_id}", response_model=UploadResponse)
def finalize_upload(
    upload_id: str,
    payload: UploadFinalizeRequest,
    user: AuthenticatedUser = Depends(require_permission("jobs:write")),
) -> UploadResponse:
    apply_rate_limit(user, "/v1/upload/{upload_id}")
    upload = _upload_service.finalize_upload(
        upload_id,
        owner_user_id=user.user_id,
        payload=payload.model_dump(),
        access_token=user.access_token,
    )
    return UploadResponse.model_validate(upload)


@router.post("/v1/upload/{upload_id}/resume", response_model=UploadResumeResponse)
def resume_upload(
    upload_id: str,
    user: AuthenticatedUser = Depends(require_permission("jobs:write")),
) -> UploadResumeResponse:
    apply_rate_limit(user, "/v1/upload/{upload_id}/resume")
    upload = _upload_service.resume_upload(
        upload_id,
        owner_user_id=user.user_id,
        access_token=user.access_token,
    )
    return UploadResumeResponse.model_validate(upload)
