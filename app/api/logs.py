"""SEC-009 routes for log settings and deletion requests."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.contracts import DeleteLogsRequest, DeleteLogsResponse, LogSettingsResponse, LogSettingsUpdateRequest
from app.api.dependencies import AuthenticatedUser, apply_rate_limit, get_current_user, require_permission
from app.services.security_service import SecurityService

router = APIRouter()
_security_service = SecurityService()


@router.patch("/v1/orgs/{org_id}/settings/logs", response_model=LogSettingsResponse)
def patch_log_settings(
    org_id: str,
    payload: LogSettingsUpdateRequest,
    user: AuthenticatedUser = Depends(require_permission("logs:write")),
) -> LogSettingsResponse:
    apply_rate_limit(user, "/v1/orgs/{org_id}/settings/logs")
    record = _security_service.update_log_settings(
        org_id=org_id,
        user_id=user.user_id,
        plan_tier=user.plan_tier,
        retention_days=payload.retention_days,
        redaction_mode=payload.redaction_mode,
        categories=payload.categories,
        export_targets=payload.export_targets,
        access_token=user.access_token,
    )
    return LogSettingsResponse(
        org_id=record["org_id"],
        retention_days=record["retention_days"],
        redaction_mode=record["redaction_mode"],
        categories=record["categories"],
        export_targets=record["export_targets"],
        updated_by=record["updated_by"],
    )


@router.post("/v1/user/delete_logs", response_model=DeleteLogsResponse)
def delete_logs(
    payload: DeleteLogsRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> DeleteLogsResponse:
    apply_rate_limit(user, "/v1/user/delete_logs")
    record = _security_service.delete_logs(
        user_id=user.user_id,
        categories=payload.categories,
        date_from=payload.date_from,
        date_to=payload.date_to,
        reason=payload.reason,
        access_token=user.access_token,
    )
    return DeleteLogsResponse(
        deletion_request_id=record["deletion_request_id"],
        deletion_proof_id=record["deletion_proof_id"],
        deleted_categories=record["deleted_categories"],
        deleted_entries=record["deleted_entries"],
        status=record["status"],
    )
