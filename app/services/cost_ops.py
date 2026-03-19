"""Packet 4H admin cost operations snapshot service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.billing.stripe_client import BillingPricingMetadata, resolve_billing_pricing_metadata
from app.db.phase2_store import JobRepository
from app.observability.monitoring import (
    record_cost_anomaly,
    record_cost_margin_breach,
    record_cost_ops_snapshot,
)
from app.services.billing_service import monthly_limit_for_tier
from app.services.cost_estimation import (
    API_CALL_COST_USD,
    BillingPricingUnavailableError,
    ESTIMATE_OUTLIER_THRESHOLD_PERCENT,
    ESTIMATOR_VERSION,
    GPU_COST_PER_SECOND_USD,
    STORAGE_OPERATION_COST_USD,
)
from app.services.runtime_ops import (
    autoscaler_idle_scale_down_healthy,
    current_runtime_snapshot,
    emit_incident,
    incident_history,
)

SUMMARY_WINDOW_DAYS = 30
QUARTERLY_WINDOW_DAYS = 90
GROSS_MARGIN_TARGET_PERCENT = 60.0


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _isoformat(value: datetime) -> str:
    return value.isoformat()


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _job_terminal_timestamp(job: dict[str, Any]) -> datetime | None:
    reconciliation_summary = job.get("cost_reconciliation_summary") or {}
    for candidate in (
        reconciliation_summary.get("reconciled_at"),
        job.get("completed_at"),
    ):
        parsed = _parse_timestamp(str(candidate or ""))
        if parsed is not None:
            return parsed
    return None


def _operational_cost_breakdown(job: dict[str, Any]) -> dict[str, float]:
    cost_summary = job.get("cost_summary") or {}
    gpu = round(float(cost_summary.get("gpu_seconds", 0) or 0) * GPU_COST_PER_SECOND_USD, 4)
    storage = round(float(cost_summary.get("storage_operations", 0) or 0) * STORAGE_OPERATION_COST_USD, 4)
    api = round(float(cost_summary.get("api_calls", 0) or 0) * API_CALL_COST_USD, 4)
    return {"gpu": gpu, "storage": storage, "api": api}


def _job_overage_rate_usd_per_minute(job: dict[str, Any], *, pricing_metadata: BillingPricingMetadata) -> float:
    billing_breakdown = (job.get("cost_estimate_summary") or {}).get("billing_breakdown_usd") or {}
    stored_rate = float(billing_breakdown.get("overage_rate_usd_per_minute", 0.0) or 0.0)
    return stored_rate if stored_rate > 0 else pricing_metadata.overage_rate_usd_per_minute


def _included_minutes(job: dict[str, Any], reconciliation_summary: dict[str, Any], *, pricing_metadata: BillingPricingMetadata) -> int:
    actual_usage_minutes = int(reconciliation_summary.get("actual_usage_minutes", 0) or 0)
    actual_charge_total_usd = float(reconciliation_summary.get("actual_charge_total_usd", 0.0) or 0.0)
    overage_rate = _job_overage_rate_usd_per_minute(job, pricing_metadata=pricing_metadata)
    actual_overage_minutes = 0
    if overage_rate > 0 and actual_charge_total_usd > 0:
        actual_overage_minutes = int(round(actual_charge_total_usd / overage_rate))
    actual_overage_minutes = max(min(actual_overage_minutes, actual_usage_minutes), 0)
    return max(actual_usage_minutes - actual_overage_minutes, 0)


def _job_financials(
    job: dict[str, Any],
    *,
    pricing_metadata: BillingPricingMetadata,
) -> dict[str, float]:
    reconciliation_summary = job.get("cost_reconciliation_summary") or {}
    actual_cost_total_usd = round(float(reconciliation_summary.get("actual_total_cost_usd", 0.0) or 0.0), 4)
    actual_charge_total_usd = round(float(reconciliation_summary.get("actual_charge_total_usd", 0.0) or 0.0), 4)
    plan_tier = str(job.get("plan_tier", "hobbyist"))
    monthly_limit = max(monthly_limit_for_tier(plan_tier), 1)
    included_minutes = _included_minutes(
        job,
        reconciliation_summary,
        pricing_metadata=pricing_metadata,
    )
    subscription_price_usd = pricing_metadata.subscription_price_usd_for_tier(plan_tier)
    included_revenue_usd = round((subscription_price_usd / monthly_limit) * included_minutes, 4)
    revenue_total_usd = round(included_revenue_usd + actual_charge_total_usd, 4)
    gross_margin_percent = (
        round(((revenue_total_usd - actual_cost_total_usd) / revenue_total_usd) * 100, 2)
        if revenue_total_usd > 0
        else (-100.0 if actual_cost_total_usd > 0 else 0.0)
    )
    return {
        "actual_cost_total_usd": actual_cost_total_usd,
        "actual_charge_total_usd": actual_charge_total_usd,
        "revenue_total_usd": revenue_total_usd,
        "gross_margin_percent": gross_margin_percent,
    }


def _cache_hit_rate_percent(jobs: list[dict[str, Any]]) -> float:
    hits = misses = bypassed = 0
    for job in jobs:
        summary = job.get("cache_summary") or {}
        hits += int(summary.get("hits", 0) or 0)
        misses += int(summary.get("misses", 0) or 0)
        bypassed += int(summary.get("bypassed", 0) or 0)
    total = hits + misses + bypassed
    if total <= 0:
        runtime_hit_rate = [float((job.get("cache_summary") or {}).get("hit_rate", 0.0) or 0.0) for job in jobs]
        return round(sum(runtime_hit_rate) / len(runtime_hit_rate), 2) if runtime_hit_rate else 0.0
    return round((hits / total) * 100, 2)


def _gpu_utilization_percent(jobs: list[dict[str, Any]], runtime_snapshot: dict[str, Any]) -> float:
    samples = [
        float((job.get("gpu_summary") or {}).get("utilization_percent", 0.0) or 0.0)
        for job in jobs
        if (job.get("gpu_summary") or {}).get("utilization_percent") is not None
    ]
    positive_samples = [sample for sample in samples if sample > 0]
    if positive_samples:
        return round(sum(positive_samples) / len(positive_samples), 2)
    return round(float(runtime_snapshot.get("utilization_percent", 0.0) or 0.0), 2)


def _anomaly_types(
    job: dict[str, Any],
    *,
    gross_margin_percent: float,
) -> list[str]:
    reconciliation_summary = job.get("cost_reconciliation_summary") or {}
    anomaly_types: list[str] = []
    delta_usd = float(reconciliation_summary.get("delta_usd", 0.0) or 0.0)
    delta_percent = float(reconciliation_summary.get("delta_percent", 0.0) or 0.0)
    # Packet 4H only promotes positive cost overruns, not under-runs, to anomalies.
    if delta_usd > 0 and delta_percent > ESTIMATE_OUTLIER_THRESHOLD_PERCENT:
        anomaly_types.append("cost_delta")
    if gross_margin_percent < GROSS_MARGIN_TARGET_PERCENT:
        anomaly_types.append("gross_margin")
    return anomaly_types


def _emit_anomaly_incidents(anomalies: list[dict[str, Any]]) -> None:
    existing_keys = {str(item.get("incident_key")) for item in incident_history()}
    for anomaly in anomalies:
        job_id = anomaly["job_id"]
        if "cost_delta" in anomaly["anomaly_types"]:
            source_signal = f"cost-anomaly-{job_id}"
            incident_key = f"P2:{source_signal}"
            if incident_key not in existing_keys:
                emit_incident(
                    severity="P2",
                    source_signal=source_signal,
                    summary="Job cost exceeded the launch-time estimate by more than 20 percent.",
                    metadata={
                        "job_id": job_id,
                        "delta_percent": anomaly["delta_percent"],
                        "actual_cost_total_usd": anomaly["actual_cost_total_usd"],
                        "actual_charge_total_usd": anomaly["actual_charge_total_usd"],
                    },
                )
                record_cost_anomaly(category="cost_delta")
                existing_keys.add(incident_key)
        if "gross_margin" in anomaly["anomaly_types"]:
            source_signal = f"gross-margin-breach-{job_id}"
            incident_key = f"P2:{source_signal}"
            if incident_key not in existing_keys:
                emit_incident(
                    severity="P2",
                    source_signal=source_signal,
                    summary="Job gross margin fell below the 60 percent target.",
                    metadata={
                        "job_id": job_id,
                        "gross_margin_percent": anomaly["gross_margin_percent"],
                        "actual_cost_total_usd": anomaly["actual_cost_total_usd"],
                        "actual_charge_total_usd": anomaly["actual_charge_total_usd"],
                    },
                )
                record_cost_anomaly(category="gross_margin")
                record_cost_margin_breach(estimator_version=ESTIMATOR_VERSION)
                existing_keys.add(incident_key)


def _recommendations(
    *,
    gpu_utilization_percent: float,
    cache_hit_rate_percent: float,
    anomaly_count: int,
    gross_margin_percent: float,
) -> list[dict[str, Any]]:
    def recommendation(
        *,
        category: str,
        threshold_met: bool,
        metric_value: float | int,
        threshold_value: float,
        success_summary: str,
        action_summary: str,
        priority: str,
    ) -> dict[str, Any]:
        return {
            "category": category,
            "priority": "none" if threshold_met else priority,
            "action_required": not threshold_met,
            "summary": success_summary if threshold_met else action_summary,
            "evidence": {
                "metric_value": round(float(metric_value), 2),
                "threshold_value": round(float(threshold_value), 2),
            },
        }

    return [
        recommendation(
            category="cache_efficiency",
            threshold_met=cache_hit_rate_percent >= 40.0,
            metric_value=cache_hit_rate_percent,
            threshold_value=40.0,
            success_summary="Cache hit rate is meeting the Packet 4 target.",
            action_summary="Cache hit rate is below target; prioritize cache-key tuning and hot-path reuse.",
            priority="medium",
        ),
        recommendation(
            category="gpu_utilization",
            threshold_met=gpu_utilization_percent >= 70.0,
            metric_value=gpu_utilization_percent,
            threshold_value=70.0,
            success_summary="GPU utilization is meeting the Packet 4 target.",
            action_summary="GPU utilization is below target; rebalance warm-pool sizing and dispatch throughput.",
            priority="medium",
        ),
        recommendation(
            category="cost_anomaly_remediation",
            threshold_met=anomaly_count == 0,
            metric_value=anomaly_count,
            threshold_value=0.0,
            success_summary="No recent cost anomalies require remediation.",
            action_summary="Recent cost anomalies require review and remediation against launch-time estimates.",
            priority="high",
        ),
        recommendation(
            category="gross_margin_protection",
            threshold_met=gross_margin_percent >= GROSS_MARGIN_TARGET_PERCENT,
            metric_value=gross_margin_percent,
            threshold_value=GROSS_MARGIN_TARGET_PERCENT,
            success_summary="Gross margin is above the Packet 4 target.",
            action_summary="Gross margin is below target; review pricing, cache efficiency, and GPU utilization.",
            priority="high",
        ),
    ]


def _windowed_jobs(quarterly_start: datetime) -> list[dict[str, Any]]:
    jobs = JobRepository().list_cost_ops_jobs_since(earliest_timestamp=quarterly_start)
    completed_jobs: list[dict[str, Any]] = []
    for job in jobs:
        timestamp = _job_terminal_timestamp(job)
        if timestamp is None:
            continue
        completed_jobs.append({**job, "_terminal_timestamp": timestamp})
    return completed_jobs


def _evaluate_cost_ops_snapshot(
    *,
    pricing_metadata: BillingPricingMetadata,
) -> dict[str, Any]:
    now = _utc_now()
    summary_start = now - timedelta(days=SUMMARY_WINDOW_DAYS)
    quarterly_start = now - timedelta(days=QUARTERLY_WINDOW_DAYS)
    completed_jobs = _windowed_jobs(quarterly_start)
    summary_jobs = [job for job in completed_jobs if job["_terminal_timestamp"] >= summary_start]
    runtime_snapshot = current_runtime_snapshot()

    cost_totals = {"gpu": 0.0, "storage": 0.0, "api": 0.0, "actual_charge_total": 0.0}
    revenue_total_usd = 0.0
    cost_total_usd = 0.0
    anomalies: list[dict[str, Any]] = []
    for job in summary_jobs:
        breakdown = _operational_cost_breakdown(job)
        for key in ("gpu", "storage", "api"):
            cost_totals[key] = round(cost_totals[key] + breakdown[key], 4)
        financials = _job_financials(job, pricing_metadata=pricing_metadata)
        revenue_total_usd = round(revenue_total_usd + financials["revenue_total_usd"], 4)
        cost_total_usd = round(cost_total_usd + financials["actual_cost_total_usd"], 4)
        cost_totals["actual_charge_total"] = round(
            cost_totals["actual_charge_total"] + financials["actual_charge_total_usd"],
            4,
        )
        anomaly_types = _anomaly_types(job, gross_margin_percent=financials["gross_margin_percent"])
        if anomaly_types:
            anomalies.append(
                {
                    "job_id": str(job["job_id"]),
                    "detected_at": _isoformat(job["_terminal_timestamp"]),
                    "anomaly_types": anomaly_types,
                    "delta_percent": round(
                        float((job.get("cost_reconciliation_summary") or {}).get("delta_percent", 0.0) or 0.0),
                        2,
                    ),
                    "gross_margin_percent": financials["gross_margin_percent"],
                    "actual_cost_total_usd": financials["actual_cost_total_usd"],
                    "actual_charge_total_usd": financials["actual_charge_total_usd"],
                }
            )

    anomalies = sorted(anomalies, key=lambda item: item["detected_at"], reverse=True)
    gross_margin_percent = (
        round(((revenue_total_usd - cost_total_usd) / revenue_total_usd) * 100, 2)
        if revenue_total_usd > 0
        else (-100.0 if cost_total_usd > 0 else 0.0)
    )
    operational_efficiency = {
        "gpu_utilization_percent": _gpu_utilization_percent(summary_jobs, runtime_snapshot),
        "cache_hit_rate_percent": _cache_hit_rate_percent(summary_jobs),
        "autoscaler_idle_scale_down_healthy": autoscaler_idle_scale_down_healthy(runtime_snapshot),
    }
    return {
        "generated_at": _isoformat(now),
        "summary_window_start": _isoformat(summary_start),
        "summary_window_end": _isoformat(now),
        "quarterly_window_start": _isoformat(quarterly_start),
        "quarterly_window_end": _isoformat(now),
        "cost_totals_usd": cost_totals,
        "gross_margin_summary": {
            "revenue_total_usd": revenue_total_usd,
            "cost_total_usd": cost_total_usd,
            "gross_margin_percent": gross_margin_percent,
            "target_margin_percent": GROSS_MARGIN_TARGET_PERCENT,
            "below_target": gross_margin_percent < GROSS_MARGIN_TARGET_PERCENT,
        },
        "operational_efficiency": operational_efficiency,
        "recent_anomalies": anomalies[:10],
        "recommendations": _recommendations(
            gpu_utilization_percent=operational_efficiency["gpu_utilization_percent"],
            cache_hit_rate_percent=operational_efficiency["cache_hit_rate_percent"],
            anomaly_count=len(anomalies),
            gross_margin_percent=gross_margin_percent,
        ),
        "_all_anomalies": anomalies,
    }


def _build_cost_ops_snapshot(
    *,
    pricing_metadata: BillingPricingMetadata,
    emit_signals: bool,
) -> dict[str, Any]:
    snapshot = _evaluate_cost_ops_snapshot(pricing_metadata=pricing_metadata)
    if emit_signals:
        _emit_anomaly_incidents(snapshot["_all_anomalies"])
        record_cost_ops_snapshot(
            gpu_utilization_percent=snapshot["operational_efficiency"]["gpu_utilization_percent"],
            cache_hit_rate_percent=snapshot["operational_efficiency"]["cache_hit_rate_percent"],
            gross_margin_percent=snapshot["gross_margin_summary"]["gross_margin_percent"],
            anomaly_count=len(snapshot["_all_anomalies"]),
        )
    return {key: value for key, value in snapshot.items() if not key.startswith("_")}


def _resolve_pricing_metadata() -> BillingPricingMetadata:
    try:
        return resolve_billing_pricing_metadata()
    except Exception as exc:
        raise BillingPricingUnavailableError(
            "Pricing data is temporarily unavailable. Retry the request once billing metadata is available."
        ) from exc


def refresh_cost_ops_signals() -> dict[str, Any]:
    return _build_cost_ops_snapshot(
        pricing_metadata=_resolve_pricing_metadata(),
        emit_signals=True,
    )


def current_cost_ops_snapshot() -> dict[str, Any]:
    return _build_cost_ops_snapshot(
        pricing_metadata=_resolve_pricing_metadata(),
        emit_signals=False,
    )
