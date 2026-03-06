"""Maps to: ENG-002, NFR-007"""

from fastapi.testclient import TestClient

from app.main import app
from app.services.billing_service import BillingService, monthly_limit_for_tier
from tests.helpers.auth import fake_auth_header

client = TestClient(app)


def test_usage_endpoint_exposes_threshold_alerts_and_price_reference(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.users.billing_price_references",
        lambda: {
            "subscription_product_id": "prod_subscription",
            "subscription_price_id": "price_subscription",
            "overage_product_id": "prod_overage",
            "overage_price_id": "price_overage",
        },
    )
    service = BillingService()
    limit = monthly_limit_for_tier("museum")
    service.consume_minutes(user_id="usage-user", plan_tier="museum", minutes=int(limit * 0.9))
    service.record_estimate(user_id="usage-user", plan_tier="museum", estimated_minutes=12)

    response = client.get("/v1/users/me/usage", headers=fake_auth_header("usage-user", tier="museum"))
    assert response.status_code == 200
    payload = response.json()
    assert payload["threshold_alerts"] == [80, 90]
    assert payload["estimated_next_job_minutes"] == 12
    assert payload["price_reference"].startswith("price_")
    assert payload["overage_price_reference"].startswith("price_")
    assert payload["approved_overage_minutes"] == 0
    assert payload["remaining_approved_overage_minutes"] == 0
    assert payload["reconciliation_source"] == "user_usage_monthly"
    assert payload["reconciliation_status"] == "estimate_pending"
