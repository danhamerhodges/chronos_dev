"""
Maps to:
- FR-005
- ENG-015
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db.phase2_store import UploadRepository, reset_phase2_store
from app.models.status import UploadStatus
from app.services.job_runtime import configure_segment_failures
from app.main import app
from tests.helpers.auth import fake_auth_header
from tests.helpers.jobs import run_all_jobs

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state() -> None:
    reset_phase2_store()


def _seed_completed_upload(*, upload_id: str, owner_user_id: str) -> None:
    repo = UploadRepository()
    repo.create_session(
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
    repo.update_session(
        upload_id,
        owner_user_id=owner_user_id,
        patch={"status": UploadStatus.COMPLETED.value, "completed_at": "2026-03-12T00:00:00+00:00"},
        access_token=f"test-token-for-{owner_user_id}",
    )


def _seed_detection(upload_id: str, owner_user_id: str) -> None:
    UploadRepository().update_session(
        upload_id,
        owner_user_id=owner_user_id,
        patch={
            "detection_snapshot": {
                "detection_id": f"detection-{upload_id}",
                "job_id": f"upload:{upload_id}",
                "upload_id": upload_id,
                "era": "1970s Super 8 Film",
                "confidence": 0.61,
                "manual_confirmation_required": True,
                "top_candidates": [{"era": "1970s Super 8 Film", "confidence": 0.61}],
                "forensic_markers": {
                    "grain_structure": "consumer film grain",
                    "color_saturation": 0.58,
                    "format_artifacts": ["frame_jitter"],
                },
                "warnings": ["Manual confirmation required due to low confidence."],
                "processing_timestamp": "2026-03-12T00:00:00+00:00",
                "source": "system",
                "model_version": "deterministic-fallback",
                "prompt_version": "v1",
                "estimated_usage_minutes": 3,
                "estimated_duration_seconds": 180,
                "capture_medium": "super_8",
                "media_uri": f"gs://chronos-test-bucket/uploads/{owner_user_id}/{upload_id}/archive.mov",
                "original_filename": "archive.mov",
                "mime_type": "video/quicktime",
            }
        },
        access_token=f"test-token-for-{owner_user_id}",
    )


def _save_configuration(*, upload_id: str, owner_user_id: str) -> dict[str, object]:
    response = client.patch(
        f"/v1/upload/{upload_id}/configuration",
        headers=fake_auth_header(owner_user_id, tier="pro"),
        json={
            "persona": "filmmaker",
            "fidelity_tier": "Restore",
            "grain_preset": "Heavy",
            "estimated_duration_seconds": 180,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_packet_4d_export_flow_surfaces_delivery_artifacts_for_completed_jobs() -> None:
    _seed_completed_upload(upload_id="upload-export-complete", owner_user_id="export-flow-user")
    _seed_detection("upload-export-complete", "export-flow-user")
    configuration = _save_configuration(upload_id="upload-export-complete", owner_user_id="export-flow-user")
    headers = fake_auth_header("export-flow-user", tier="pro")

    created = client.post("/v1/jobs", headers=headers, json=configuration["job_payload_preview"])
    assert created.status_code == 202
    job_id = created.json()["job_id"]

    run_all_jobs()

    export = client.get(f"/v1/jobs/{job_id}/export", headers=headers)
    assert export.status_code == 200
    export_payload = export.json()
    assert export_payload["package_contents"] == [
        f"{job_id}-av1.mp4",
        "transformation_manifest.json",
        "uncertainty_callouts.json",
        "quality_report.pdf",
        "deletion_proof.pdf",
    ]

    manifest = client.get(f"/v1/manifests/{job_id}", headers=headers)
    assert manifest.status_code == 200

    proof = client.get(f"/v1/deletion-proofs/{export_payload['deletion_proof_id']}", headers=headers)
    assert proof.status_code == 200
    assert proof.json()["job_id"] == job_id


def test_packet_4d_export_flow_supports_partial_jobs() -> None:
    _seed_completed_upload(upload_id="upload-export-partial", owner_user_id="partial-export-user")
    _seed_detection("upload-export-partial", "partial-export-user")
    configuration = _save_configuration(upload_id="upload-export-partial", owner_user_id="partial-export-user")
    headers = fake_auth_header("partial-export-user", tier="pro")

    created = client.post("/v1/jobs", headers=headers, json=configuration["job_payload_preview"])
    job_id = created.json()["job_id"]
    configure_segment_failures(job_id, 1, ["persistent", "persistent", "persistent"])

    run_all_jobs()

    detail = client.get(f"/v1/jobs/{job_id}", headers=headers)
    export = client.get(f"/v1/jobs/{job_id}/export", headers=headers)

    assert detail.status_code == 200
    assert detail.json()["status"] == "partial"
    assert export.status_code == 200
    assert export.json()["status"] == "partial"
