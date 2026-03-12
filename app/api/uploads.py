"""Upload routes for Packet 4A."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.contracts import (
    UploadConfigurationRequest,
    UploadConfigurationResponse,
    UploadCreateRequest,
    UploadDetectEraRequest,
    UploadDetectEraResponse,
    UploadFinalizeRequest,
    UploadResumeResponse,
    UploadResponse,
)
from app.api.dependencies import AuthenticatedUser, apply_rate_limit, require_permission
from app.services.configuration_service import ConfigurationService
from app.services.upload_service import UploadService

router = APIRouter()


def get_upload_service() -> UploadService:
    return UploadService()


def get_configuration_service() -> ConfigurationService:
    return ConfigurationService()


@router.post("/v1/upload", response_model=UploadResponse)
def create_upload(
    payload: UploadCreateRequest,
    user: AuthenticatedUser = Depends(require_permission("jobs:write")),
    upload_service: UploadService = Depends(get_upload_service),
) -> UploadResponse:
    apply_rate_limit(user, "/v1/upload")
    upload = upload_service.create_upload(
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
    upload_service: UploadService = Depends(get_upload_service),
) -> UploadResponse:
    apply_rate_limit(user, "/v1/upload/{upload_id}")
    upload = upload_service.finalize_upload(
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
    upload_service: UploadService = Depends(get_upload_service),
) -> UploadResumeResponse:
    apply_rate_limit(user, "/v1/upload/{upload_id}/resume")
    upload = upload_service.resume_upload(
        upload_id,
        owner_user_id=user.user_id,
        access_token=user.access_token,
    )
    return UploadResumeResponse.model_validate(upload)


@router.post("/v1/upload/{upload_id}/detect-era", response_model=UploadDetectEraResponse)
def detect_upload_era(
    upload_id: str,
    payload: UploadDetectEraRequest,
    user: AuthenticatedUser = Depends(require_permission("jobs:write")),
    configuration_service: ConfigurationService = Depends(get_configuration_service),
) -> UploadDetectEraResponse:
    apply_rate_limit(user, "/v1/upload/{upload_id}/detect-era")
    detection = configuration_service.detect_upload_era(
        upload_id=upload_id,
        user_id=user.user_id,
        role=user.role,
        plan_tier=user.plan_tier,
        org_id=user.org_id,
        payload=payload.model_dump(),
        access_token=user.access_token,
    )
    return UploadDetectEraResponse.model_validate(detection)


@router.patch("/v1/upload/{upload_id}/configuration", response_model=UploadConfigurationResponse)
def save_upload_configuration(
    upload_id: str,
    payload: UploadConfigurationRequest,
    user: AuthenticatedUser = Depends(require_permission("jobs:write")),
    configuration_service: ConfigurationService = Depends(get_configuration_service),
) -> UploadConfigurationResponse:
    apply_rate_limit(user, "/v1/upload/{upload_id}/configuration")
    configuration = configuration_service.save_upload_configuration(
        upload_id=upload_id,
        user_id=user.user_id,
        role=user.role,
        plan_tier=user.plan_tier,
        org_id=user.org_id,
        payload=payload.model_dump(),
        access_token=user.access_token,
    )
    return UploadConfigurationResponse.model_validate(configuration)
