"""
Maps to:
- ENG-011
- FR-006
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.phase2_store import reset_phase2_store
from app.services import preview_generation as preview_generation_service
from app.services.job_dispatcher import queued_dispatch_messages, reset_job_dispatcher_state
from app.services.job_service import JobService
from tests.helpers.auth import fake_auth_header
from tests.helpers.jobs import valid_job_request
from tests.helpers.previews import seed_completed_upload, seed_detection, save_configuration_with_approved_preview

client = TestClient(app)


def setup_function() -> None:
    reset_phase2_store()
    reset_job_dispatcher_state()


def _approved_launch_payload(*, upload_id: str, owner_user_id: str) -> dict[str, object]:
    seed_completed_upload(upload_id=upload_id, owner_user_id=owner_user_id)
    seed_detection(upload_id=upload_id, owner_user_id=owner_user_id)
    configuration = save_configuration_with_approved_preview(
        client,
        upload_id=upload_id,
        owner_user_id=owner_user_id,
    )
    return dict(configuration["job_payload_preview"])


def test_job_submission_requires_approved_preview_provenance() -> None:
    response = client.post("/v1/jobs", headers=fake_auth_header("job-user-1"), json=valid_job_request())

    assert response.status_code == 409
    payload = response.json()
    assert payload["type"] == "/problems/preview_approval_required"
    assert "approved-preview launch provenance" in payload["detail"]


def test_job_submission_returns_422_for_malformed_launch_context() -> None:
    response = client.post(
        "/v1/jobs",
        headers=fake_auth_header("job-user-1"),
        json=valid_job_request(
            launch_context={
                "source": "legacy_job_launch",
                "upload_id": 123,
                "configuration_fingerprint": "short",
            }
        ),
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["title"] == "Request Validation Failed"
    assert {item["field"] for item in payload["errors"]} >= {
        "launch_context.source",
        "launch_context.upload_id",
        "launch_context.configuration_fingerprint",
    }


def test_approved_generic_job_launch_is_idempotent_and_returns_same_job_id() -> None:
    payload = _approved_launch_payload(upload_id="job-approved-upload", owner_user_id="job-approved-user")
    headers = fake_auth_header("job-approved-user", tier="pro")

    first = client.post("/v1/jobs", headers=headers, json=payload)
    second = client.post("/v1/jobs", headers=headers, json=payload)

    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json()["job_id"] == first.json()["job_id"]
    assert first.json()["status"] == "queued"
    assert len(queued_dispatch_messages()) == 1


def test_generic_launch_retry_reuses_job_id_after_dispatch_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _approved_launch_payload(upload_id="job-dispatch-retry-upload", owner_user_id="job-dispatch-retry-user")
    headers = fake_auth_header("job-dispatch-retry-user", tier="pro")
    attempts = {"count": 0}
    original_publish = preview_generation_service.publish_job

    def flaky_publish(job_id: str, *, plan_tier: str, source: str = "api"):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("dispatch offline")
        return original_publish(job_id, plan_tier=plan_tier, source=source)

    monkeypatch.setattr(preview_generation_service, "publish_job", flaky_publish)

    first = client.post("/v1/jobs", headers=headers, json=payload)
    second = client.post("/v1/jobs", headers=headers, json=payload)

    assert first.status_code == 503
    assert first.json()["type"] == "/problems/launch_dispatch_failed"
    assert second.status_code == 202
    assert second.json()["job_id"]
    assert second.json()["job_id"] == queued_dispatch_messages()[0].job_id


def test_cross_user_job_lookup_is_denied() -> None:
    created = JobService().create_job(
        user_id="job-owner",
        plan_tier="pro",
        org_id="org-default",
        payload=valid_job_request(),
        access_token="test-token-for-job-owner",
        publish_immediately=False,
    )

    response = client.get(
        f"/v1/jobs/{created['job_id']}",
        headers=fake_auth_header("other-user"),
    )

    assert response.status_code == 404
    assert response.json()["title"] == "Not Found"


def test_list_jobs_returns_only_current_user_jobs() -> None:
    service = JobService()
    service.create_job(
        user_id="job-user-a",
        plan_tier="pro",
        org_id="org-default",
        payload=valid_job_request(),
        access_token="test-token-for-job-user-a",
        publish_immediately=False,
    )
    service.create_job(
        user_id="job-user-b",
        plan_tier="pro",
        org_id="org-default",
        payload=valid_job_request(original_filename="other.mov"),
        access_token="test-token-for-job-user-b",
        publish_immediately=False,
    )

    response = client.get("/v1/jobs", headers=fake_auth_header("job-user-a"))

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["jobs"]) == 1
    assert payload["jobs"][0]["original_filename"] == "sample.mov"


def test_job_service_accepts_string_fidelity_tier_from_preview_payload() -> None:
    service = JobService()
    job_id = str(uuid4())

    created = service.create_job(
        user_id="job-user-string-tier",
        plan_tier="pro",
        org_id="org-default",
        payload=valid_job_request(),
        access_token="test-token-for-job-user-string-tier",
        job_id_override=job_id,
        publish_immediately=False,
    )

    assert created["job_id"] == job_id
    assert created["effective_fidelity_tier"] == "Restore"
