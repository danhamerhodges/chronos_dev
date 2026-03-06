"""Maps to: ENG-002, ENG-004, FR-002, NFR-007"""

from fastapi.testclient import TestClient

from app.main import app
from tests.helpers.auth import fake_auth_header
from tests.helpers.phase2 import valid_detect_request

client = TestClient(app)


def test_detect_era_round_trip_updates_usage_and_supports_override() -> None:
    detect_response = client.post(
        "/v1/detect-era",
        headers=fake_auth_header("integrator", tier="pro"),
        json=valid_detect_request(
            job_id="job-integration",
            manual_override_era="1950s Kodachrome Film",
            override_reason="Confirmed from sleeve metadata",
        ),
    )
    assert detect_response.status_code == 200
    detect_payload = detect_response.json()
    assert detect_payload["source"] == "user_override"
    assert detect_payload["era"] == "1950s Kodachrome Film"

    usage_response = client.get("/v1/users/me/usage", headers=fake_auth_header("integrator", tier="pro"))
    assert usage_response.status_code == 200
    usage_payload = usage_response.json()
    assert usage_payload["estimated_next_job_minutes"] == 3
    assert usage_payload["plan_tier"] == "pro"
