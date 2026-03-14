"""
Maps to:
- FR-005
- ENG-015
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db.phase2_store import JobExportPackageRepository, reset_phase2_store
from app.main import app
from app.services.job_runtime import configure_segment_failures
from tests.helpers.auth import fake_auth_header
from tests.helpers.jobs import run_all_jobs, valid_job_request

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state() -> None:
    reset_phase2_store()


def _complete_job(*, user_id: str, tier: str = "pro") -> str:
    created = client.post("/v1/jobs", headers=fake_auth_header(user_id, tier=tier), json=valid_job_request()).json()
    run_all_jobs()
    return created["job_id"]


def _partial_job(*, user_id: str, tier: str = "pro") -> str:
    created = client.post("/v1/jobs", headers=fake_auth_header(user_id, tier=tier), json=valid_job_request()).json()
    configure_segment_failures(created["job_id"], 1, ["persistent", "persistent", "persistent"])
    run_all_jobs()
    return created["job_id"]


def test_owner_can_fetch_default_av1_export_for_completed_job() -> None:
    job_id = _complete_job(user_id="export-owner", tier="pro")

    response = client.get(f"/v1/jobs/{job_id}/export", headers=fake_auth_header("export-owner", tier="pro"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == job_id
    assert payload["status"] == "completed"
    assert payload["variant"] == "av1"
    assert payload["download_url"].startswith("https://storage.googleapis.com/")
    assert "/download/storage/v1/" not in payload["download_url"]
    assert "X-Goog-Algorithm=GOOG4-HMAC-SHA256" in payload["download_url"]
    assert "X-Goog-Credential=" in payload["download_url"]
    assert "X-Goog-Date=" in payload["download_url"]
    assert "X-Goog-Expires=" in payload["download_url"]
    assert "X-Goog-Signature=" in payload["download_url"]
    assert payload["file_name"].endswith("-av1.zip")
    assert set(payload["package_contents"]) == {
        f"{job_id}-av1.mp4",
        "transformation_manifest.json",
        "uncertainty_callouts.json",
        "quality_report.pdf",
        "deletion_proof.pdf",
    }
    assert payload["deletion_proof_id"]


def test_owner_can_fetch_h264_export_for_completed_job() -> None:
    job_id = _complete_job(user_id="export-h264-owner", tier="pro")

    response = client.get(
        f"/v1/jobs/{job_id}/export",
        params={"variant": "h264"},
        headers=fake_auth_header("export-h264-owner", tier="pro"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["variant"] == "h264"
    assert f"{job_id}-h264.mp4" in payload["package_contents"]


def test_partial_jobs_export_successfully() -> None:
    job_id = _partial_job(user_id="export-partial-owner", tier="pro")

    response = client.get(f"/v1/jobs/{job_id}/export", headers=fake_auth_header("export-partial-owner", tier="pro"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "partial"


def test_inflight_jobs_return_409_until_processing_finishes() -> None:
    created = client.post("/v1/jobs", headers=fake_auth_header("export-queued-owner", tier="pro"), json=valid_job_request()).json()

    response = client.get(
        f"/v1/jobs/{created['job_id']}/export",
        headers=fake_auth_header("export-queued-owner", tier="pro"),
    )

    assert response.status_code == 409
    assert response.json()["title"] == "Export Not Ready"


def test_cancelled_jobs_return_409_for_export() -> None:
    created = client.post("/v1/jobs", headers=fake_auth_header("export-cancel-owner", tier="pro"), json=valid_job_request()).json()
    cancel = client.delete(f"/v1/jobs/{created['job_id']}", headers=fake_auth_header("export-cancel-owner", tier="pro"))
    assert cancel.status_code == 200
    run_all_jobs()

    response = client.get(
        f"/v1/jobs/{created['job_id']}/export",
        headers=fake_auth_header("export-cancel-owner", tier="pro"),
    )

    assert response.status_code == 409


def test_failed_jobs_return_409_for_export() -> None:
    created = client.post("/v1/jobs", headers=fake_auth_header("export-failed-owner", tier="pro"), json=valid_job_request()).json()
    for segment_index in range(3):
        configure_segment_failures(created["job_id"], segment_index, ["persistent", "persistent", "persistent"])
    run_all_jobs()

    response = client.get(
        f"/v1/jobs/{created['job_id']}/export",
        headers=fake_auth_header("export-failed-owner", tier="pro"),
    )

    assert response.status_code == 409


def test_expired_export_package_returns_410() -> None:
    job_id = _complete_job(user_id="export-expired-owner", tier="pro")
    JobExportPackageRepository().update_package_for_worker(
        job_id,
        variant="av1",
        patch={"deleted_at": "2026-03-14T00:00:00+00:00"},
    )

    response = client.get(f"/v1/jobs/{job_id}/export", headers=fake_auth_header("export-expired-owner", tier="pro"))

    assert response.status_code == 410
    assert response.json()["title"] == "Download Expired"


def test_non_owner_gets_404_for_export_package() -> None:
    job_id = _complete_job(user_id="export-owner-only", tier="pro")

    response = client.get(f"/v1/jobs/{job_id}/export", headers=fake_auth_header("other-export-user", tier="pro"))

    assert response.status_code == 404


@pytest.mark.parametrize("retention_days", [8, 14, 60, 90])
def test_museum_can_request_extended_retention_windows(retention_days: int) -> None:
    job_id = _complete_job(user_id="museum-export-owner", tier="museum")

    response = client.get(
        f"/v1/jobs/{job_id}/export",
        params={"retention_days": retention_days},
        headers=fake_auth_header("museum-export-owner", tier="museum"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["variant"] == "av1"
    assert payload["expires_at"].startswith("20")


def test_museum_retention_above_ninety_days_returns_400() -> None:
    job_id = _complete_job(user_id="museum-retention-invalid", tier="museum")

    response = client.get(
        f"/v1/jobs/{job_id}/export",
        params={"retention_days": 91},
        headers=fake_auth_header("museum-retention-invalid", tier="museum"),
    )

    assert response.status_code == 400


def test_non_museum_retention_above_seven_days_returns_403() -> None:
    job_id = _complete_job(user_id="pro-export-owner", tier="pro")

    response = client.get(
        f"/v1/jobs/{job_id}/export",
        params={"retention_days": 30},
        headers=fake_auth_header("pro-export-owner", tier="pro"),
    )

    assert response.status_code == 403
    assert response.json()["title"] == "Plan Upgrade Required"
