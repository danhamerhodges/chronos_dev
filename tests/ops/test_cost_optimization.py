"""Maps to: NFR-003, ENG-013"""

from fastapi.testclient import TestClient

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
