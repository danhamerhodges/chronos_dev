"""Maps to: ENG-012"""

from fastapi.testclient import TestClient

import app.services.job_runtime as job_runtime
from app.main import app
from app.services.job_runtime import configure_segment_failures
from tests.helpers.auth import fake_auth_header
from tests.helpers.jobs import create_seed_job, run_all_jobs

client = TestClient(app)


def test_transient_failure_retries_and_recovers_segment() -> None:
    created = create_seed_job(user_id="retry-user")
    configure_segment_failures(created["job_id"], 0, ["transient", "network"])

    run_all_jobs()
    response = client.get(f"/v1/jobs/{created['job_id']}", headers=fake_auth_header("retry-user"))

    assert response.status_code == 200
    first_segment = response.json()["segments"][0]
    assert first_segment["status"] == "completed"
    assert first_segment["attempt_count"] == 3
    assert first_segment["retry_backoffs_seconds"] == [1, 2]


def test_transient_failure_retry_branch_honors_backoff_sleep(monkeypatch) -> None:
    sleeps: list[int] = []
    monkeypatch.setattr(job_runtime, "_sleep_for_retry", lambda seconds: sleeps.append(seconds))

    created = create_seed_job(user_id="retry-sleep-user")
    configure_segment_failures(created["job_id"], 0, ["transient", "network"])

    run_all_jobs()

    assert sleeps == [1, 2]
