"""Maps to: ENG-007"""

from fastapi.testclient import TestClient

import app.services.job_runtime as job_runtime
from app.main import app
from tests.helpers.auth import fake_auth_header
from tests.helpers.jobs import run_all_jobs, valid_job_request

client = TestClient(app)


def test_deterministic_mode_persists_reproducibility_summary() -> None:
    created = client.post(
        "/v1/jobs",
        headers=fake_auth_header("det-user", tier="pro"),
        json=valid_job_request(reproducibility_mode="deterministic"),
    ).json()

    run_all_jobs()
    response = client.get(f"/v1/jobs/{created['job_id']}", headers=fake_auth_header("det-user", tier="pro"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["reproducibility_mode"] == "deterministic"
    assert payload["reproducibility_summary"]["verification_status"] == "pass"
    assert payload["reproducibility_summary"]["rollup"] == "pass"


def test_reproducibility_failures_escalate_to_partial_rollup() -> None:
    created = client.post(
        "/v1/jobs",
        headers=fake_auth_header("repro-fail-user", tier="pro"),
        json=valid_job_request(reproducibility_mode="deterministic"),
    ).json()
    set_failures = client.post(
        f"/v1/testing/jobs/{created['job_id']}/segments/0/reproducibility-failures",
        headers=fake_auth_header("repro-fail-user", tier="pro"),
        json={"failures": 3},
    )

    run_all_jobs()
    response = client.get(
        f"/v1/jobs/{created['job_id']}",
        headers=fake_auth_header("repro-fail-user", tier="pro"),
    )

    assert set_failures.status_code == 200
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "partial"
    assert payload["failed_segments"] == [0]
    assert payload["reproducibility_summary"]["rollup"] == "critical"


def test_reproducibility_retry_branch_honors_backoff_sleep(monkeypatch) -> None:
    sleeps: list[int] = []
    monkeypatch.setattr(job_runtime, "_sleep_for_retry", lambda seconds: sleeps.append(seconds))

    created = client.post(
        "/v1/jobs",
        headers=fake_auth_header("repro-sleep-user", tier="pro"),
        json=valid_job_request(reproducibility_mode="deterministic"),
    ).json()
    response = client.post(
        f"/v1/testing/jobs/{created['job_id']}/segments/0/reproducibility-failures",
        headers=fake_auth_header("repro-sleep-user", tier="pro"),
        json={"failures": 2},
    )

    assert response.status_code == 200
    run_all_jobs()

    assert sleeps == [1, 2]
