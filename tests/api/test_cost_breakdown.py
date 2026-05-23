"""Maps to: ENG-013, NFR-003, NFR-006"""

from fastapi.testclient import TestClient

from app.main import app
from app.services.billing_service import BillingService, EffectivePricingSnapshot, monthly_limit_for_tier
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


def test_estimate_uses_pricebook_backed_overage_rate(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.cost_estimation.effective_pricing_for_plan",
        lambda plan_tier, pricing_metadata=None: EffectivePricingSnapshot(
            pricebook_version="test-pricebook-v2",
            subscription_price_id="price_custom_subscription",
            subscription_price_usd=99.0,
            included_minutes_monthly=60,
            overage_enabled=True,
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
    assert payload["effective_pricing"]["subscription_price_id"] == "price_custom_subscription"
