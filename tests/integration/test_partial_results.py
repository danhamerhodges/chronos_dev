"""Maps to: ENG-012"""

from fastapi.testclient import TestClient

from app.main import app
from app.services.job_runtime import configure_segment_failures
from tests.helpers.auth import fake_auth_header
from tests.helpers.jobs import create_seed_job, run_all_jobs

client = TestClient(app)


def test_partial_results_are_returned_when_one_segment_fails() -> None:
    created = create_seed_job(user_id="partial-user")
    configure_segment_failures(created["job_id"], 1, ["persistent", "persistent", "persistent"])

    run_all_jobs()
    response = client.get(f"/v1/jobs/{created['job_id']}", headers=fake_auth_header("partial-user"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "partial"
    assert payload["failed_segments"] == [1]
    assert payload["warnings"] == ["One or more segments failed. Partial results are available."]
    assert payload["result_uri"].endswith("/partial-result.mp4")
