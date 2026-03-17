"""Maps to: NFR-003, ENG-008"""

from fastapi.testclient import TestClient

from app.billing.stripe_client import BillingPricingMetadata
from app.main import app
from tests.helpers.auth import fake_auth_header

client = TestClient(app)


def test_cost_snapshot_reports_gpu_target_health(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.cost_ops.resolve_billing_pricing_metadata",
        lambda: BillingPricingMetadata(
            subscription_price_id="price_pro",
            overage_price_id="price_overage",
            overage_rate_usd_per_minute=0.75,
            subscription_price_usd=120.0,
            subscription_price_ids_by_tier={
                "hobbyist": "",
                "pro": "price_pro",
                "museum": "price_museum",
            },
            subscription_prices_usd_by_tier={
                "hobbyist": 0.0,
                "pro": 120.0,
                "museum": 500.0,
            },
        ),
    )
    monkeypatch.setattr(
        "app.services.cost_ops.current_runtime_snapshot",
        lambda: {
            "queue_depth": 0,
            "queue_age_seconds": 0.0,
            "desired_warm_instances": 1,
            "active_warm_instances": 1,
            "busy_instances": 0,
            "idle_instances": 1,
            "utilization_percent": 75.0,
            "alert_routes": {"pagerduty": "memory", "slack": "memory"},
            "incidents": [],
            "alerts": [],
            "training_calendar_url": None,
        },
    )

    response = client.get("/v1/ops/costs", headers=fake_auth_header("ops-admin", role="admin"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["operational_efficiency"]["gpu_utilization_percent"] == 75.0
    assert payload["operational_efficiency"]["autoscaler_idle_scale_down_healthy"] is True
    gpu_recommendation = next(
        item for item in payload["recommendations"] if item["category"] == "gpu_utilization"
    )
    assert gpu_recommendation["priority"] == "none"
    assert gpu_recommendation["action_required"] is False


def test_cost_snapshot_flags_idle_timeout_violation(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.cost_ops.resolve_billing_pricing_metadata",
        lambda: BillingPricingMetadata(
            subscription_price_id="price_pro",
            overage_price_id="price_overage",
            overage_rate_usd_per_minute=0.75,
            subscription_price_usd=120.0,
            subscription_price_ids_by_tier={
                "hobbyist": "",
                "pro": "price_pro",
                "museum": "price_museum",
            },
            subscription_prices_usd_by_tier={
                "hobbyist": 0.0,
                "pro": 120.0,
                "museum": 500.0,
            },
        ),
    )
    monkeypatch.setattr(
        "app.services.cost_ops.current_runtime_snapshot",
        lambda: {
            "queue_depth": 0,
            "queue_age_seconds": 0.0,
            "desired_warm_instances": 1,
            "active_warm_instances": 2,
            "busy_instances": 0,
            "idle_instances": 2,
            "utilization_percent": 20.0,
            "alert_routes": {"pagerduty": "memory", "slack": "memory"},
            "incidents": [],
            "alerts": [],
            "training_calendar_url": None,
        },
    )
    monkeypatch.setattr(
        "app.services.cost_ops.autoscaler_idle_scale_down_healthy",
        lambda snapshot: False,
    )

    response = client.get("/v1/ops/costs", headers=fake_auth_header("ops-admin", role="admin"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["operational_efficiency"]["autoscaler_idle_scale_down_healthy"] is False
