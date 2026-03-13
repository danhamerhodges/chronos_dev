"""Packet 4B fidelity catalog routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.contracts import FidelityTierCatalogResponse
from app.api.dependencies import AuthenticatedUser, apply_rate_limit, get_current_user
from app.services.configuration_service import ConfigurationService

router = APIRouter()


def get_configuration_service() -> ConfigurationService:
    return ConfigurationService()


@router.get("/v1/fidelity-tiers", response_model=FidelityTierCatalogResponse)
def list_fidelity_tiers(
    user: AuthenticatedUser = Depends(get_current_user),
    configuration_service: ConfigurationService = Depends(get_configuration_service),
) -> FidelityTierCatalogResponse:
    apply_rate_limit(user, "/v1/fidelity-tiers")
    catalog = configuration_service.list_fidelity_tiers(
        user_id=user.user_id,
        role=user.role,
        plan_tier=user.plan_tier,
        org_id=user.org_id,
        access_token=user.access_token,
    )
    return FidelityTierCatalogResponse.model_validate(catalog)
