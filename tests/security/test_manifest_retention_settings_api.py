"""
Maps to:
- SEC-005
- SEC-001
- SEC-013
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db.phase2_store import ManifestRetentionSettingsRepository, reset_phase2_store
from app.main import app
from tests.helpers.auth import fake_auth_header

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state() -> None:
    reset_phase2_store()
    response = client.post("/v1/testing/reset-rate-limits", headers=fake_auth_header("retention-settings-reset"))
    assert response.status_code == 200


@pytest.mark.parametrize(
    ("manifest_retention_days", "expected_class"),
    [(0, "0d"), (90, "90d"), (365, "365d"), (1825, "1825d"), (None, "indefinite")],
)
def test_museum_admin_can_update_manifest_retention_settings(
    manifest_retention_days: int | None,
    expected_class: str,
) -> None:
    response = client.patch(
        "/v1/orgs/museum-org/settings/retention",
        headers=fake_auth_header("museum-admin", role="admin", tier="museum", org_id="museum-org"),
        json={
            "manifest_retention_days": manifest_retention_days,
            "manifest_redaction_enabled": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["org_id"] == "museum-org"
    assert payload["plan_tier"] == "museum"
    assert payload["manifest_retention_days"] == manifest_retention_days
    assert payload["manifest_redaction_enabled"] is True
    assert payload["retention_class"] == expected_class
    assert payload["updated_by"] == "museum-admin"
    assert payload["updated_at"]

    persisted = ManifestRetentionSettingsRepository().get("museum-org")
    assert persisted is not None
    assert persisted["manifest_retention_days"] == manifest_retention_days
    assert persisted["manifest_redaction_enabled"] is True


def test_platform_admin_can_update_manifest_retention_settings() -> None:
    response = client.patch(
        "/v1/orgs/museum-org/settings/retention",
        headers=fake_auth_header("platform-admin", role="platform_admin", tier="museum", org_id="museum-org"),
        json={
            "manifest_retention_days": 365,
            "manifest_redaction_enabled": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["retention_class"] == "365d"
    assert payload["updated_by"] == "platform-admin"


def test_museum_admin_can_read_current_manifest_retention_settings() -> None:
    ManifestRetentionSettingsRepository().upsert(
        org_id="museum-org",
        plan_tier="museum",
        manifest_retention_days=90,
        manifest_redaction_enabled=True,
        updated_by="previous-admin",
    )

    response = client.get(
        "/v1/orgs/museum-org/settings/retention",
        headers=fake_auth_header("museum-admin", role="admin", tier="museum", org_id="museum-org"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["org_id"] == "museum-org"
    assert payload["manifest_retention_days"] == 90
    assert payload["manifest_redaction_enabled"] is True
    assert payload["retention_class"] == "90d"


def test_non_admin_cannot_update_manifest_retention_settings() -> None:
    response = client.patch(
        "/v1/orgs/museum-org/settings/retention",
        headers=fake_auth_header("museum-member", role="member", tier="museum", org_id="museum-org"),
        json={
            "manifest_retention_days": 90,
            "manifest_redaction_enabled": True,
        },
    )

    assert response.status_code == 403
    assert response.json()["title"] == "Forbidden"


def test_cross_org_manifest_retention_settings_write_is_forbidden() -> None:
    response = client.patch(
        "/v1/orgs/other-org/settings/retention",
        headers=fake_auth_header("museum-admin", role="admin", tier="museum", org_id="museum-org"),
        json={
            "manifest_retention_days": 90,
            "manifest_redaction_enabled": True,
        },
    )

    assert response.status_code == 403
    assert response.json()["title"] == "Forbidden"


def test_non_museum_tier_cannot_update_manifest_retention_settings() -> None:
    response = client.patch(
        "/v1/orgs/pro-org/settings/retention",
        headers=fake_auth_header("pro-admin", role="admin", tier="pro", org_id="pro-org"),
        json={
            "manifest_retention_days": 90,
            "manifest_redaction_enabled": True,
        },
    )

    assert response.status_code == 403
    assert response.json()["title"] == "Forbidden"


def test_unsupported_manifest_retention_value_returns_400() -> None:
    response = client.patch(
        "/v1/orgs/museum-org/settings/retention",
        headers=fake_auth_header("museum-admin", role="admin", tier="museum", org_id="museum-org"),
        json={
            "manifest_retention_days": 30,
            "manifest_redaction_enabled": True,
        },
    )

    assert response.status_code == 400
    assert response.json()["title"] == "Invalid Retention Settings"
