"""
Maps to:
- SEC-004
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.db.phase2_store import BillingAccountRepository
from app.main import app
from tests.helpers.auth import fake_auth_header
from tests.helpers.jobs import create_seed_job, run_all_jobs
from tests.helpers.previews import create_preview, save_configuration, seed_completed_upload, seed_detection

client = TestClient(app)


def test_owner_scoped_artifacts_hide_cross_user_resources() -> None:
    job = create_seed_job(user_id="access-owner", tier="pro")
    run_all_jobs()
    owner_export = client.get(
        f"/v1/jobs/{job['job_id']}/export",
        headers=fake_auth_header("access-owner", tier="pro"),
    )
    assert owner_export.status_code == 200
    proof_id = owner_export.json()["deletion_proof_id"]

    seed_completed_upload(upload_id="access-preview-upload", owner_user_id="preview-owner")
    seed_detection(upload_id="access-preview-upload", owner_user_id="preview-owner")
    save_configuration(client, upload_id="access-preview-upload", owner_user_id="preview-owner")
    preview = create_preview(client, upload_id="access-preview-upload", owner_user_id="preview-owner")

    responses = [
        client.get(f"/v1/jobs/{job['job_id']}", headers=fake_auth_header("access-other", tier="pro")),
        client.get(f"/v1/manifests/{job['job_id']}", headers=fake_auth_header("access-other", tier="pro")),
        client.get(f"/v1/deletion-proofs/{proof_id}", headers=fake_auth_header("access-other", tier="pro")),
        client.post(
            "/v1/upload/access-preview-upload/resume",
            headers=fake_auth_header("access-other", tier="pro"),
        ),
        client.get(
            f"/v1/previews/{preview['preview_id']}",
            headers=fake_auth_header("access-other", tier="pro"),
        ),
    ]

    assert [response.status_code for response in responses] == [404, 404, 404, 404, 404]


def test_self_billing_routes_use_authenticated_org_scope(monkeypatch) -> None:
    repo = BillingAccountRepository()
    repo.upsert_by_org(
        org_id="org-alpha",
        owner_user_id="billing-alpha-owner",
        patch={
            "stripe_customer_id": "cus_alpha",
            "subscription_status": "active",
            "recent_invoices": [{"invoice_id": "in_alpha", "status": "paid"}],
        },
    )
    repo.upsert_by_org(
        org_id="org-beta",
        owner_user_id="billing-beta-owner",
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

    member_headers = fake_auth_header("billing-alpha-owner", role="member", tier="museum", org_id="org-alpha")
    admin_headers = fake_auth_header("billing-alpha-admin", role="admin", tier="museum", org_id="org-alpha")
    summary = client.get("/v1/users/me/billing", headers=member_headers)
    portal = client.post("/v1/users/me/billing/portal-session", headers=admin_headers)

    assert summary.status_code == 200
    assert summary.json()["org_id"] == "org-alpha"
    assert summary.json()["stripe_customer_id"] == "cus_alpha"
    assert summary.json()["recent_invoices"] == [{"invoice_id": "in_alpha", "status": "paid"}]
    assert "cus_beta" not in json.dumps(summary.json())

    assert portal.status_code == 200
    assert portal.json()["url"] == "https://billing.example.test/cus_alpha"
