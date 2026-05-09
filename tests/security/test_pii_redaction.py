"""Maps to: SEC-009, OPS-002"""

import json
import logging

from app.observability.logging import JsonFormatter


def test_standard_redaction_masks_tokens_and_email_addresses() -> None:
    formatter = JsonFormatter(redaction_mode="standard")
    record = logging.LogRecord(
        "chronos.test",
        logging.INFO,
        __file__,
        1,
        "authorization=Bearer secret-token email=user@example.com",
        args=(),
        exc_info=None,
    )
    payload = json.loads(formatter.format(record))

    assert "secret-token" not in payload["message"]
    assert "user@example.com" not in payload["message"]
    assert "[REDACTED_EMAIL]" in payload["message"]


def test_standard_redaction_masks_stripe_resource_ids() -> None:
    formatter = JsonFormatter(redaction_mode="standard")
    record = logging.LogRecord(
        "stripe",
        logging.INFO,
        __file__,
        1,
        "Request to Stripe api url=https://api.stripe.com/v1/prices/price_123 customer=cus_123 invoice=in_123",
        args=(),
        exc_info=None,
    )
    payload = json.loads(formatter.format(record))

    assert "price_123" not in payload["message"]
    assert "cus_123" not in payload["message"]
    assert "in_123" not in payload["message"]
    assert payload["message"].count("[REDACTED_STRIPE_ID]") == 3


def test_strict_redaction_masks_gcs_paths() -> None:
    formatter = JsonFormatter(redaction_mode="strict")
    record = logging.LogRecord(
        "chronos.test",
        logging.INFO,
        __file__,
        1,
        "job job_123 uploaded to gs://chronos-dev/raw/object.json",
        args=(),
        exc_info=None,
    )
    payload = json.loads(formatter.format(record))

    assert "job_123" not in payload["message"]
    assert "gs://chronos-dev/raw/object.json" not in payload["message"]
    assert "[REDACTED_JOB]" in payload["message"]
