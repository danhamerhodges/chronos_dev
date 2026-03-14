"""
Maps to:
- FR-004
- DS-006
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db.phase2_store import UploadRepository, reset_phase2_store
from app.main import app
from app.models.status import UploadStatus
from tests.helpers.auth import fake_auth_header
from tests.helpers.jobs import run_all_jobs

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
        patch={"status": UploadStatus.COMPLETED.value, "completed_at": "2026-03-12T00:00:00+00:00"},
        access_token=f"test-token-for-{owner_user_id}",
    ) or created


def _seed_low_confidence_detection(upload_id: str, owner_user_id: str) -> None:
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
                "manual_override_era": None,
                "override_reason": None,
                "capture_medium": "super_8",
                "media_uri": f"gs://chronos-test-bucket/uploads/{owner_user_id}/{upload_id}/archive.mov",
                "original_filename": "archive.mov",
                "mime_type": "video/quicktime",
            }
        },
        access_token=f"test-token-for-{owner_user_id}",
    )


def _save_configuration(*, upload_id: str, owner_user_id: str) -> dict[str, object]:
    headers = fake_auth_header(owner_user_id, tier="pro")
    response = client.patch(
        f"/v1/upload/{upload_id}/configuration",
        headers=headers,
        json={
            "persona": "filmmaker",
            "fidelity_tier": "Restore",
            "grain_preset": "Heavy",
            "estimated_duration_seconds": 180,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_packet_4c_launch_flow_surfaces_callouts_through_terminal_state() -> None:
    upload = _seed_completed_upload(upload_id="upload-processing", owner_user_id="processing-user")
    _seed_low_confidence_detection(upload["upload_id"], "processing-user")
    configuration = _save_configuration(upload_id=upload["upload_id"], owner_user_id="processing-user")
    headers = fake_auth_header("processing-user", tier="pro")

    created = client.post("/v1/jobs", headers=headers, json=configuration["job_payload_preview"])
    assert created.status_code == 202
    job_id = created.json()["job_id"]

    queued_detail = client.get(f"/v1/jobs/{job_id}", headers=headers)
    queued_callouts = client.get(f"/v1/jobs/{job_id}/uncertainty-callouts", headers=headers)
    assert queued_detail.status_code == 200
    assert queued_detail.json()["status"] == "queued"
    assert queued_callouts.status_code == 200
    assert {item["code"] for item in queued_callouts.json()["callouts"]} == {"low_confidence_era_classification"}

    run_all_jobs()
    completed_detail = client.get(f"/v1/jobs/{job_id}", headers=headers)
    completed_callouts = client.get(f"/v1/jobs/{job_id}/uncertainty-callouts", headers=headers)

    assert completed_detail.status_code == 200
    assert completed_detail.json()["status"] == "completed"
    assert completed_detail.json()["progress"]["percent_complete"] == 100.0
    assert completed_callouts.status_code == 200
    assert {item["code"] for item in completed_callouts.json()["callouts"]} >= {"low_confidence_era_classification"}


def test_packet_4c_cancel_flow_reuses_existing_job_api_and_callout_endpoint() -> None:
    upload = _seed_completed_upload(upload_id="upload-cancel", owner_user_id="cancel-flow-user")
    _seed_low_confidence_detection(upload["upload_id"], "cancel-flow-user")
    configuration = _save_configuration(upload_id=upload["upload_id"], owner_user_id="cancel-flow-user")
    headers = fake_auth_header("cancel-flow-user", tier="pro")

    created = client.post("/v1/jobs", headers=headers, json=configuration["job_payload_preview"])
    job_id = created.json()["job_id"]

    cancel = client.delete(f"/v1/jobs/{job_id}", headers=headers)
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancel_requested"

    queued_callouts = client.get(f"/v1/jobs/{job_id}/uncertainty-callouts", headers=headers)
    assert queued_callouts.status_code == 200
    assert {item["code"] for item in queued_callouts.json()["callouts"]} == {"low_confidence_era_classification"}

    run_all_jobs()
    cancelled_detail = client.get(f"/v1/jobs/{job_id}", headers=headers)
    cancelled_callouts = client.get(f"/v1/jobs/{job_id}/uncertainty-callouts", headers=headers)

    assert cancelled_detail.status_code == 200
    assert cancelled_detail.json()["status"] == "cancelled"
    assert cancelled_callouts.status_code == 200
    assert {item["code"] for item in cancelled_callouts.json()["callouts"]} == {"low_confidence_era_classification"}
