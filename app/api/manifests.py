"""Transformation manifest routes for Packet 3B."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.contracts import TransformationManifestResponse
from app.api.dependencies import AuthenticatedUser, apply_rate_limit, require_permission
from app.services.job_service import JobService

router = APIRouter()
_job_service = JobService()


@router.get("/v1/manifests/{job_id}", response_model=TransformationManifestResponse)
def get_manifest(
    job_id: str,
    user: AuthenticatedUser = Depends(require_permission("jobs:read")),
) -> TransformationManifestResponse:
    apply_rate_limit(user, "/v1/manifests/{job_id}")
    manifest = _job_service.get_manifest(job_id, owner_user_id=user.user_id, access_token=user.access_token)
    return TransformationManifestResponse.model_validate(manifest)
