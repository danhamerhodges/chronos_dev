"""Era-detection routes for Phase 2."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.contracts import DetectEraRequest, DetectEraResponse, EraCatalogResponse
from app.api.dependencies import AuthenticatedUser, apply_rate_limit, get_current_user
from app.api.problem_details import ProblemException
from app.services.billing_service import BillingService, billable_minutes_for_duration
from app.services.era_detection_service import EraDetectionService
from app.validation.schema_validation import validate_era_profile

router = APIRouter()
_era_detection_service = EraDetectionService()
_billing_service = BillingService()


@router.get("/v1/eras", response_model=EraCatalogResponse)
def list_eras() -> EraCatalogResponse:
    return EraCatalogResponse(eras=_era_detection_service.supported_eras())


@router.post("/v1/detect-era", response_model=DetectEraResponse)
def detect_era(request: DetectEraRequest, user: AuthenticatedUser = Depends(get_current_user)) -> DetectEraResponse:
    apply_rate_limit(user, "/v1/detect-era")
    validation = validate_era_profile(request.era_profile.model_dump())
    if not validation.is_valid:
        raise ProblemException(
            title="Schema Validation Failed",
            detail="Era profile validation failed. Fix the highlighted fields and retry.",
            status_code=400,
            errors=validation.as_problem_errors(),
        )
    if request.manual_override_era and not _era_detection_service.is_supported_era(request.manual_override_era):
        raise ProblemException(
            title="Unsupported Era Override",
            detail="Manual override era must match one of the supported eras returned by /v1/eras.",
            status_code=400,
            errors=[
                {
                    "field": "manual_override_era",
                    "message": "Manual override era must match the supported era catalog.",
                    "rule_id": "FR-002",
                }
            ],
        )

    detection = _era_detection_service.detect(
        job_id=request.job_id,
        user_id=user.user_id,
        org_id=user.org_id,
        media_uri=request.media_uri,
        original_filename=request.original_filename,
        mime_type=request.mime_type,
        payload=request.model_dump(),
        access_token=user.access_token,
    )
    estimated_usage_minutes = billable_minutes_for_duration(
        duration_seconds=request.estimated_duration_seconds,
        mode=request.era_profile.mode,
    )
    _billing_service.record_estimate(
        user_id=user.user_id,
        plan_tier=user.plan_tier,
        estimated_minutes=estimated_usage_minutes,
        access_token=user.access_token,
    )
    detection["estimated_usage_minutes"] = estimated_usage_minutes
    detection["warnings"].extend(issue.message for issue in validation.warnings)
    return DetectEraResponse.model_validate(detection)
