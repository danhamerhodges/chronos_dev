"""Stripe client helpers using Product/Price IDs from configuration only."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
import time
from typing import Any

import stripe
from app.config import settings


@dataclass(frozen=True)
class StripeConfig:
    secret_key: str
    product_id: str
    price_id: str
    overage_product_id: str
    overage_price_id: str
    hobbyist_price_id: str = ""
    pro_price_id: str = ""
    museum_price_id: str = ""


@dataclass(frozen=True)
class BillingPricingMetadata:
    subscription_price_id: str
    overage_price_id: str
    overage_rate_usd_per_minute: float
    subscription_price_usd: float = 0.0
    subscription_price_ids_by_tier: dict[str, str] | None = None
    subscription_prices_usd_by_tier: dict[str, float] | None = None

    def subscription_price_id_for_tier(self, plan_tier: str) -> str:
        normalized_tier = plan_tier.strip().lower()
        tier_mapping = self.subscription_price_ids_by_tier or {}
        if normalized_tier in tier_mapping:
            return str(tier_mapping[normalized_tier])
        return str(self.subscription_price_id)

    def subscription_price_usd_for_tier(self, plan_tier: str) -> float:
        normalized_tier = plan_tier.strip().lower()
        tier_mapping = self.subscription_prices_usd_by_tier or {}
        if normalized_tier in tier_mapping:
            return float(tier_mapping[normalized_tier])
        return float(self.subscription_price_usd)


def load_stripe_config() -> StripeConfig:
    return StripeConfig(
        secret_key=settings.stripe_secret_key,
        product_id=settings.stripe_product_id,
        price_id=settings.stripe_price_id,
        hobbyist_price_id=settings.stripe_hobbyist_price_id,
        pro_price_id=settings.stripe_pro_price_id,
        museum_price_id=settings.stripe_museum_price_id,
        overage_product_id=settings.stripe_overage_product_id,
        overage_price_id=settings.stripe_overage_price_id,
    )


def validate_no_hardcoded_prices(config: StripeConfig) -> bool:
    tier_price_ids = [config.hobbyist_price_id, config.pro_price_id, config.museum_price_id]
    return (
        config.product_id.startswith("prod_")
        and config.price_id.startswith("price_")
        and config.overage_product_id.startswith("prod_")
        and config.overage_price_id.startswith("price_")
        and all((not price_id) or price_id.startswith("price_") for price_id in tier_price_ids)
    )


def billing_price_references(config: StripeConfig | None = None) -> dict[str, str]:
    cfg = config or load_stripe_config()
    return {
        "subscription_product_id": cfg.product_id,
        "subscription_price_id": cfg.price_id,
        "overage_product_id": cfg.overage_product_id,
        "overage_price_id": cfg.overage_price_id,
    }


def lifecycle_capabilities() -> list[str]:
    return [
        "create_subscription",
        "update_subscription",
        "cancel_subscription",
        "invoice_retrieval",
        "customer_portal",
        "tax_calculation",
    ]


def _apply_api_key(config: StripeConfig) -> None:
    stripe.api_key = config.secret_key


def _cache_bucket(ttl_seconds: int) -> int:
    return int(time.time() // max(ttl_seconds, 1))


def _stripe_field(resource: Any, field: str) -> Any:
    if isinstance(resource, dict):
        return resource.get(field)
    value = getattr(resource, field, None)
    if value is not None:
        return value
    try:
        return resource[field]
    except Exception:
        return None


@lru_cache(maxsize=16)
def _cached_overage_rate(secret_key: str, overage_price_id: str, cache_bucket: int) -> float:
    del cache_bucket
    stripe.api_key = secret_key
    price = stripe.Price.retrieve(overage_price_id)
    raw_amount = _stripe_field(price, "unit_amount_decimal")
    if raw_amount is None:
        raw_amount = _stripe_field(price, "unit_amount")
    if raw_amount is None:
        raise ValueError("Stripe overage price is missing unit_amount metadata.")
    return float((Decimal(str(raw_amount)) / Decimal("100")).quantize(Decimal("0.0001")))


@lru_cache(maxsize=16)
def _cached_subscription_price(secret_key: str, subscription_price_id: str, cache_bucket: int) -> float:
    del cache_bucket
    stripe.api_key = secret_key
    price = stripe.Price.retrieve(subscription_price_id)
    raw_amount = _stripe_field(price, "unit_amount_decimal")
    if raw_amount is None:
        raw_amount = _stripe_field(price, "unit_amount")
    if raw_amount is None:
        raise ValueError("Stripe subscription price is missing unit_amount metadata.")
    return float((Decimal(str(raw_amount)) / Decimal("100")).quantize(Decimal("0.0001")))


def _subscription_price_ids_by_tier(config: StripeConfig) -> dict[str, str]:
    default_paid_price_id = config.price_id
    return {
        "hobbyist": config.hobbyist_price_id,
        "pro": config.pro_price_id or default_paid_price_id,
        "museum": config.museum_price_id or default_paid_price_id,
    }


def retrieve_catalog_entities(config: StripeConfig | None = None) -> tuple[Any, Any]:
    """Retrieve Stripe Product and Price via the Stripe SDK."""
    cfg = config or load_stripe_config()
    _apply_api_key(cfg)
    product = stripe.Product.retrieve(cfg.product_id)
    price = stripe.Price.retrieve(cfg.price_id)
    return product, price


def resolve_billing_pricing_metadata(
    config: StripeConfig | None = None,
    *,
    cache_ttl_seconds: int = 300,
) -> BillingPricingMetadata:
    cfg = config or load_stripe_config()
    if not cfg.secret_key:
        raise ValueError("STRIPE_SECRET_KEY is required for billing price resolution.")
    cache_bucket = _cache_bucket(cache_ttl_seconds)
    subscription_price_ids_by_tier = _subscription_price_ids_by_tier(cfg)
    subscription_prices_usd_by_tier = {
        tier: (
            _cached_subscription_price(
                cfg.secret_key,
                price_id,
                cache_bucket,
            )
            if price_id
            else 0.0
        )
        for tier, price_id in subscription_price_ids_by_tier.items()
    }
    return BillingPricingMetadata(
        subscription_price_id=cfg.price_id,
        overage_price_id=cfg.overage_price_id,
        overage_rate_usd_per_minute=_cached_overage_rate(
            cfg.secret_key,
            cfg.overage_price_id,
            cache_bucket,
        ),
        subscription_price_usd=subscription_prices_usd_by_tier.get("pro", 0.0),
        subscription_price_ids_by_tier=subscription_price_ids_by_tier,
        subscription_prices_usd_by_tier=subscription_prices_usd_by_tier,
    )


def create_billing_portal_session(customer_id: str, return_url: str | None = None) -> Any:
    cfg = load_stripe_config()
    _apply_api_key(cfg)
    effective_return_url = (return_url or settings.stripe_billing_portal_return_url).strip()
    if not effective_return_url:
        raise ValueError("STRIPE_BILLING_PORTAL_RETURN_URL is required for billing portal sessions")

    return stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=effective_return_url,
    )
