"""Maps to: ENG-010"""

from fastapi.testclient import TestClient

from app.main import app
from tests.helpers.auth import fake_auth_header
from tests.helpers.jobs import run_all_jobs, valid_job_request

client = TestClient(app)


def test_manifest_endpoint_returns_job_manifest_for_owner() -> None:
    created = client.post("/v1/jobs", headers=fake_auth_header("manifest-owner", tier="pro"), json=valid_job_request()).json()

    run_all_jobs()
    response = client.get(
        f"/v1/manifests/{created['job_id']}",
        headers=fake_auth_header("manifest-owner", tier="pro"),
    )

    assert response.status_code == 200
    assert response.json()["manifest_id"] == created["job_id"]


def test_manifest_endpoint_hides_other_users_artifacts() -> None:
    created = client.post("/v1/jobs", headers=fake_auth_header("manifest-owner-b", tier="pro"), json=valid_job_request()).json()

    run_all_jobs()
    response = client.get(
        f"/v1/manifests/{created['job_id']}",
        headers=fake_auth_header("manifest-other", tier="pro"),
    )

    assert response.status_code == 404
