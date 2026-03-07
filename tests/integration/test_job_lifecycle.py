"""Maps to: ENG-011, ENG-012"""

from fastapi.testclient import TestClient

from app.main import app
from tests.helpers.auth import fake_auth_header
from tests.helpers.jobs import run_all_jobs, valid_job_request

client = TestClient(app)


def test_job_lifecycle_transitions_from_queued_to_completed() -> None:
    created = client.post("/v1/jobs", headers=fake_auth_header("lifecycle-user"), json=valid_job_request()).json()

    assert created["status"] == "queued"

    run_all_jobs()
    response = client.get(f"/v1/jobs/{created['job_id']}", headers=fake_auth_header("lifecycle-user"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["manifest_available"] is True
    assert payload["performance_summary"]["total_ms"] is not None
    assert payload["quality_summary"]["thresholds_met"] is True
    assert payload["cache_summary"]["hits"] >= 0
    assert payload["gpu_summary"]["gpu_type"] == "L4"
    assert payload["cost_summary"]["gpu_seconds"] >= 0
    assert payload["slo_summary"]["compliant"] in {True, False}
    assert payload["progress"]["percent_complete"] == 100.0
    assert payload["result_uri"].endswith("/result.mp4")


def test_job_cancellation_is_cooperatively_applied() -> None:
    created = client.post("/v1/jobs", headers=fake_auth_header("cancel-user"), json=valid_job_request()).json()

    cancel = client.delete(f"/v1/jobs/{created['job_id']}", headers=fake_auth_header("cancel-user"))
    run_all_jobs()
    response = client.get(f"/v1/jobs/{created['job_id']}", headers=fake_auth_header("cancel-user"))

    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancel_requested"
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
