"""
Maps to:
- ENG-014
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db.phase2_store import PreviewSessionRepository
from app.db.phase2_store import reset_phase2_store
from app.main import app
from tests.helpers.auth import fake_auth_header
from tests.helpers.previews import save_configuration, seed_completed_upload, seed_detection

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state() -> None:
    reset_phase2_store()


def test_preview_pipeline_creates_rereads_and_reuses_cached_session() -> None:
    seed_completed_upload(upload_id="preview-pipeline-upload", owner_user_id="preview-pipeline-user")
    seed_detection(upload_id="preview-pipeline-upload", owner_user_id="preview-pipeline-user")
    save_configuration(client, upload_id="preview-pipeline-upload", owner_user_id="preview-pipeline-user")
    headers = fake_auth_header("preview-pipeline-user", tier="pro")

    created = client.post("/v1/previews", headers=headers, json={"upload_id": "preview-pipeline-upload"})
    reread = client.get(f"/v1/previews/{created.json()['preview_id']}", headers=headers)
    cached = client.post("/v1/previews", headers=headers, json={"upload_id": "preview-pipeline-upload"})

    assert created.status_code == 200
    assert reread.status_code == 200
    assert cached.status_code == 200
    assert reread.json()["preview_id"] == created.json()["preview_id"]
    assert cached.json()["preview_id"] == created.json()["preview_id"]


def test_resaving_configuration_marks_existing_preview_stale_and_requires_new_preview() -> None:
    seed_completed_upload(upload_id="preview-stale-upload", owner_user_id="preview-stale-user")
    seed_detection(upload_id="preview-stale-upload", owner_user_id="preview-stale-user")
    save_configuration(client, upload_id="preview-stale-upload", owner_user_id="preview-stale-user")
    headers = fake_auth_header("preview-stale-user", tier="pro")

    first = client.post("/v1/previews", headers=headers, json={"upload_id": "preview-stale-upload"})
    assert first.status_code == 200
    first_preview_id = first.json()["preview_id"]

    save_configuration(client, upload_id="preview-stale-upload", owner_user_id="preview-stale-user")

    stale = client.get(f"/v1/previews/{first_preview_id}", headers=headers)
    refreshed = client.post("/v1/previews", headers=headers, json={"upload_id": "preview-stale-upload"})

    assert stale.status_code == 200
    assert stale.json()["stale"] is True
    assert refreshed.status_code == 200
    assert refreshed.json()["stale"] is False
    assert refreshed.json()["preview_id"] != first_preview_id


def test_identical_reupload_reuses_preview_artifacts_but_gets_a_new_preview_session() -> None:
    seed_completed_upload(upload_id="preview-reuse-upload-a", owner_user_id="preview-reuse-user")
    seed_detection(upload_id="preview-reuse-upload-a", owner_user_id="preview-reuse-user")
    save_configuration(client, upload_id="preview-reuse-upload-a", owner_user_id="preview-reuse-user")
    headers = fake_auth_header("preview-reuse-user", tier="pro")

    first = client.post("/v1/previews", headers=headers, json={"upload_id": "preview-reuse-upload-a"})
    assert first.status_code == 200

    seed_completed_upload(upload_id="preview-reuse-upload-b", owner_user_id="preview-reuse-user")
    seed_detection(upload_id="preview-reuse-upload-b", owner_user_id="preview-reuse-user")
    save_configuration(client, upload_id="preview-reuse-upload-b", owner_user_id="preview-reuse-user")

    second = client.post("/v1/previews", headers=headers, json={"upload_id": "preview-reuse-upload-b"})
    assert second.status_code == 200
    assert second.json()["preview_id"] != first.json()["preview_id"]

    repo = PreviewSessionRepository()
    first_preview = repo.get_preview(
        first.json()["preview_id"],
        owner_user_id="preview-reuse-user",
        access_token="test-token-for-preview-reuse-user",
    )
    second_preview = repo.get_preview(
        second.json()["preview_id"],
        owner_user_id="preview-reuse-user",
        access_token="test-token-for-preview-reuse-user",
    )

    assert first_preview is not None
    assert second_preview is not None
    assert second_preview["preview_root_uri"] == first_preview["preview_root_uri"]
    assert second_preview["keyframes"] == first_preview["keyframes"]
