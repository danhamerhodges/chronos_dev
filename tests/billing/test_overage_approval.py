"""Maps to: NFR-007"""

import pytest

from app.services.billing_service import BillingService, monthly_limit_for_tier


def test_overage_approval_clears_hard_stop() -> None:
    service = BillingService()
    limit = monthly_limit_for_tier("hobbyist")

    snapshot = service.consume_minutes(user_id="user-overage", plan_tier="hobbyist", minutes=limit)
    assert snapshot.hard_stop is True

    snapshot = service.approve_overage(
        user_id="user-overage",
        plan_tier="hobbyist",
        approval_scope="single_job",
        requested_minutes=30,
    )
    assert snapshot.hard_stop is False
    assert snapshot.overage_approval_scope == "single_job"
    assert snapshot.approved_for_minutes == 30


def test_upgrade_tier_scope_is_recorded_without_granting_overage_minutes() -> None:
    service = BillingService()

    snapshot = service.approve_overage(
        user_id="user-upgrade",
        plan_tier="hobbyist",
        approval_scope="upgrade_tier",
        requested_minutes=0,
    )

    assert snapshot.overage_approval_scope == "upgrade_tier"
    assert snapshot.approved_for_minutes == 0


def test_invalid_overage_scope_is_rejected() -> None:
    service = BillingService()

    with pytest.raises(ValueError, match="approval_scope must be one of"):
        service.approve_overage(
            user_id="user-invalid-overage",
            plan_tier="hobbyist",
            approval_scope="forever",
            requested_minutes=15,
        )
