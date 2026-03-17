"""Packet 3C runtime operations control plane."""

from __future__ import annotations

import hashlib
import importlib
import json
from datetime import datetime, timedelta, timezone
from math import ceil
from typing import Any
from uuid import uuid4

import httpx

from app.config import settings
from app.db.phase2_store import RuntimeOpsRepository
from app.observability.monitoring import (
    alert_routes,
    record_alert_delivery,
    record_cache_event,
    record_gpu_allocation,
    record_incident,
    record_runtime_snapshot,
    record_slo_evaluation,
)
from app.services.job_pipeline import build_pipeline_variant_fingerprint

_MEMORY_SEGMENT_CACHE: dict[str, dict[str, Any]] = {}
_SLO_HISTORY: list[dict[str, Any]] = []
_ALERT_HISTORY: list[dict[str, Any]] = []


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def reset_runtime_ops_state() -> None:
    _MEMORY_SEGMENT_CACHE.clear()
    _SLO_HISTORY.clear()
    _ALERT_HISTORY.clear()


def _parse_iso8601(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _lease_metadata(lease: dict[str, Any]) -> dict[str, Any]:
    metadata = lease.get("metadata") or {}
    return metadata if isinstance(metadata, dict) else {}


def _lease_snapshot_float(lease: dict[str, Any], key: str, default: float = 0.0) -> float:
    raw_value = _lease_metadata(lease).get(key, lease.get(key, default))
    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return default


def _lease_snapshot_int(lease: dict[str, Any], key: str, default: int = 0) -> int:
    return int(_lease_snapshot_float(lease, key, float(default)))


def _runtime_snapshot_metadata(
    *,
    lease: dict[str, Any] | None = None,
    queue_age_seconds: float,
    desired_warm_instances: int,
) -> dict[str, Any]:
    metadata = {**(_lease_metadata(lease or {}))}
    metadata.update(
        {
            "mode": settings.gpu_pool_mode,
            "queue_age_seconds": round(queue_age_seconds, 3),
            "desired_warm_instances": desired_warm_instances,
        }
    )
    return metadata


def _lease_payload(
    lease: dict[str, Any],
    *,
    queue_depth_snapshot: int,
    queue_age_seconds: float,
    desired_warm_instances: int,
) -> dict[str, Any]:
    return {
        "gpu_type": lease.get("gpu_type", "L4"),
        "lease_state": lease.get("lease_state", "idle"),
        "is_warm": bool(lease.get("is_warm", True)),
        "current_job_id": lease.get("current_job_id"),
        "queue_depth_snapshot": queue_depth_snapshot,
        "metadata": _runtime_snapshot_metadata(
            lease=lease,
            queue_age_seconds=queue_age_seconds,
            desired_warm_instances=desired_warm_instances,
        ),
        "allocated_at": lease.get("allocated_at"),
        "released_at": lease.get("released_at"),
        "expires_at": lease.get("expires_at"),
    }


def _runnable_backlog_depth(repo: RuntimeOpsRepository) -> int:
    return max(int(repo.queued_job_backlog_count() or 0), 1)


def _segment_cache_backend():
    if settings.segment_cache_mode.lower() != "redis" or not settings.redis_url:
        return None
    try:
        redis = importlib.import_module("redis")
    except ImportError as exc:  # pragma: no cover - dependency gated
        raise RuntimeError("redis package is required when SEGMENT_CACHE_MODE=redis.") from exc
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


def build_segment_cache_key(
    *,
    user_id: str,
    source_asset_checksum: str,
    segment: dict[str, Any],
    effective_fidelity_profile: dict[str, Any],
    reproducibility_mode: str,
    version_namespace: str,
    pipeline_variant: dict[str, str] | None = None,
) -> str:
    payload = {
        "user_id": user_id,
        "source_asset_checksum": source_asset_checksum,
        "segment_index": segment["segment_index"],
        "segment_start_seconds": segment["segment_start_seconds"],
        "segment_end_seconds": segment["segment_end_seconds"],
        "effective_fidelity_profile": effective_fidelity_profile,
        "reproducibility_mode": reproducibility_mode,
        "version_namespace": version_namespace,
    }
    if pipeline_variant:
        payload["pipeline_variant"] = pipeline_variant
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return f"{settings.segment_cache_namespace}:{digest}"


def lookup_segment_cache(
    *,
    job: dict[str, Any],
    segment: dict[str, Any],
    effective_fidelity_profile: dict[str, Any],
    version_namespace: str,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    pipeline_variant = build_pipeline_variant_fingerprint(
        processing_mode=str(job.get("processing_mode", "balanced")),
        config=job.get("config") or {},
        era_profile=job.get("era_profile") or {},
        effective_fidelity_profile=effective_fidelity_profile,
    )
    cache_key = build_segment_cache_key(
        user_id=str(job["owner_user_id"]),
        source_asset_checksum=str(job["source_asset_checksum"]),
        segment=segment,
        effective_fidelity_profile=effective_fidelity_profile,
        reproducibility_mode=str(job["reproducibility_mode"]),
        version_namespace=version_namespace,
        pipeline_variant=pipeline_variant,
    )
    started = datetime.now(timezone.utc)
    backend = _segment_cache_backend()
    try:
        if backend is None:
            record = _MEMORY_SEGMENT_CACHE.get(cache_key)
        else:
            raw = backend.get(cache_key)
            record = json.loads(raw) if raw else None
        latency_ms = max(int((datetime.now(timezone.utc) - started).total_seconds() * 1000), 1)
        if record:
            record_cache_event("hit", latency_ms=latency_ms)
            return record, {
                "cache_status": "hit",
                "cache_hit_latency_ms": latency_ms,
                "cache_namespace": settings.segment_cache_namespace,
                "cached_output_uri": record.get("output_uri"),
                "degraded": False,
            }
        record_cache_event("miss", latency_ms=latency_ms)
        return None, {
            "cache_status": "miss",
            "cache_hit_latency_ms": latency_ms,
            "cache_namespace": settings.segment_cache_namespace,
            "cached_output_uri": None,
            "degraded": False,
        }
    except Exception:
        record_cache_event("degraded")
        return None, {
            "cache_status": "bypass",
            "cache_hit_latency_ms": None,
            "cache_namespace": settings.segment_cache_namespace,
            "cached_output_uri": None,
            "degraded": True,
        }


def store_segment_cache(*, cache_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    backend = _segment_cache_backend()
    try:
        if backend is None:
            _MEMORY_SEGMENT_CACHE[cache_key] = dict(payload)
            return {"cache_status": "stored", "degraded": False}
        backend.setex(cache_key, settings.segment_cache_ttl_seconds, json.dumps(payload, sort_keys=True, default=str))
        return {"cache_status": "stored", "degraded": False}
    except Exception:
        record_cache_event("degraded")
        return {"cache_status": "bypass", "degraded": True}


def _desired_warm_pool(queue_depth: int) -> int:
    min_warm = max(settings.gpu_pool_min_warm_instances, 0)
    threshold = max(settings.gpu_pool_queue_depth_threshold, 1)
    if queue_depth <= threshold:
        return min_warm
    increments = ceil((queue_depth - threshold) / threshold)
    return min_warm + (increments * max(settings.gpu_pool_scale_step, 1))


def reconcile_gpu_pool(*, queue_depth: int, queue_age_seconds: float = 0.0) -> dict[str, Any]:
    repo = RuntimeOpsRepository()
    leases = repo.list_gpu_leases()
    active_warm = [
        lease
        for lease in leases
        if lease.get("lease_state") != "released" and lease.get("is_warm") is True
    ]
    idle_warm = [lease for lease in active_warm if lease.get("lease_state") == "idle"]
    desired = _desired_warm_pool(queue_depth)
    while len(active_warm) < desired:
        worker_id = f"warm-{uuid4().hex[:8]}"
        lease = repo.upsert_gpu_lease(
            worker_id=worker_id,
            payload={
                "gpu_type": "L4",
                "lease_state": "idle",
                "is_warm": True,
                "current_job_id": None,
                "queue_depth_snapshot": queue_depth,
                "metadata": _runtime_snapshot_metadata(
                    queue_age_seconds=queue_age_seconds,
                    desired_warm_instances=desired,
                ),
                "released_at": None,
                "allocated_at": None,
                "expires_at": (
                    datetime.now(timezone.utc) + timedelta(seconds=settings.gpu_pool_idle_timeout_seconds)
                ).isoformat(),
            },
        )
        active_warm.append(lease)
        idle_warm.append(lease)
    if len(active_warm) > desired:
        removable = idle_warm[: max(len(active_warm) - desired, 0)]
        for lease in removable:
            repo.delete_gpu_lease(str(lease["worker_id"]))
        active_warm = [
            lease
            for lease in repo.list_gpu_leases()
            if lease.get("lease_state") != "released" and lease.get("is_warm") is True
        ]
    refreshed_warm: list[dict[str, Any]] = []
    for lease in active_warm:
        refreshed_warm.append(
            repo.upsert_gpu_lease(
                worker_id=str(lease["worker_id"]),
                payload=_lease_payload(
                    lease,
                    queue_depth_snapshot=queue_depth,
                    queue_age_seconds=queue_age_seconds,
                    desired_warm_instances=desired,
                ),
            )
        )
    active_warm = refreshed_warm
    busy_warm = [lease for lease in active_warm if lease.get("lease_state") == "busy"]
    snapshot = {
        "queue_depth": queue_depth,
        "queue_age_seconds": round(queue_age_seconds, 3),
        "desired_warm_instances": desired,
        "active_warm_instances": len(active_warm),
        "busy_instances": len(busy_warm),
        "idle_instances": max(len(active_warm) - len(busy_warm), 0),
    }
    utilization = round((len(busy_warm) / max(len(active_warm), 1)) * 100, 2) if active_warm else 0.0
    snapshot["utilization_percent"] = utilization
    record_runtime_snapshot(snapshot)
    return snapshot


def allocate_gpu(job: dict[str, Any]) -> dict[str, Any]:
    queued_at = _parse_iso8601(str(job.get("queued_at"))) or datetime.now(timezone.utc)
    queue_wait_ms = max(int((datetime.now(timezone.utc) - queued_at).total_seconds() * 1000), 0)
    repo = RuntimeOpsRepository()
    queue_age_seconds = round(queue_wait_ms / 1000, 3)
    queue_depth = _runnable_backlog_depth(repo)
    pool = reconcile_gpu_pool(queue_depth=queue_depth, queue_age_seconds=queue_age_seconds)
    target_gpu = "RTX 6000" if str(job.get("plan_tier", "")).lower() == "museum" else "L4"
    leases = repo.list_gpu_leases()
    selected = next(
        (lease for lease in leases if lease.get("lease_state") == "idle" and lease.get("is_warm") is True),
        None,
    )
    warm_start = selected is not None
    allocation_latency_ms = (
        settings.gpu_warm_allocation_latency_ms if warm_start else settings.gpu_cold_allocation_latency_ms
    )
    worker_id = str(selected["worker_id"]) if selected else f"cold-{uuid4().hex[:8]}"
    try:
        repo.upsert_gpu_lease(
            worker_id=worker_id,
            payload={
                "gpu_type": target_gpu,
                "lease_state": "busy",
                "is_warm": warm_start,
                "current_job_id": job["job_id"],
                "queue_depth_snapshot": pool["queue_depth"],
                "metadata": {
                    **_runtime_snapshot_metadata(
                        lease=selected,
                        queue_age_seconds=queue_age_seconds,
                        desired_warm_instances=pool["desired_warm_instances"],
                    ),
                    "plan_tier": job.get("plan_tier"),
                    "warm_start": warm_start,
                },
                "allocated_at": _utc_now(),
                "released_at": None,
                "expires_at": (
                    datetime.now(timezone.utc) + timedelta(seconds=settings.gpu_pool_idle_timeout_seconds)
                ).isoformat(),
            },
        )
        record_gpu_allocation(gpu_type=target_gpu, warm=warm_start, latency_ms=allocation_latency_ms)
        pool = reconcile_gpu_pool(queue_depth=pool["queue_depth"], queue_age_seconds=queue_age_seconds)
    except Exception:
        if selected is not None:
            repo.upsert_gpu_lease(
                worker_id=worker_id,
                payload=_lease_payload(
                    selected,
                    queue_depth_snapshot=int(selected.get("queue_depth_snapshot") or queue_depth),
                    queue_age_seconds=_lease_snapshot_float(selected, "queue_age_seconds", queue_age_seconds),
                    desired_warm_instances=_lease_snapshot_int(
                        selected,
                        "desired_warm_instances",
                        pool["desired_warm_instances"],
                    ),
                ),
            )
        else:
            repo.delete_gpu_lease(worker_id)
        raise
    return {
        "gpu_type": target_gpu,
        "warm_start": warm_start,
        "allocation_latency_ms": allocation_latency_ms,
        "queue_wait_ms": queue_wait_ms,
        "gpu_runtime_seconds": 0,
        "desired_warm_instances": pool["desired_warm_instances"],
        "active_warm_instances": pool["active_warm_instances"],
        "busy_instances": pool["busy_instances"],
        "utilization_percent": pool["utilization_percent"],
        "worker_id": worker_id,
    }


def release_gpu(job_id: str, *, gpu_runtime_seconds: int) -> dict[str, Any]:
    repo = RuntimeOpsRepository()
    for lease in repo.list_gpu_leases():
        if lease.get("current_job_id") != job_id:
            continue
        queue_depth_snapshot = int(lease.get("queue_depth_snapshot") or 0)
        queue_age_seconds = _lease_snapshot_float(lease, "queue_age_seconds", 0.0)
        if lease.get("is_warm"):
            repo.upsert_gpu_lease(
                worker_id=str(lease["worker_id"]),
                payload={
                    "gpu_type": lease.get("gpu_type", "L4"),
                    "lease_state": "idle",
                    "is_warm": True,
                    "current_job_id": None,
                    "queue_depth_snapshot": queue_depth_snapshot,
                    "metadata": {
                        **_runtime_snapshot_metadata(
                            lease=lease,
                            queue_age_seconds=queue_age_seconds,
                            desired_warm_instances=_lease_snapshot_int(
                                lease,
                                "desired_warm_instances",
                                max(settings.gpu_pool_min_warm_instances, 0),
                            ),
                        ),
                        "last_gpu_runtime_seconds": gpu_runtime_seconds,
                    },
                    "allocated_at": lease.get("allocated_at"),
                    "released_at": _utc_now(),
                    "expires_at": (
                        datetime.now(timezone.utc) + timedelta(seconds=settings.gpu_pool_idle_timeout_seconds)
                    ).isoformat(),
                },
            )
        else:
            repo.delete_gpu_lease(str(lease["worker_id"]))
        break
    return reconcile_gpu_pool(queue_depth=0, queue_age_seconds=0.0)


def autoscaler_idle_scale_down_healthy(snapshot: dict[str, Any] | None = None) -> bool:
    effective_snapshot = snapshot or current_runtime_snapshot()
    queue_depth = int(effective_snapshot.get("queue_depth", 0) or 0)
    active_warm_instances = int(effective_snapshot.get("active_warm_instances", 0) or 0)
    desired_warm_instances = int(effective_snapshot.get("desired_warm_instances", 0) or 0)
    min_warm = max(settings.gpu_pool_min_warm_instances, 0)
    if queue_depth > 0:
        return active_warm_instances >= desired_warm_instances

    leases = RuntimeOpsRepository().list_gpu_leases()
    idle_warm = [
        lease
        for lease in leases
        if lease.get("lease_state") != "released"
        and lease.get("is_warm") is True
        and lease.get("lease_state") == "idle"
    ]
    if len(idle_warm) <= min_warm:
        return True

    now = datetime.now(timezone.utc)
    sorted_idle = sorted(
        idle_warm,
        key=lambda lease: _parse_iso8601(str(lease.get("expires_at") or "")) or datetime.min.replace(tzinfo=timezone.utc),
    )
    extra_idle = sorted_idle[: len(sorted_idle) - min_warm]
    for lease in extra_idle:
        expires_at = _parse_iso8601(str(lease.get("expires_at") or ""))
        if expires_at is None or expires_at <= now:
            return False
    return True


def _route_alert(*, route: str, payload: dict[str, Any]) -> None:
    if settings.alert_routing_mode.lower() == "memory":
        return
    if route == "pagerduty" and settings.pagerduty_integration_key:
        httpx.post(
            "https://events.pagerduty.com/v2/enqueue",
            json={
                "routing_key": settings.pagerduty_integration_key,
                "event_action": "trigger",
                "payload": {
                    "summary": payload["summary"],
                    "severity": "critical" if payload["severity"] in {"P0", "P1"} else "warning",
                    "source": "chronosrefine",
                    "custom_details": payload,
                },
                "dedup_key": payload["incident_key"],
            },
            timeout=5.0,
        ).raise_for_status()
    elif route == "slack" and settings.slack_alert_webhook_url:
        httpx.post(
            settings.slack_alert_webhook_url,
            json={
                "text": f"[{payload['severity']}] {payload['summary']}",
                "attachments": [{"text": json.dumps(payload, sort_keys=True, default=str)}],
            },
            timeout=5.0,
        ).raise_for_status()


def emit_incident(
    *,
    severity: str,
    source_signal: str,
    summary: str,
    metadata: dict[str, Any],
    incident_state: str = "open",
) -> dict[str, Any]:
    incident_key = f"{severity}:{source_signal}"
    issue_tracker_url = (
        f"{settings.runtime_ops_incident_tracker_base_url.rstrip('/')}/{incident_key}"
        if settings.runtime_ops_incident_tracker_base_url
        else ""
    )
    payload = {
        "severity": severity,
        "incident_state": incident_state,
        "source_signal": source_signal,
        "runbook_key": source_signal,
        "issue_tracker_url": issue_tracker_url,
        "status_page_url": settings.runtime_ops_status_page_url,
        "communication_status": "drafted",
        "detection_delay_seconds": int(metadata.get("detection_delay_seconds", 0) or 0),
        "resolution_time_seconds": metadata.get("resolution_time_seconds"),
        "postmortem_due_at": (
            datetime.now(timezone.utc) + timedelta(days=7)
        ).isoformat()
        if severity in {"P0", "P1"}
        else None,
        "metadata": {**metadata, "summary": summary},
        "opened_at": metadata.get("opened_at", _utc_now()),
        "acknowledged_at": metadata.get("acknowledged_at"),
        "resolved_at": metadata.get("resolved_at"),
    }
    incident = RuntimeOpsRepository().upsert_incident(incident_key=incident_key, payload=payload)
    for route, status in alert_routes().items():
        if route == "pagerduty" and severity in {"P0", "P1"}:
            outcome = "delivered"
            try:
                _route_alert(route=route, payload={"incident_key": incident_key, "severity": severity, "summary": summary, **metadata})
            except Exception:
                outcome = "failed"
            record_alert_delivery(route=route, severity=severity, outcome=outcome)
        if route == "slack" and severity in {"P2", "P3"}:
            outcome = "delivered"
            try:
                _route_alert(route=route, payload={"incident_key": incident_key, "severity": severity, "summary": summary, **metadata})
            except Exception:
                outcome = "failed"
            record_alert_delivery(route=route, severity=severity, outcome=outcome)
    record_incident(severity=severity, state=incident_state)
    _ALERT_HISTORY.append({"incident_key": incident_key, "severity": severity, "summary": summary, "metadata": metadata})
    return incident


def alert_history() -> list[dict[str, Any]]:
    return [dict(item) for item in _ALERT_HISTORY]


def incident_history() -> list[dict[str, Any]]:
    return RuntimeOpsRepository().list_incidents()


def evaluate_job_slo(job: dict[str, Any]) -> dict[str, Any]:
    target_total_ms = int(job["estimated_duration_seconds"]) * 2000
    actual_total_ms = int((job.get("stage_timings") or {}).get("total_ms") or 0)
    ratio = round(actual_total_ms / max(target_total_ms, 1), 6)
    prior_ratios = [item["ratio"] for item in _SLO_HISTORY]
    _SLO_HISTORY.append({"job_id": job["job_id"], "ratio": ratio, "plan_tier": job.get("plan_tier", "hobbyist")})
    ratios = sorted(item["ratio"] for item in _SLO_HISTORY)
    index = min(max(ceil(len(ratios) * 0.95) - 1, 0), len(ratios) - 1)
    p95_ratio = ratios[index]
    degraded = bool(prior_ratios) and p95_ratio > (sorted(prior_ratios)[min(max(ceil(len(prior_ratios) * 0.95) - 1, 0), len(prior_ratios) - 1)] * (1 + (settings.slo_degradation_threshold_percent / 100)))
    compliant = p95_ratio <= 1.0
    failed_jobs = sum(1 for item in _SLO_HISTORY if item["ratio"] > 1.0)
    error_budget_burn_percent = round((failed_jobs / max(len(_SLO_HISTORY), 1)) * 100, 2)
    summary = {
        "target_total_ms": target_total_ms,
        "actual_total_ms": actual_total_ms,
        "p95_ratio": p95_ratio,
        "compliant": compliant,
        "degraded": degraded,
        "error_budget_burn_percent": error_budget_burn_percent,
        "museum_sla_applies": str(job.get("plan_tier", "")).lower() == "museum" and settings.museum_processing_sla_enabled,
    }
    record_slo_evaluation(
        compliant=compliant,
        p95_ratio=p95_ratio,
        degraded=degraded,
        error_budget_burn_percent=error_budget_burn_percent,
    )
    if not compliant:
        emit_incident(
            severity="P1" if summary["museum_sla_applies"] else "P2",
            source_signal="processing-time-slo",
            summary="Processing time SLO breached.",
            metadata={"job_id": job["job_id"], "p95_ratio": p95_ratio, "actual_total_ms": actual_total_ms},
        )
    elif degraded:
        emit_incident(
            severity="P3",
            source_signal="processing-time-regression",
            summary="Processing time p95 degraded more than 10 percent.",
            metadata={"job_id": job["job_id"], "p95_ratio": p95_ratio},
        )
    return summary


def evaluate_runtime_snapshot(snapshot: dict[str, Any], cache_summary: dict[str, Any]) -> list[dict[str, Any]]:
    incidents: list[dict[str, Any]] = []
    if snapshot["queue_depth"] > snapshot["active_warm_instances"] and snapshot["busy_instances"] >= snapshot["active_warm_instances"]:
        incidents.append(
            emit_incident(
                severity="P2",
                source_signal="gpu-pool-exhaustion",
                summary="GPU pool is saturated and queue depth exceeds active warm capacity.",
                metadata=snapshot,
            )
        )
    if cache_summary.get("degraded"):
        incidents.append(
            emit_incident(
                severity="P3",
                source_signal="redis-cache-degraded",
                summary="Segment cache degraded mode is active.",
                metadata=cache_summary,
            )
        )
    return incidents


def current_runtime_snapshot() -> dict[str, Any]:
    incidents = incident_history()
    leases = RuntimeOpsRepository().list_gpu_leases()
    active_warm = [
        lease
        for lease in leases
        if lease.get("lease_state") != "released" and lease.get("is_warm") is True
    ]
    busy_warm = [lease for lease in active_warm if lease.get("lease_state") == "busy"]
    queue_depth = max((int(lease.get("queue_depth_snapshot") or 0) for lease in active_warm), default=0)
    queue_age_seconds = round(max((_lease_snapshot_float(lease, "queue_age_seconds", 0.0) for lease in active_warm), default=0.0), 3)
    desired_warm_instances = max(
        max(settings.gpu_pool_min_warm_instances, 0),
        max((_lease_snapshot_int(lease, "desired_warm_instances", 0) for lease in active_warm), default=0),
    )
    utilization_percent = round((len(busy_warm) / max(len(active_warm), 1)) * 100, 2) if active_warm else 0.0
    snapshot = {
        "queue_depth": queue_depth,
        "queue_age_seconds": queue_age_seconds,
        "desired_warm_instances": desired_warm_instances,
        "active_warm_instances": len(active_warm),
        "busy_instances": len(busy_warm),
        "idle_instances": max(len(active_warm) - len(busy_warm), 0),
        "utilization_percent": utilization_percent,
        "alert_routes": alert_routes(),
        "incidents": incidents,
        "alerts": alert_history(),
        "training_calendar_url": settings.runtime_ops_training_calendar_url,
    }
    record_runtime_snapshot({k: v for k, v in snapshot.items() if isinstance(v, (int, float))})
    return snapshot
