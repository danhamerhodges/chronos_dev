"""Maps to: ENG-013, NFR-003"""

from fastapi.testclient import TestClient

from app.main import app
from app.services.billing_service import BillingService, monthly_limit_for_tier
from tests.helpers.auth import fake_auth_header
from tests.helpers.jobs import create_seed_job, run_all_jobs, valid_job_request

client = TestClient(app)


def test_terminal_job_exposes_cost_estimate_and_reconciliation_summaries() -> None:
    created = create_seed_job(
        user_id="cost-reconciliation-user",
        tier="pro",
        payload=valid_job_request(estimated_duration_seconds=90, fidelity_tier="Restore"),
    )

    run_all_jobs()
    response = client.get(f"/v1/jobs/{created['job_id']}", headers=fake_auth_header("cost-reconciliation-user", tier="pro"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["cost_estimate_summary"]["estimator_version"] == "packet4e-v1"
    assert payload["cost_estimate_summary"]["usage_snapshot"]["estimated_next_job_minutes"] == 3
    assert payload["cost_summary"]["total_cost_usd"] >= 0
    assert payload["cost_reconciliation_summary"]["estimator_version"] == "packet4e-v1"
    assert payload["cost_reconciliation_summary"]["outlier_flagged"] is False


def test_terminal_job_flags_cost_reconciliation_outliers(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.job_runtime.calculate_operational_cost_summary",
        lambda **kwargs: {
            "gpu_seconds": kwargs["gpu_seconds"],
            "storage_operations": kwargs["storage_operations"],
            "api_calls": kwargs["api_calls"],
            "total_cost_usd": 25.0,
        },
    )
    created = create_seed_job(
        user_id="cost-outlier-user",
        tier="museum",
        payload=valid_job_request(estimated_duration_seconds=60, fidelity_tier="Restore"),
    )

    run_all_jobs()
    response = client.get(f"/v1/jobs/{created['job_id']}", headers=fake_auth_header("cost-outlier-user", tier="museum"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["cost_reconciliation_summary"]["actual_total_cost_usd"] == 25.0
    assert payload["cost_reconciliation_summary"]["outlier_flagged"] is True
    assert payload["cost_reconciliation_summary"]["delta_percent"] > 20.0


def test_terminal_reconciliation_uses_post_consumption_billing_state() -> None:
    billing = BillingService()
    monthly_limit = monthly_limit_for_tier("pro")
    billing.consume_minutes(user_id="cost-reconciliation-drift-user", plan_tier="pro", minutes=monthly_limit - 5)

    created = create_seed_job(
        user_id="cost-reconciliation-drift-user",
        tier="pro",
        payload=valid_job_request(estimated_duration_seconds=90, fidelity_tier="Restore"),
    )

    billing.consume_minutes(user_id="cost-reconciliation-drift-user", plan_tier="pro", minutes=4)

    run_all_jobs()
    response = client.get(
        f"/v1/jobs/{created['job_id']}",
        headers=fake_auth_header("cost-reconciliation-drift-user", tier="pro"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["cost_estimate_summary"]["billing_breakdown_usd"]["estimated_charge_total_usd"] == 0.0
    assert payload["cost_reconciliation_summary"]["actual_usage_minutes"] == 3
    assert payload["cost_reconciliation_summary"]["actual_charge_total_usd"] == 1.5


def test_terminal_job_still_completes_when_cost_signal_refresh_fails(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.job_runtime.refresh_cost_ops_signals",
        lambda: (_ for _ in ()).throw(RuntimeError("cost ops unavailable")),
    )

    created = create_seed_job(
        user_id="cost-signal-failure-user",
        tier="pro",
        payload=valid_job_request(estimated_duration_seconds=90, fidelity_tier="Restore"),
    )

    run_all_jobs()
    response = client.get(
        f"/v1/jobs/{created['job_id']}",
        headers=fake_auth_header("cost-signal-failure-user", tier="pro"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["cost_reconciliation_summary"]["estimator_version"] == "packet4e-v1"
