"""Maps to: NFR-006"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient
import pytest

from app.billing.pricebook import (
    CommercialPricebookConfigurationError,
    parse_commercial_pricebook,
    validate_commercial_pricebook_configuration,
)
from app.main import app
from app.services.billing_service import BillingService
from tests.helpers.auth import fake_auth_header
from tests.helpers.previews import seed_completed_upload, seed_detection

client = TestClient(app)


def _pricebook_payload(
    *,
    hobbyist_minutes: int = 30,
    hobbyist_fidelity_tiers: list[str] | None = None,
    hobbyist_resolution_cap: str = "1080p",
    pro_retention_days: int = 7,
) -> str:
    return json.dumps(
        {
            "version": "test-pricebook-override",
            "entries": {
                "price_hobbyist": {
                    "plan_tier": "hobbyist",
                    "included_minutes_monthly": hobbyist_minutes,
                    "overage": {"enabled": False, "price_id": "", "rate_usd_per_minute": 0.0},
                    "entitlements": {
                        "preview_review": True,
                        "fidelity_tiers": hobbyist_fidelity_tiers or ["Enhance"],
                        "resolution_cap": hobbyist_resolution_cap,
                        "parallel_jobs": 1,
                        "export_retention_days": 7,
                    },
                },
                "price_pro": {
                    "plan_tier": "pro",
                    "included_minutes_monthly": 60,
                    "overage": {"enabled": True, "price_id": "price_pro_overage", "rate_usd_per_minute": 0.5},
                    "entitlements": {
                        "preview_review": True,
                        "fidelity_tiers": ["Enhance", "Restore", "Conserve"],
                        "resolution_cap": "4k",
                        "parallel_jobs": 5,
                        "export_retention_days": pro_retention_days,
                    },
                },
                "price_museum": {
                    "plan_tier": "museum",
                    "included_minutes_monthly": 500,
                    "overage": {"enabled": True, "price_id": "price_museum_overage", "rate_usd_per_minute": 0.4},
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
    )


def test_pricebook_parser_rejects_incomplete_current_surface_entry() -> None:
    with pytest.raises(CommercialPricebookConfigurationError, match="export_retention_days"):
        parse_commercial_pricebook(
            json.dumps(
                {
                    "version": "broken-pricebook",
                    "entries": {
                        "price_hobbyist": {
                            "plan_tier": "hobbyist",
                            "included_minutes_monthly": 30,
                            "overage": {"enabled": False, "price_id": "", "rate_usd_per_minute": 0.0},
                            "entitlements": {
                                "preview_review": True,
                                "fidelity_tiers": ["Enhance"],
                                "resolution_cap": "1080p",
                                "parallel_jobs": 1,
                            },
                        }
                    },
                }
            )
        )


def test_pricebook_parser_rejects_missing_payload() -> None:
    with pytest.raises(CommercialPricebookConfigurationError, match="COMMERCIAL_PRICEBOOK_JSON is required"):
        parse_commercial_pricebook("")


def test_pricebook_parser_rejects_malformed_json() -> None:
    with pytest.raises(CommercialPricebookConfigurationError, match="must be valid JSON"):
        parse_commercial_pricebook("{not-json")


def test_pricebook_configuration_rejects_inconsistent_active_price_mapping() -> None:
    with pytest.raises(CommercialPricebookConfigurationError, match="missing an entry for recurring price id price_pro_live"):
        validate_commercial_pricebook_configuration(
            raw_json=_pricebook_payload(),
            recurring_price_ids_by_tier={
                "hobbyist": "price_hobbyist",
                "pro": "price_pro_live",
                "museum": "price_museum",
            },
        )


def test_usage_snapshot_refreshes_when_pricebook_changes_without_recreating_usage(monkeypatch) -> None:
    service = BillingService()

    initial = service.snapshot(user_id="pricebook-refresh-user", plan_tier="hobbyist")
    assert initial.monthly_limit_minutes == 30

    monkeypatch.setattr(
        "app.services.billing_service.cached_commercial_pricebook",
        lambda *_args: parse_commercial_pricebook(_pricebook_payload(hobbyist_minutes=45)),
    )

    refreshed = service.snapshot(user_id="pricebook-refresh-user", plan_tier="hobbyist")
    assert refreshed.monthly_limit_minutes == 45


def test_hobbyist_configuration_entitlements_follow_pricebook(monkeypatch) -> None:
    seed_completed_upload(upload_id="pricebook-config-upload", owner_user_id="pricebook-config-user")
    seed_detection(upload_id="pricebook-config-upload", owner_user_id="pricebook-config-user")
    monkeypatch.setattr(
        "app.services.billing_service.cached_commercial_pricebook",
        lambda *_args: parse_commercial_pricebook(
            _pricebook_payload(
                hobbyist_fidelity_tiers=["Enhance", "Restore"],
                hobbyist_resolution_cap="4k",
            )
        ),
    )

    response = client.patch(
        "/v1/upload/pricebook-config-upload/configuration",
        headers=fake_auth_header("pricebook-config-user", tier="hobbyist"),
        json={
            "persona": "filmmaker",
            "fidelity_tier": "Restore",
            "grain_preset": "Heavy",
            "estimated_duration_seconds": 180,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["fidelity_tier"] == "Restore"
    assert payload["job_payload_preview"]["era_profile"]["resolution_cap"] == "4k"
