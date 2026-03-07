"""In-process async runtime abstraction for Packet 3A."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import httpx

from app.api.contracts import FidelityTier, WebhookEventType
from app.config import settings
from app.db.phase2_store import JobRepository, ManifestRepository, WebhookSubscriptionRepository
from app.models.processing import ReproducibilityMode
from app.models.status import JobStatus
from app.observability.monitoring import (
    record_job_runtime_event,
    record_job_stage_timings,
    record_segment_failure,
    record_segment_retry,
    record_webhook_attempt,
)
from app.services.fidelity_profiles import fidelity_profile_for
from app.services.billing_service import BillingService, billable_minutes_for_duration
from app.services.job_dispatcher import (
    pop_next_dispatch_message,
    publish_job,
    requeue_dispatch_message,
    reset_job_dispatcher_state,
)
from app.services.job_worker import (
    authorize_trusted_worker,
    default_trusted_worker_token,
    progress_events_for_job as worker_progress_events_for_job,
    publish_progress_event,
    reset_worker_state,
    run_worker_message,
)
from app.services.quality_metrics import ReferenceQualityMetricsProvider, aggregate_quality_metrics
from app.services.reproducibility import build_segment_reproducibility_proof, rollup_reproducibility
from app.services.runtime_ops import (
    allocate_gpu,
    build_segment_cache_key,
    evaluate_job_slo,
    evaluate_runtime_snapshot,
    lookup_segment_cache,
    reconcile_gpu_pool,
    release_gpu,
    reset_runtime_ops_state,
    store_segment_cache,
)
from app.services.transformation_manifest import finalize_manifest_payload

RETRY_BACKOFF_SECONDS = (1, 2, 4)
_WEBHOOK_DELIVERIES: list[dict[str, Any]] = []
_SEGMENT_FAILURE_PLANS: dict[tuple[str, int], list[str]] = defaultdict(list)
_REPRODUCIBILITY_FAILURE_PLANS: dict[tuple[str, int], int] = defaultdict(int)
_DEAD_LETTER_QUEUE: list[str] = []


def reset_job_runtime_state() -> None:
    reset_job_dispatcher_state()
    reset_worker_state()
    reset_runtime_ops_state()
    _WEBHOOK_DELIVERIES.clear()
    _SEGMENT_FAILURE_PLANS.clear()
    _REPRODUCIBILITY_FAILURE_PLANS.clear()
    _DEAD_LETTER_QUEUE.clear()


def enqueue_job(job_id: str, *, plan_tier: str) -> None:
    publish_job(job_id, plan_tier=plan_tier)


def configure_segment_failures(job_id: str, segment_index: int, failures: list[str]) -> None:
    _SEGMENT_FAILURE_PLANS[(job_id, segment_index)] = list(failures)


def configure_reproducibility_failures(job_id: str, segment_index: int, failures: int) -> None:
    _REPRODUCIBILITY_FAILURE_PLANS[(job_id, segment_index)] = max(int(failures), 0)


def progress_events_for_job(job_id: str) -> list[dict[str, Any]]:
    return worker_progress_events_for_job(job_id)


def webhook_deliveries_for_job(job_id: str) -> list[dict[str, Any]]:
    return [dict(item) for item in _WEBHOOK_DELIVERIES if item["job_id"] == job_id]


def dead_letter_jobs() -> list[str]:
    return list(_DEAD_LETTER_QUEUE)


def drain_job_queue(*, max_jobs: int | None = None) -> list[str]:
    processed: list[str] = []
    while max_jobs is None or len(processed) < max_jobs:
        message = pop_next_dispatch_message()
        if message is None:
            break
        payload = {
            "job_id": message.job_id,
            "plan_tier": message.plan_tier,
            "source": message.source,
            "submitted_at": message.submitted_at,
        }
        trusted_token = default_trusted_worker_token()
        try:
            run_worker_message(payload, trusted_token=trusted_token)
        except Exception:
            requeue_dispatch_message(message)
            raise
        processed.append(message.job_id)
    return processed


def process_job(job_id: str, *, trusted_token: str | None = None) -> dict[str, Any] | None:
    trusted_token = authorize_trusted_worker(trusted_token)
    repo = JobRepository()
    job = repo.get_job_for_worker(job_id)
    if job is None:
        return None

    try:
        if job["status"] == JobStatus.CANCEL_REQUESTED.value:
            cancelled = _cancel_job(repo, job_id, segment_index=0, trusted_token=trusted_token)
            _deliver_webhooks(cancelled, WebhookEventType.CANCELLED.value)
            return cancelled

        processing = repo.update_job_for_worker(
            job_id,
            patch={
                "status": JobStatus.PROCESSING.value,
                "started_at": job.get("started_at") or job.get("updated_at"),
                "current_operation": "Preparing processing pipeline",
            },
        )
        gpu_allocation = allocate_gpu(processing)
        stage_timings = {
            **(processing.get("stage_timings") or {}),
            "queue_wait_ms": gpu_allocation["queue_wait_ms"],
            "allocation_ms": gpu_allocation["allocation_latency_ms"],
        }
        processing = repo.update_job_for_worker(
            job_id,
            patch={
                "stage_timings": stage_timings,
                "gpu_summary": {
                    "gpu_type": gpu_allocation["gpu_type"],
                    "warm_start": gpu_allocation["warm_start"],
                    "allocation_latency_ms": gpu_allocation["allocation_latency_ms"],
                    "gpu_runtime_seconds": 0,
                    "desired_warm_instances": gpu_allocation["desired_warm_instances"],
                    "active_warm_instances": gpu_allocation["active_warm_instances"],
                    "busy_instances": gpu_allocation["busy_instances"],
                    "utilization_percent": gpu_allocation["utilization_percent"],
                },
            },
        )
        record_job_runtime_event("started")
        _publish_progress(processing, segment_index=0, trusted_token=trusted_token)
        _deliver_webhooks(processing, WebhookEventType.STARTED.value)

        segments = repo.list_segments(job_id)
        for segment in segments:
            current = repo.get_job_for_worker(job_id)
            if current is None:
                return None
            if current["status"] == JobStatus.CANCEL_REQUESTED.value:
                cancelled = _cancel_job(
                    repo,
                    job_id,
                    segment_index=segment["segment_index"],
                    trusted_token=trusted_token,
                )
                _deliver_webhooks(cancelled, WebhookEventType.CANCELLED.value)
                return cancelled
            _process_segment(repo, current, segment, trusted_token=trusted_token)

        completed = _finalize_job(repo, job_id, trusted_token=trusted_token)
        event_type = {
            JobStatus.COMPLETED.value: WebhookEventType.COMPLETED.value,
            JobStatus.PARTIAL.value: WebhookEventType.PARTIAL.value,
            JobStatus.FAILED.value: WebhookEventType.FAILED.value,
            JobStatus.CANCELLED.value: WebhookEventType.CANCELLED.value,
        }[completed["status"]]
        _publish_progress(
            completed,
            segment_index=max(completed["segment_count"] - 1, 0),
            trusted_token=trusted_token,
        )
        _deliver_webhooks(completed, event_type)
        return completed
    except Exception as exc:
        failed = repo.update_job_for_worker(
            job_id,
            patch={
                "status": JobStatus.FAILED.value,
                "last_error": str(exc),
                "current_operation": "Failed during worker execution",
                "completed_at": job.get("updated_at"),
            },
        )
        if job_id not in _DEAD_LETTER_QUEUE:
            _DEAD_LETTER_QUEUE.append(job_id)
        BillingService().consume_minutes(
            user_id=failed["owner_user_id"],
            plan_tier=failed["plan_tier"],
            minutes=0,
        )
        record_job_runtime_event("failed")
        _publish_progress(failed, segment_index=0, trusted_token=trusted_token)
        _deliver_webhooks(failed, WebhookEventType.FAILED.value)
        return failed


def _process_segment(
    repo: JobRepository,
    job: dict[str, Any],
    segment: dict[str, Any],
    *,
    trusted_token: str | None,
) -> None:
    segment_count = max(job["segment_count"], 1)
    retry_backoffs = list(segment.get("retry_backoffs_seconds") or [])
    quality_provider = ReferenceQualityMetricsProvider()
    reproducibility_mode = ReproducibilityMode(job.get("reproducibility_mode", ReproducibilityMode.PERCEPTUAL_EQUIVALENCE.value))
    fidelity_profile = job.get("effective_fidelity_profile") or fidelity_profile_for(FidelityTier(job["fidelity_tier"]))
    version_namespace = f"{fidelity_profile['tier']}:{settings.build_sha}:{settings.gemini_model}"
    cache_entry, cache_state = lookup_segment_cache(
        job=job,
        segment=segment,
        effective_fidelity_profile=fidelity_profile,
        version_namespace=version_namespace,
    )
    if cache_entry:
        repo.update_segment_for_worker(
            job["job_id"],
            segment["segment_index"],
            patch={
                "status": "completed",
                "attempt_count": max(segment["attempt_count"], 1),
                "output_uri": cache_entry["output_uri"],
                "cache_status": cache_state["cache_status"],
                "cache_hit_latency_ms": cache_state["cache_hit_latency_ms"],
                "cache_namespace": cache_state["cache_namespace"],
                "cached_output_uri": cache_entry["output_uri"],
                "gpu_type": (job.get("gpu_summary") or {}).get("gpu_type"),
                "allocation_latency_ms": (job.get("stage_timings") or {}).get("allocation_ms"),
                "quality_metrics": cache_entry.get("quality_metrics"),
                "reproducibility_proof": cache_entry.get("reproducibility_proof"),
                "uncertainty_callouts": cache_entry.get("uncertainty_callouts") or [],
            },
        )
        _update_processing_progress(
            repo,
            job["job_id"],
            segment["segment_index"],
            segment_count,
            trusted_token=trusted_token,
        )
        return
    for attempt in range(segment["attempt_count"] + 1, len(RETRY_BACKOFF_SECONDS) + 1):
        repo.update_segment_for_worker(
            job["job_id"],
            segment["segment_index"],
            patch={"status": "processing", "attempt_count": attempt},
        )
        operation = f"{job['fidelity_tier']} segment {segment['segment_index'] + 1}/{segment_count}"
        repo.update_job_for_worker(
            job["job_id"],
            patch={"current_operation": operation},
        )

        failure = _next_failure(job["job_id"], segment["segment_index"])
        if failure is None:
            output_uri = f"gs://chronos/jobs/{job['job_id']}/segment-{segment['segment_index']:04d}.mp4"
            quality_metrics = quality_provider.calculate(
                job=job,
                segment=segment,
                fidelity_profile=fidelity_profile,
            )
            reproducibility_failed = _should_fail_reproducibility(job["job_id"], segment["segment_index"])
            proof = build_segment_reproducibility_proof(
                job=job,
                segment=segment,
                quality_metrics=quality_metrics,
                mode=reproducibility_mode,
                rerun_count=max(attempt - 1, 0),
                verification_failed=reproducibility_failed,
            )
            if reproducibility_failed:
                if attempt < len(RETRY_BACKOFF_SECONDS):
                    backoff_seconds = RETRY_BACKOFF_SECONDS[attempt - 1]
                    retry_backoffs.append(backoff_seconds)
                    repo.update_segment_for_worker(
                        job["job_id"],
                        segment["segment_index"],
                    patch={
                        "status": "queued",
                        "attempt_count": attempt,
                        "last_error_classification": "reproducibility",
                        "retry_backoffs_seconds": retry_backoffs,
                        "cache_status": cache_state["cache_status"],
                        "cache_hit_latency_ms": cache_state["cache_hit_latency_ms"],
                        "cache_namespace": cache_state["cache_namespace"],
                        "quality_metrics": quality_metrics,
                        "reproducibility_proof": proof,
                        "uncertainty_callouts": quality_metrics["uncertainty_callouts"],
                    },
                )
                    record_segment_retry("reproducibility")
                    continue
                repo.update_segment_for_worker(
                    job["job_id"],
                    segment["segment_index"],
                    patch={
                        "status": "failed",
                        "attempt_count": attempt,
                        "last_error_classification": "reproducibility",
                        "retry_backoffs_seconds": retry_backoffs,
                        "cache_status": cache_state["cache_status"],
                        "cache_hit_latency_ms": cache_state["cache_hit_latency_ms"],
                        "cache_namespace": cache_state["cache_namespace"],
                        "quality_metrics": quality_metrics,
                        "reproducibility_proof": proof,
                        "uncertainty_callouts": quality_metrics["uncertainty_callouts"],
                    },
                )
                record_segment_failure("reproducibility")
                _update_processing_progress(
                    repo,
                    job["job_id"],
                    segment["segment_index"],
                    segment_count,
                    trusted_token=trusted_token,
                )
                return
            cache_key = build_segment_cache_key(
                user_id=str(job["owner_user_id"]),
                source_asset_checksum=str(job["source_asset_checksum"]),
                segment=segment,
                effective_fidelity_profile=fidelity_profile,
                reproducibility_mode=reproducibility_mode.value,
                version_namespace=version_namespace,
            )
            cache_store = store_segment_cache(
                cache_key=cache_key,
                payload={
                    "output_uri": output_uri,
                    "quality_metrics": quality_metrics,
                    "reproducibility_proof": proof,
                    "uncertainty_callouts": quality_metrics["uncertainty_callouts"],
                },
            )
            effective_cache_state = dict(cache_state)
            if cache_store.get("degraded"):
                effective_cache_state.update(
                    {
                        "cache_status": "bypass",
                        "cache_hit_latency_ms": None,
                        "cached_output_uri": None,
                        "degraded": True,
                    }
                )
            repo.update_segment_for_worker(
                job["job_id"],
                segment["segment_index"],
                patch={
                    "status": "completed",
                    "attempt_count": attempt,
                    "output_uri": output_uri,
                    "last_error_classification": None,
                    "retry_backoffs_seconds": retry_backoffs,
                    "cache_status": effective_cache_state["cache_status"],
                    "cache_hit_latency_ms": effective_cache_state["cache_hit_latency_ms"],
                    "cache_namespace": effective_cache_state["cache_namespace"],
                    "cached_output_uri": effective_cache_state["cached_output_uri"],
                    "gpu_type": (job.get("gpu_summary") or {}).get("gpu_type"),
                    "allocation_latency_ms": (job.get("stage_timings") or {}).get("allocation_ms"),
                    "quality_metrics": quality_metrics,
                    "reproducibility_proof": proof,
                    "uncertainty_callouts": quality_metrics["uncertainty_callouts"],
                },
            )
            _update_processing_progress(
                repo,
                job["job_id"],
                segment["segment_index"],
                segment_count,
                trusted_token=trusted_token,
            )
            return

        error_classification = _classify_failure(failure)
        if attempt < len(RETRY_BACKOFF_SECONDS):
            backoff_seconds = RETRY_BACKOFF_SECONDS[attempt - 1]
            retry_backoffs.append(backoff_seconds)
            repo.update_segment_for_worker(
                job["job_id"],
                segment["segment_index"],
                patch={
                    "status": "queued",
                    "attempt_count": attempt,
                    "last_error_classification": error_classification,
                    "retry_backoffs_seconds": retry_backoffs,
                    "cache_status": cache_state["cache_status"],
                    "cache_hit_latency_ms": cache_state["cache_hit_latency_ms"],
                    "cache_namespace": cache_state["cache_namespace"],
                },
            )
            record_segment_retry(error_classification)
            continue

        repo.update_segment_for_worker(
            job["job_id"],
            segment["segment_index"],
            patch={
                "status": "failed",
                "attempt_count": attempt,
                "last_error_classification": error_classification,
                "retry_backoffs_seconds": retry_backoffs,
                "cache_status": cache_state["cache_status"],
                "cache_hit_latency_ms": cache_state["cache_hit_latency_ms"],
                "cache_namespace": cache_state["cache_namespace"],
            },
        )
        record_segment_failure(error_classification)
        _update_processing_progress(
            repo,
            job["job_id"],
            segment["segment_index"],
            segment_count,
            trusted_token=trusted_token,
        )
        return


def _update_processing_progress(
    repo: JobRepository,
    job_id: str,
    segment_index: int,
    segment_count: int,
    *,
    trusted_token: str | None,
) -> None:
    segments = repo.list_segments(job_id)
    completed_segments = sum(1 for item in segments if item["status"] == "completed")
    failed_segments = [item["segment_index"] for item in segments if item["status"] == "failed"]
    processed_segments = completed_segments + len(failed_segments)
    percent_complete = round((processed_segments / max(segment_count, 1)) * 100, 2)
    remaining_segments = max(segment_count - processed_segments, 0)
    processing_ms = sum(
        int(
            item.get("cache_hit_latency_ms")
            or (item.get("quality_metrics") or {}).get(
                "metric_latency_ms",
                item["segment_duration_seconds"] * 100,
            )
        )
        for item in segments
        if item["status"] in {"completed", "failed"}
    )
    cache_hits = sum(1 for item in segments if item.get("cache_status") == "hit")
    cache_bypassed = sum(1 for item in segments if item.get("cache_status") == "bypass")
    cache_misses = max(processed_segments - cache_hits - cache_bypassed, 0)
    stage_timings = {
        **(repo.get_job_for_worker(job_id).get("stage_timings") or {}),
        "processing_ms": processing_ms,
        "encoding_ms": max((completed_segments - cache_hits) * 90, 0) + (cache_hits * 15),
    }
    stage_timings["total_ms"] = _timing_total(stage_timings)
    current_job = repo.get_job_for_worker(job_id)
    cache_summary = {
        "hits": cache_hits,
        "misses": cache_misses,
        "bypassed": cache_bypassed,
        "degraded": cache_bypassed > 0,
        "hit_rate": round(cache_hits / max(cache_hits + cache_misses, 1), 4),
        "saved_gpu_seconds": cache_hits * 10,
    }
    gpu_summary = {
        **(current_job.get("gpu_summary") or {}),
        "gpu_runtime_seconds": sum(
            item["segment_duration_seconds"]
            for item in segments
            if item["status"] in {"completed", "failed"} and item.get("cache_status") != "hit"
        ),
    }
    patch = {
        "completed_segment_count": completed_segments,
        "failed_segment_count": len(failed_segments),
        "failed_segments": failed_segments,
        "progress_percent": percent_complete,
        "eta_seconds": remaining_segments * 10,
        "current_operation": f"Processed segment {segment_index + 1}/{segment_count}",
        "stage_timings": stage_timings,
        "cache_summary": cache_summary,
        "gpu_summary": gpu_summary,
    }
    job = repo.update_job_for_worker(job_id, patch=patch)
    _publish_progress(job, segment_index=segment_index, trusted_token=trusted_token)


def _finalize_job(repo: JobRepository, job_id: str, *, trusted_token: str | None) -> dict[str, Any]:
    job = repo.get_job_for_worker(job_id)
    if job is None:
        raise RuntimeError(f"Unknown job {job_id}")
    segments = repo.list_segments(job_id)
    failed_segments = [item["segment_index"] for item in segments if item["status"] == "failed"]
    completed_segments = [item["segment_index"] for item in segments if item["status"] == "completed"]
    if job["status"] == JobStatus.CANCEL_REQUESTED.value:
        return _cancel_job(
            repo,
            job_id,
            segment_index=max(len(segments) - 1, 0),
            trusted_token=trusted_token,
        )
    if failed_segments and completed_segments:
        status = JobStatus.PARTIAL
        result_uri = f"gs://chronos/jobs/{job_id}/partial-result.mp4"
        warnings = ["One or more segments failed. Partial results are available."]
    elif failed_segments:
        status = JobStatus.FAILED
        result_uri = None
        warnings = ["All processed segments failed."]
        if job_id not in _DEAD_LETTER_QUEUE:
            _DEAD_LETTER_QUEUE.append(job_id)
    else:
        status = JobStatus.COMPLETED
        result_uri = f"gs://chronos/jobs/{job_id}/result.mp4"
        warnings = []

    completed_quality = [item["quality_metrics"] for item in segments if item.get("quality_metrics")]
    quality_summary = aggregate_quality_metrics(completed_quality)
    reproducibility_summary = rollup_reproducibility(
        mode=ReproducibilityMode(job.get("reproducibility_mode", ReproducibilityMode.PERCEPTUAL_EQUIVALENCE.value)),
        segment_proofs=[item["reproducibility_proof"] for item in segments if item.get("reproducibility_proof")],
    )
    cache_hits = sum(1 for item in segments if item.get("cache_status") == "hit")
    cache_bypassed = sum(1 for item in segments if item.get("cache_status") == "bypass")
    cache_misses = max(len(segments) - cache_hits - cache_bypassed, 0)
    cache_summary = {
        "hits": cache_hits,
        "misses": cache_misses,
        "bypassed": cache_bypassed,
        "degraded": cache_bypassed > 0,
        "hit_rate": round(cache_hits / max(cache_hits + cache_misses, 1), 4),
        "saved_gpu_seconds": sum(
            item["segment_duration_seconds"] for item in segments if item.get("cache_status") == "hit"
        ),
    }
    gpu_runtime_seconds = sum(
        item["segment_duration_seconds"]
        for item in segments
        if item["status"] in {"completed", "failed"} and item.get("cache_status") != "hit"
    )
    stage_timings = {
        **(job.get("stage_timings") or {}),
        "processing_ms": sum(
            int(
                item.get("cache_hit_latency_ms")
                or (item.get("quality_metrics") or {}).get(
                    "metric_latency_ms",
                    item["segment_duration_seconds"] * 100,
                )
            )
            for item in segments
            if item["status"] in {"completed", "failed"}
        ),
        "encoding_ms": max((len(completed_segments) - cache_hits) * 90, 0) + (cache_hits * 15),
        "download_ms": 40 if status in {JobStatus.COMPLETED, JobStatus.PARTIAL} else None,
    }
    stage_timings["total_ms"] = _timing_total(stage_timings)
    released_pool = release_gpu(job_id, gpu_runtime_seconds=gpu_runtime_seconds)
    gpu_summary = {
        **(job.get("gpu_summary") or {}),
        "gpu_runtime_seconds": gpu_runtime_seconds,
        "desired_warm_instances": released_pool["desired_warm_instances"],
        "active_warm_instances": released_pool["active_warm_instances"],
        "busy_instances": released_pool["busy_instances"],
        "utilization_percent": released_pool["utilization_percent"],
    }
    cost_summary = {
        "gpu_seconds": gpu_runtime_seconds,
        "storage_operations": len(completed_segments) + int(bool(result_uri)),
        "api_calls": len(completed_quality),
        "total_cost_usd": round((gpu_runtime_seconds * 0.012) + ((len(completed_segments) + int(bool(result_uri))) * 0.001), 4),
    }
    slo_summary = evaluate_job_slo({**job, "stage_timings": stage_timings})

    finalized = repo.update_job_for_worker(
        job_id,
        patch={
            "status": status.value,
            "result_uri": result_uri,
            "warnings": warnings,
            "last_error": None if status != JobStatus.FAILED else "Processing failed after retry exhaustion.",
            "current_operation": "Completed" if status == JobStatus.COMPLETED else "Completed with segment failures",
            "completed_at": job.get("updated_at"),
            "eta_seconds": 0,
            "progress_percent": 100.0,
            "quality_summary": quality_summary,
            "reproducibility_summary": reproducibility_summary,
            "stage_timings": stage_timings,
            "cache_summary": cache_summary,
            "gpu_summary": gpu_summary,
            "cost_summary": cost_summary,
            "slo_summary": slo_summary,
        },
    )
    record_job_stage_timings(stage_timings)
    evaluate_runtime_snapshot(released_pool, cache_summary)
    if status in {JobStatus.COMPLETED, JobStatus.PARTIAL}:
        try:
            manifest_payload = finalize_manifest_payload(
                manifest_id=job_id,
                generated_at=finalized["updated_at"],
                job=finalized,
                segments=repo.list_segments(job_id),
            )
            ManifestRepository().upsert_manifest_for_worker(job_id=job_id, manifest=manifest_payload)
            finalized = repo.update_job_for_worker(
                job_id,
                patch={
                    "manifest_available": True,
                    "manifest_uri": manifest_payload["manifest_uri"],
                    "manifest_sha256": manifest_payload["manifest_sha256"],
                    "manifest_generated_at": manifest_payload["generated_at"],
                    "manifest_size_bytes": manifest_payload["size_bytes"],
                },
            )
        except Exception as exc:
            finalized = repo.update_job_for_worker(
                job_id,
                patch={
                    "status": JobStatus.FAILED.value,
                    "last_error": f"Manifest generation failed: {exc}",
                    "warnings": (warnings or []) + ["Manifest generation failed after processing completed."],
                    "current_operation": "Manifest generation failed",
                },
            )
            status = JobStatus.FAILED
    record_job_runtime_event(status.value)
    if status in {JobStatus.COMPLETED, JobStatus.PARTIAL}:
        BillingService().consume_minutes(
            user_id=finalized["owner_user_id"],
            plan_tier=finalized["plan_tier"],
            minutes=billable_minutes_for_duration(
                finalized["estimated_duration_seconds"],
                finalized["fidelity_tier"],
            ),
        )
    elif status == JobStatus.FAILED:
        BillingService().consume_minutes(
            user_id=finalized["owner_user_id"],
            plan_tier=finalized["plan_tier"],
            minutes=0,
        )
    return finalized


def _cancel_job(repo: JobRepository, job_id: str, *, segment_index: int, trusted_token: str | None = None) -> dict[str, Any]:
    cancelled = repo.update_job_for_worker(
        job_id,
        patch={
            "status": JobStatus.CANCELLED.value,
            "completed_at": repo.get_job_for_worker(job_id)["updated_at"],
            "current_operation": "Cancellation acknowledged",
            "eta_seconds": 0,
        },
    )
    BillingService().consume_minutes(
        user_id=cancelled["owner_user_id"],
        plan_tier=cancelled["plan_tier"],
        minutes=0,
    )
    _publish_progress(cancelled, segment_index=segment_index, trusted_token=trusted_token)
    record_job_runtime_event("cancelled")
    return cancelled


def _publish_progress(job: dict[str, Any], *, segment_index: int, trusted_token: str | None) -> None:
    payload = {
        "job_id": job["job_id"],
        "segment_index": segment_index,
        "segment_count": job["segment_count"],
        "percent_complete": float(job["progress_percent"]),
        "eta_seconds": int(job["eta_seconds"]),
        "status": job["status"],
        "current_operation": job["current_operation"],
        "updated_at": job["updated_at"],
        "channel": job["progress_topic"],
        "event": "progress_update",
    }
    publish_progress_event(
        trusted_token=authorize_trusted_worker(trusted_token),
        payload=payload,
    )


def _deliver_webhooks(job: dict[str, Any], event_type: str) -> None:
    subscriptions = WebhookSubscriptionRepository().list_enabled(
        owner_user_id=job["owner_user_id"],
        event_type=event_type,
    )
    payload = {
        "job_id": job["job_id"],
        "event_type": event_type,
        "status": job["status"],
        "progress_topic": job["progress_topic"],
        "effective_fidelity_tier": job.get("effective_fidelity_tier", job["fidelity_tier"]),
        "performance_summary": {
            "stage_timings": job.get("stage_timings") or {},
            "queue_wait_ms": (job.get("stage_timings") or {}).get("queue_wait_ms"),
            "allocation_ms": (job.get("stage_timings") or {}).get("allocation_ms"),
            "total_ms": (job.get("stage_timings") or {}).get("total_ms"),
            "throughput_ratio": (job.get("slo_summary") or {}).get("p95_ratio"),
        },
        "quality_summary": job.get("quality_summary") or {"e_hf": 0.0, "s_ls_db": 0.0, "t_tc": 0.0, "thresholds_met": False},
        "cache_summary": job.get("cache_summary")
        or {"hits": 0, "misses": 0, "bypassed": 0, "degraded": False, "hit_rate": 0.0, "saved_gpu_seconds": 0},
        "gpu_summary": job.get("gpu_summary")
        or {
            "gpu_type": None,
            "warm_start": None,
            "allocation_latency_ms": None,
            "gpu_runtime_seconds": 0,
            "desired_warm_instances": 0,
            "active_warm_instances": 0,
            "busy_instances": 0,
            "utilization_percent": 0.0,
        },
        "cost_summary": job.get("cost_summary")
        or {"gpu_seconds": 0, "storage_operations": 0, "api_calls": 0, "total_cost_usd": 0.0},
        "slo_summary": job.get("slo_summary")
        or {
            "target_total_ms": int(job["estimated_duration_seconds"]) * 2000,
            "actual_total_ms": (job.get("stage_timings") or {}).get("total_ms"),
            "p95_ratio": None,
            "compliant": None,
            "degraded": False,
            "error_budget_burn_percent": 0.0,
            "museum_sla_applies": str(job.get("plan_tier", "")).lower() == "museum",
        },
        "reproducibility_mode": job.get("reproducibility_mode", ReproducibilityMode.PERCEPTUAL_EQUIVALENCE.value),
        "manifest_available": bool(job.get("manifest_available")),
        "updated_at": job["updated_at"],
    }
    for subscription in subscriptions:
        for attempt in range(1, 4):
            try:
                _send_webhook_request(subscription["webhook_url"], payload)
                _WEBHOOK_DELIVERIES.append(
                    {
                        "job_id": job["job_id"],
                        "event_type": event_type,
                        "webhook_url": subscription["webhook_url"],
                        "attempt": attempt,
                        "status": "delivered",
                    }
                )
                record_webhook_attempt("delivered")
                break
            except Exception as exc:
                delivery = {
                    "job_id": job["job_id"],
                    "event_type": event_type,
                    "webhook_url": subscription["webhook_url"],
                    "attempt": attempt,
                    "status": "failed" if attempt == 3 else "retrying",
                    "error": str(exc),
                    "backoff_seconds": RETRY_BACKOFF_SECONDS[attempt - 1],
                }
                _WEBHOOK_DELIVERIES.append(delivery)
                record_webhook_attempt(delivery["status"])
                if attempt == 3:
                    break


def _send_webhook_request(webhook_url: str, payload: dict[str, Any]) -> None:
    if settings.environment == "test":
        return
    with httpx.Client(timeout=5.0) as client:
        response = client.post(webhook_url, json=payload)
        response.raise_for_status()


def _next_failure(job_id: str, segment_index: int) -> str | None:
    plan = _SEGMENT_FAILURE_PLANS.get((job_id, segment_index), [])
    if not plan:
        return None
    failure = plan.pop(0)
    _SEGMENT_FAILURE_PLANS[(job_id, segment_index)] = plan
    return failure


def _classify_failure(failure: str) -> str:
    if failure in {"network", "gpu_oom", "transient"}:
        return "transient"
    return "persistent"


def _should_fail_reproducibility(job_id: str, segment_index: int) -> bool:
    key = (job_id, segment_index)
    remaining = _REPRODUCIBILITY_FAILURE_PLANS.get(key, 0)
    if remaining <= 0:
        return False
    _REPRODUCIBILITY_FAILURE_PLANS[key] = remaining - 1
    return True


def _timing_total(stage_timings: dict[str, Any]) -> int:
    return sum(
        int(value)
        for key, value in stage_timings.items()
        if key != "total_ms" and isinstance(value, int)
    )
