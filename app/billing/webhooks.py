"""Webhook verification baseline for NFR-012."""

from __future__ import annotations

import hmac
import hashlib
from typing import Any

import stripe


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def construct_event(payload: bytes, stripe_signature_header: str, secret: str) -> Any:
    """Construct and verify a Stripe event from webhook payload + signature."""
    return stripe.Webhook.construct_event(payload=payload, sig_header=stripe_signature_header, secret=secret)
