"""Job orchestration service for Packet 3A."""

from __future__ import annotations

from uuid import uuid4

from app.api.problem_details import ProblemException
from app.db.phase2_store import JobRepository, ManifestRepository
from app.models.processing import ReproducibilityMode
from app.models.status import JobStatus
from app.services.billing_service import BillingService, billable_minutes_for_duration
from app.services.fidelity_profiles import resolve_fidelity_profile
from app.services.job_dispatcher import publish_job
from app.services.job_pipeline import build_segments
from app.services.reproducibility import validate_reproducibility_mode
from app.services.uncertainty_callouts import UncertaintyCalloutService
from app.validation.schema_validation import validate_era_profile


class JobService:
    def __init__(self) -> None:
        self._repo = JobRepository()
        self._manifests = ManifestRepository()
        self._billing = BillingService()
        self._callouts = UncertaintyCalloutService()

    def create_job(
        self,
        *,
        user_id: str,
        plan_tier: str,
        org_id: str,
        payload: dict[str, object],
        access_token: str | None = None,
    ) -> dict[str, object]:
        validation = validate_era_profile(payload["era_profile"])
        if not validation.is_valid:
            raise ProblemException(
                title="Schema Validation Failed",
                detail="Era profile validation failed. Fix the highlighted fields and retry.",
                status_code=400,
                errors=validation.as_problem_errors(),
            )

        estimated_minutes = billable_minutes_for_duration(
            duration_seconds=int(payload["estimated_duration_seconds"]),
            mode=str(payload["fidelity_tier"]),
        )
        reproducibility_mode = ReproducibilityMode(str(payload.get("reproducibility_mode") or ReproducibilityMode.PERCEPTUAL_EQUIVALENCE.value))
        validate_reproducibility_mode(reproducibility_mode, plan_tier=plan_tier)
        effective_fidelity_profile = resolve_fidelity_profile(
            requested_tier=payload["fidelity_tier"],
            era_profile=payload["era_profile"],
            config=payload.get("config") or {},
        )
        billing_snapshot = self._billing.record_estimate(
            user_id=user_id,
            plan_tier=plan_tier,
            estimated_minutes=estimated_minutes,
            access_token=access_token,
        )
        if billing_snapshot.hard_stop:
            raise ProblemException(
                title="Overage Approval Required",
                detail="This request exceeds the available monthly processing budget. Approve overage or upgrade before retrying.",
                status_code=403,
                errors=[
                    {
                        "field": "estimated_duration_seconds",
                        "message": "The projected usage exceeds the available monthly processing budget.",
                        "rule_id": "NFR-007",
                    }
                ],
            )

        job_id = str(uuid4())
        segments = build_segments(
            user_id=user_id,
            source_asset_checksum=str(payload["source_asset_checksum"]),
            estimated_duration_seconds=int(payload["estimated_duration_seconds"]),
            fidelity_tier=str(payload["fidelity_tier"]),
            reproducibility_mode=reproducibility_mode.value,
            processing_mode=str(payload["processing_mode"]),
            era_profile=payload["era_profile"],
            effective_fidelity_profile=effective_fidelity_profile,
            config=payload.get("config") or {},
        )
        job = self._repo.create_job(
            job_id=job_id,
            owner_user_id=user_id,
            plan_tier=plan_tier,
            org_id=org_id,
            media_uri=str(payload["media_uri"]),
            original_filename=str(payload.get("original_filename") or ""),
            mime_type=str(payload.get("mime_type") or ""),
            source_asset_checksum=str(payload["source_asset_checksum"]),
            fidelity_tier=str(payload["fidelity_tier"]),
            effective_fidelity_tier=str(payload["fidelity_tier"]),
            effective_fidelity_profile=effective_fidelity_profile,
            reproducibility_mode=reproducibility_mode.value,
            processing_mode=str(payload["processing_mode"]),
            era_profile=payload["era_profile"],
            config=payload.get("config") or {},
            estimated_duration_seconds=int(payload["estimated_duration_seconds"]),
            segments=segments,
            access_token=access_token,
        )
        publish_job(job_id, plan_tier=plan_tier)
        created = self._job_response_payload(job)
        created["queued_at"] = job["queued_at"]
        return created

    def get_job(self, job_id: str, *, owner_user_id: str, access_token: str | None = None) -> dict[str, object]:
        job = self._repo.get_job(job_id, owner_user_id=owner_user_id, access_token=access_token)
        if job is None:
            raise ProblemException(
                title="Not Found",
                detail="Job not found for the current user.",
                status_code=404,
            )
        segments = self._repo.list_segments(job_id, owner_user_id=owner_user_id, access_token=access_token)
        return self._job_response_payload(job, include_segments=True, segments=segments)

    def list_jobs(self, *, owner_user_id: str, access_token: str | None = None) -> list[dict[str, object]]:
        jobs = self._repo.list_jobs(owner_user_id=owner_user_id, access_token=access_token)
        return [self._job_response_payload(job) for job in jobs]

    def get_manifest(
        self,
        job_id: str,
        *,
        owner_user_id: str,
        access_token: str | None = None,
    ) -> dict[str, object]:
        manifest = self._manifests.get_manifest(job_id, owner_user_id=owner_user_id, access_token=access_token)
        if manifest is None:
            raise ProblemException(
                title="Not Found",
                detail="Transformation manifest not found for the current user.",
                status_code=404,
            )
        return manifest

    def request_cancellation(self, job_id: str, *, owner_user_id: str, access_token: str | None = None) -> dict[str, object]:
        job = self._repo.request_cancellation(job_id, owner_user_id=owner_user_id, access_token=access_token)
        if job is None:
            raise ProblemException(
                title="Not Found",
                detail="Job not found for the current user.",
                status_code=404,
            )
        if job["status"] == JobStatus.CANCEL_REQUESTED.value and not job.get("cancel_requested_at"):
            raise ProblemException(
                title="Cancellation Failed",
                detail="Job cancellation request did not persist correctly.",
                status_code=500,
            )
        return job

    def get_uncertainty_callouts(
        self,
        job_id: str,
        *,
        owner_user_id: str,
        access_token: str | None = None,
    ) -> dict[str, object]:
        return self._callouts.list_callouts(job_id, owner_user_id=owner_user_id, access_token=access_token)

    def _progress_from_job(self, job: dict[str, object]) -> dict[str, object]:
        segment_count = int(job.get("segment_count", 0) or 0)
        completed = int(job.get("completed_segment_count", 0) or 0)
        failed = int(job.get("failed_segment_count", 0) or 0)
        segment_index = max(completed + failed - 1, 0) if segment_count else 0
        return {
            "job_id": job["job_id"],
            "segment_index": segment_index,
            "segment_count": segment_count,
            "percent_complete": float(job.get("progress_percent", 0.0) or 0.0),
            "eta_seconds": int(job.get("eta_seconds", 0) or 0),
            "status": job["status"],
            "current_operation": job.get("current_operation") or "",
            "updated_at": job["updated_at"],
        }

    def _job_response_payload(
        self,
        job: dict[str, object],
        *,
        include_segments: bool = False,
        segments: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        stage_timings = job.get("stage_timings") or {
            "upload_ms": None,
            "era_detection_ms": None,
            "queue_wait_ms": None,
            "allocation_ms": None,
            "processing_ms": None,
            "encoding_ms": None,
            "download_ms": None,
            "total_ms": None,
        }
        performance_summary = {
            "stage_timings": stage_timings,
            "queue_wait_ms": stage_timings.get("queue_wait_ms"),
            "allocation_ms": stage_timings.get("allocation_ms"),
            "total_ms": stage_timings.get("total_ms"),
            "throughput_ratio": round(
                (int(stage_timings.get("total_ms") or 0) / max(int(job["estimated_duration_seconds"]) * 2000, 1)),
                6,
            )
            if stage_timings.get("total_ms") is not None
            else None,
        }
        payload = {
            "job_id": job["job_id"],
            "media_uri": job["media_uri"],
            "original_filename": job["original_filename"],
            "mime_type": job["mime_type"],
            "fidelity_tier": job["fidelity_tier"],
            "effective_fidelity_tier": job.get("effective_fidelity_tier", job["fidelity_tier"]),
            "processing_mode": job["processing_mode"],
            "reproducibility_mode": job.get(
                "reproducibility_mode",
                ReproducibilityMode.PERCEPTUAL_EQUIVALENCE.value,
            ),
            "estimated_duration_seconds": job["estimated_duration_seconds"],
            "status": job["status"],
            "progress_topic": job["progress_topic"],
            "result_uri": job.get("result_uri"),
            "manifest_available": bool(job.get("manifest_available")),
            "manifest": {
                "manifest_id": job["job_id"],
                "manifest_uri": job.get("manifest_uri"),
                "manifest_sha256": job.get("manifest_sha256"),
                "generated_at": job.get("manifest_generated_at"),
                "size_bytes": int(job.get("manifest_size_bytes", 0) or 0),
            }
            if job.get("manifest_available")
            else None,
            "performance_summary": performance_summary,
            "quality_summary": job.get("quality_summary")
            or {"e_hf": 0.0, "s_ls_db": 0.0, "t_tc": 0.0, "thresholds_met": False},
            "reproducibility_summary": job.get("reproducibility_summary"),
            "stage_timings": stage_timings,
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
                "actual_total_ms": stage_timings.get("total_ms"),
                "p95_ratio": None,
                "compliant": None,
                "degraded": False,
                "error_budget_burn_percent": 0.0,
                "museum_sla_applies": str(job.get("plan_tier", "")).lower() == "museum",
            },
            "failed_segments": job.get("failed_segments") or [],
            "warnings": job.get("warnings") or [],
            "created_at": job["created_at"],
            "updated_at": job["updated_at"],
            "progress": self._progress_from_job(job),
        }
        if include_segments:
            payload.update(
                {
                    "started_at": job.get("started_at"),
                    "completed_at": job.get("completed_at"),
                    "cancel_requested_at": job.get("cancel_requested_at"),
                    "last_error": job.get("last_error"),
                    "segments": [self._segment_response_payload(segment) for segment in (segments or [])],
                }
            )
        return payload

    def _segment_response_payload(self, segment: dict[str, object]) -> dict[str, object]:
        return {
            "job_id": segment["job_id"],
            "segment_index": segment["segment_index"],
            "segment_start_seconds": segment["segment_start_seconds"],
            "segment_end_seconds": segment["segment_end_seconds"],
            "segment_duration_seconds": segment["segment_duration_seconds"],
            "status": segment["status"],
            "attempt_count": segment.get("attempt_count", 0),
            "idempotency_key": segment["idempotency_key"],
            "last_error_classification": segment.get("last_error_classification"),
            "retry_backoffs_seconds": segment.get("retry_backoffs_seconds") or [],
            "output_uri": segment.get("output_uri"),
            "cache_status": segment.get("cache_status", "miss"),
            "cache_hit_latency_ms": segment.get("cache_hit_latency_ms"),
            "cache_namespace": segment.get("cache_namespace"),
            "cached_output_uri": segment.get("cached_output_uri"),
            "gpu_type": segment.get("gpu_type"),
            "allocation_latency_ms": segment.get("allocation_latency_ms"),
            "updated_at": segment["updated_at"],
        }
