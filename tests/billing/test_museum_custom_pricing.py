"""
Maps to:
- NFR-006
"""

from app.billing.stripe_client import BillingPricingMetadata
from app.db.phase2_store import BillingAccountRepository
from app.services.billing_service import effective_pricing_for_plan


def _pricing_metadata() -> BillingPricingMetadata:
    return BillingPricingMetadata(
        subscription_price_id="price_pro",
        overage_price_id="price_overage",
        overage_rate_usd_per_minute=0.75,
        subscription_price_usd=120.0,
        subscription_price_ids_by_tier={
            "hobbyist": "price_hobbyist",
            "pro": "price_pro",
            "museum": "price_museum",
        },
        subscription_prices_usd_by_tier={
            "hobbyist": 0.0,
            "pro": 29.0,
            "museum": 500.0,
        },
    )


def test_museum_recurring_override_wins_over_quote_pricing() -> None:
    BillingAccountRepository().upsert_by_org(
        org_id="org-museum-recurring",
        owner_user_id="museum-owner",
        patch={
            "subscription_price_id": "price_museum_recurring_custom",
            "subscription_price_usd": 750.0,
            "included_minutes_monthly": 800,
            "overage_price_id": "price_museum_overage_custom",
            "overage_rate_usd_per_minute": 0.35,
            "museum_quote_pricing": {
                "subscription_price_id": "price_museum_quote_custom",
                "subscription_price_usd": 650.0,
                "included_minutes_monthly": 700,
                "overage_price_id": "price_museum_quote_overage",
                "overage_rate_usd_per_minute": 0.45,
            },
        },
    )

    effective = effective_pricing_for_plan(
        "museum",
        org_id="org-museum-recurring",
        pricing_metadata=_pricing_metadata(),
    )

    assert effective.subscription_price_id == "price_museum_recurring_custom"
    assert effective.subscription_price_usd == 750.0
    assert effective.included_minutes_monthly == 800
    assert effective.overage_price_id == "price_museum_overage_custom"
    assert effective.entitlement_source == "museum_recurring_override"


def test_museum_quote_override_applies_when_no_recurring_override_exists() -> None:
    BillingAccountRepository().upsert_by_org(
        org_id="org-museum-quote",
        owner_user_id="museum-owner",
        patch={
            "museum_quote_pricing": {
                "subscription_price_id": "price_museum_quote_custom",
                "subscription_price_usd": 640.0,
                "included_minutes_monthly": 720,
                "overage_price_id": "price_museum_quote_overage",
                "overage_rate_usd_per_minute": 0.42,
            },
        },
    )

    effective = effective_pricing_for_plan(
        "museum",
        org_id="org-museum-quote",
        pricing_metadata=_pricing_metadata(),
    )

    assert effective.subscription_price_id == "price_museum_quote_custom"
    assert effective.subscription_price_usd == 640.0
    assert effective.included_minutes_monthly == 720
    assert effective.overage_price_id == "price_museum_quote_overage"
    assert effective.entitlement_source == "museum_quote_override"
