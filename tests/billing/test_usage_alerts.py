"""Maps to: ENG-002, NFR-006, NFR-007"""

from fastapi.testclient import TestClient

from app.main import app
from app.services.billing_service import BillingService, monthly_limit_for_tier
from tests.helpers.auth import fake_auth_header

client = TestClient(app)


def test_usage_endpoint_exposes_threshold_alerts_and_effective_pricing() -> None:
    service = BillingService()
    limit = monthly_limit_for_tier("museum")
    service.consume_minutes(user_id="usage-user", plan_tier="museum", minutes=int(limit * 0.9))
    service.record_estimate(user_id="usage-user", plan_tier="museum", estimated_minutes=12)

    response = client.get("/v1/users/me/usage", headers=fake_auth_header("usage-user", tier="museum"))
    assert response.status_code == 200
    payload = response.json()
    assert payload["threshold_alerts"] == [80, 90]
    assert payload["estimated_next_job_minutes"] == 12
    assert payload["price_reference"] == "price_museum"
    assert payload["overage_price_reference"] == "price_museum_overage"
    assert payload["approved_overage_minutes"] == 0
    assert payload["remaining_approved_overage_minutes"] == 0
    assert payload["reconciliation_source"] == "user_usage_monthly"
    assert payload["reconciliation_status"] == "estimate_pending"
    assert payload["effective_pricing"] == {
        "pricebook_version": "test-pricebook-v1",
        "subscription_price_id": "price_museum",
        "subscription_price_usd": 500.0,
        "included_minutes_monthly": 500,
        "overage_enabled": True,
        "overage_price_id": "price_museum_overage",
        "overage_rate_usd_per_minute": 0.4,
        "entitlement_source": "commercial_pricebook",
    }
