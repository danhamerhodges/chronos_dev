"""
Maps to:
- ENG-014

Preview test helpers for Packet 4F.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.db.phase2_store import UploadRepository
from app.models.status import UploadStatus
from tests.helpers.auth import fake_auth_header


def seed_completed_upload(*, upload_id: str, owner_user_id: str) -> None:
    repo = UploadRepository()
    repo.create_session(
        upload_id=upload_id,
        owner_user_id=owner_user_id,
        org_id="org-default",
        original_filename="preview-source.mov",
        mime_type="video/quicktime",
        size_bytes=1024 * 1024,
        checksum_sha256="previewabc123456789",
        bucket_name="chronos-test-bucket",
        object_path=f"uploads/{owner_user_id}/{upload_id}/preview-source.mov",
        resumable_session_url=f"https://example.invalid/{upload_id}",
        access_token=f"test-token-for-{owner_user_id}",
    )
    repo.update_session(
        upload_id,
        owner_user_id=owner_user_id,
        patch={"status": UploadStatus.COMPLETED.value, "completed_at": "2026-03-15T00:00:00+00:00"},
        access_token=f"test-token-for-{owner_user_id}",
    )


def seed_detection(*, upload_id: str, owner_user_id: str) -> None:
    UploadRepository().update_session(
        upload_id,
        owner_user_id=owner_user_id,
        patch={
            "detection_snapshot": {
                "detection_id": f"detection-{upload_id}",
                "job_id": f"upload:{upload_id}",
                "upload_id": upload_id,
                "era": "1970s Super 8 Film",
                "confidence": 0.72,
                "manual_confirmation_required": False,
                "top_candidates": [{"era": "1970s Super 8 Film", "confidence": 0.72}],
                "forensic_markers": {
                    "grain_structure": "consumer film grain",
                    "color_saturation": 0.58,
                    "format_artifacts": ["frame_jitter"],
                },
                "warnings": [],
                "processing_timestamp": "2026-03-15T00:00:00+00:00",
                "source": "system",
                "model_version": "deterministic-fallback",
                "prompt_version": "v1",
                "estimated_usage_minutes": 3,
                "estimated_duration_seconds": 180,
                "capture_medium": "super_8",
                "media_uri": f"gs://chronos-test-bucket/uploads/{owner_user_id}/{upload_id}/preview-source.mov",
                "original_filename": "preview-source.mov",
                "mime_type": "video/quicktime",
            }
        },
        access_token=f"test-token-for-{owner_user_id}",
    )


def save_configuration(
    client: TestClient,
    *,
    upload_id: str,
    owner_user_id: str,
    tier: str = "pro",
) -> dict[str, object]:
    response = client.patch(
        f"/v1/upload/{upload_id}/configuration",
        headers=fake_auth_header(owner_user_id, tier=tier),
        json={
            "persona": "filmmaker",
            "fidelity_tier": "Restore" if tier != "hobbyist" else "Enhance",
            "grain_preset": "Heavy",
            "estimated_duration_seconds": 180,
        },
    )
    assert response.status_code == 200
    return response.json()
