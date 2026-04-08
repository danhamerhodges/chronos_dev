"""Maps to: ENG-003"""

from fastapi.testclient import TestClient

from app.main import app
from tests.helpers.auth import fake_auth_header
from tests.helpers.jobs import create_seed_job, run_all_jobs

client = TestClient(app)


def test_segment_outputs_are_persisted_after_processing() -> None:
    created = create_seed_job(user_id="segment-user")

    run_all_jobs()
    response = client.get(f"/v1/jobs/{created['job_id']}", headers=fake_auth_header("segment-user"))

    assert response.status_code == 200
    segments = response.json()["segments"]
    assert len(segments) == 3
    assert all(segment["status"] == "completed" for segment in segments)
    assert all(segment["output_uri"].endswith(".mp4") for segment in segments)
