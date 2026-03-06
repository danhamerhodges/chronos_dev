"""Maps to: NFR-007"""

from app.services.billing_service import (
    BillingService,
    billable_minutes_for_duration,
    monthly_limit_for_tier,
)


def test_billable_minutes_apply_mode_multiplier() -> None:
    assert billable_minutes_for_duration(180, "Enhance") == 3
    assert billable_minutes_for_duration(180, "Restore") == 5
    assert billable_minutes_for_duration(180, "Conserve") == 6


def test_hard_stop_engages_when_usage_exceeds_monthly_limit_without_approval() -> None:
    service = BillingService()
    limit = monthly_limit_for_tier("hobbyist")
    snapshot = service.consume_minutes(user_id="user-hard-stop", plan_tier="hobbyist", minutes=limit)

    assert snapshot.hard_stop is True
    assert snapshot.remaining_minutes == 0


def test_hard_stop_engages_when_next_estimate_exceeds_available_budget() -> None:
    service = BillingService()
    limit = monthly_limit_for_tier("hobbyist")
    service.consume_minutes(user_id="user-projected-stop", plan_tier="hobbyist", minutes=limit - 2)

    snapshot = service.record_estimate(
        user_id="user-projected-stop",
        plan_tier="hobbyist",
        estimated_minutes=5,
    )

    assert snapshot.hard_stop is True


def test_single_job_overage_budget_clears_projected_hard_stop() -> None:
    service = BillingService()
    limit = monthly_limit_for_tier("hobbyist")
    service.consume_minutes(user_id="user-approved-stop", plan_tier="hobbyist", minutes=limit - 2)
    service.record_estimate(user_id="user-approved-stop", plan_tier="hobbyist", estimated_minutes=5)

    snapshot = service.approve_overage(
        user_id="user-approved-stop",
        plan_tier="hobbyist",
        approval_scope="single_job",
        requested_minutes=5,
    )

    assert snapshot.hard_stop is False
    assert snapshot.remaining_approved_overage_minutes == 5
