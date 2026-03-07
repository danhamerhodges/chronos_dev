"""Maps to: SEC-009"""

from fastapi.testclient import TestClient

from app.main import app
from tests.helpers.auth import fake_auth_header

client = TestClient(app)


def test_admin_can_update_log_retention_settings() -> None:
    response = client.patch(
        "/v1/orgs/org-1/settings/logs",
        headers=fake_auth_header("admin-1", role="admin", tier="museum", org_id="org-1"),
        json={
            "retention_days": 365,
            "redaction_mode": "strict",
            "categories": ["application_logs", "audit_logs"],
            "export_targets": ["cloud_logging", "splunk"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["org_id"] == "org-1"
    assert payload["redaction_mode"] == "strict"
    assert payload["export_targets"] == ["cloud_logging", "splunk"]


def test_hobbyist_cannot_enable_strict_redaction() -> None:
    response = client.patch(
        "/v1/orgs/org-2/settings/logs",
        headers=fake_auth_header("admin-2", role="admin", tier="hobbyist", org_id="org-2"),
        json={
            "retention_days": 30,
            "redaction_mode": "strict",
            "categories": ["application_logs"],
            "export_targets": [],
        },
    )

    assert response.status_code == 400
    assert response.json()["title"] == "Invalid Log Settings"


def test_cross_org_log_settings_write_is_forbidden() -> None:
    response = client.patch(
        "/v1/orgs/org-2/settings/logs",
        headers=fake_auth_header("admin-1", role="admin", tier="museum", org_id="org-1"),
        json={
            "retention_days": 365,
            "redaction_mode": "strict",
            "categories": ["application_logs", "audit_logs"],
            "export_targets": ["cloud_logging"],
        },
    )

    assert response.status_code == 403
    assert response.json()["title"] == "Forbidden"


def test_non_admin_cannot_update_log_retention_settings() -> None:
    response = client.patch(
        "/v1/orgs/org-1/settings/logs",
        headers=fake_auth_header("member-1", role="member", tier="museum", org_id="org-1"),
        json={
            "retention_days": 365,
            "redaction_mode": "strict",
            "categories": ["application_logs"],
            "export_targets": ["cloud_logging"],
        },
    )

    assert response.status_code == 403
    assert response.json()["title"] == "Forbidden"
