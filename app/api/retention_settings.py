"""SEC-005 routes for transformation manifest retention settings."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.contracts import ManifestRetentionSettingsResponse, ManifestRetentionSettingsUpdateRequest
from app.api.dependencies import AuthenticatedUser, apply_rate_limit, require_permission
from app.api.problem_details import ProblemException
from app.services.manifest_retention import ManifestRetentionService

router = APIRouter()
_manifest_retention_service = ManifestRetentionService()


@router.patch("/v1/orgs/{org_id}/settings/retention", response_model=ManifestRetentionSettingsResponse)
def patch_manifest_retention_settings(
    org_id: str,
    payload: ManifestRetentionSettingsUpdateRequest,
    user: AuthenticatedUser = Depends(require_permission("retention:write")),
) -> ManifestRetentionSettingsResponse:
    apply_rate_limit(user, "/v1/orgs/{org_id}/settings/retention")
    if org_id != user.org_id:
        raise ProblemException(
            title="Forbidden",
            detail="You do not have permission to modify this organization's retention settings.",
            status_code=403,
        )
    if user.plan_tier.lower() != "museum":
        raise ProblemException(
            title="Forbidden",
            detail="SEC-005 manifest retention settings are available only for Museum-tier organizations.",
            status_code=403,
        )
    try:
        record = _manifest_retention_service.update_settings(
            org_id=org_id,
            user_id=user.user_id,
            plan_tier=user.plan_tier,
            manifest_retention_days=payload.manifest_retention_days,
            manifest_redaction_enabled=payload.manifest_redaction_enabled,
            access_token=user.access_token,
        )
    except ValueError as exc:
        raise ProblemException(
            title="Invalid Retention Settings",
            detail=str(exc),
            status_code=400,
        ) from exc
    return ManifestRetentionSettingsResponse.model_validate(record)
