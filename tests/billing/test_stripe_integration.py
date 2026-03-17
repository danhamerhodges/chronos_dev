"""Maps to: NFR-012"""

import os

import pytest

from app.billing.stripe_client import (
    StripeConfig,
    create_billing_portal_session,
    resolve_billing_pricing_metadata,
    retrieve_catalog_entities,
    validate_no_hardcoded_prices,
)


def test_stripe_identifiers_must_be_resource_ids() -> None:
    config = StripeConfig(
        secret_key="sk_test_x",
        product_id="prod_abc",
        price_id="price_xyz",
        overage_product_id="prod_overage",
        overage_price_id="price_overage",
    )
    assert validate_no_hardcoded_prices(config) is True


def test_billing_portal_requires_return_url() -> None:
    with pytest.raises(ValueError):
        create_billing_portal_session(customer_id="cus_test", return_url="   ")


def test_resolve_billing_pricing_metadata_returns_tier_specific_subscription_prices(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.billing.stripe_client.load_stripe_config",
        lambda: StripeConfig(
            secret_key="sk_test_x",
            product_id="prod_sub",
            price_id="price_shared",
            overage_product_id="prod_overage",
            overage_price_id="price_overage",
            hobbyist_price_id="price_hobbyist",
            pro_price_id="price_pro",
            museum_price_id="price_museum",
        ),
    )
    monkeypatch.setattr(
        "app.billing.stripe_client.stripe.Price.retrieve",
        lambda price_id: {
            "price_hobbyist": {"unit_amount": 0},
            "price_pro": {"unit_amount": 2900},
            "price_museum": {"unit_amount": 50000},
            "price_overage": {"unit_amount_decimal": "75"},
            "price_shared": {"unit_amount": 2900},
        }[price_id],
    )

    metadata = resolve_billing_pricing_metadata(cache_ttl_seconds=1)

    assert metadata.subscription_price_id_for_tier("hobbyist") == "price_hobbyist"
    assert metadata.subscription_price_id_for_tier("pro") == "price_pro"
    assert metadata.subscription_price_id_for_tier("museum") == "price_museum"
    assert metadata.subscription_price_usd_for_tier("hobbyist") == 0.0
    assert metadata.subscription_price_usd_for_tier("pro") == 29.0
    assert metadata.subscription_price_usd_for_tier("museum") == 500.0
    assert metadata.overage_rate_usd_per_minute == 0.75


def test_resolve_billing_pricing_metadata_supports_shared_price_fallback(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.billing.stripe_client.load_stripe_config",
        lambda: StripeConfig(
            secret_key="sk_test_x",
            product_id="prod_sub",
            price_id="price_shared",
            overage_product_id="prod_overage",
            overage_price_id="price_overage",
            hobbyist_price_id="",
            pro_price_id="",
            museum_price_id="",
        ),
    )
    monkeypatch.setattr(
        "app.billing.stripe_client.stripe.Price.retrieve",
        lambda price_id: {
            "price_shared": {"unit_amount": 2900},
            "price_overage": {"unit_amount_decimal": "75"},
        }[price_id],
    )

    metadata = resolve_billing_pricing_metadata(cache_ttl_seconds=1)

    assert metadata.subscription_price_id_for_tier("pro") == "price_shared"
    assert metadata.subscription_price_id_for_tier("museum") == "price_shared"
    assert metadata.subscription_price_usd_for_tier("pro") == 29.0
    assert metadata.subscription_price_usd_for_tier("museum") == 29.0
    assert metadata.subscription_price_usd_for_tier("hobbyist") == 0.0


@pytest.mark.skipif(
    os.getenv("CHRONOS_RUN_STRIPE_INTEGRATION") != "1",
    reason="Stripe integration tests disabled",
)
def test_stripe_catalog_retrieval_smoke() -> None:
    product, price = retrieve_catalog_entities()
    assert product is not None
    assert price is not None


@pytest.mark.skipif(
    os.getenv("CHRONOS_RUN_STRIPE_INTEGRATION") != "1",
    reason="Stripe integration tests disabled",
)
def test_stripe_billing_portal_smoke() -> None:
    customer_id = os.getenv("CHRONOS_TEST_STRIPE_CUSTOMER_ID", "")
    if not customer_id:
        pytest.skip("Missing CHRONOS_TEST_STRIPE_CUSTOMER_ID for billing portal integration")

    return_url = os.getenv("STRIPE_BILLING_PORTAL_RETURN_URL", "")
    if not return_url:
        pytest.skip("Missing STRIPE_BILLING_PORTAL_RETURN_URL for billing portal integration")

    session = create_billing_portal_session(customer_id=customer_id, return_url=return_url)
    assert session is not None
