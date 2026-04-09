"""Maps to: ENG-016, SEC-013, OPS-001, OPS-002, NFR-012, DS-007"""

import json
import os

import pytest

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("TEST_AUTH_OVERRIDE", "1")
os.environ.setdefault("STRIPE_HOBBYIST_PRICE_ID", "price_hobbyist")
os.environ.setdefault("STRIPE_PRO_PRICE_ID", "price_pro")
os.environ.setdefault("STRIPE_MUSEUM_PRICE_ID", "price_museum")
os.environ.setdefault(
    "COMMERCIAL_PRICEBOOK_JSON",
    json.dumps(
        {
            "version": "test-pricebook-v1",
            "entries": {
                "price_hobbyist": {
                    "plan_tier": "hobbyist",
                    "included_minutes_monthly": 30,
                    "overage": {
                        "enabled": False,
                        "price_id": "",
                        "rate_usd_per_minute": 0.0,
                    },
                    "entitlements": {
                        "preview_review": True,
                        "fidelity_tiers": ["Enhance"],
                        "resolution_cap": "1080p",
                        "parallel_jobs": 1,
                        "export_retention_days": 7,
                    },
                },
                "price_pro": {
                    "plan_tier": "pro",
                    "included_minutes_monthly": 60,
                    "overage": {
                        "enabled": True,
                        "price_id": "price_pro_overage",
                        "rate_usd_per_minute": 0.5,
                    },
                    "entitlements": {
                        "preview_review": True,
                        "fidelity_tiers": ["Enhance", "Restore", "Conserve"],
                        "resolution_cap": "4k",
                        "parallel_jobs": 5,
                        "export_retention_days": 7,
                    },
                },
                "price_museum": {
                    "plan_tier": "museum",
                    "included_minutes_monthly": 500,
                    "overage": {
                        "enabled": True,
                        "price_id": "price_museum_overage",
                        "rate_usd_per_minute": 0.4,
                    },
                    "entitlements": {
                        "preview_review": True,
                        "fidelity_tiers": ["Enhance", "Restore", "Conserve"],
                        "resolution_cap": "native_scan",
                        "parallel_jobs": 20,
                        "export_retention_days": 90,
                    },
                },
            },
        }
    ),
)

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
            subscription_price_usd=120.0,
            subscription_price_ids_by_tier={
                "hobbyist": "",
                "pro": "price_subscription",
                "museum": "price_subscription",
            },
            subscription_prices_usd_by_tier={
                "hobbyist": 0.0,
                "pro": 120.0,
                "museum": 120.0,
            },
        ),
    )
    monkeypatch.setattr(
        "app.services.cost_ops.resolve_billing_pricing_metadata",
        lambda: BillingPricingMetadata(
            subscription_price_id="price_subscription",
            overage_price_id="price_overage",
            overage_rate_usd_per_minute=0.75,
            subscription_price_usd=120.0,
            subscription_price_ids_by_tier={
                "hobbyist": "",
                "pro": "price_subscription",
                "museum": "price_subscription",
            },
            subscription_prices_usd_by_tier={
                "hobbyist": 0.0,
                "pro": 120.0,
                "museum": 120.0,
            },
        ),
    )
    monkeypatch.setattr(
        "app.api.users.resolve_billing_pricing_metadata",
        lambda: BillingPricingMetadata(
            subscription_price_id="price_subscription",
            overage_price_id="price_overage",
            overage_rate_usd_per_minute=0.75,
            subscription_price_usd=120.0,
            subscription_price_ids_by_tier={
                "hobbyist": "price_hobbyist",
                "pro": "price_pro",
                "museum": "price_museum",
            },
            subscription_prices_usd_by_tier={
                "hobbyist": 0.0,
                "pro": 29.0,
                "museum": 500.0,
            },
        ),
    )
