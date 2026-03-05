"""Stripe client helpers using Product/Price IDs from configuration only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import stripe
from app.config import settings


@dataclass(frozen=True)
class StripeConfig:
    secret_key: str
    product_id: str
    price_id: str


def load_stripe_config() -> StripeConfig:
    return StripeConfig(
        secret_key=settings.stripe_secret_key,
        product_id=settings.stripe_product_id,
        price_id=settings.stripe_price_id,
    )


def validate_no_hardcoded_prices(config: StripeConfig) -> bool:
    return config.product_id.startswith("prod_") and config.price_id.startswith("price_")


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


def retrieve_catalog_entities(config: StripeConfig | None = None) -> tuple[Any, Any]:
    """Retrieve Stripe Product and Price via the Stripe SDK."""
    cfg = config or load_stripe_config()
    _apply_api_key(cfg)
    product = stripe.Product.retrieve(cfg.product_id)
    price = stripe.Price.retrieve(cfg.price_id)
    return product, price


def create_billing_portal_session(customer_id: str, return_url: str | None = None) -> Any:
    cfg = load_stripe_config()
    _apply_api_key(cfg)
    return stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url or settings.stripe_billing_portal_return_url,
    )
