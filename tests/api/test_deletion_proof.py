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
from tests.helpers.auth import fake_auth_header
from tests.helpers.jobs import run_all_jobs, valid_job_request

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state() -> None:
    reset_phase2_store()


def test_deletion_proof_route_returns_job_linked_metadata_and_signed_pdf_url() -> None:
    created = client.post("/v1/jobs", headers=fake_auth_header("proof-owner", tier="museum"), json=valid_job_request()).json()
    run_all_jobs()
    export = client.get(
        f"/v1/jobs/{created['job_id']}/export",
        headers=fake_auth_header("proof-owner", tier="museum"),
    )
    proof_id = export.json()["deletion_proof_id"]

    response = client.get(
        f"/v1/deletion-proofs/{proof_id}",
        headers=fake_auth_header("proof-owner", tier="museum"),
    )

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "private, no-store"
    payload = response.json()
    assert payload["deletion_proof_id"] == proof_id
    assert payload["job_id"] == created["job_id"]
    assert payload["signature_algorithm"] == "HMAC-SHA256"
    assert payload["proof_sha256"]
    assert payload["pdf_download_url"].startswith("https://storage.googleapis.com/")
    assert "X-Goog-Algorithm=GOOG4-HMAC-SHA256" in payload["pdf_download_url"]
    assert payload["verification_summary"]["status"] == "verified"


def test_deletion_proof_route_is_owner_scoped() -> None:
    created = client.post("/v1/jobs", headers=fake_auth_header("proof-owner-only", tier="pro"), json=valid_job_request()).json()
    run_all_jobs()
    export = client.get(
        f"/v1/jobs/{created['job_id']}/export",
        headers=fake_auth_header("proof-owner-only", tier="pro"),
    )
    proof_id = export.json()["deletion_proof_id"]

    response = client.get(
        f"/v1/deletion-proofs/{proof_id}",
        headers=fake_auth_header("other-proof-user", tier="pro"),
    )

    assert response.status_code == 404


def test_deletion_proof_route_remains_available_after_export_package_expiry() -> None:
    created = client.post("/v1/jobs", headers=fake_auth_header("proof-expiry-owner", tier="pro"), json=valid_job_request()).json()
    run_all_jobs()
    export = client.get(
        f"/v1/jobs/{created['job_id']}/export",
        headers=fake_auth_header("proof-expiry-owner", tier="pro"),
    )
    proof_id = export.json()["deletion_proof_id"]
    JobExportPackageRepository().update_package_for_worker(
        created["job_id"],
        variant="av1",
        patch={"deleted_at": "2026-03-14T00:00:00+00:00"},
    )

    response = client.get(
        f"/v1/deletion-proofs/{proof_id}",
        headers=fake_auth_header("proof-expiry-owner", tier="pro"),
    )

    assert response.status_code == 200


def test_terminal_job_detail_exposes_deletion_proof_id() -> None:
    created = client.post("/v1/jobs", headers=fake_auth_header("proof-detail-owner", tier="museum"), json=valid_job_request()).json()
    run_all_jobs()

    detail = client.get(
        f"/v1/jobs/{created['job_id']}",
        headers=fake_auth_header("proof-detail-owner", tier="museum"),
    )
    export = client.get(
        f"/v1/jobs/{created['job_id']}/export",
        headers=fake_auth_header("proof-detail-owner", tier="museum"),
    )

    assert detail.status_code == 200
    assert export.status_code == 200
    assert detail.json()["deletion_proof_id"] == export.json()["deletion_proof_id"]
