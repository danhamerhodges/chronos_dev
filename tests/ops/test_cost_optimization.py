"""Maps to: NFR-003, ENG-013"""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.billing.stripe_client import BillingPricingMetadata
from app.db.phase2_store import JobRepository
from app.main import app
from app.observability.monitoring import record_cost_reconciliation
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


def test_cost_snapshot_uses_quarterly_window_for_recommendations(monkeypatch) -> None:
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
            "utilization_percent": 10.0,
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
            "total_cost_usd": 0.5,
        },
    )

    created = client.post(
        "/v1/jobs",
        headers=fake_auth_header("ops-quarterly-user", role="admin", tier="pro"),
        json=valid_job_request(estimated_duration_seconds=60, fidelity_tier="Restore"),
    ).json()

    run_all_jobs()
    quarterly_timestamp = (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%S")
    job = JobRepository().get_job_for_worker(created["job_id"])
    assert job is not None
    reconciliation_summary = dict(job["cost_reconciliation_summary"])
    reconciliation_summary["reconciled_at"] = quarterly_timestamp
    JobRepository().update_job_for_worker(
        created["job_id"],
        patch={
            "completed_at": quarterly_timestamp,
            "cache_summary": {"hits": 10, "misses": 0, "bypassed": 0},
            "gpu_summary": {
                "historical_utilization_percent": 95.0,
                "utilization_percent": 0.0,
            },
            "cost_reconciliation_summary": reconciliation_summary,
        },
    )

    snapshot = client.get("/v1/ops/costs", headers=fake_auth_header("ops-admin", role="admin"))

    assert snapshot.status_code == 200
    recommendations = {item["category"]: item for item in snapshot.json()["recommendations"]}
    assert recommendations["cache_efficiency"]["priority"] == "none"
    assert recommendations["cache_efficiency"]["action_required"] is False
    assert recommendations["gpu_utilization"]["priority"] == "none"
    assert recommendations["gpu_utilization"]["action_required"] is False


def test_negative_cost_reconciliation_inputs_do_not_make_counters_negative() -> None:
    record_cost_reconciliation(
        estimator_version="packet4e-v1",
        delta_percent=0.0,
        outlier=False,
        actual_total_cost_usd=-3.0,
        actual_charge_total_usd=-2.0,
    )

    metrics = client.get("/v1/metrics")

    assert metrics.status_code == 200
    assert 'chronos_cost_actual_total_usd_sum{estimator_version="packet4e-v1"} 0.0000' in metrics.text
    assert 'chronos_cost_actual_charge_total_usd_sum{estimator_version="packet4e-v1"} 0.0000' in metrics.text
    assert 'chronos_runtime_gauge{name="cost_actual_total_usd_latest:packet4e-v1"} 0.0' in metrics.text
    assert 'chronos_runtime_gauge{name="cost_actual_charge_total_usd_latest:packet4e-v1"} 0.0' in metrics.text
