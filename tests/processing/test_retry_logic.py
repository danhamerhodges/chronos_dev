"""Maps to: ENG-012"""

from fastapi.testclient import TestClient

from app.main import app
from app.services.job_runtime import configure_segment_failures, dead_letter_jobs
from tests.helpers.auth import fake_auth_header
from tests.helpers.jobs import run_all_jobs, valid_job_request

client = TestClient(app)


def test_persistent_segment_failure_exhausts_three_attempts() -> None:
    created = client.post("/v1/jobs", headers=fake_auth_header("persistent-user"), json=valid_job_request()).json()
    configure_segment_failures(created["job_id"], 0, ["persistent", "persistent", "persistent"])
    configure_segment_failures(created["job_id"], 1, ["persistent", "persistent", "persistent"])
    configure_segment_failures(created["job_id"], 2, ["persistent", "persistent", "persistent"])

    run_all_jobs()
    response = client.get(f"/v1/jobs/{created['job_id']}", headers=fake_auth_header("persistent-user"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "failed"
    assert all(segment["attempt_count"] == 3 for segment in payload["segments"])
    assert created["job_id"] in dead_letter_jobs()
