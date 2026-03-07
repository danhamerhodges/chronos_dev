"""Maps to: ENG-011"""

from fastapi.testclient import TestClient

from app.main import app
from app.services.job_runtime import progress_events_for_job
from tests.helpers.auth import fake_auth_header
from tests.helpers.jobs import run_all_jobs, valid_job_request

client = TestClient(app)


def test_progress_events_match_canonical_payload_contract() -> None:
    created = client.post("/v1/jobs", headers=fake_auth_header("progress-user"), json=valid_job_request()).json()

    run_all_jobs()
    events = progress_events_for_job(created["job_id"])

    assert events
    latest = events[-1]
    assert latest["channel"] == f"job_progress:{created['job_id']}"
    assert latest["event"] == "progress_update"
    assert set(latest) >= {
        "job_id",
        "segment_index",
        "segment_count",
        "percent_complete",
        "eta_seconds",
        "status",
        "current_operation",
        "updated_at",
    }


def test_job_status_polling_uses_one_second_cache_ttl() -> None:
    created = client.post("/v1/jobs", headers=fake_auth_header("poll-user"), json=valid_job_request()).json()

    response = client.get(f"/v1/jobs/{created['job_id']}", headers=fake_auth_header("poll-user"))

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "private, max-age=1"


def test_polling_response_matches_latest_progress_event() -> None:
    created = client.post("/v1/jobs", headers=fake_auth_header("progress-sync-user"), json=valid_job_request()).json()

    run_all_jobs()
    response = client.get(f"/v1/jobs/{created['job_id']}", headers=fake_auth_header("progress-sync-user"))
    latest = progress_events_for_job(created["job_id"])[-1]

    assert response.status_code == 200
    payload = response.json()
    assert payload["progress"]["status"] == latest["status"]
    assert payload["progress"]["percent_complete"] == latest["percent_complete"]
    assert payload["progress"]["eta_seconds"] == latest["eta_seconds"]
