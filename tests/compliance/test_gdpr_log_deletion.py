"""Maps to: SEC-009"""

from fastapi.testclient import TestClient

from app.main import app
from tests.helpers.auth import fake_auth_header

client = TestClient(app)


def test_user_can_submit_gdpr_log_deletion_request() -> None:
    response = client.post(
        "/v1/user/delete_logs",
        headers=fake_auth_header("privacy-user"),
        json={
            "categories": ["application_logs", "audit_logs"],
            "date_from": "2025-01-01",
            "date_to": "2025-01-31",
            "reason": "GDPR request",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["deleted_categories"] == ["application_logs", "audit_logs"]
    assert payload["deletion_request_id"]
    assert payload["deletion_proof_id"]


def test_log_deletion_rejects_invalid_date_ranges() -> None:
    response = client.post(
        "/v1/user/delete_logs",
        headers=fake_auth_header("privacy-user"),
        json={
            "categories": ["application_logs"],
            "date_from": "2025-02-01",
            "date_to": "2025-01-01",
        },
    )

    assert response.status_code == 400
    assert response.json()["title"] == "Invalid Log Deletion Request"
