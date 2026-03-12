"""Maps to: ENG-002, ENG-010, ENG-011, SEC-009, FR-001, FR-003, DS-001"""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from tests.helpers.auth import fake_auth_header

client = TestClient(app)


def test_v1_health_returns_component_statuses() -> None:
    response = client.get("/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"healthy", "degraded"}
    assert set(payload["components"]) == {"database", "redis", "gcs"}


def test_version_returns_build_metadata() -> None:
    response = client.get("/v1/version")
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"version", "build_sha", "build_time"}


def test_user_route_requires_bearer_token() -> None:
    response = client.get("/v1/users/me")
    assert response.status_code == 401
    payload = response.json()
    assert payload["title"] == "Unauthorized"
    assert payload["status"] == 401


def test_partial_profile_update_preserves_existing_preferences() -> None:
    headers = fake_auth_header("user-profile-preserve")
    seed = client.patch(
        "/v1/users/me",
        headers=headers,
        json={"preferences": {"theme": "sepia"}},
    )
    assert seed.status_code == 200

    response = client.patch(
        "/v1/users/me",
        headers=headers,
        json={"display_name": "Archivist"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["display_name"] == "Archivist"
    assert payload["preferences"] == {"theme": "sepia"}


def test_testing_reset_rate_limits_endpoint_is_available_in_test_mode() -> None:
    response = client.post("/v1/testing/reset-rate-limits", headers=fake_auth_header("user-1"))
    assert response.status_code == 200
    assert response.json() == {"status": "reset"}


def test_testing_job_dispatcher_endpoint_is_available_in_test_mode() -> None:
    response = client.post("/v1/testing/jobs/run-dispatcher", headers=fake_auth_header("user-1"))
    assert response.status_code == 200
    assert response.json() == {"processed_jobs": []}


def test_admin_runtime_ops_snapshot_requires_ops_permission() -> None:
    response = client.get("/v1/ops/runtime", headers=fake_auth_header("ops-admin", role="admin"))
    assert response.status_code == 200
    payload = response.json()
    assert "desired_warm_instances" in payload
    assert "alert_routes" in payload


def test_request_validation_errors_use_problem_details_shape() -> None:
    response = client.post(
        "/v1/detect-era",
        headers=fake_auth_header("user-2"),
        json={},
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload["title"] == "Request Validation Failed"
    assert payload["errors"]


def test_tracked_openapi_spec_covers_phase2_subset() -> None:
    root = Path(__file__).resolve().parents[2]
    openapi_spec = (root / "docs" / "api" / "openapi.yaml").read_text(encoding="utf-8")

    assert "/v1/upload:" in openapi_spec
    assert "/v1/upload/{upload_id}:" in openapi_spec
    assert "/v1/upload/{upload_id}/resume:" in openapi_spec
    assert "/v1/upload/{upload_id}/detect-era:" in openapi_spec
    assert "/v1/upload/{upload_id}/configuration:" in openapi_spec
    assert "/v1/fidelity-tiers:" in openapi_spec
    assert "/v1/detect-era:" in openapi_spec
    assert "/v1/orgs/{org_id}/settings/logs:" in openapi_spec
    assert "/v1/jobs:" in openapi_spec
    assert "/v1/manifests/{job_id}:" in openapi_spec
    assert "/v1/ops/runtime:" in openapi_spec
