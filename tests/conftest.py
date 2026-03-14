"""Maps to: ENG-016, SEC-013, OPS-001, OPS-002, NFR-012, DS-007"""

import os

import pytest

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("TEST_AUTH_OVERRIDE", "1")

try:
    from fastapi.testclient import TestClient
    from app.billing.stripe_client import BillingPricingMetadata
    from app.main import app
    from app.db.phase2_store import reset_phase2_store
    from app.observability.monitoring import reset_monitoring_state
    from app.services.job_runtime import reset_job_runtime_state
    from app.services.rate_limits import reset_rate_limits

    client = TestClient(app)
except Exception as exc:  # pragma: no cover - dependency-gated environment
    client = None
    pytestmark = pytest.mark.skip(reason=f"Test client unavailable in current environment: {exc}")


@pytest.fixture(autouse=True)
def reset_phase2_state(monkeypatch: pytest.MonkeyPatch) -> None:
    if client is None:
        return
    reset_phase2_store()
    reset_job_runtime_state()
    reset_rate_limits()
    reset_monitoring_state()
    monkeypatch.setattr(
        "app.services.cost_estimation.resolve_billing_pricing_metadata",
        lambda: BillingPricingMetadata(
            subscription_price_id="price_subscription",
            overage_price_id="price_overage",
            overage_rate_usd_per_minute=0.75,
        ),
    )
