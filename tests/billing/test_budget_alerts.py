"""Maps to: NFR-007"""

from app.services.billing_service import BillingService, monthly_limit_for_tier


def test_budget_threshold_alerts_trigger_at_80_90_100() -> None:
    service = BillingService()
    limit = monthly_limit_for_tier("pro")

    snapshot = service.consume_minutes(user_id="user-budget", plan_tier="pro", minutes=int(limit * 0.8))
    assert snapshot.threshold_alerts == [80]

    snapshot = service.consume_minutes(user_id="user-budget", plan_tier="pro", minutes=int(limit * 0.1))
    assert snapshot.threshold_alerts == [80, 90]

    snapshot = service.consume_minutes(user_id="user-budget", plan_tier="pro", minutes=limit - snapshot.used_minutes)
    assert snapshot.threshold_alerts == [80, 90, 100]


def test_reconciliation_status_switches_to_usage_reconciled_after_consumption() -> None:
    service = BillingService()

    service.record_estimate(user_id="user-reconciled", plan_tier="pro", estimated_minutes=9)
    snapshot = service.consume_minutes(user_id="user-reconciled", plan_tier="pro", minutes=9)

    assert snapshot.reconciliation_status == "usage_reconciled"
