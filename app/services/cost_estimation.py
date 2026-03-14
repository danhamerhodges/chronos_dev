"""Packet 4E cost estimation and reconciliation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import ceil
from typing import Any

from app.billing.stripe_client import billing_price_references, resolve_billing_pricing_metadata
from app.services.billing_service import BillingService, BillingSnapshot, billable_minutes_for_duration
from app.observability.monitoring import record_cost_reconciliation

ESTIMATOR_VERSION = "packet4e-v1"
ESTIMATE_OUTLIER_THRESHOLD_PERCENT = 20.0
SEGMENT_DURATION_SECONDS = 10
GPU_COST_PER_SECOND_USD = 0.012
STORAGE_OPERATION_COST_USD = 0.001
API_CALL_COST_USD = 0.0
CONFIDENCE_INTERVAL_BY_TIER = {
    "Enhance": 0.10,
    "Restore": 0.12,
    "Conserve": 0.15,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def calculate_operational_cost_summary(
    *,
    gpu_seconds: int,
    storage_operations: int,
    api_calls: int,
) -> dict[str, float | int]:
    gpu_time = round(max(gpu_seconds, 0) * GPU_COST_PER_SECOND_USD, 4)
    storage = round(max(storage_operations, 0) * STORAGE_OPERATION_COST_USD, 4)
    api_call_cost = round(max(api_calls, 0) * API_CALL_COST_USD, 4)
    return {
        "gpu_seconds": max(int(gpu_seconds), 0),
        "storage_operations": max(int(storage_operations), 0),
        "api_calls": max(int(api_calls), 0),
        "total_cost_usd": round(gpu_time + storage + api_call_cost, 4),
    }


def _operational_breakdown(
    *,
    gpu_seconds: int,
    storage_operations: int,
    api_calls: int,
) -> dict[str, float]:
    summary = calculate_operational_cost_summary(
        gpu_seconds=gpu_seconds,
        storage_operations=storage_operations,
        api_calls=api_calls,
    )
    gpu_time = round(summary["gpu_seconds"] * GPU_COST_PER_SECOND_USD, 4)
    storage = round(summary["storage_operations"] * STORAGE_OPERATION_COST_USD, 4)
    api_call_cost = round(summary["api_calls"] * API_CALL_COST_USD, 4)
    return {
        "gpu_time": gpu_time,
        "storage": storage,
        "api_calls": api_call_cost,
        "total": round(gpu_time + storage + api_call_cost, 4),
    }


def _build_usage_snapshot(snapshot: BillingSnapshot) -> dict[str, Any]:
    price_refs = billing_price_references()
    return {
        "user_id": snapshot.user_id,
        "plan_tier": snapshot.plan_tier,
        "used_minutes": snapshot.used_minutes,
        "monthly_limit_minutes": snapshot.monthly_limit_minutes,
        "remaining_minutes": snapshot.remaining_minutes,
        "estimated_next_job_minutes": snapshot.estimated_next_job_minutes,
        "approved_overage_minutes": snapshot.approved_for_minutes,
        "remaining_approved_overage_minutes": snapshot.remaining_approved_overage_minutes,
        "threshold_alerts": snapshot.threshold_alerts,
        "overage_approval_scope": snapshot.overage_approval_scope,
        "hard_stop": snapshot.hard_stop,
        "price_reference": price_refs["subscription_price_id"],
        "overage_price_reference": price_refs["overage_price_id"],
        "reconciliation_source": snapshot.reconciliation_source,
        "reconciliation_status": snapshot.reconciliation_status,
    }


def _confidence_interval(total_cost: float, *, fidelity_tier: str) -> dict[str, float]:
    multiplier = CONFIDENCE_INTERVAL_BY_TIER.get(fidelity_tier, 0.12)
    low = max(total_cost * (1 - multiplier), 0.0)
    high = total_cost * (1 + multiplier)
    return {
        "low": round(low, 4),
        "high": round(high, 4),
    }


@dataclass(frozen=True)
class CostEstimateResult:
    summary: dict[str, Any]
    usage_snapshot: BillingSnapshot


class BillingPricingUnavailableError(RuntimeError):
    """Raised when billing pricing metadata cannot be resolved for estimate/launch requests."""


class CostEstimationService:
    def __init__(self) -> None:
        self._billing = BillingService()

    def estimate_launch(
        self,
        *,
        user_id: str,
        plan_tier: str,
        payload: dict[str, Any],
        access_token: str | None = None,
    ) -> CostEstimateResult:
        estimated_duration_seconds = int(payload["estimated_duration_seconds"])
        fidelity_tier = str(payload["fidelity_tier"])
        estimated_usage_minutes = billable_minutes_for_duration(estimated_duration_seconds, fidelity_tier)
        usage_snapshot = self._billing.record_estimate(
            user_id=user_id,
            plan_tier=plan_tier,
            estimated_minutes=estimated_usage_minutes,
            access_token=access_token,
        )
        segment_count = max(ceil(max(estimated_duration_seconds, 1) / SEGMENT_DURATION_SECONDS), 1)
        operational_breakdown = _operational_breakdown(
            gpu_seconds=estimated_duration_seconds,
            storage_operations=segment_count + 1,
            api_calls=segment_count,
        )
        try:
            pricing_metadata = resolve_billing_pricing_metadata()
        except Exception as exc:
            raise BillingPricingUnavailableError(
                "Pricing data is temporarily unavailable. Retry the request once billing metadata is available."
            ) from exc
        included_usage = min(estimated_usage_minutes, max(usage_snapshot.monthly_limit_minutes - usage_snapshot.used_minutes, 0))
        overage_minutes = max(estimated_usage_minutes - included_usage, 0)
        charge_total = round(overage_minutes * pricing_metadata.overage_rate_usd_per_minute, 4)
        summary = {
            "estimated_usage_minutes": estimated_usage_minutes,
            "operational_cost_breakdown_usd": operational_breakdown,
            "billing_breakdown_usd": {
                "included_usage": included_usage,
                "overage_minutes": overage_minutes,
                "overage_rate_usd_per_minute": pricing_metadata.overage_rate_usd_per_minute,
                "estimated_charge_total_usd": charge_total,
            },
            "confidence_interval_usd": _confidence_interval(
                operational_breakdown["total"],
                fidelity_tier=fidelity_tier,
            ),
            "usage_snapshot": _build_usage_snapshot(usage_snapshot),
            "launch_blocker": "overage_approval_required" if usage_snapshot.hard_stop else "none",
            "estimator_version": ESTIMATOR_VERSION,
            "generated_at": _utc_now(),
        }
        return CostEstimateResult(summary=summary, usage_snapshot=usage_snapshot)

    def reconcile_estimate(
        self,
        *,
        estimate_summary: dict[str, Any] | None,
        actual_cost_summary: dict[str, Any] | None,
        actual_usage_minutes: int,
        reconciled_at: str,
        usage_before_job_minutes: int | None = None,
        post_billing_snapshot: BillingSnapshot | None = None,
    ) -> dict[str, Any] | None:
        if not estimate_summary:
            return None
        billing_breakdown = estimate_summary.get("billing_breakdown_usd") or {}
        usage_snapshot = estimate_summary.get("usage_snapshot") or {}
        estimated_total = float((estimate_summary.get("operational_cost_breakdown_usd") or {}).get("total", 0.0) or 0.0)
        actual_total = float((actual_cost_summary or {}).get("total_cost_usd", 0.0) or 0.0)
        delta_usd = round(actual_total - estimated_total, 4)
        delta_percent = (
            round((abs(delta_usd) / max(actual_total, 0.0001)) * 100, 2)
            if actual_total > 0
            else (0.0 if estimated_total == 0 else 100.0)
        )
        if post_billing_snapshot is not None and usage_before_job_minutes is not None:
            remaining_included = max(post_billing_snapshot.monthly_limit_minutes - max(usage_before_job_minutes, 0), 0)
        else:
            remaining_included = max(
                int(usage_snapshot.get("monthly_limit_minutes", 0) or 0) - int(usage_snapshot.get("used_minutes", 0) or 0),
                0,
            )
        actual_included_usage = min(actual_usage_minutes, remaining_included)
        actual_overage_minutes = max(actual_usage_minutes - actual_included_usage, 0)
        overage_rate = float(billing_breakdown.get("overage_rate_usd_per_minute", 0.0) or 0.0)
        summary = {
            "estimated_total_cost_usd": estimated_total,
            "actual_total_cost_usd": actual_total,
            "delta_usd": delta_usd,
            "delta_percent": delta_percent,
            "estimated_charge_total_usd": round(float(billing_breakdown.get("estimated_charge_total_usd", 0.0) or 0.0), 4),
            "actual_charge_total_usd": round(actual_overage_minutes * overage_rate, 4),
            "actual_usage_minutes": max(actual_usage_minutes, 0),
            "outlier_threshold_percent": ESTIMATE_OUTLIER_THRESHOLD_PERCENT,
            "outlier_flagged": delta_percent > ESTIMATE_OUTLIER_THRESHOLD_PERCENT,
            "estimator_version": str(estimate_summary.get("estimator_version") or ESTIMATOR_VERSION),
            "reconciled_at": reconciled_at,
        }
        record_cost_reconciliation(
            estimator_version=summary["estimator_version"],
            delta_percent=summary["delta_percent"],
            outlier=summary["outlier_flagged"],
        )
        return summary
