"""Maps to: NFR-012, NFR-006"""

from datetime import datetime, timezone
from types import SimpleNamespace
import os

import pytest
from fastapi.testclient import TestClient

from app.api import webhooks as webhooks_api
from app.billing.webhooks import construct_event, verify_signature
from app.db.phase2_store import BillingAccountRepository, ProcessedStripeEventRepository
from app.main import app

client = TestClient(app)


class _StripeObjectLikeMetadata:
    def __init__(self, payload: dict[str, str]) -> None:
        self._data = dict(payload)

    def __getitem__(self, key):
        if key in self._data:
            return self._data[key]
        raise KeyError(key)

    def to_dict_recursive(self) -> dict[str, str]:
        return dict(self._data)


def test_signature_verification() -> None:
    payload = b"{}"
    secret = "unit_test_secret"

    import hmac
    import hashlib

    signature = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    assert verify_signature(payload, signature, secret) is True


@pytest.mark.skipif(
    os.getenv("CHRONOS_RUN_STRIPE_INTEGRATION") != "1",
    reason="Stripe integration tests disabled",
)
def test_construct_event_with_real_signature() -> None:
    payload = b'{"id":"evt_test","object":"event"}'
    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    if not secret:
        pytest.skip("Missing STRIPE_WEBHOOK_SECRET")

    import time
    import hmac
    import hashlib

    timestamp = int(time.time())
    signed_payload = f"{timestamp}.{payload.decode('utf-8')}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    header = f"t={timestamp},v1={sig}"
    event = construct_event(payload=payload, stripe_signature_header=header, secret=secret)
    assert event is not None


def test_webhook_route_rejects_invalid_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(webhooks_api, "settings", SimpleNamespace(stripe_webhook_secret="whsec_test"))
    monkeypatch.setattr(
        webhooks_api,
        "construct_event",
        lambda payload, stripe_signature_header, secret: (_ for _ in ()).throw(ValueError("bad signature")),
    )

    response = client.post(
        "/v1/webhooks/stripe",
        headers={"Stripe-Signature": "invalid"},
        content=b"{}",
    )

    assert response.status_code == 400
    assert response.json()["title"] == "Invalid Stripe Webhook"


def test_webhook_route_processes_duplicate_replays(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(webhooks_api, "settings", SimpleNamespace(stripe_webhook_secret="whsec_test"))
    event = {
        "id": "evt_duplicate",
        "type": "invoice.paid",
        "data": {
            "object": {
                "id": "in_duplicate",
                "customer": "cus_duplicate",
                "status": "paid",
                "amount_paid": 1500,
                "amount_due": 0,
                "metadata": {
                    "org_id": "org-duplicate",
                    "owner_user_id": "duplicate-owner",
                },
            }
        },
    }
    monkeypatch.setattr(webhooks_api, "construct_event", lambda payload, stripe_signature_header, secret: event)

    first = client.post("/v1/webhooks/stripe", headers={"Stripe-Signature": "valid"}, content=b"{}")
    second = client.post("/v1/webhooks/stripe", headers={"Stripe-Signature": "valid"}, content=b"{}")

    assert first.status_code == 200
    assert first.json()["status"] == "processed"
    assert first.json()["duplicate"] is False
    assert second.status_code == 200
    assert second.json()["status"] == "duplicate"
    assert second.json()["duplicate"] is True
    account = BillingAccountRepository().get_by_org("org-duplicate")
    assert account is not None
    assert account["recent_invoices"][0]["invoice_id"] == "in_duplicate"


def test_webhook_route_handles_stripe_object_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(webhooks_api, "settings", SimpleNamespace(stripe_webhook_secret="whsec_test"))
    stripe_resource = SimpleNamespace(
        id="in_sdk_metadata",
        customer="cus_sdk_metadata",
        status="paid",
        amount_paid=2500,
        amount_due=0,
        metadata=_StripeObjectLikeMetadata(
            {
                "org_id": "org-sdk-metadata",
                "owner_user_id": "sdk-owner",
            }
        ),
    )
    event = {
        "id": "evt_sdk_metadata",
        "type": "invoice.paid",
        "data": {"object": stripe_resource},
    }
    monkeypatch.setattr(webhooks_api, "construct_event", lambda payload, stripe_signature_header, secret: event)

    response = client.post("/v1/webhooks/stripe", headers={"Stripe-Signature": "valid"}, content=b"{}")

    assert response.status_code == 200
    assert response.json()["status"] == "processed"
    assert response.json()["org_id"] == "org-sdk-metadata"
    account = BillingAccountRepository().get_by_org("org-sdk-metadata")
    assert account is not None
    assert account["recent_invoices"][0]["invoice_id"] == "in_sdk_metadata"


def test_subscription_webhook_preserves_zero_priced_updates(monkeypatch: pytest.MonkeyPatch) -> None:
    BillingAccountRepository().upsert_by_org(
        org_id="org-zero-price",
        owner_user_id="zero-price-owner",
        patch={
            "stripe_customer_id": "cus_zero_price",
            "subscription_price_id": "price_paid",
            "subscription_price_usd": 29.0,
        },
    )
    monkeypatch.setattr(webhooks_api, "settings", SimpleNamespace(stripe_webhook_secret="whsec_test"))
    event = {
        "id": "evt_zero_price",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_zero_price",
                "customer": "cus_zero_price",
                "status": "active",
                "items": {"data": [{"price": {"id": "price_free", "unit_amount": 0}}]},
                "metadata": {"org_id": "org-zero-price", "owner_user_id": "zero-price-owner"},
            }
        },
    }
    monkeypatch.setattr(webhooks_api, "construct_event", lambda payload, stripe_signature_header, secret: event)

    response = client.post("/v1/webhooks/stripe", headers={"Stripe-Signature": "valid"}, content=b"{}")

    assert response.status_code == 200
    account = BillingAccountRepository().get_by_org("org-zero-price")
    assert account is not None
    assert account["subscription_price_id"] == "price_free"
    assert account["subscription_price_usd"] == 0.0


def test_webhook_prefers_customer_org_binding_over_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    BillingAccountRepository().upsert_by_org(
        org_id="org-bound-customer",
        owner_user_id="bound-owner",
        patch={"stripe_customer_id": "cus_bound"},
    )
    monkeypatch.setattr(webhooks_api, "settings", SimpleNamespace(stripe_webhook_secret="whsec_test"))
    event = {
        "id": "evt_bound_customer",
        "type": "invoice.paid",
        "created": 1700000000,
        "data": {
            "object": {
                "id": "in_bound_customer",
                "customer": "cus_bound",
                "status": "paid",
                "amount_paid": 1500,
                "amount_due": 0,
                "metadata": {"org_id": "org-stale-metadata", "owner_user_id": "metadata-owner"},
            }
        },
    }
    monkeypatch.setattr(webhooks_api, "construct_event", lambda payload, stripe_signature_header, secret: event)

    response = client.post("/v1/webhooks/stripe", headers={"Stripe-Signature": "valid"}, content=b"{}")

    assert response.status_code == 200
    assert response.json()["org_id"] == "org-bound-customer"
    bound_account = BillingAccountRepository().get_by_org("org-bound-customer")
    stale_account = BillingAccountRepository().get_by_org("org-stale-metadata")
    assert bound_account is not None
    assert bound_account["recent_invoices"][0]["invoice_id"] == "in_bound_customer"
    assert stale_account is None


def test_webhook_last_synced_at_uses_event_timestamp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(webhooks_api, "settings", SimpleNamespace(stripe_webhook_secret="whsec_test"))
    event_created = 1700000000
    event = {
        "id": "evt_event_timestamp",
        "type": "customer.subscription.updated",
        "created": event_created,
        "data": {
            "object": {
                "id": "sub_event_timestamp",
                "customer": "cus_event_timestamp",
                "created": 1600000000,
                "status": "active",
                "items": {"data": [{"price": {"id": "price_museum", "unit_amount": 50000}}]},
                "metadata": {"org_id": "org-event-timestamp", "owner_user_id": "timestamp-owner"},
            }
        },
    }
    monkeypatch.setattr(webhooks_api, "construct_event", lambda payload, stripe_signature_header, secret: event)

    response = client.post("/v1/webhooks/stripe", headers={"Stripe-Signature": "valid"}, content=b"{}")

    assert response.status_code == 200
    account = BillingAccountRepository().get_by_org("org-event-timestamp")
    assert account is not None
    assert account["last_synced_at"] == datetime.fromtimestamp(event_created, tz=timezone.utc).isoformat()


def test_webhook_route_reclaims_failed_event_once_then_stays_duplicate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(webhooks_api, "settings", SimpleNamespace(stripe_webhook_secret="whsec_test"))
    events = {
        "failed": {
            "id": "evt_retry",
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_retry",
                    "customer": "cus_retry",
                    "status": "active",
                    "items": {"data": [{"price": {"id": "price_museum", "unit_amount": 50000}}]},
                    "metadata": {},
                }
            },
        },
        "processed": {
            "id": "evt_retry",
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_retry",
                    "customer": "cus_retry",
                    "status": "active",
                    "items": {"data": [{"price": {"id": "price_museum", "unit_amount": 50000}}]},
                    "metadata": {
                        "org_id": "org-retry",
                        "owner_user_id": "retry-owner",
                        "included_minutes_monthly": "500",
                        "overage_price_id": "price_museum_overage",
                        "overage_rate_usd_per_minute": "0.4",
                    },
                }
            },
        },
    }
    state = {"attempt": 0}

    def fake_construct_event(payload, stripe_signature_header, secret):
        state["attempt"] += 1
        if state["attempt"] == 1:
            return events["failed"]
        return events["processed"]

    monkeypatch.setattr(webhooks_api, "construct_event", fake_construct_event)

    first = client.post("/v1/webhooks/stripe", headers={"Stripe-Signature": "valid"}, content=b"{}")
    second = client.post("/v1/webhooks/stripe", headers={"Stripe-Signature": "valid"}, content=b"{}")
    third = client.post("/v1/webhooks/stripe", headers={"Stripe-Signature": "valid"}, content=b"{}")

    assert first.status_code == 503
    assert second.status_code == 200
    assert second.json()["status"] == "processed"
    assert third.status_code == 200
    assert third.json()["status"] == "duplicate"
    processed_event = ProcessedStripeEventRepository().get_event("evt_retry")
    assert processed_event is not None
    assert processed_event["processing_status"] == "processed"
    account = BillingAccountRepository().get_by_org("org-retry")
    assert account is not None
    assert account["subscription_price_id"] == "price_museum"
