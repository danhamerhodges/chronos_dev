"""Admin runtime operations routes for Packet 3C."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.contracts import RuntimeOpsSnapshotResponse
from app.api.dependencies import AuthenticatedUser, apply_rate_limit, require_permission
from app.services.runtime_ops import current_runtime_snapshot

router = APIRouter()


@router.get("/v1/ops/runtime", response_model=RuntimeOpsSnapshotResponse)
def get_runtime_snapshot(
    user: AuthenticatedUser = Depends(require_permission("ops:read")),
) -> RuntimeOpsSnapshotResponse:
    apply_rate_limit(user, "/v1/ops/runtime")
    return RuntimeOpsSnapshotResponse.model_validate(current_runtime_snapshot())
