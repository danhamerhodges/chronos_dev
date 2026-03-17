"""Maps to: NFR-003, ENG-013"""

from fastapi.testclient import TestClient

from app.billing.stripe_client import BillingPricingMetadata
from app.main import app
from tests.helpers.auth import fake_auth_header
from tests.helpers.jobs import run_all_jobs, valid_job_request

client = TestClient(app)


def test_cost_reconciliation_outliers_emit_monitoring_signal(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.job_runtime.calculate_operational_cost_summary",
        lambda **kwargs: {
            "gpu_seconds": kwargs["gpu_seconds"],
            "storage_operations": kwargs["storage_operations"],
            "api_calls": kwargs["api_calls"],
            "total_cost_usd": 40.0,
        },
    )
    client.post(
        "/v1/jobs",
        headers=fake_auth_header("ops-cost-user", tier="museum"),
        json=valid_job_request(estimated_duration_seconds=60, fidelity_tier="Restore"),
    )

    run_all_jobs()
    metrics = client.get("/v1/metrics")

    assert metrics.status_code == 200
    assert "cost_reconciliations_total" in metrics.text
    assert 'cost_reconciliation_outliers_total{estimator_version="packet4e-v1"} 1' in metrics.text


def test_cost_snapshot_generates_quarterly_recommendations_and_cost_ops_metrics(monkeypatch) -> None:
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
            "utilization_percent": 55.0,
            "alert_routes": {"pagerduty": "memory", "slack": "memory"},
            "incidents": [],
            "alerts": [],
            "training_calendar_url": None,
        },
    )
    monkeypatch.setattr(
        "app.services.job_runtime.calculate_operational_cost_summary",
        lambda **kwargs: {
            "gpu_seconds": kwargs["gpu_seconds"],
            "storage_operations": kwargs["storage_operations"],
            "api_calls": kwargs["api_calls"],
            "total_cost_usd": 40.0,
        },
    )
    client.post(
        "/v1/jobs",
        headers=fake_auth_header("ops-opt-user", tier="museum"),
        json=valid_job_request(estimated_duration_seconds=60, fidelity_tier="Restore"),
    )

    run_all_jobs()
    metrics = client.get("/v1/metrics")
    snapshot = client.get("/v1/ops/costs", headers=fake_auth_header("ops-admin", role="admin"))

    assert snapshot.status_code == 200
    categories = {item["category"] for item in snapshot.json()["recommendations"]}
    assert categories == {
        "cache_efficiency",
        "gpu_utilization",
        "cost_anomaly_remediation",
        "gross_margin_protection",
    }
    assert metrics.status_code == 200
    assert "cost_actual_total_usd_sum" in metrics.text
    assert "cost_margin_breaches_total" in metrics.text
    assert "cost_anomalies_total" in metrics.text
    assert 'runtime_gauge{name="cost_ops_gross_margin_percent"}' in metrics.text
    assert 'runtime_gauge{name="cost_ops_recent_anomaly_count"}' in metrics.text
