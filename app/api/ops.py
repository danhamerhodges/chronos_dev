"""Admin runtime operations routes for Packet 3C."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.contracts import CostOpsSnapshotResponse, RuntimeOpsSnapshotResponse
from app.api.dependencies import AuthenticatedUser, apply_rate_limit, require_permission
from app.api.problem_details import ProblemException
from app.services.cost_estimation import BillingPricingUnavailableError
from app.services.cost_ops import current_cost_ops_snapshot
from app.services.runtime_ops import current_runtime_snapshot

router = APIRouter()


@router.get("/v1/ops/runtime", response_model=RuntimeOpsSnapshotResponse)
def get_runtime_snapshot(
    user: AuthenticatedUser = Depends(require_permission("ops:read")),
) -> RuntimeOpsSnapshotResponse:
    apply_rate_limit(user, "/v1/ops/runtime")
    return RuntimeOpsSnapshotResponse.model_validate(current_runtime_snapshot())


@router.get("/v1/ops/costs", response_model=CostOpsSnapshotResponse)
def get_cost_snapshot(
    user: AuthenticatedUser = Depends(require_permission("ops:read")),
) -> CostOpsSnapshotResponse:
    apply_rate_limit(user, "/v1/ops/costs")
    try:
        return CostOpsSnapshotResponse.model_validate(current_cost_ops_snapshot())
    except BillingPricingUnavailableError as exc:
        raise ProblemException(
            title="Billing Pricing Unavailable",
            detail="Pricing data is temporarily unavailable. Retry the request once billing metadata is available.",
            status_code=503,
        ) from exc
