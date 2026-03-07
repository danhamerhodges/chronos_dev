"""Maps to: NFR-002"""

from fastapi.testclient import TestClient

from app.main import app
from tests.helpers.auth import fake_auth_header
from tests.helpers.jobs import run_all_jobs, valid_job_request

client = TestClient(app)


def test_job_stage_timings_are_recorded_for_baseline_slo_reporting() -> None:
    created = client.post("/v1/jobs", headers=fake_auth_header("perf-user", tier="pro"), json=valid_job_request()).json()

    run_all_jobs()
    response = client.get(f"/v1/jobs/{created['job_id']}", headers=fake_auth_header("perf-user", tier="pro"))
    metrics = client.get("/v1/metrics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["stage_timings"]["processing_ms"] is not None
    assert payload["stage_timings"]["encoding_ms"] is not None
    assert payload["stage_timings"]["total_ms"] >= payload["stage_timings"]["processing_ms"]
    assert payload["stage_timings"]["queue_wait_ms"] is not None
    assert payload["stage_timings"]["allocation_ms"] is not None
    assert payload["slo_summary"]["target_total_ms"] == 54000
    assert payload["performance_summary"]["throughput_ratio"] is not None
    assert "job_stage_duration_ms_sum" in metrics.text
