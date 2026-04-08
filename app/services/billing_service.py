"""Cost-control helpers for NFR-007."""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.billing.pricebook import (
    CommercialPricebookConfigurationError,
    CommercialPricebookEntry,
    cached_commercial_pricebook,
    resolve_pricebook_entry,
)
from app.billing.stripe_client import BillingPricingMetadata
from app.config import settings
from app.db.phase2_store import UsageRepository

APPROVAL_SCOPE_SINGLE_JOB = "single_job"
APPROVAL_SCOPE_MONTH = "month"
APPROVAL_SCOPE_UPGRADE_TIER = "upgrade_tier"
APPROVAL_SCOPES = {
    APPROVAL_SCOPE_SINGLE_JOB,
    APPROVAL_SCOPE_MONTH,
    APPROVAL_SCOPE_UPGRADE_TIER,
}


@dataclass(frozen=True)
class BillingSnapshot:
    user_id: str
    plan_tier: str
    used_minutes: int
    monthly_limit_minutes: int
    estimated_next_job_minutes: int
    threshold_alerts: list[int]
    overage_approval_scope: str | None
    approved_for_minutes: int
    reconciliation_source: str
    reconciliation_status: str

    @property
    def remaining_minutes(self) -> int:
        return max(self.monthly_limit_minutes - self.used_minutes, 0)

    @property
    def remaining_approved_overage_minutes(self) -> int:
        overage_consumed = max(self.used_minutes - self.monthly_limit_minutes, 0)
        return max(self.approved_for_minutes - overage_consumed, 0)

    @property
    def effective_limit_minutes(self) -> int:
        return self.monthly_limit_minutes + self.approved_for_minutes

    @property
    def hard_stop(self) -> bool:
        projected_usage = self.used_minutes + max(self.estimated_next_job_minutes, 0)
        return self.used_minutes >= self.effective_limit_minutes or projected_usage > self.effective_limit_minutes


@dataclass(frozen=True)
class EffectivePricingSnapshot:
    pricebook_version: str
    subscription_price_id: str
    subscription_price_usd: float
    included_minutes_monthly: int
    overage_enabled: bool
    overage_price_id: str
    overage_rate_usd_per_minute: float
    entitlement_source: str = "commercial_pricebook"


class CommercialPricingUnavailableError(RuntimeError):
    """Raised when pricebook-backed pricing or entitlements cannot be resolved."""


def _recurring_price_ids_by_tier() -> dict[str, str]:
    return {
        "hobbyist": settings.stripe_hobbyist_price_id.strip(),
        "pro": settings.stripe_pro_price_id.strip(),
        "museum": settings.stripe_museum_price_id.strip(),
    }


def _commercial_pricebook_entry(plan_tier: str) -> tuple[str, CommercialPricebookEntry]:
    try:
        pricebook = cached_commercial_pricebook(
            settings.commercial_pricebook_json,
            settings.stripe_hobbyist_price_id,
            settings.stripe_pro_price_id,
            settings.stripe_museum_price_id,
        )
        entry = resolve_pricebook_entry(
            pricebook=pricebook,
            recurring_price_ids_by_tier=_recurring_price_ids_by_tier(),
            plan_tier=plan_tier,
        )
    except CommercialPricebookConfigurationError as exc:
        raise CommercialPricingUnavailableError(
            "Billing pricing is temporarily unavailable because the commercial pricebook configuration is invalid."
        ) from exc
    return pricebook.version, entry


def monthly_limit_for_tier(plan_tier: str) -> int:
    _, entry = _commercial_pricebook_entry(plan_tier)
    return entry.included_minutes_monthly


def allowed_fidelity_tiers_for_plan(plan_tier: str) -> tuple[str, ...]:
    _, entry = _commercial_pricebook_entry(plan_tier)
    return entry.entitlements.fidelity_tiers


def resolution_cap_for_plan(plan_tier: str) -> str:
    _, entry = _commercial_pricebook_entry(plan_tier)
    return entry.entitlements.resolution_cap


def max_retention_days_for_plan(plan_tier: str) -> int:
    _, entry = _commercial_pricebook_entry(plan_tier)
    return entry.entitlements.export_retention_days


def effective_pricing_for_plan(
    plan_tier: str,
    *,
    pricing_metadata: BillingPricingMetadata | None = None,
) -> EffectivePricingSnapshot:
    version, entry = _commercial_pricebook_entry(plan_tier)
    subscription_price_usd = (
        pricing_metadata.subscription_price_usd_for_tier(plan_tier)
        if pricing_metadata is not None
        else 0.0
    )
    return EffectivePricingSnapshot(
        pricebook_version=version,
        subscription_price_id=entry.subscription_price_id,
        subscription_price_usd=subscription_price_usd,
        included_minutes_monthly=entry.included_minutes_monthly,
        overage_enabled=entry.overage.enabled,
        overage_price_id=entry.overage.price_id,
        overage_rate_usd_per_minute=entry.overage.rate_usd_per_minute,
    )


def billable_minutes_for_duration(duration_seconds: int, mode: str) -> int:
    base_minutes = math.ceil(max(duration_seconds, 0) / 60)
    multiplier = {"Enhance": 1.0, "Restore": 1.5, "Conserve": 2.0}.get(mode, 1.0)
    return max(math.ceil(base_minutes * multiplier), 0)


def _threshold_alerts(used_minutes: int, monthly_limit_minutes: int) -> list[int]:
    if monthly_limit_minutes <= 0:
        return []
    usage_pct = (used_minutes / monthly_limit_minutes) * 100
    return [threshold for threshold in (80, 90, 100) if usage_pct >= threshold]


def _normalize_approval_scope(approval_scope: str) -> str:
    normalized = approval_scope.strip().lower()
    if normalized not in APPROVAL_SCOPES:
        raise ValueError("approval_scope must be one of: single_job, month, upgrade_tier")
    return normalized


def _reconciliation_status(used_minutes: int, estimated_next_job_minutes: int) -> str:
    if estimated_next_job_minutes > 0:
        return "estimate_pending"
    if used_minutes > 0:
        return "usage_reconciled"
    return "not_started"


class BillingService:
    def __init__(self) -> None:
        self._usage_repo = UsageRepository()

    def _snapshot_from_usage(self, usage: dict[str, object]) -> BillingSnapshot:
        return BillingSnapshot(
            user_id=str(usage["user_id"]),
            plan_tier=str(usage["plan_tier"]),
            used_minutes=int(usage["used_minutes"]),
            monthly_limit_minutes=int(usage["monthly_limit_minutes"]),
            estimated_next_job_minutes=int(usage.get("estimated_next_job_minutes", 0) or 0),
            threshold_alerts=[int(value) for value in usage.get("threshold_alerts", []) or []],
            overage_approval_scope=(
                str(usage["overage_approval_scope"]) if usage.get("overage_approval_scope") else None
            ),
            approved_for_minutes=int(usage.get("approved_for_minutes", 0) or 0),
            reconciliation_source="user_usage_monthly",
            reconciliation_status=_reconciliation_status(
                int(usage["used_minutes"]),
                int(usage.get("estimated_next_job_minutes", 0) or 0),
            ),
        )

    def snapshot(self, *, user_id: str, plan_tier: str, access_token: str | None = None) -> BillingSnapshot:
        usage = self._usage_repo.get_or_create(
            user_id=user_id,
            plan_tier=plan_tier,
            monthly_limit_minutes=monthly_limit_for_tier(plan_tier),
            access_token=access_token,
        )
        return self._snapshot_from_usage(usage)

    def record_estimate(
        self,
        *,
        user_id: str,
        plan_tier: str,
        estimated_minutes: int,
        access_token: str | None = None,
    ) -> BillingSnapshot:
        usage = self._usage_repo.get_or_create(
            user_id=user_id,
            plan_tier=plan_tier,
            monthly_limit_minutes=monthly_limit_for_tier(plan_tier),
            access_token=access_token,
        )
        updated = self._usage_repo.update(
            user_id,
            {
                "estimated_next_job_minutes": estimated_minutes,
                "threshold_alerts": _threshold_alerts(usage["used_minutes"], usage["monthly_limit_minutes"]),
            },
            access_token=access_token,
        )
        return self._snapshot_from_usage(updated)

    def consume_minutes(
        self,
        *,
        user_id: str,
        plan_tier: str,
        minutes: int,
        access_token: str | None = None,
    ) -> BillingSnapshot:
        usage = self._usage_repo.get_or_create(
            user_id=user_id,
            plan_tier=plan_tier,
            monthly_limit_minutes=monthly_limit_for_tier(plan_tier),
            access_token=access_token,
        )
        used_minutes = usage["used_minutes"] + max(minutes, 0)
        approval_scope = usage.get("overage_approval_scope")
        approved_for_minutes = int(usage.get("approved_for_minutes", 0) or 0)
        overage_consumed = max(used_minutes - usage["monthly_limit_minutes"], 0)
        if approval_scope == APPROVAL_SCOPE_SINGLE_JOB and overage_consumed >= approved_for_minutes:
            approval_scope = None
        updated = self._usage_repo.update(
            user_id,
            {
                "used_minutes": used_minutes,
                "estimated_next_job_minutes": 0,
                "overage_approval_scope": approval_scope,
                "threshold_alerts": _threshold_alerts(used_minutes, usage["monthly_limit_minutes"]),
            },
            access_token=access_token,
        )
        return self._snapshot_from_usage(updated)

    def approve_overage(
        self,
        *,
        user_id: str,
        plan_tier: str,
        approval_scope: str,
        requested_minutes: int,
        access_token: str | None = None,
    ) -> BillingSnapshot:
        usage = self._usage_repo.get_or_create(
            user_id=user_id,
            plan_tier=plan_tier,
            monthly_limit_minutes=monthly_limit_for_tier(plan_tier),
            access_token=access_token,
        )
        normalized_scope = _normalize_approval_scope(approval_scope)
        approved_minutes = max(requested_minutes, 0)
        if normalized_scope != APPROVAL_SCOPE_UPGRADE_TIER and approved_minutes <= 0:
            approved_minutes = int(usage.get("estimated_next_job_minutes", 0) or 0)
        if normalized_scope != APPROVAL_SCOPE_UPGRADE_TIER and approved_minutes <= 0:
            raise ValueError("requested_minutes must be positive when approval_scope is single_job or month")
        updated = self._usage_repo.update(
            user_id,
            {
                "overage_approval_scope": normalized_scope,
                "approved_for_minutes": 0 if normalized_scope == APPROVAL_SCOPE_UPGRADE_TIER else approved_minutes,
                "threshold_alerts": _threshold_alerts(usage["used_minutes"], usage["monthly_limit_minutes"]),
            },
            access_token=access_token,
        )
        return self._snapshot_from_usage(updated)
