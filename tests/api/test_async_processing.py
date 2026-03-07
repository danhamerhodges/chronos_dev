"""Maps to: ENG-011"""

from fastapi.testclient import TestClient

from app.main import app
from tests.helpers.auth import fake_auth_header
from tests.helpers.jobs import valid_job_request

client = TestClient(app)


def test_job_submission_returns_queued_job_id_immediately() -> None:
    response = client.post("/v1/jobs", headers=fake_auth_header("job-user-1"), json=valid_job_request())

    assert response.status_code == 202
    payload = response.json()
    assert payload["job_id"]
    assert payload["status"] == "queued"
    assert payload["effective_fidelity_tier"] == "Restore"
    assert payload["reproducibility_mode"] == "perceptual_equivalence"
    assert payload["manifest_available"] is False
    assert payload["performance_summary"]["stage_timings"]["queue_wait_ms"] is None
    assert payload["cache_summary"]["hits"] == 0
    assert payload["gpu_summary"]["gpu_runtime_seconds"] == 0
    assert payload["cost_summary"]["total_cost_usd"] == 0.0
    assert payload["slo_summary"]["target_total_ms"] == 54000
    assert payload["progress"]["status"] == "queued"
    assert payload["progress"]["segment_count"] == 3


def test_cross_user_job_lookup_is_denied() -> None:
    created = client.post("/v1/jobs", headers=fake_auth_header("job-owner"), json=valid_job_request()).json()

    response = client.get(
        f"/v1/jobs/{created['job_id']}",
        headers=fake_auth_header("other-user"),
    )

    assert response.status_code == 404
    assert response.json()["title"] == "Not Found"


def test_list_jobs_returns_only_current_user_jobs() -> None:
    client.post("/v1/jobs", headers=fake_auth_header("job-user-a"), json=valid_job_request())
    client.post(
        "/v1/jobs",
        headers=fake_auth_header("job-user-b"),
        json=valid_job_request(original_filename="other.mov"),
    )

    response = client.get("/v1/jobs", headers=fake_auth_header("job-user-a"))

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["jobs"]) == 1
    assert payload["jobs"][0]["original_filename"] == "sample.mov"
