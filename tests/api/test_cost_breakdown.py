"""Maps to: ENG-013, NFR-003"""

from fastapi.testclient import TestClient

from app.billing.stripe_client import BillingPricingMetadata
from app.main import app
from app.services.billing_service import BillingService, monthly_limit_for_tier
from tests.helpers.auth import fake_auth_header
from tests.helpers.jobs import valid_job_request

client = TestClient(app)


def test_estimate_breakdown_totals_match_component_sum() -> None:
    response = client.post(
        "/v1/jobs/estimate",
        headers=fake_auth_header("estimate-breakdown-user", tier="museum"),
        json=valid_job_request(estimated_duration_seconds=240, fidelity_tier="Restore"),
    )

    assert response.status_code == 200
    payload = response.json()
    operational = payload["operational_cost_breakdown_usd"]
    assert operational["total"] == round(operational["gpu_time"] + operational["storage"] + operational["api_calls"], 4)
    assert payload["confidence_interval_usd"]["high"] >= operational["total"]
    assert payload["confidence_interval_usd"]["low"] <= operational["total"]


def test_estimate_uses_configured_pricing_metadata_for_overage_rate(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.cost_estimation.resolve_billing_pricing_metadata",
        lambda: BillingPricingMetadata(
            subscription_price_id="price_custom_subscription",
            overage_price_id="price_custom_overage",
            overage_rate_usd_per_minute=1.23,
        ),
    )
    service = BillingService()
    limit = monthly_limit_for_tier("pro")
    service.consume_minutes(user_id="estimate-pricing-user", plan_tier="pro", minutes=limit)

    response = client.post(
        "/v1/jobs/estimate",
        headers=fake_auth_header("estimate-pricing-user", tier="pro"),
        json=valid_job_request(estimated_duration_seconds=120, fidelity_tier="Restore"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["billing_breakdown_usd"]["overage_rate_usd_per_minute"] == 1.23
    assert payload["billing_breakdown_usd"]["estimated_charge_total_usd"] == 3.69
