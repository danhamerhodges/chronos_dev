"""Maps to: NFR-003, ENG-013"""

from fastapi.testclient import TestClient

from app.billing.stripe_client import BillingPricingMetadata
from app.db.phase2_store import JobRepository
from app.main import app
from app.services.billing_service import BillingService, monthly_limit_for_tier
from app.services.runtime_ops import incident_history
from tests.helpers.auth import fake_auth_header
from tests.helpers.jobs import create_seed_job, run_all_jobs, valid_job_request

client = TestClient(app)


def _pricing_metadata(*, hobbyist: float = 0.0, pro: float, museum: float) -> BillingPricingMetadata:
    return BillingPricingMetadata(
        subscription_price_id="price_pro",
        overage_price_id="price_overage",
        overage_rate_usd_per_minute=0.75,
        subscription_price_usd=pro,
        subscription_price_ids_by_tier={
            "hobbyist": "" if hobbyist == 0.0 else "price_hobbyist",
            "pro": "price_pro",
            "museum": "price_museum",
        },
        subscription_prices_usd_by_tier={
            "hobbyist": hobbyist,
            "pro": pro,
            "museum": museum,
        },
    )


def _cost_metric_lines(metrics_text: str) -> list[str]:
    prefixes = (
        "chronos_cost_anomalies_total",
        "chronos_cost_margin_breaches_total",
        "chronos_runtime_gauge{name=\"cost_ops_",
    )
    return [line for line in metrics_text.splitlines() if line.startswith(prefixes)]


def test_cost_snapshot_reports_totals_and_margin(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.cost_ops.resolve_billing_pricing_metadata",
        lambda: _pricing_metadata(pro=900.0, museum=1500.0),
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
            "utilization_percent": 72.5,
            "alert_routes": {"pagerduty": "memory", "slack": "memory"},
            "incidents": [],
            "alerts": [],
            "training_calendar_url": None,
        },
    )
    monkeypatch.setattr(
        "app.services.job_runtime.calculate_operational_cost_summary",
        lambda **kwargs: {
            "gpu_seconds": 60,
            "storage_operations": 2,
            "api_calls": 1,
            "total_cost_usd": 0.5,
        },
    )

    create_seed_job(
        user_id="ops-cost-admin",
        tier="pro",
        payload=valid_job_request(estimated_duration_seconds=60, fidelity_tier="Restore"),
    )

    run_all_jobs()
    response = client.get("/v1/ops/costs", headers=fake_auth_header("ops-admin", role="admin", tier="pro"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["cost_totals_usd"] == {
        "gpu": 0.72,
        "storage": 0.002,
        "api": 0.0,
        "actual_charge_total": 0.0,
    }
    assert payload["gross_margin_summary"]["revenue_total_usd"] == 3.0
    assert payload["gross_margin_summary"]["cost_total_usd"] == 0.5
    assert payload["gross_margin_summary"]["gross_margin_percent"] == 83.33
    assert payload["gross_margin_summary"]["below_target"] is False
    assert payload["operational_efficiency"]["gpu_utilization_percent"] == 72.5


def test_cost_snapshot_ignores_terminal_pool_gpu_snapshot_without_historical_samples() -> None:
    runtime_snapshot = {"utilization_percent": 72.5}
    jobs = [
        {"gpu_summary": {"utilization_percent": 0.0}},
    ]

    from app.services.cost_ops import _gpu_utilization_percent

    assert _gpu_utilization_percent(jobs, runtime_snapshot) == 72.5


def test_cost_snapshot_flags_margin_breach_and_incident(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.cost_ops.resolve_billing_pricing_metadata",
        lambda: _pricing_metadata(pro=60.0, museum=120.0),
    )
    monkeypatch.setattr(
        "app.services.job_runtime.calculate_operational_cost_summary",
        lambda **kwargs: {
            "gpu_seconds": 60,
            "storage_operations": 7,
            "api_calls": 6,
            "total_cost_usd": 0.727,
        },
    )

    create_seed_job(
        user_id="ops-margin-admin",
        tier="pro",
        payload=valid_job_request(estimated_duration_seconds=60, fidelity_tier="Restore"),
    )

    run_all_jobs()
    incidents = incident_history()
    assert any(item["source_signal"].startswith("gross-margin-breach-") for item in incidents)
    response = client.get("/v1/ops/costs", headers=fake_auth_header("ops-admin", role="admin", tier="pro"))

    assert response.status_code == 200
    payload = response.json()
    anomaly = payload["recent_anomalies"][0]
    assert anomaly["anomaly_types"] == ["gross_margin"]
    assert anomaly["gross_margin_percent"] == -263.5
    assert payload["gross_margin_summary"]["below_target"] is True
    assert any(item["source_signal"] == f"gross-margin-breach-{anomaly['job_id']}" for item in incidents)


def test_cost_delta_incident_emits_without_ops_snapshot_poll(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.cost_ops.resolve_billing_pricing_metadata",
        lambda: _pricing_metadata(pro=120.0, museum=500.0),
    )
    monkeypatch.setattr(
        "app.services.job_runtime.calculate_operational_cost_summary",
        lambda **kwargs: {
            "gpu_seconds": kwargs["gpu_seconds"],
            "storage_operations": kwargs["storage_operations"],
            "api_calls": kwargs["api_calls"],
            "total_cost_usd": 25.0,
        },
    )

    create_seed_job(
        user_id="ops-delta-user",
        tier="museum",
        payload=valid_job_request(estimated_duration_seconds=60, fidelity_tier="Restore"),
    )

    run_all_jobs()

    incidents = incident_history()
    assert any(item["source_signal"].startswith("cost-anomaly-") for item in incidents)


def test_cost_ops_snapshot_is_side_effect_free(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.cost_ops.resolve_billing_pricing_metadata",
        lambda: _pricing_metadata(pro=120.0, museum=500.0),
    )
    monkeypatch.setattr(
        "app.services.job_runtime.calculate_operational_cost_summary",
        lambda **kwargs: {
            "gpu_seconds": kwargs["gpu_seconds"],
            "storage_operations": kwargs["storage_operations"],
            "api_calls": kwargs["api_calls"],
            "total_cost_usd": 25.0,
        },
    )

    create_seed_job(
        user_id="ops-side-effect-user",
        tier="museum",
        payload=valid_job_request(estimated_duration_seconds=60, fidelity_tier="Restore"),
    )

    run_all_jobs()
    monkeypatch.setattr(
        "app.services.cost_ops._emit_anomaly_incidents",
        lambda anomalies: (_ for _ in ()).throw(AssertionError("GET /v1/ops/costs must not emit incidents")),
    )
    monkeypatch.setattr(
        "app.services.cost_ops.record_cost_ops_snapshot",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("GET /v1/ops/costs must not mutate monitoring state")),
    )
    incidents_before = incident_history()
    metrics_before = _cost_metric_lines(client.get("/v1/metrics").text)

    response = client.get("/v1/ops/costs", headers=fake_auth_header("ops-admin", role="admin", tier="museum"))

    assert response.status_code == 200
    assert incident_history() == incidents_before
    metrics_after = _cost_metric_lines(client.get("/v1/metrics").text)
    assert metrics_after == metrics_before


def test_cost_snapshot_excludes_non_completed_jobs_even_with_reconciliation(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.cost_ops.resolve_billing_pricing_metadata",
        lambda: _pricing_metadata(pro=120.0, museum=500.0),
    )
    created = create_seed_job(
        user_id="ops-queued-user",
        tier="pro",
        payload=valid_job_request(estimated_duration_seconds=60, fidelity_tier="Restore"),
    )
    JobRepository().update_job_for_worker(
        created["job_id"],
        patch={
            "cost_reconciliation_summary": {
                "actual_total_cost_usd": 25.0,
                "actual_charge_total_usd": 1.5,
                "actual_usage_minutes": 3,
                "delta_usd": 24.0,
                "delta_percent": 96.0,
                "reconciled_at": "2026-03-19T12:00:00+00:00",
            },
        },
    )

    response = client.get("/v1/ops/costs", headers=fake_auth_header("ops-admin", role="admin", tier="pro"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["cost_totals_usd"] == {
        "gpu": 0.0,
        "storage": 0.0,
        "api": 0.0,
        "actual_charge_total": 0.0,
    }
    assert payload["recent_anomalies"] == []


def test_negative_cost_delta_does_not_emit_anomaly(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.cost_ops.resolve_billing_pricing_metadata",
        lambda: _pricing_metadata(pro=900.0, museum=1500.0),
    )
    monkeypatch.setattr(
        "app.services.job_runtime.calculate_operational_cost_summary",
        lambda **kwargs: {
            "gpu_seconds": kwargs["gpu_seconds"],
            "storage_operations": kwargs["storage_operations"],
            "api_calls": kwargs["api_calls"],
            "total_cost_usd": 0.05,
        },
    )

    create_seed_job(
        user_id="ops-negative-delta-user",
        tier="pro",
        payload=valid_job_request(estimated_duration_seconds=60, fidelity_tier="Restore"),
    )

    run_all_jobs()
    response = client.get("/v1/ops/costs", headers=fake_auth_header("ops-admin", role="admin", tier="pro"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["recent_anomalies"] == []
    assert not any(item["source_signal"].startswith("cost-anomaly-") for item in incident_history())


def test_cost_snapshot_returns_503_when_pricing_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.cost_ops.resolve_billing_pricing_metadata",
        lambda: (_ for _ in ()).throw(ValueError("missing pricing")),
    )

    response = client.get("/v1/ops/costs", headers=fake_auth_header("ops-admin", role="admin"))

    assert response.status_code == 503
    payload = response.json()
    assert payload["title"] == "Billing Pricing Unavailable"


def test_cost_snapshot_uses_reconciled_usage_split_for_revenue(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.cost_ops.resolve_billing_pricing_metadata",
        lambda: _pricing_metadata(pro=120.0, museum=500.0),
    )
    billing = BillingService()
    monthly_limit = monthly_limit_for_tier("pro")
    billing.consume_minutes(user_id="ops-revenue-split-user", plan_tier="pro", minutes=monthly_limit - 5)

    created = create_seed_job(
        user_id="ops-revenue-split-user",
        tier="pro",
        payload=valid_job_request(estimated_duration_seconds=90, fidelity_tier="Restore"),
    )

    billing.consume_minutes(user_id="ops-revenue-split-user", plan_tier="pro", minutes=4)

    run_all_jobs()
    response = client.get(
        "/v1/ops/costs",
        headers=fake_auth_header("ops-admin", role="admin", tier="pro"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["recent_anomalies"][0]["anomaly_types"] == ["gross_margin"]
    assert payload["gross_margin_summary"]["revenue_total_usd"] == 1.7
    assert payload["cost_totals_usd"]["actual_charge_total"] == 1.5
    assert created["job_id"]
