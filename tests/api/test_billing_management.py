"""
Maps to:
- NFR-006
- NFR-012
- SEC-013
"""

from __future__ import annotations

import json
import os

from fastapi.testclient import TestClient

from app.db.phase2_store import BillingAccountRepository
from app.main import app
from tests.helpers.auth import fake_auth_header

client = TestClient(app)


def test_billing_summary_and_portal_session_are_org_scoped(monkeypatch) -> None:
    repo = BillingAccountRepository()
    repo.upsert_by_org(
        org_id="org-alpha",
        owner_user_id="billing-owner-alpha",
        patch={
            "stripe_customer_id": "cus_alpha",
            "subscription_status": "active",
            "recent_invoices": [{"invoice_id": "in_alpha", "status": "paid"}],
            "museum_quote_id": "qt_alpha",
            "museum_quote_status": "open",
        },
    )
    repo.upsert_by_org(
        org_id="org-beta",
        owner_user_id="billing-owner-beta",
        patch={
            "stripe_customer_id": "cus_beta",
            "subscription_status": "past_due",
            "recent_invoices": [{"invoice_id": "in_beta", "status": "open"}],
        },
    )
    monkeypatch.setattr(
        "app.services.billing_management.create_billing_portal_session",
        lambda customer_id, return_url: {"url": f"https://billing.example.test/{customer_id}"},
    )

    member_headers = fake_auth_header("billing-owner-alpha", role="member", tier="museum", org_id="org-alpha")
    admin_headers = fake_auth_header("billing-owner-alpha", role="admin", tier="museum", org_id="org-alpha")
    summary = client.get("/v1/users/me/billing", headers=member_headers)
    member_portal = client.post("/v1/users/me/billing/portal-session", headers=member_headers)
    admin_portal = client.post("/v1/users/me/billing/portal-session", headers=admin_headers)

    assert summary.status_code == 200
    summary_payload = summary.json()
    assert summary_payload["org_id"] == "org-alpha"
    assert summary_payload["stripe_customer_id"] == "cus_alpha"
    assert summary_payload["subscription_status"] == "active"
    assert summary_payload["recent_invoices"] == [{"invoice_id": "in_alpha", "status": "paid"}]
    assert summary_payload["museum_quote"] == {"quote_id": "qt_alpha", "status": "open"}

    assert member_portal.status_code == 403
    assert admin_portal.status_code == 200
    assert admin_portal.json()["url"] == "https://billing.example.test/cus_alpha"


def test_pricebook_activation_requires_platform_admin() -> None:
    payload = json.loads(os.environ["COMMERCIAL_PRICEBOOK_JSON"])
    payload["version"] = "test-pricebook-v2-activation"
    request_body = {
        "bootstrap_from_environment": False,
        "change_summary": "activate audited revision",
        "payload": payload,
    }

    member = client.put(
        "/v1/ops/billing/pricebook",
        headers=fake_auth_header("member-user", role="member", tier="museum", org_id="org-platform"),
        json=request_body,
    )
    admin = client.put(
        "/v1/ops/billing/pricebook",
        headers=fake_auth_header("admin-user", role="admin", tier="museum", org_id="org-platform"),
        json=request_body,
    )
    platform_admin = client.put(
        "/v1/ops/billing/pricebook",
        headers=fake_auth_header("platform-user", role="platform_admin", tier="museum", org_id="org-platform"),
        json=request_body,
    )

    assert member.status_code == 403
    assert admin.status_code == 403
    assert platform_admin.status_code == 200
    assert platform_admin.json()["version"] == "test-pricebook-v2-activation"
    assert platform_admin.json()["source"] == "api"
