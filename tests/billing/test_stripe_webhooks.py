"""Maps to: NFR-012"""

import os

import pytest

from app.billing.webhooks import construct_event, verify_signature


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
