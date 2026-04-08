"""
Maps to:
- ENG-013
- FR-006
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.billing_service import BillingService, monthly_limit_for_tier
from tests.helpers.auth import fake_auth_header
from tests.helpers.jobs import valid_job_request
from tests.helpers.previews import seed_completed_upload, seed_detection, save_configuration_with_approved_preview

client = TestClient(app)


def test_estimate_route_returns_full_breakdown_for_valid_launch_payload() -> None:
    response = client.post(
        "/v1/jobs/estimate",
        headers=fake_auth_header("estimate-user", tier="pro"),
        json=valid_job_request(estimated_duration_seconds=180, fidelity_tier="Restore"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["estimated_usage_minutes"] == 5
    assert payload["operational_cost_breakdown_usd"]["gpu_time"] > 0
    assert payload["operational_cost_breakdown_usd"]["total"] > 0
    assert payload["billing_breakdown_usd"]["included_usage"] == 5
    assert payload["billing_breakdown_usd"]["overage_minutes"] == 0
    assert payload["usage_snapshot"]["estimated_next_job_minutes"] == 5
    assert payload["launch_blocker"] == "none"
    assert payload["estimator_version"] == "packet4e-v1"
    assert len(payload["configuration_fingerprint"]) == 64


def test_estimate_route_accepts_launch_context_without_preview_enforcement() -> None:
    response = client.post(
        "/v1/jobs/estimate",
        headers=fake_auth_header("estimate-user-with-context", tier="pro"),
        json=valid_job_request(
            launch_context={
                "source": "approved_preview",
                "upload_id": "upload-estimate-context",
                "configuration_fingerprint": "a" * 64,
            }
        ),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["launch_blocker"] == "none"


def test_estimate_route_returns_overage_blocker_instead_of_403() -> None:
    service = BillingService()
    limit = monthly_limit_for_tier("hobbyist")
    service.consume_minutes(user_id="estimate-overage-user", plan_tier="hobbyist", minutes=limit)

    response = client.post(
        "/v1/jobs/estimate",
        headers=fake_auth_header("estimate-overage-user", tier="hobbyist"),
        json=valid_job_request(estimated_duration_seconds=180, fidelity_tier="Restore"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["launch_blocker"] == "overage_approval_required"
    assert payload["usage_snapshot"]["hard_stop"] is True


def test_estimate_route_returns_503_when_pricing_metadata_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.cost_estimation.resolve_billing_pricing_metadata",
        lambda: (_ for _ in ()).throw(ValueError("STRIPE_SECRET_KEY is required for billing price resolution.")),
    )

    response = client.post(
        "/v1/jobs/estimate",
        headers=fake_auth_header("estimate-pricing-unavailable", tier="pro"),
        json=valid_job_request(estimated_duration_seconds=180, fidelity_tier="Restore"),
    )

    assert response.status_code == 503
    payload = response.json()
    assert payload["title"] == "Billing Pricing Unavailable"
    assert "Pricing data is temporarily unavailable." in payload["detail"]


def test_launch_route_returns_503_when_pricing_metadata_is_invalid(monkeypatch) -> None:
    seed_completed_upload(upload_id="launch-pricing-upload", owner_user_id="launch-pricing-unavailable")
    seed_detection(upload_id="launch-pricing-upload", owner_user_id="launch-pricing-unavailable")
    configuration = save_configuration_with_approved_preview(
        client,
        upload_id="launch-pricing-upload",
        owner_user_id="launch-pricing-unavailable",
    )
    monkeypatch.setattr(
        "app.services.cost_estimation.resolve_billing_pricing_metadata",
        lambda: (_ for _ in ()).throw(ValueError("Stripe overage price is missing unit_amount metadata.")),
    )

    response = client.post(
        "/v1/jobs",
        headers=fake_auth_header("launch-pricing-unavailable", tier="pro"),
        json=configuration["job_payload_preview"],
    )

    assert response.status_code == 503
    payload = response.json()
    assert payload["title"] == "Billing Pricing Unavailable"
    assert "Pricing data is temporarily unavailable." in payload["detail"]


@pytest.mark.parametrize(
    ("tier", "fidelity_tier", "expected_minutes"),
    [
        ("hobbyist", "Enhance", 3),
        ("pro", "Restore", 5),
        ("museum", "Conserve", 6),
    ],
)
def test_estimate_route_covers_all_three_plan_tiers(
    tier: str,
    fidelity_tier: str,
    expected_minutes: int,
) -> None:
    response = client.post(
        "/v1/jobs/estimate",
        headers=fake_auth_header(f"estimate-{tier}", tier=tier),
        json=valid_job_request(estimated_duration_seconds=180, fidelity_tier=fidelity_tier),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["usage_snapshot"]["plan_tier"] == tier
    assert payload["estimated_usage_minutes"] == expected_minutes
