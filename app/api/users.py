"""User profile and usage routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.contracts import (
    OverageApprovalRequest,
    OverageApprovalResponse,
    UsageResponse,
    UserProfileResponse,
    UserProfileUpdateRequest,
)
from app.api.dependencies import AuthenticatedUser, apply_rate_limit, get_current_user
from app.api.problem_details import ProblemException
from app.billing.stripe_client import billing_price_references
from app.db.phase2_store import UserProfileRepository
from app.services.billing_service import BillingService

router = APIRouter()
_user_repo = UserProfileRepository()
_billing_service = BillingService()


@router.get("/v1/users/me", response_model=UserProfileResponse)
def get_me(user: AuthenticatedUser = Depends(get_current_user)) -> UserProfileResponse:
    apply_rate_limit(user, "/v1/users/me")
    profile = _user_repo.get_or_create(
        user_id=user.user_id,
        role=user.role,
        plan_tier=user.plan_tier,
        org_id=user.org_id,
        access_token=user.access_token,
    )
    return UserProfileResponse.model_validate(profile)


@router.patch("/v1/users/me", response_model=UserProfileResponse)
def patch_me(
    payload: UserProfileUpdateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> UserProfileResponse:
    apply_rate_limit(user, "/v1/users/me")
    _user_repo.get_or_create(
        user_id=user.user_id,
        role=user.role,
        plan_tier=user.plan_tier,
        org_id=user.org_id,
        access_token=user.access_token,
    )
    profile = _user_repo.update(user.user_id, payload.model_dump(), access_token=user.access_token)
    return UserProfileResponse.model_validate(profile)


@router.get("/v1/users/me/usage", response_model=UsageResponse)
def get_usage(user: AuthenticatedUser = Depends(get_current_user)) -> UsageResponse:
    apply_rate_limit(user, "/v1/users/me/usage")
    snapshot = _billing_service.snapshot(user_id=user.user_id, plan_tier=user.plan_tier, access_token=user.access_token)
    price_refs = billing_price_references()
    return UsageResponse(
        user_id=snapshot.user_id,
        plan_tier=snapshot.plan_tier,
        used_minutes=snapshot.used_minutes,
        monthly_limit_minutes=snapshot.monthly_limit_minutes,
        remaining_minutes=snapshot.remaining_minutes,
        estimated_next_job_minutes=snapshot.estimated_next_job_minutes,
        approved_overage_minutes=snapshot.approved_for_minutes,
        remaining_approved_overage_minutes=snapshot.remaining_approved_overage_minutes,
        threshold_alerts=snapshot.threshold_alerts,
        overage_approval_scope=snapshot.overage_approval_scope,
        hard_stop=snapshot.hard_stop,
        price_reference=price_refs["subscription_price_id"],
        overage_price_reference=price_refs["overage_price_id"],
        reconciliation_source=snapshot.reconciliation_source,
        reconciliation_status=snapshot.reconciliation_status,
    )


@router.post("/v1/users/me/approve-overage", response_model=OverageApprovalResponse)
def approve_overage(
    payload: OverageApprovalRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> OverageApprovalResponse:
    apply_rate_limit(user, "/v1/users/me/approve-overage")
    try:
        snapshot = _billing_service.approve_overage(
            user_id=user.user_id,
            plan_tier=user.plan_tier,
            approval_scope=payload.approval_scope,
            requested_minutes=payload.requested_minutes,
            access_token=user.access_token,
        )
    except ValueError as exc:
        raise ProblemException(
            title="Invalid Overage Approval",
            detail=str(exc),
            status_code=400,
            errors=[
                {
                    "field": "approval_scope",
                    "message": str(exc),
                    "rule_id": "NFR-007",
                }
            ],
        ) from exc
    price_refs = billing_price_references()
    return OverageApprovalResponse(
        user_id=snapshot.user_id,
        approval_scope=snapshot.overage_approval_scope or payload.approval_scope,
        approved_for_minutes=snapshot.approved_for_minutes,
        remaining_approved_overage_minutes=snapshot.remaining_approved_overage_minutes,
        remaining_minutes=snapshot.remaining_minutes,
        threshold_alerts=snapshot.threshold_alerts,
        overage_price_reference=price_refs["overage_price_id"],
    )
