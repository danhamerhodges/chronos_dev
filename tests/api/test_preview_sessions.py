"""
Maps to:
- FR-006
- ENG-014
"""

from __future__ import annotations

import asyncio
from copy import deepcopy

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api import previews as previews_api
from app.db.phase2_store import PreviewSessionRepository, UploadRepository, reset_phase2_store
from app.main import app
from app.services.job_dispatcher import queued_dispatch_messages, reset_job_dispatcher_state
from app.services.preview_generation import PreviewStorageUnavailableError
from tests.helpers.auth import fake_auth_header
from tests.helpers.previews import save_configuration, seed_completed_upload, seed_detection

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state() -> None:
    reset_phase2_store()
    reset_job_dispatcher_state()


def _create_preview(*, upload_id: str, owner_user_id: str) -> dict[str, object]:
    response = client.post(
        "/v1/previews",
        headers=fake_auth_header(owner_user_id, tier="pro"),
        json={"upload_id": upload_id},
    )
    assert response.status_code == 200
    return response.json()


def _approve_preview(*, preview_id: str, owner_user_id: str) -> dict[str, object]:
    response = client.post(
        f"/v1/previews/{preview_id}/review",
        headers=fake_auth_header(owner_user_id, tier="pro"),
        json={"review_status": "approved"},
    )
    assert response.status_code == 200
    return response.json()


def test_owner_can_create_and_reread_preview_session() -> None:
    seed_completed_upload(upload_id="preview-owner-upload", owner_user_id="preview-owner")
    seed_detection(upload_id="preview-owner-upload", owner_user_id="preview-owner")
    save_configuration(client, upload_id="preview-owner-upload", owner_user_id="preview-owner")

    created = client.post(
        "/v1/previews",
        headers=fake_auth_header("preview-owner", tier="pro"),
        json={"upload_id": "preview-owner-upload"},
    )

    assert created.status_code == 200
    payload = created.json()
    assert payload["upload_id"] == "preview-owner-upload"
    assert payload["status"] == "ready"
    assert payload["review_status"] == "pending"
    assert payload["reviewed_at"] is None
    assert payload["launch_status"] == "not_launched"
    assert payload["launched_job_id"] is None
    assert payload["stale"] is False
    assert payload["keyframe_count"] == 10
    assert len(payload["keyframes"]) == 10

    reread = client.get(
        f"/v1/previews/{payload['preview_id']}",
        headers=fake_auth_header("preview-owner", tier="pro"),
    )
    assert reread.status_code == 200
    assert reread.json()["preview_id"] == payload["preview_id"]

    forbidden = client.get(
        f"/v1/previews/{payload['preview_id']}",
        headers=fake_auth_header("preview-other", tier="pro"),
    )
    assert forbidden.status_code == 404


def test_preview_create_returns_409_for_incomplete_upload() -> None:
    UploadRepository().create_session(
        upload_id="preview-pending-upload",
        owner_user_id="preview-incomplete",
        org_id="org-default",
        original_filename="pending.mov",
        mime_type="video/quicktime",
        size_bytes=1024 * 1024,
        checksum_sha256="pendingabc12345678",
        bucket_name="chronos-test-bucket",
        object_path="uploads/preview-incomplete/preview-pending-upload/pending.mov",
        resumable_session_url="https://example.invalid/pending",
        access_token="test-token-for-preview-incomplete",
    )
    response = client.post(
        "/v1/previews",
        headers=fake_auth_header("preview-incomplete", tier="pro"),
        json={"upload_id": "preview-pending-upload"},
    )

    assert response.status_code == 409
    assert response.json()["title"] == "Upload Not Ready"


def test_preview_create_returns_409_when_saved_configuration_is_missing() -> None:
    seed_completed_upload(upload_id="preview-no-config", owner_user_id="preview-no-config-user")
    seed_detection(upload_id="preview-no-config", owner_user_id="preview-no-config-user")

    response = client.post(
        "/v1/previews",
        headers=fake_auth_header("preview-no-config-user", tier="pro"),
        json={"upload_id": "preview-no-config"},
    )

    assert response.status_code == 409
    assert response.json()["title"] == "Configuration Not Ready"


def test_preview_create_reuses_cached_session_for_same_upload_and_configuration() -> None:
    seed_completed_upload(upload_id="preview-cache-upload", owner_user_id="preview-cache-user")
    seed_detection(upload_id="preview-cache-upload", owner_user_id="preview-cache-user")
    save_configuration(client, upload_id="preview-cache-upload", owner_user_id="preview-cache-user")
    headers = fake_auth_header("preview-cache-user", tier="pro")

    first = client.post("/v1/previews", headers=headers, json={"upload_id": "preview-cache-upload"})
    second = client.post("/v1/previews", headers=headers, json={"upload_id": "preview-cache-upload"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["preview_id"] == first.json()["preview_id"]
    assert second.json()["configuration_fingerprint"] == first.json()["configuration_fingerprint"]
    assert second.json()["review_status"] == "pending"


def test_preview_create_is_idempotent_under_concurrent_identical_requests() -> None:
    seed_completed_upload(upload_id="preview-concurrent-upload", owner_user_id="preview-concurrent-user")
    seed_detection(upload_id="preview-concurrent-upload", owner_user_id="preview-concurrent-user")
    save_configuration(client, upload_id="preview-concurrent-upload", owner_user_id="preview-concurrent-user")
    headers = fake_auth_header("preview-concurrent-user", tier="pro")

    async def run_requests() -> list[httpx.Response]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as async_client:
            return list(
                await asyncio.gather(
                    *(
                        async_client.post(
                            "/v1/previews",
                            headers=headers,
                            json={"upload_id": "preview-concurrent-upload"},
                        )
                        for _ in range(6)
                    )
                )
            )

    responses = asyncio.run(run_requests())

    assert all(response.status_code == 200 for response in responses)
    preview_ids = {response.json()["preview_id"] for response in responses}
    assert len(preview_ids) == 1


def test_preview_create_ignores_exact_hit_when_fingerprint_changes_with_same_snapshot_identity() -> None:
    upload_id = "preview-fingerprint-collision-upload"
    owner_user_id = "preview-fingerprint-collision-user"
    seed_completed_upload(upload_id=upload_id, owner_user_id=owner_user_id)
    seed_detection(upload_id=upload_id, owner_user_id=owner_user_id)
    save_configuration(client, upload_id=upload_id, owner_user_id=owner_user_id)
    headers = fake_auth_header(owner_user_id, tier="pro")

    first = client.post("/v1/previews", headers=headers, json={"upload_id": upload_id})
    assert first.status_code == 200

    repo = UploadRepository()
    session = repo.get_session(
        upload_id,
        owner_user_id=owner_user_id,
        access_token=f"test-token-for-{owner_user_id}",
    )
    assert session is not None
    updated_launch_config = deepcopy(session["launch_config"])
    updated_launch_config["job_payload_preview"]["config"]["persona"] = "archivist"
    persisted = repo.update_session(
        upload_id,
        owner_user_id=owner_user_id,
        patch={
            "launch_config": updated_launch_config,
            "configured_at": session["configured_at"],
        },
        access_token=f"test-token-for-{owner_user_id}",
    )
    assert persisted is not None

    second = client.post("/v1/previews", headers=headers, json={"upload_id": upload_id})

    assert second.status_code == 200
    assert second.json()["preview_id"] == first.json()["preview_id"]
    assert second.json()["configuration_fingerprint"] != first.json()["configuration_fingerprint"]


def test_expired_preview_session_returns_410() -> None:
    seed_completed_upload(upload_id="preview-expired-upload", owner_user_id="preview-expired-user")
    seed_detection(upload_id="preview-expired-upload", owner_user_id="preview-expired-user")
    save_configuration(client, upload_id="preview-expired-upload", owner_user_id="preview-expired-user")
    headers = fake_auth_header("preview-expired-user", tier="pro")

    created = client.post("/v1/previews", headers=headers, json={"upload_id": "preview-expired-upload"})
    assert created.status_code == 200
    preview_id = created.json()["preview_id"]

    updated = PreviewSessionRepository().update_preview(
        preview_id,
        owner_user_id="preview-expired-user",
        patch={"expires_at": "2020-01-01T00:00:00+00:00"},
        access_token="test-token-for-preview-expired-user",
    )
    assert updated is not None

    expired = client.get(f"/v1/previews/{preview_id}", headers=headers)

    assert expired.status_code == 410
    assert expired.json()["title"] == "Preview Expired"
    assert expired.json()["type"] == "/problems/preview_expired"


def test_owner_can_approve_reject_and_reapprove_before_launch() -> None:
    seed_completed_upload(upload_id="preview-review-upload", owner_user_id="preview-review-user")
    seed_detection(upload_id="preview-review-upload", owner_user_id="preview-review-user")
    save_configuration(client, upload_id="preview-review-upload", owner_user_id="preview-review-user")

    created = _create_preview(upload_id="preview-review-upload", owner_user_id="preview-review-user")

    approved = client.post(
        f"/v1/previews/{created['preview_id']}/review",
        headers=fake_auth_header("preview-review-user", tier="pro"),
        json={"review_status": "approved"},
    )
    rejected = client.post(
        f"/v1/previews/{created['preview_id']}/review",
        headers=fake_auth_header("preview-review-user", tier="pro"),
        json={"review_status": "rejected"},
    )
    reapproved = client.post(
        f"/v1/previews/{created['preview_id']}/review",
        headers=fake_auth_header("preview-review-user", tier="pro"),
        json={"review_status": "approved"},
    )

    assert approved.status_code == 200
    assert approved.json()["review_status"] == "approved"
    assert approved.json()["reviewed_at"] is not None
    assert rejected.status_code == 200
    assert rejected.json()["review_status"] == "rejected"
    assert reapproved.status_code == 200
    assert reapproved.json()["review_status"] == "approved"


def test_repeated_same_state_review_is_idempotent() -> None:
    seed_completed_upload(upload_id="preview-idempotent-upload", owner_user_id="preview-idempotent-user")
    seed_detection(upload_id="preview-idempotent-upload", owner_user_id="preview-idempotent-user")
    save_configuration(client, upload_id="preview-idempotent-upload", owner_user_id="preview-idempotent-user")

    created = _create_preview(upload_id="preview-idempotent-upload", owner_user_id="preview-idempotent-user")
    approved = _approve_preview(preview_id=str(created["preview_id"]), owner_user_id="preview-idempotent-user")
    approved_again = client.post(
        f"/v1/previews/{created['preview_id']}/review",
        headers=fake_auth_header("preview-idempotent-user", tier="pro"),
        json={"review_status": "approved"},
    )

    assert approved_again.status_code == 200
    assert approved_again.json()["review_status"] == "approved"
    assert approved_again.json()["reviewed_at"] == approved["reviewed_at"]


def test_cross_user_review_and_launch_are_denied() -> None:
    seed_completed_upload(upload_id="preview-cross-user-upload", owner_user_id="preview-cross-owner")
    seed_detection(upload_id="preview-cross-user-upload", owner_user_id="preview-cross-owner")
    configuration = save_configuration(client, upload_id="preview-cross-user-upload", owner_user_id="preview-cross-owner")
    created = _create_preview(upload_id="preview-cross-user-upload", owner_user_id="preview-cross-owner")

    review = client.post(
        f"/v1/previews/{created['preview_id']}/review",
        headers=fake_auth_header("preview-cross-other", tier="pro"),
        json={"review_status": "approved"},
    )
    launch = client.post(
        f"/v1/previews/{created['preview_id']}/launch",
        headers=fake_auth_header("preview-cross-other", tier="pro"),
        json={"configuration_fingerprint": configuration["configuration_fingerprint"]},
    )

    assert review.status_code == 404
    assert launch.status_code == 404


def test_launch_requires_approved_preview_and_exact_configuration_fingerprint() -> None:
    seed_completed_upload(upload_id="preview-launch-upload", owner_user_id="preview-launch-user")
    seed_detection(upload_id="preview-launch-upload", owner_user_id="preview-launch-user")
    configuration = save_configuration(client, upload_id="preview-launch-upload", owner_user_id="preview-launch-user")
    created = _create_preview(upload_id="preview-launch-upload", owner_user_id="preview-launch-user")

    blocked = client.post(
        f"/v1/previews/{created['preview_id']}/launch",
        headers=fake_auth_header("preview-launch-user", tier="pro"),
        json={"configuration_fingerprint": configuration["configuration_fingerprint"]},
    )
    wrong_fingerprint = client.post(
        f"/v1/previews/{created['preview_id']}/launch",
        headers=fake_auth_header("preview-launch-user", tier="pro"),
        json={"configuration_fingerprint": "0" * 64},
    )

    assert blocked.status_code == 409
    assert blocked.json()["type"] == "/problems/preview_approval_required"
    assert wrong_fingerprint.status_code == 409
    assert wrong_fingerprint.json()["type"] == "/problems/preview_stale"


def test_approved_preview_launch_is_idempotent_and_freezes_review_state() -> None:
    seed_completed_upload(upload_id="preview-approved-launch-upload", owner_user_id="preview-approved-launch-user")
    seed_detection(upload_id="preview-approved-launch-upload", owner_user_id="preview-approved-launch-user")
    configuration = save_configuration(
        client,
        upload_id="preview-approved-launch-upload",
        owner_user_id="preview-approved-launch-user",
    )
    created = _create_preview(
        upload_id="preview-approved-launch-upload",
        owner_user_id="preview-approved-launch-user",
    )
    _approve_preview(
        preview_id=str(created["preview_id"]),
        owner_user_id="preview-approved-launch-user",
    )

    first_launch = client.post(
        f"/v1/previews/{created['preview_id']}/launch",
        headers=fake_auth_header("preview-approved-launch-user", tier="pro"),
        json={"configuration_fingerprint": configuration["configuration_fingerprint"]},
    )
    second_launch = client.post(
        f"/v1/previews/{created['preview_id']}/launch",
        headers=fake_auth_header("preview-approved-launch-user", tier="pro"),
        json={"configuration_fingerprint": configuration["configuration_fingerprint"]},
    )
    review_after_launch = client.post(
        f"/v1/previews/{created['preview_id']}/review",
        headers=fake_auth_header("preview-approved-launch-user", tier="pro"),
        json={"review_status": "rejected"},
    )

    assert first_launch.status_code == 202
    assert second_launch.status_code == 202
    assert second_launch.json()["job_id"] == first_launch.json()["job_id"]
    assert len(queued_dispatch_messages()) == 1
    assert review_after_launch.status_code == 409
    assert review_after_launch.json()["type"] == "/problems/preview_already_launched"


def test_claimed_launch_retry_reuses_same_job_id_after_dispatch_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    seed_completed_upload(upload_id="preview-dispatch-retry-upload", owner_user_id="preview-dispatch-retry-user")
    seed_detection(upload_id="preview-dispatch-retry-upload", owner_user_id="preview-dispatch-retry-user")
    configuration = save_configuration(
        client,
        upload_id="preview-dispatch-retry-upload",
        owner_user_id="preview-dispatch-retry-user",
    )
    created = _create_preview(
        upload_id="preview-dispatch-retry-upload",
        owner_user_id="preview-dispatch-retry-user",
    )
    _approve_preview(
        preview_id=str(created["preview_id"]),
        owner_user_id="preview-dispatch-retry-user",
    )

    attempts = {"count": 0}
    from app.services import preview_generation as preview_generation_service

    original_publish = preview_generation_service.publish_job

    def flaky_publish(job_id: str, *, plan_tier: str, source: str = "api"):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("dispatch offline")
        return original_publish(job_id, plan_tier=plan_tier, source=source)

    monkeypatch.setattr(preview_generation_service, "publish_job", flaky_publish)

    first_launch = client.post(
        f"/v1/previews/{created['preview_id']}/launch",
        headers=fake_auth_header("preview-dispatch-retry-user", tier="pro"),
        json={"configuration_fingerprint": configuration["configuration_fingerprint"]},
    )
    pending_preview = PreviewSessionRepository().get_preview(
        str(created["preview_id"]),
        owner_user_id="preview-dispatch-retry-user",
        access_token="test-token-for-preview-dispatch-retry-user",
    )
    second_launch = client.post(
        f"/v1/previews/{created['preview_id']}/launch",
        headers=fake_auth_header("preview-dispatch-retry-user", tier="pro"),
        json={"configuration_fingerprint": configuration["configuration_fingerprint"]},
    )

    assert first_launch.status_code == 503
    assert first_launch.json()["type"] == "/problems/launch_dispatch_failed"
    assert pending_preview is not None
    assert pending_preview["launch_status"] == "launch_pending"
    assert pending_preview["launched_external_job_id"]
    assert second_launch.status_code == 202
    assert second_launch.json()["job_id"] == pending_preview["launched_external_job_id"]
    assert len(queued_dispatch_messages()) == 1


def test_preview_create_does_not_return_expired_exact_hit_when_delete_patch_misses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upload_id = "preview-expired-create-upload"
    owner_user_id = "preview-expired-create-user"
    seed_completed_upload(upload_id=upload_id, owner_user_id=owner_user_id)
    seed_detection(upload_id=upload_id, owner_user_id=owner_user_id)
    save_configuration(client, upload_id=upload_id, owner_user_id=owner_user_id)
    headers = fake_auth_header(owner_user_id, tier="pro")

    created = client.post("/v1/previews", headers=headers, json={"upload_id": upload_id})
    assert created.status_code == 200
    preview_id = created.json()["preview_id"]
    expired_timestamp = "2020-01-01T00:00:00+00:00"

    updated = PreviewSessionRepository().update_preview(
        preview_id,
        owner_user_id=owner_user_id,
        patch={"expires_at": expired_timestamp},
        access_token=f"test-token-for-{owner_user_id}",
    )
    assert updated is not None

    monkeypatch.setattr(previews_api._preview_service._previews, "update_preview", lambda *args, **kwargs: None)

    recreated = client.post("/v1/previews", headers=headers, json={"upload_id": upload_id})

    assert recreated.status_code == 200
    assert recreated.json()["preview_id"] == preview_id
    assert recreated.json()["expires_at"] != expired_timestamp


def test_preview_create_returns_503_when_preview_signing_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    seed_completed_upload(upload_id="preview-unavailable-upload", owner_user_id="preview-unavailable-user")
    seed_detection(upload_id="preview-unavailable-upload", owner_user_id="preview-unavailable-user")
    save_configuration(client, upload_id="preview-unavailable-upload", owner_user_id="preview-unavailable-user")

    monkeypatch.setattr(
        previews_api._preview_service,
        "_sign_value",
        lambda value: (_ for _ in ()).throw(PreviewStorageUnavailableError(value)),
    )

    response = client.post(
        "/v1/previews",
        headers=fake_auth_header("preview-unavailable-user", tier="pro"),
        json={"upload_id": "preview-unavailable-upload"},
    )

    assert response.status_code == 503
    assert response.json()["title"] == "Preview Storage Unavailable"
