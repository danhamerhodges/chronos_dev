"""
Maps to:
- FR-003
- DS-001
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db.phase2_store import UploadRepository, reset_phase2_store
from app.main import app
from app.models.status import UploadStatus
from tests.helpers.auth import fake_auth_header

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state() -> None:
    reset_phase2_store()


def _seed_completed_upload(*, upload_id: str, owner_user_id: str) -> dict[str, object]:
    repo = UploadRepository()
    created = repo.create_session(
        upload_id=upload_id,
        owner_user_id=owner_user_id,
        org_id="org-default",
        original_filename="archive.mov",
        mime_type="video/quicktime",
        size_bytes=1024 * 1024,
        checksum_sha256="abc12345def67890",
        bucket_name="chronos-test-bucket",
        object_path=f"uploads/{owner_user_id}/{upload_id}/archive.mov",
        resumable_session_url=f"https://example.invalid/{upload_id}",
        access_token=f"test-token-for-{owner_user_id}",
    )
    return repo.update_session(
        upload_id,
        owner_user_id=owner_user_id,
        patch={"status": UploadStatus.COMPLETED.value, "completed_at": "2026-03-11T00:00:00+00:00"},
        access_token=f"test-token-for-{owner_user_id}",
    ) or created


def test_packet_4b_job_payload_preview_is_accepted_by_jobs_api() -> None:
    upload = _seed_completed_upload(upload_id="upload-handoff", owner_user_id="handoff-user")
    headers = fake_auth_header("handoff-user", tier="pro")

    detect = client.post(
        f"/v1/upload/{upload['upload_id']}/detect-era",
        headers=headers,
        json={"estimated_duration_seconds": 180},
    )
    assert detect.status_code == 200

    configuration = client.patch(
        f"/v1/upload/{upload['upload_id']}/configuration",
        headers=headers,
        json={
            "persona": "filmmaker",
            "fidelity_tier": "Conserve",
            "grain_preset": "Heavy",
            "estimated_duration_seconds": 180,
        },
    )
    assert configuration.status_code == 200

    job_create = client.post(
        "/v1/jobs",
        headers=headers,
        json=configuration.json()["job_payload_preview"],
    )

    assert job_create.status_code == 202
    payload = job_create.json()
    assert payload["status"] == "queued"
    assert payload["fidelity_tier"] == "Conserve"
