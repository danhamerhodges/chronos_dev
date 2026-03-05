"""Maps to: NFR-012"""

from app.billing.metering import billable_units, usage_event_key
from app.billing.stripe_client import lifecycle_capabilities


def test_usage_event_key_stable() -> None:
    assert usage_event_key("acct_1", "jobs", "day") == "acct_1:jobs:day"


def test_billable_units_non_negative() -> None:
    assert billable_units(-5) == 0


def test_subscription_lifecycle_capabilities_declared() -> None:
    capabilities = lifecycle_capabilities()
    assert "invoice_retrieval" in capabilities
    assert "customer_portal" in capabilities
