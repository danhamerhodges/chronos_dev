"""Maps to: NFR-012"""

import os

import pytest

from app.billing.stripe_client import (
    StripeConfig,
    create_billing_portal_session,
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
