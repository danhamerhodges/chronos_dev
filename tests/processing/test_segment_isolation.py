"""Maps to: ENG-012"""

from fastapi.testclient import TestClient

from app.main import app
from app.services.job_runtime import configure_segment_failures
from tests.helpers.auth import fake_auth_header
from tests.helpers.jobs import create_seed_job, run_all_jobs

client = TestClient(app)


def test_failed_segment_is_isolated_from_other_segments() -> None:
    created = create_seed_job(user_id="isolation-user")
    configure_segment_failures(created["job_id"], 1, ["persistent", "persistent", "persistent"])

    run_all_jobs()
    response = client.get(f"/v1/jobs/{created['job_id']}", headers=fake_auth_header("isolation-user"))

    assert response.status_code == 200
    segments = response.json()["segments"]
    assert [segment["status"] for segment in segments] == ["completed", "failed", "completed"]
