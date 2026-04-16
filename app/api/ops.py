"""Admin runtime operations routes for Packet 3C and Packet 5D."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.contracts import (
    CostOpsSnapshotResponse,
    PricebookActivationRequest,
    PricebookActivationResponse,
    RuntimeOpsSnapshotResponse,
)
from app.api.dependencies import AuthenticatedUser, apply_rate_limit, require_permission
from app.api.problem_details import ProblemException
from app.services.billing_management import BillingManagementService
from app.services.cost_estimation import BillingPricingUnavailableError
from app.services.cost_ops import current_cost_ops_snapshot
from app.services.runtime_ops import current_runtime_snapshot

router = APIRouter()
_billing_management = BillingManagementService()


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


@router.put("/v1/ops/billing/pricebook", response_model=PricebookActivationResponse)
def activate_pricebook(
    payload: PricebookActivationRequest,
    user: AuthenticatedUser = Depends(require_permission("ops:write")),
) -> PricebookActivationResponse:
    apply_rate_limit(user, "/v1/ops/billing/pricebook")
    try:
        activated = _billing_management.activate_pricebook(
            payload=payload.payload,
            bootstrap_from_environment=payload.bootstrap_from_environment,
            change_summary=payload.change_summary,
            actor_user_id=user.user_id,
            actor_org_id=user.org_id,
        )
    except ValueError as exc:
        status_code = 409 if "already" in str(exc).lower() else 400
        raise ProblemException(
            title="Pricebook Activation Failed",
            detail=str(exc),
            status_code=status_code,
        ) from exc
    return PricebookActivationResponse(
        version=str(activated["version"]),
        source=str(activated["source"]),
        active=bool(activated.get("active", True)),
        activated_at=str(activated["activated_at"]),
    )
