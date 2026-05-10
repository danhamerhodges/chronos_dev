"""
Maps to:
- SEC-001
"""

from __future__ import annotations

import json
import os

from fastapi.testclient import TestClient

from app.main import app
from tests.helpers.auth import fake_auth_header

client = TestClient(app)


def test_protected_routes_require_bearer_token() -> None:
    routes = [
        ("GET", "/v1/users/me", None),
        ("GET", "/v1/jobs", None),
        ("GET", "/v1/ops/runtime", None),
        ("GET", "/v1/users/me/billing", None),
    ]

    for method, path, body in routes:
        response = client.request(method, path, json=body)
        assert response.status_code == 401
        assert response.json()["title"] == "Unauthorized"


def test_insufficient_roles_are_forbidden() -> None:
    member_portal = client.post(
        "/v1/users/me/billing/portal-session",
        headers=fake_auth_header("billing-member", role="member", tier="museum"),
    )
    member_ops = client.get(
        "/v1/ops/runtime",
        headers=fake_auth_header("ops-member", role="member", tier="museum"),
    )
    analyst_logs = client.patch(
        "/v1/orgs/org-alpha/settings/logs",
        headers=fake_auth_header("logs-analyst", role="analyst", tier="museum", org_id="org-alpha"),
        json={"retention_days": 30, "redaction_mode": "standard", "categories": ["auth"]},
    )

    assert member_portal.status_code == 403
    assert member_ops.status_code == 403
    assert analyst_logs.status_code == 403


def test_ops_pricebook_activation_remains_platform_admin_only() -> None:
    payload = json.loads(os.environ["COMMERCIAL_PRICEBOOK_JSON"])
    payload["version"] = "packet-5e-pricebook-auth"
    request_body = {
        "bootstrap_from_environment": False,
        "change_summary": "verify Packet 5E ops write boundary",
        "payload": payload,
    }

    read = client.get(
        "/v1/ops/runtime",
        headers=fake_auth_header("ops-admin", role="admin", tier="museum", org_id="org-ops"),
    )
    admin_write = client.put(
        "/v1/ops/billing/pricebook",
        headers=fake_auth_header("ops-admin", role="admin", tier="museum", org_id="org-ops"),
        json=request_body,
    )
    platform_write = client.put(
        "/v1/ops/billing/pricebook",
        headers=fake_auth_header("ops-platform", role="platform_admin", tier="museum", org_id="org-ops"),
        json=request_body,
    )

    assert read.status_code == 200
    assert admin_write.status_code == 403
    assert platform_write.status_code == 200
    assert platform_write.json()["version"] == "packet-5e-pricebook-auth"
