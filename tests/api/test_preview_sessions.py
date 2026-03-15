"""
Maps to:
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
from app.services.preview_generation import PreviewStorageUnavailableError
from tests.helpers.auth import fake_auth_header
from tests.helpers.previews import save_configuration, seed_completed_upload, seed_detection

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state() -> None:
    reset_phase2_store()


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
