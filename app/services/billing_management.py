"""Billing management services for Packet 5D."""

from __future__ import annotations

from typing import Any

from app.billing.stripe_client import create_billing_portal_session, resolve_billing_pricing_metadata
from app.config import settings
from app.db.phase2_store import BillingAccountRepository, BillingAuditRepository
from app.observability.monitoring import record_billing_event
from app.services.billing_service import CommercialPricingUnavailableError, effective_pricing_for_plan
from app.services.commercial_pricebook_service import (
    activate_pricebook_revision,
    bootstrap_pricebook_revision_from_environment,
)


class BillingPortalUnavailableError(RuntimeError):
    """Raised when a billing portal session cannot be created."""


def _effective_pricing_payload(effective_pricing) -> dict[str, Any]:
    return {
        "pricebook_version": effective_pricing.pricebook_version,
        "subscription_price_id": effective_pricing.subscription_price_id,
        "subscription_price_usd": effective_pricing.subscription_price_usd,
        "included_minutes_monthly": effective_pricing.included_minutes_monthly,
        "overage_enabled": effective_pricing.overage_enabled,
        "overage_price_id": effective_pricing.overage_price_id,
        "overage_rate_usd_per_minute": effective_pricing.overage_rate_usd_per_minute,
        "entitlement_source": effective_pricing.entitlement_source,
    }


class BillingManagementService:
    def __init__(self) -> None:
        self._accounts = BillingAccountRepository()
        self._audit = BillingAuditRepository()

    def billing_summary(
        self,
        *,
        user_id: str,
        org_id: str,
        plan_tier: str,
        access_token: str,
    ) -> dict[str, Any]:
        account = self._accounts.get_by_org(org_id, access_token=access_token)
        effective_pricing = effective_pricing_for_plan(
            plan_tier,
            org_id=org_id,
            access_token=access_token,
            pricing_metadata=resolve_billing_pricing_metadata(),
        )
        record_billing_event("billing_summary", outcome="success")
        return {
            "org_id": org_id,
            "user_id": user_id,
            "plan_tier": plan_tier,
            "subscription_status": account.get("subscription_status") if account else None,
            "stripe_customer_id": account.get("stripe_customer_id") if account else None,
            "portal_available": bool(account and account.get("stripe_customer_id")),
            "effective_pricing": _effective_pricing_payload(effective_pricing),
            "recent_invoices": list((account or {}).get("recent_invoices") or []),
            "museum_quote": {
                "quote_id": str(account.get("museum_quote_id")),
                "status": str(account.get("museum_quote_status") or ""),
            }
            if account and account.get("museum_quote_id")
            else None,
        }

    def create_portal_session(self, *, org_id: str, access_token: str) -> str:
        account = self._accounts.get_by_org(org_id, access_token=access_token)
        customer_id = str((account or {}).get("stripe_customer_id") or "").strip()
        if not customer_id:
            record_billing_event("portal_session", outcome="unavailable")
            raise BillingPortalUnavailableError(
                "A Stripe customer binding is required before a billing portal session can be created."
            )
        try:
            session = create_billing_portal_session(
                customer_id=customer_id,
                return_url=settings.stripe_billing_portal_return_url,
            )
        except ValueError as exc:
            record_billing_event("portal_session", outcome="misconfigured")
            raise BillingPortalUnavailableError(str(exc)) from exc
        url_value = getattr(session, "url", None)
        if url_value is None and isinstance(session, dict):
            url_value = session.get("url")
        url = str(url_value or "").strip()
        if not url:
            record_billing_event("portal_session", outcome="invalid")
            raise BillingPortalUnavailableError("Stripe billing portal session did not return a URL.")
        record_billing_event("portal_session", outcome="success")
        return url

    def activate_pricebook(
        self,
        *,
        payload: dict[str, Any] | None,
        bootstrap_from_environment: bool,
        change_summary: str,
        actor_user_id: str,
        actor_org_id: str,
    ) -> dict[str, Any]:
        if bootstrap_from_environment:
            if not settings.commercial_pricebook_bootstrap_enabled:
                raise ValueError("Hosted environment bootstrap import is not enabled.")
            activated = bootstrap_pricebook_revision_from_environment(
                applied_by_user_id=actor_user_id,
                applied_by_org_id=actor_org_id,
                change_summary=change_summary,
            )
        else:
            if payload is None:
                raise ValueError("payload is required unless bootstrap_from_environment is true.")
            activated = activate_pricebook_revision(
                payload=payload,
                applied_by_user_id=actor_user_id,
                applied_by_org_id=actor_org_id,
                change_summary=change_summary,
            )
        self._audit.append_event(
            org_id=actor_org_id,
            source="billing_pricebook",
            event_type="pricebook_activated",
            actor_user_id=actor_user_id,
            before_summary={},
            after_summary={
                "active_version": activated["version"],
                "source": activated["source"],
            },
        )
        record_billing_event("pricebook_activation", outcome="success")
        return activated
