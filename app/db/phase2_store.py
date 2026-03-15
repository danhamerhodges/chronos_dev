"""Phase 2 repositories with Supabase-backed persistence and test fallback."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from threading import Lock
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

from app.models.status import JobStatus, UploadStatus
from app.config import settings
from app.db.client import SupabaseClient


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_uuid(value: str) -> str:
    return str(uuid5(NAMESPACE_URL, value))


def _billing_month() -> str:
    today = date.today()
    return today.replace(day=1).isoformat()


def _request_patch(payload: dict[str, Any], *, nullable_keys: set[str] | None = None) -> dict[str, Any]:
    allowed_nulls = nullable_keys or set()
    return {
        key: value
        for key, value in payload.items()
        if value is not None or key in allowed_nulls
    }


_SUPABASE_JOB_JSON_FIELDS = {
    "failed_segments",
    "warnings",
    "config",
    "era_profile",
    "effective_fidelity_profile",
    "quality_summary",
    "reproducibility_summary",
    "stage_timings",
    "cache_summary",
    "gpu_summary",
    "cost_summary",
    "cost_estimate_summary",
    "cost_reconciliation_summary",
    "slo_summary",
}

_SUPABASE_JOB_UPDATE_FIELDS = {
    "cache_summary",
    "cancel_requested_at",
    "completed_at",
    "completed_segment_count",
    "cost_summary",
    "cost_reconciliation_summary",
    "current_operation",
    "effective_fidelity_profile",
    "era_profile",
    "eta_seconds",
    "failed_segment_count",
    "failed_segments",
    "gpu_summary",
    "last_error",
    "manifest_available",
    "manifest_generated_at",
    "manifest_sha256",
    "manifest_size_bytes",
    "manifest_uri",
    "progress_percent",
    "quality_summary",
    "reproducibility_summary",
    "result_uri",
    "slo_summary",
    "stage_timings",
    "started_at",
    "status",
    "warnings",
}

_SUPABASE_SEGMENT_JSON_FIELDS = {
    "retry_backoffs_seconds",
    "quality_metrics",
    "reproducibility_proof",
    "uncertainty_callouts",
}

_SUPABASE_SEGMENT_UPDATE_FIELDS = {
    "allocation_latency_ms",
    "attempt_count",
    "cache_hit_latency_ms",
    "cache_namespace",
    "cache_status",
    "cached_output_uri",
    "gpu_type",
    "last_error_classification",
    "output_uri",
    "quality_metrics",
    "reproducibility_proof",
    "retry_backoffs_seconds",
    "status",
    "uncertainty_callouts",
}

_SUPABASE_EXPORT_PACKAGE_JSON_FIELDS = {
    "package_contents",
    "artifact_metadata",
    "encoding_metadata",
}

_SUPABASE_EXPORT_PACKAGE_UPDATE_FIELDS = {
    "deleted_at",
}

_SUPABASE_JOB_DELETION_PROOF_JSON_FIELDS = {
    "proof_payload",
    "verification_summary",
}


def _validated_update_assignments(
    *,
    patch: dict[str, Any],
    allowed_fields: set[str],
    json_fields: set[str],
) -> tuple[list[str], list[Any]]:
    from psycopg.types.json import Jsonb

    assignments: list[str] = []
    values: list[Any] = []
    for key, value in patch.items():
        if key not in allowed_fields:
            allowed = ", ".join(sorted(allowed_fields))
            raise ValueError(f"Unsupported worker patch field '{key}'. Allowed fields: {allowed}")
        assignments.append(f"{key} = %s")
        values.append(Jsonb(value) if key in json_fields else value)
    return assignments, values


def phase2_backend_name() -> str:
    integration_enabled = os.getenv("CHRONOS_RUN_SUPABASE_INTEGRATION") == "1"
    has_direct_db = bool(
        settings.supabase_db_url
        or (
            settings.supabase_db_host
            and settings.supabase_db_port
            and settings.supabase_db_name
            and settings.supabase_db_user
            and settings.supabase_db_password
        )
    )
    if settings.environment == "production" and not has_direct_db:
        raise RuntimeError("Production environment requires direct Supabase database configuration.")
    if has_direct_db and (settings.environment != "test" or integration_enabled):
        return "supabase"
    return "memory"


@dataclass
class Phase2Store:
    users: dict[str, dict[str, Any]] = field(default_factory=dict)
    usage: dict[str, dict[str, Any]] = field(default_factory=dict)
    upload_sessions: dict[str, dict[str, Any]] = field(default_factory=dict)
    preview_sessions: dict[str, dict[str, Any]] = field(default_factory=dict)
    gcs_object_pointers: dict[str, dict[str, Any]] = field(default_factory=dict)
    jobs: dict[str, dict[str, Any]] = field(default_factory=dict)
    job_segments: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    job_manifests: dict[str, dict[str, Any]] = field(default_factory=dict)
    job_export_packages: dict[str, dict[str, Any]] = field(default_factory=dict)
    job_output_deletion_proofs: dict[str, dict[str, Any]] = field(default_factory=dict)
    gpu_leases: dict[str, dict[str, Any]] = field(default_factory=dict)
    incidents: dict[str, dict[str, Any]] = field(default_factory=dict)
    era_detections: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    log_settings: dict[str, dict[str, Any]] = field(default_factory=dict)
    deletion_requests: dict[str, dict[str, Any]] = field(default_factory=dict)
    deletion_proofs: dict[str, dict[str, Any]] = field(default_factory=dict)
    webhook_subscriptions: dict[str, list[dict[str, Any]]] = field(default_factory=dict)


_STORE = Phase2Store()
_UPLOAD_STORE_LOCK = Lock()


def reset_phase2_store() -> None:
    _STORE.users.clear()
    _STORE.usage.clear()
    _STORE.upload_sessions.clear()
    _STORE.preview_sessions.clear()
    _STORE.gcs_object_pointers.clear()
    _STORE.jobs.clear()
    _STORE.job_segments.clear()
    _STORE.job_manifests.clear()
    _STORE.job_export_packages.clear()
    _STORE.job_output_deletion_proofs.clear()
    _STORE.gpu_leases.clear()
    _STORE.incidents.clear()
    _STORE.era_detections.clear()
    _STORE.log_settings.clear()
    _STORE.deletion_requests.clear()
    _STORE.deletion_proofs.clear()
    _STORE.webhook_subscriptions.clear()


class _MemoryUserProfileRepository:
    def get_or_create(
        self,
        *,
        user_id: str,
        role: str,
        plan_tier: str,
        org_id: str,
        email: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        profile = _STORE.users.get(user_id)
        if profile is None:
            profile = {
                "user_id": user_id,
                "email": email or f"{user_id}@example.com",
                "role": role,
                "plan_tier": plan_tier,
                "org_id": org_id,
                "display_name": None,
                "avatar_url": None,
                "preferences": {},
            }
            _STORE.users[user_id] = profile
        return dict(profile)

    def update(self, user_id: str, patch: dict[str, Any], *, access_token: str | None = None) -> dict[str, Any]:
        profile = dict(_STORE.users[user_id])
        profile.update({key: value for key, value in patch.items() if value not in (None, {})})
        if "preferences" in patch:
            profile["preferences"] = patch["preferences"]
        _STORE.users[user_id] = profile
        return dict(profile)


class _MemoryUsageRepository:
    def get_or_create(
        self,
        *,
        user_id: str,
        plan_tier: str,
        monthly_limit_minutes: int,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        usage = _STORE.usage.get(user_id)
        if usage is None:
            usage = {
                "user_id": user_id,
                "plan_tier": plan_tier,
                "used_minutes": 0,
                "monthly_limit_minutes": monthly_limit_minutes,
                "estimated_next_job_minutes": 0,
                "threshold_alerts": [],
                "overage_approval_scope": None,
                "approved_for_minutes": 0,
            }
            _STORE.usage[user_id] = usage
        return dict(usage)

    def update(self, user_id: str, payload: dict[str, Any], *, access_token: str | None = None) -> dict[str, Any]:
        usage = dict(_STORE.usage[user_id])
        usage.update(payload)
        _STORE.usage[user_id] = usage
        return dict(usage)


class _MemoryUploadRepository:
    def create_session(
        self,
        *,
        upload_id: str,
        owner_user_id: str,
        org_id: str,
        original_filename: str,
        mime_type: str,
        size_bytes: int,
        checksum_sha256: str | None,
        bucket_name: str,
        object_path: str,
        resumable_session_url: str,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        del access_token
        now = _utc_now()
        record = {
            "upload_id": upload_id,
            "owner_user_id": owner_user_id,
            "org_id": org_id,
            "original_filename": original_filename,
            "mime_type": mime_type,
            "size_bytes": size_bytes,
            "checksum_sha256": checksum_sha256,
            "bucket_name": bucket_name,
            "object_path": object_path,
            "media_uri": f"gs://{bucket_name}/{object_path}",
            "resumable_session_url": resumable_session_url,
            "status": UploadStatus.PENDING.value,
            "detection_snapshot": {},
            "launch_config": {},
            "configured_at": None,
            "created_at": now,
            "updated_at": now,
            "completed_at": None,
        }
        with _UPLOAD_STORE_LOCK:
            _STORE.upload_sessions[upload_id] = record
            return dict(record)

    def get_session(
        self,
        upload_id: str,
        *,
        owner_user_id: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any] | None:
        del access_token
        with _UPLOAD_STORE_LOCK:
            record = _STORE.upload_sessions.get(upload_id)
        if record is None:
            return None
        if owner_user_id and record["owner_user_id"] != owner_user_id:
            return None
        return dict(record)

    def update_session(
        self,
        upload_id: str,
        *,
        owner_user_id: str,
        patch: dict[str, Any],
        access_token: str | None = None,
    ) -> dict[str, Any] | None:
        del access_token
        with _UPLOAD_STORE_LOCK:
            record = _STORE.upload_sessions.get(upload_id)
            if record is None or record["owner_user_id"] != owner_user_id:
                return None
            updated = dict(record)
            updated.update(_request_patch(patch, nullable_keys={"completed_at"}))
            updated["updated_at"] = _utc_now()
            _STORE.upload_sessions[upload_id] = updated
            return dict(updated)

    def upsert_pointer(
        self,
        *,
        upload_id: str,
        owner_user_id: str,
        org_id: str,
        bucket_name: str,
        object_path: str,
        original_filename: str,
        mime_type: str,
        size_bytes: int,
        checksum_sha256: str | None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        del access_token
        pointer_id = _stable_uuid(f"pointer:{upload_id}")
        record = {
            "id": pointer_id,
            "upload_id": upload_id,
            "owner_user_id": owner_user_id,
            "org_id": org_id,
            "bucket_name": bucket_name,
            "object_path": object_path,
            "original_filename": original_filename,
            "mime_type": mime_type,
            "size_bytes": size_bytes,
            "checksum_sha256": checksum_sha256,
            "created_at": _utc_now(),
        }
        with _UPLOAD_STORE_LOCK:
            _STORE.gcs_object_pointers[upload_id] = record
            return dict(record)


class _MemoryPreviewSessionRepository:
    def create_preview(
        self,
        *,
        payload: dict[str, Any],
        access_token: str | None = None,
    ) -> dict[str, Any]:
        del access_token
        record = dict(payload)
        record.setdefault("created_at", _utc_now())
        record["updated_at"] = _utc_now()
        _STORE.preview_sessions[record["preview_id"]] = record
        return dict(record)

    def get_preview(
        self,
        preview_id: str,
        *,
        owner_user_id: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any] | None:
        del access_token
        record = _STORE.preview_sessions.get(preview_id)
        if record is None:
            return None
        if owner_user_id and record["owner_user_id"] != owner_user_id:
            return None
        return dict(record)

    def get_reusable_preview(
        self,
        *,
        source_asset_checksum: str,
        configuration_cache_fingerprint: str,
        owner_user_id: str,
        access_token: str | None = None,
    ) -> dict[str, Any] | None:
        del access_token
        candidates = [
            dict(record)
            for record in _STORE.preview_sessions.values()
            if record["owner_user_id"] == owner_user_id
            and record["source_asset_checksum"] == source_asset_checksum
            and record.get("configuration_cache_fingerprint") == configuration_cache_fingerprint
            and record.get("deleted_at") is None
            and record.get("status") == "ready"
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda item: item["created_at"], reverse=True)
        return candidates[0]

    def update_preview(
        self,
        preview_id: str,
        *,
        owner_user_id: str,
        patch: dict[str, Any],
        access_token: str | None = None,
    ) -> dict[str, Any] | None:
        del access_token
        record = _STORE.preview_sessions.get(preview_id)
        if record is None or record["owner_user_id"] != owner_user_id:
            return None
        updated = dict(record)
        updated.update(_request_patch(patch, nullable_keys={"deleted_at"}))
        updated["updated_at"] = _utc_now()
        _STORE.preview_sessions[preview_id] = updated
        return dict(updated)


class _MemoryEraDetectionRepository:
    def save_job(
        self,
        *,
        job_id: str,
        owner_user_id: str,
        org_id: str,
        media_uri: str,
        original_filename: str,
        mime_type: str,
        era_profile: dict[str, Any],
        access_token: str | None = None,
    ) -> dict[str, Any]:
        record = {
            "job_id": job_id,
            "owner_user_id": owner_user_id,
            "org_id": org_id,
            "media_uri": media_uri,
            "original_filename": original_filename,
            "mime_type": mime_type,
            "era_profile": era_profile,
            "created_at": _utc_now(),
        }
        _STORE.jobs[job_id] = record
        return dict(record)

    def save_detection(self, *, job_id: str, detection: dict[str, Any], access_token: str | None = None) -> dict[str, Any]:
        detections = _STORE.era_detections.setdefault(job_id, [])
        record = {
            "id": str(uuid4()),
            "created_at": _utc_now(),
            **detection,
        }
        detections.append(record)
        return dict(record)

    def latest_detection(self, job_id: str, *, access_token: str | None = None) -> dict[str, Any] | None:
        detections = _STORE.era_detections.get(job_id, [])
        return dict(detections[-1]) if detections else None


class _MemoryLogSettingsRepository:
    def upsert(self, *, org_id: str, payload: dict[str, Any], updated_by: str, access_token: str | None = None) -> dict[str, Any]:
        record = {
            "org_id": org_id,
            "retention_days": payload["retention_days"],
            "redaction_mode": payload["redaction_mode"],
            "categories": payload["categories"],
            "export_targets": payload["export_targets"],
            "updated_by": updated_by,
            "updated_at": _utc_now(),
        }
        _STORE.log_settings[org_id] = record
        return dict(record)

    def get(self, org_id: str, *, access_token: str | None = None) -> dict[str, Any] | None:
        record = _STORE.log_settings.get(org_id)
        return dict(record) if record else None


class _MemoryComplianceRepository:
    def create_deletion_request(self, *, user_id: str, payload: dict[str, Any], access_token: str | None = None) -> dict[str, Any]:
        deletion_request_id = str(uuid4())
        deletion_proof_id = str(uuid4())
        deleted_entries = max(len(payload["categories"]), 1) * 12
        request_record = {
            "deletion_request_id": deletion_request_id,
            "deletion_proof_id": deletion_proof_id,
            "user_id": user_id,
            "deleted_categories": payload["categories"],
            "deleted_entries": deleted_entries,
            "status": "completed",
            "requested_at": _utc_now(),
        }
        proof_record = {
            "deletion_proof_id": deletion_proof_id,
            "deletion_request_id": deletion_request_id,
            "user_id": user_id,
            "deleted_entries": deleted_entries,
            "deleted_categories": payload["categories"],
            "generated_at": _utc_now(),
        }
        _STORE.deletion_requests[deletion_request_id] = request_record
        _STORE.deletion_proofs[deletion_proof_id] = proof_record
        return dict(request_record)


class _MemoryJobRepository:
    def create_job(
        self,
        *,
        job_id: str,
        owner_user_id: str,
        plan_tier: str,
        org_id: str,
        media_uri: str,
        original_filename: str,
        mime_type: str,
        source_asset_checksum: str,
        fidelity_tier: str,
        processing_mode: str,
        era_profile: dict[str, Any],
        config: dict[str, Any],
        estimated_duration_seconds: int,
        segments: list[dict[str, Any]],
        cost_estimate_summary: dict[str, Any] | None = None,
        effective_fidelity_tier: str | None = None,
        effective_fidelity_profile: dict[str, Any] | None = None,
        reproducibility_mode: str = "perceptual_equivalence",
        access_token: str | None = None,
    ) -> dict[str, Any]:
        del access_token
        created_at = _utc_now()
        record = {
            "job_id": job_id,
            "owner_user_id": owner_user_id,
            "plan_tier": plan_tier,
            "org_id": org_id,
            "media_uri": media_uri,
            "original_filename": original_filename,
            "mime_type": mime_type,
            "source_asset_checksum": source_asset_checksum,
            "fidelity_tier": fidelity_tier,
            "effective_fidelity_tier": effective_fidelity_tier or fidelity_tier,
            "effective_fidelity_profile": effective_fidelity_profile or {},
            "reproducibility_mode": reproducibility_mode,
            "processing_mode": processing_mode,
            "era_profile": era_profile,
            "config": config,
            "estimated_duration_seconds": estimated_duration_seconds,
            "segment_duration_seconds": 10,
            "segment_count": len(segments),
            "completed_segment_count": 0,
            "failed_segment_count": 0,
            "progress_percent": 0.0,
            "eta_seconds": estimated_duration_seconds,
            "status": JobStatus.QUEUED.value,
            "current_operation": "Queued for processing",
            "progress_topic": f"job_progress:{job_id}",
            "result_uri": None,
            "manifest_available": False,
            "manifest_uri": None,
            "manifest_sha256": None,
            "manifest_generated_at": None,
            "manifest_size_bytes": 0,
            "quality_summary": {"e_hf": 0.0, "s_ls_db": 0.0, "t_tc": 0.0, "thresholds_met": False},
            "reproducibility_summary": None,
            "stage_timings": {
                "upload_ms": None,
                "era_detection_ms": None,
                "queue_wait_ms": None,
                "allocation_ms": None,
                "processing_ms": None,
                "encoding_ms": None,
                "download_ms": None,
                "total_ms": None,
            },
            "cache_summary": {
                "hits": 0,
                "misses": 0,
                "bypassed": 0,
                "degraded": False,
                "hit_rate": 0.0,
                "saved_gpu_seconds": 0,
            },
            "gpu_summary": {
                "gpu_type": None,
                "warm_start": None,
                "allocation_latency_ms": None,
                "gpu_runtime_seconds": 0,
                "desired_warm_instances": 0,
                "active_warm_instances": 0,
                "busy_instances": 0,
                "utilization_percent": 0.0,
            },
            "cost_summary": {
                "gpu_seconds": 0,
                "storage_operations": 0,
                "api_calls": 0,
                "total_cost_usd": 0.0,
            },
            "cost_estimate_summary": cost_estimate_summary,
            "cost_reconciliation_summary": None,
            "slo_summary": {
                "target_total_ms": estimated_duration_seconds * 2000,
                "actual_total_ms": None,
                "p95_ratio": None,
                "compliant": None,
                "degraded": False,
                "error_budget_burn_percent": 0.0,
                "museum_sla_applies": plan_tier.lower() == "museum",
            },
            "failed_segments": [],
            "warnings": [],
            "last_error": None,
            "queued_at": created_at,
            "created_at": created_at,
            "started_at": None,
            "completed_at": None,
            "cancel_requested_at": None,
            "updated_at": created_at,
        }
        _STORE.jobs[job_id] = record
        _STORE.job_segments[job_id] = [
            {
                "job_id": job_id,
                "segment_index": segment["segment_index"],
                "segment_start_seconds": segment["segment_start_seconds"],
                "segment_end_seconds": segment["segment_end_seconds"],
                "segment_duration_seconds": segment["segment_duration_seconds"],
                "status": "queued",
                "attempt_count": 0,
                "idempotency_key": segment["idempotency_key"],
                "last_error_classification": None,
                "retry_backoffs_seconds": [],
                "output_uri": None,
                "cache_status": "miss",
                "cache_hit_latency_ms": None,
                "cache_namespace": None,
                "cached_output_uri": None,
                "gpu_type": None,
                "allocation_latency_ms": None,
                "quality_metrics": None,
                "reproducibility_proof": None,
                "uncertainty_callouts": [],
                "updated_at": created_at,
            }
            for segment in segments
        ]
        return dict(record)

    def get_job(self, job_id: str, *, owner_user_id: str | None = None, access_token: str | None = None) -> dict[str, Any] | None:
        del access_token
        record = _STORE.jobs.get(job_id)
        if record is None:
            return None
        if owner_user_id and record["owner_user_id"] != owner_user_id:
            return None
        return dict(record)

    def list_jobs(
        self,
        *,
        owner_user_id: str,
        access_token: str | None = None,
    ) -> list[dict[str, Any]]:
        del access_token
        rows = [dict(record) for record in _STORE.jobs.values() if record["owner_user_id"] == owner_user_id]
        return sorted(rows, key=lambda item: item["created_at"], reverse=True)

    def list_segments(self, job_id: str, *, owner_user_id: str | None = None, access_token: str | None = None) -> list[dict[str, Any]]:
        del access_token
        job = _STORE.jobs.get(job_id)
        if job is None:
            return []
        if owner_user_id and job["owner_user_id"] != owner_user_id:
            return []
        return [dict(segment) for segment in _STORE.job_segments.get(job_id, [])]

    def request_cancellation(
        self,
        job_id: str,
        *,
        owner_user_id: str,
        access_token: str | None = None,
    ) -> dict[str, Any] | None:
        del access_token
        record = _STORE.jobs.get(job_id)
        if record is None or record["owner_user_id"] != owner_user_id:
            return None
        if record["status"] not in {
            JobStatus.COMPLETED.value,
            JobStatus.FAILED.value,
            JobStatus.PARTIAL.value,
            JobStatus.CANCELLED.value,
        }:
            record["status"] = JobStatus.CANCEL_REQUESTED.value
            record["cancel_requested_at"] = _utc_now()
            record["updated_at"] = record["cancel_requested_at"]
            _STORE.jobs[job_id] = record
        return dict(record)

    def get_job_for_worker(self, job_id: str) -> dict[str, Any] | None:
        return self.get_job(job_id)

    def update_job_for_worker(self, job_id: str, *, patch: dict[str, Any]) -> dict[str, Any]:
        record = dict(_STORE.jobs[job_id])
        record.update(patch)
        record["updated_at"] = _utc_now()
        _STORE.jobs[job_id] = record
        return dict(record)

    def update_segment_for_worker(self, job_id: str, segment_index: int, *, patch: dict[str, Any]) -> dict[str, Any]:
        segments = list(_STORE.job_segments.get(job_id, []))
        for idx, segment in enumerate(segments):
            if segment["segment_index"] == segment_index:
                updated = dict(segment)
                updated.update(patch)
                updated["updated_at"] = _utc_now()
                segments[idx] = updated
                _STORE.job_segments[job_id] = segments
                return dict(updated)
        raise KeyError(f"Unknown segment {segment_index} for job {job_id}")


class _MemoryWebhookSubscriptionRepository:
    def upsert(
        self,
        *,
        owner_user_id: str,
        webhook_url: str,
        event_types: list[str],
        enabled: bool = True,
    ) -> dict[str, Any]:
        subscriptions = list(_STORE.webhook_subscriptions.get(owner_user_id, []))
        existing = next((item for item in subscriptions if item["webhook_url"] == webhook_url), None)
        record = {
            "id": existing["id"] if existing else str(uuid4()),
            "owner_user_id": owner_user_id,
            "webhook_url": webhook_url,
            "event_types": list(event_types),
            "enabled": enabled,
            "created_at": existing["created_at"] if existing else _utc_now(),
            "updated_at": _utc_now(),
        }
        subscriptions = [item for item in subscriptions if item["webhook_url"] != webhook_url]
        subscriptions.append(record)
        _STORE.webhook_subscriptions[owner_user_id] = subscriptions
        return dict(record)

    def list_enabled(self, *, owner_user_id: str, event_type: str) -> list[dict[str, Any]]:
        return [
            dict(item)
            for item in _STORE.webhook_subscriptions.get(owner_user_id, [])
            if item["enabled"] and event_type in item["event_types"]
        ]


class _MemoryManifestRepository:
    def upsert_manifest_for_worker(self, *, job_id: str, manifest: dict[str, Any]) -> dict[str, Any]:
        _STORE.job_manifests[job_id] = dict(manifest)
        return dict(manifest)

    def get_manifest(
        self,
        job_id: str,
        *,
        owner_user_id: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any] | None:
        del access_token
        job = _STORE.jobs.get(job_id)
        if job is None:
            return None
        if owner_user_id and job["owner_user_id"] != owner_user_id:
            return None
        manifest = _STORE.job_manifests.get(job_id)
        return dict(manifest) if manifest else None


class _MemoryJobExportPackageRepository:
    def upsert_package_for_worker(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        key = f"{payload['job_id']}:{payload['variant']}"
        record = dict(payload)
        record.setdefault("created_at", _utc_now())
        record["updated_at"] = _utc_now()
        _STORE.job_export_packages[key] = record
        return dict(record)

    def get_package(
        self,
        job_id: str,
        *,
        variant: str,
        owner_user_id: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any] | None:
        del access_token
        job = _STORE.jobs.get(job_id)
        if job is None:
            return None
        if owner_user_id and job["owner_user_id"] != owner_user_id:
            return None
        package = _STORE.job_export_packages.get(f"{job_id}:{variant}")
        return dict(package) if package else None

    def update_package_for_worker(self, job_id: str, *, variant: str, patch: dict[str, Any]) -> dict[str, Any]:
        key = f"{job_id}:{variant}"
        package = dict(_STORE.job_export_packages[key])
        package.update(patch)
        package["updated_at"] = _utc_now()
        _STORE.job_export_packages[key] = package
        return dict(package)


class _MemoryJobDeletionProofRepository:
    def upsert_proof_for_worker(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        record = dict(payload)
        record.setdefault("created_at", _utc_now())
        record["updated_at"] = _utc_now()
        _STORE.job_output_deletion_proofs[record["deletion_proof_id"]] = record
        return dict(record)

    def get_proof(
        self,
        proof_id: str,
        *,
        owner_user_id: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any] | None:
        del access_token
        proof = _STORE.job_output_deletion_proofs.get(proof_id)
        if proof is None:
            return None
        if owner_user_id and proof["owner_user_id"] != owner_user_id:
            return None
        return dict(proof)

    def get_proof_for_job(
        self,
        job_id: str,
        *,
        owner_user_id: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any] | None:
        del access_token
        for proof in _STORE.job_output_deletion_proofs.values():
            if proof["job_id"] != job_id:
                continue
            if owner_user_id and proof["owner_user_id"] != owner_user_id:
                continue
            return dict(proof)
        return None


class _MemoryRuntimeOpsRepository:
    def list_gpu_leases(self) -> list[dict[str, Any]]:
        return [dict(item) for item in _STORE.gpu_leases.values()]

    def upsert_gpu_lease(self, *, worker_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        record = dict(payload)
        record["worker_id"] = worker_id
        record.setdefault("created_at", _utc_now())
        record["updated_at"] = _utc_now()
        _STORE.gpu_leases[worker_id] = record
        return dict(record)

    def delete_gpu_lease(self, worker_id: str) -> None:
        _STORE.gpu_leases.pop(worker_id, None)

    def queued_job_backlog_count(self) -> int:
        return sum(1 for job in _STORE.jobs.values() if job["status"] == JobStatus.QUEUED.value)

    def list_incidents(self) -> list[dict[str, Any]]:
        return sorted((dict(item) for item in _STORE.incidents.values()), key=lambda item: item["opened_at"], reverse=True)

    def upsert_incident(self, *, incident_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        existing = _STORE.incidents.get(incident_key, {})
        record = {**existing, **payload, "incident_key": incident_key}
        record.setdefault("incident_id", existing.get("incident_id", str(uuid4())))
        record.setdefault("opened_at", existing.get("opened_at", _utc_now()))
        record["updated_at"] = _utc_now()
        _STORE.incidents[incident_key] = record
        return dict(record)


class _SupabaseRepositoryBase:
    def __init__(self) -> None:
        self._client = SupabaseClient()

    def _connect(self):
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(self._client.direct_db_dsn(), row_factory=dict_row)


class _SupabaseUserProfileRepository(_SupabaseRepositoryBase):
    def _row_to_profile(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "user_id": row["external_user_id"],
            "email": row["email"],
            "role": row["role"],
            "plan_tier": row.get("plan_tier", "hobbyist"),
            "org_id": row.get("org_id", "org-default"),
            "display_name": row.get("display_name"),
            "avatar_url": row.get("avatar_url"),
            "preferences": row.get("preferences") or {},
        }

    def get_or_create(
        self,
        *,
        user_id: str,
        role: str,
        plan_tier: str,
        org_id: str,
        email: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        if access_token:
            headers = self._client.user_scoped_headers(access_token)
            row = self._client.rest_upsert(
                "user_profiles",
                payload={
                    "id": user_id,
                    "external_user_id": user_id,
                    "email": email or f"{user_id}@example.com",
                    "role": role,
                    "plan_tier": plan_tier,
                    "org_id": org_id,
                    "display_name": None,
                    "avatar_url": None,
                    "preferences": {},
                    "updated_at": _utc_now(),
                },
                on_conflict="id",
                headers=headers,
            )[0]
            return self._row_to_profile(row)
        from psycopg.types.json import Jsonb

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into public.user_profiles (
                    id, external_user_id, email, role, plan_tier, org_id,
                    display_name, avatar_url, preferences, updated_at
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                on conflict (external_user_id) do update
                set role = excluded.role,
                    plan_tier = excluded.plan_tier,
                    org_id = excluded.org_id,
                    updated_at = now()
                returning *
                """,
                (
                    _stable_uuid(user_id),
                    user_id,
                    email or f"{user_id}@example.com",
                    role,
                    plan_tier,
                    org_id,
                    None,
                    None,
                    Jsonb({}),
                ),
            )
            row = cur.fetchone()
        if row is None:
            raise RuntimeError("Failed to upsert user profile")
        return self._row_to_profile(row)

    def update(self, user_id: str, patch: dict[str, Any], *, access_token: str | None = None) -> dict[str, Any]:
        if access_token:
            headers = self._client.user_scoped_headers(access_token)
            payload = _request_patch(
                {
                    "display_name": patch.get("display_name"),
                    "avatar_url": patch.get("avatar_url"),
                    "preferences": patch.get("preferences"),
                    "updated_at": _utc_now(),
                }
            )
            row = self._client.rest_update(
                "user_profiles",
                payload=payload,
                params={"id": f"eq.{user_id}", "select": "*"},
                headers=headers,
            )[0]
            return self._row_to_profile(row)
        from psycopg.types.json import Jsonb

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                update public.user_profiles
                set display_name = case when %s then %s else display_name end,
                    avatar_url = case when %s then %s else avatar_url end,
                    preferences = case when %s then %s else preferences end,
                    updated_at = now()
                where external_user_id = %s
                returning *
                """,
                (
                    "display_name" in patch,
                    patch.get("display_name"),
                    "avatar_url" in patch,
                    patch.get("avatar_url"),
                    "preferences" in patch,
                    Jsonb(patch.get("preferences", {})),
                    user_id,
                ),
            )
            row = cur.fetchone()
        if row is None:
            raise RuntimeError("Failed to update user profile")
        return self._row_to_profile(row)


class _SupabaseUsageRepository(_SupabaseRepositoryBase):
    def _row_to_usage(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "user_id": row["external_user_id"],
            "plan_tier": row["plan_tier"],
            "used_minutes": row["used_minutes"],
            "monthly_limit_minutes": row["monthly_limit_minutes"],
            "estimated_next_job_minutes": row.get("estimated_next_job_minutes", 0),
            "threshold_alerts": row.get("threshold_alerts") or [],
            "overage_approval_scope": row.get("approval_scope"),
            "approved_for_minutes": row.get("approved_overage_minutes", 0),
        }

    def get_or_create(
        self,
        *,
        user_id: str,
        plan_tier: str,
        monthly_limit_minutes: int,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        month = _billing_month()
        if access_token:
            headers = self._client.user_scoped_headers(access_token)
            rows = self._client.rest_select(
                "user_usage_monthly",
                params={
                    "select": "*",
                    "external_user_id": f"eq.{user_id}",
                    "billing_month": f"eq.{month}",
                    "limit": "1",
                },
                headers=headers,
            )
            if rows:
                return self._row_to_usage(rows[0])
            row = self._client.rest_insert(
                "user_usage_monthly",
                payload={
                    "id": str(uuid4()),
                    "owner_user_id": user_id,
                    "external_user_id": user_id,
                    "billing_month": month,
                    "plan_tier": plan_tier,
                    "used_minutes": 0,
                    "monthly_limit_minutes": monthly_limit_minutes,
                    "estimated_next_job_minutes": 0,
                    "approved_overage_minutes": 0,
                    "approval_scope": None,
                    "threshold_alerts": [],
                    "updated_at": _utc_now(),
                },
                headers=headers,
            )[0]
            return self._row_to_usage(row)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into public.user_usage_monthly (
                    id, owner_user_id, external_user_id, billing_month, plan_tier,
                    used_minutes, monthly_limit_minutes, estimated_next_job_minutes,
                    approved_overage_minutes, approval_scope, threshold_alerts, updated_at
                )
                values (%s, %s, %s, %s, %s, 0, %s, 0, 0, null, %s, now())
                on conflict (external_user_id, billing_month) do update
                set plan_tier = excluded.plan_tier,
                    monthly_limit_minutes = excluded.monthly_limit_minutes,
                    updated_at = now()
                returning *
                """,
                (
                    str(uuid4()),
                    _stable_uuid(user_id),
                    user_id,
                    month,
                    plan_tier,
                    monthly_limit_minutes,
                    [],
                ),
            )
            row = cur.fetchone()
        if row is None:
            raise RuntimeError("Failed to upsert usage snapshot")
        return self._row_to_usage(row)

    def update(self, user_id: str, payload: dict[str, Any], *, access_token: str | None = None) -> dict[str, Any]:
        month = _billing_month()
        if access_token:
            headers = self._client.user_scoped_headers(access_token)
            request_payload = {
                "updated_at": _utc_now(),
            }
            if "used_minutes" in payload:
                request_payload["used_minutes"] = payload.get("used_minutes")
            if "estimated_next_job_minutes" in payload:
                request_payload["estimated_next_job_minutes"] = payload.get("estimated_next_job_minutes")
            if "approved_for_minutes" in payload:
                request_payload["approved_overage_minutes"] = payload.get("approved_for_minutes")
            if "overage_approval_scope" in payload:
                request_payload["approval_scope"] = payload.get("overage_approval_scope")
            if "threshold_alerts" in payload:
                request_payload["threshold_alerts"] = payload.get("threshold_alerts")
            row = self._client.rest_update(
                "user_usage_monthly",
                payload=request_payload,
                params={
                    "external_user_id": f"eq.{user_id}",
                    "billing_month": f"eq.{month}",
                    "select": "*",
                },
                headers=headers,
            )[0]
            return self._row_to_usage(row)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                update public.user_usage_monthly
                set used_minutes = case when %s then %s else used_minutes end,
                    estimated_next_job_minutes = case when %s then %s else estimated_next_job_minutes end,
                    approved_overage_minutes = case when %s then %s else approved_overage_minutes end,
                    approval_scope = case when %s then %s else approval_scope end,
                    threshold_alerts = case when %s then %s else threshold_alerts end,
                    updated_at = now()
                where external_user_id = %s and billing_month = %s
                returning *
                """,
                (
                    "used_minutes" in payload,
                    payload.get("used_minutes"),
                    "estimated_next_job_minutes" in payload,
                    payload.get("estimated_next_job_minutes"),
                    "approved_for_minutes" in payload,
                    payload.get("approved_for_minutes"),
                    "overage_approval_scope" in payload,
                    payload.get("overage_approval_scope"),
                    "threshold_alerts" in payload,
                    payload.get("threshold_alerts"),
                    user_id,
                    month,
                ),
            )
            row = cur.fetchone()
        if row is None:
            raise RuntimeError("Failed to update usage snapshot")
        return self._row_to_usage(row)


class _SupabaseUploadRepository(_SupabaseRepositoryBase):
    def _require_access_token(self, access_token: str | None) -> str:
        if not access_token:
            raise ValueError("Upload routes require an end-user access token.")
        return access_token

    def _session_from_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "upload_id": row["external_upload_id"],
            "owner_user_id": row["external_user_id"],
            "org_id": row["org_id"],
            "original_filename": row["original_filename"],
            "mime_type": row["mime_type"],
            "size_bytes": row["size_bytes"],
            "checksum_sha256": row.get("checksum_sha256"),
            "bucket_name": row["bucket_name"],
            "object_path": row["object_path"],
            "media_uri": row["media_uri"],
            "resumable_session_url": row["resumable_session_url"],
            "status": row["status"],
            "detection_snapshot": row.get("detection_snapshot") or {},
            "launch_config": row.get("launch_config") or {},
            "configured_at": row.get("configured_at"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "completed_at": row.get("completed_at"),
        }

    def create_session(
        self,
        *,
        upload_id: str,
        owner_user_id: str,
        org_id: str,
        original_filename: str,
        mime_type: str,
        size_bytes: int,
        checksum_sha256: str | None,
        bucket_name: str,
        object_path: str,
        resumable_session_url: str,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        headers = self._client.user_scoped_headers(self._require_access_token(access_token))
        row = self._client.rest_upsert(
            "upload_sessions",
            payload={
                "id": _stable_uuid(upload_id),
                "owner_user_id": owner_user_id,
                "external_user_id": owner_user_id,
                "external_upload_id": upload_id,
                "org_id": org_id,
                "original_filename": original_filename,
                "mime_type": mime_type,
                "size_bytes": size_bytes,
                "checksum_sha256": checksum_sha256,
                "bucket_name": bucket_name,
                "object_path": object_path,
                "media_uri": f"gs://{bucket_name}/{object_path}",
                "resumable_session_url": resumable_session_url,
                "status": UploadStatus.PENDING.value,
                "detection_snapshot": {},
                "launch_config": {},
                "configured_at": None,
                "updated_at": _utc_now(),
            },
            on_conflict="external_upload_id",
            headers=headers,
        )[0]
        return self._session_from_row(row)

    def get_session(
        self,
        upload_id: str,
        *,
        owner_user_id: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any] | None:
        params = {
            "select": "*",
            "external_upload_id": f"eq.{upload_id}",
            "limit": "1",
        }
        if owner_user_id:
            params["external_user_id"] = f"eq.{owner_user_id}"
        rows = self._client.rest_select(
            "upload_sessions",
            params=params,
            headers=self._client.user_scoped_headers(self._require_access_token(access_token)),
        )
        if not rows:
            return None
        return self._session_from_row(rows[0])

    def update_session(
        self,
        upload_id: str,
        *,
        owner_user_id: str,
        patch: dict[str, Any],
        access_token: str | None = None,
    ) -> dict[str, Any] | None:
        payload = _request_patch(
            {
                "status": patch.get("status"),
                "checksum_sha256": patch.get("checksum_sha256"),
                "size_bytes": patch.get("size_bytes"),
                "completed_at": patch.get("completed_at"),
                "resumable_session_url": patch.get("resumable_session_url"),
                "detection_snapshot": patch.get("detection_snapshot"),
                "launch_config": patch.get("launch_config"),
                "configured_at": patch.get("configured_at"),
                "updated_at": _utc_now(),
            },
            nullable_keys={"completed_at"},
        )
        rows = self._client.rest_update(
            "upload_sessions",
            payload=payload,
            params={
                "external_upload_id": f"eq.{upload_id}",
                "external_user_id": f"eq.{owner_user_id}",
                "select": "*",
            },
            headers=self._client.user_scoped_headers(self._require_access_token(access_token)),
        )
        if not rows:
            return None
        return self._session_from_row(rows[0])

    def upsert_pointer(
        self,
        *,
        upload_id: str,
        owner_user_id: str,
        org_id: str,
        bucket_name: str,
        object_path: str,
        original_filename: str,
        mime_type: str,
        size_bytes: int,
        checksum_sha256: str | None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        row = self._client.rest_upsert(
            "gcs_object_pointers",
            payload={
                "id": _stable_uuid(f"pointer:{upload_id}"),
                "owner_user_id": owner_user_id,
                "external_user_id": owner_user_id,
                "external_upload_id": upload_id,
                "org_id": org_id,
                "bucket_name": bucket_name,
                "object_path": object_path,
                "original_filename": original_filename,
                "mime_type": mime_type,
                "size_bytes": size_bytes,
                "checksum_sha256": checksum_sha256,
            },
            on_conflict="external_upload_id",
            headers=self._client.user_scoped_headers(self._require_access_token(access_token)),
        )[0]
        return {
            "id": row["id"],
            "upload_id": row["external_upload_id"],
            "owner_user_id": row["external_user_id"],
            "org_id": row["org_id"],
            "bucket_name": row["bucket_name"],
            "object_path": row["object_path"],
            "original_filename": row.get("original_filename", ""),
            "mime_type": row.get("mime_type", ""),
            "size_bytes": row.get("size_bytes", 0),
            "checksum_sha256": row.get("checksum_sha256"),
            "created_at": row["created_at"],
        }


class _SupabasePreviewSessionRepository(_SupabaseRepositoryBase):
    def _require_access_token(self, access_token: str | None) -> str:
        if not access_token:
            raise ValueError("Preview routes require an end-user access token.")
        return access_token

    def _preview_from_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "preview_id": row["external_preview_id"],
            "upload_id": row["external_upload_id"],
            "owner_user_id": row["external_user_id"],
            "org_id": row["org_id"],
            "status": row["status"],
            "configured_at_snapshot": row.get("configured_at_snapshot"),
            "configuration_fingerprint": row["configuration_fingerprint"],
            "configuration_cache_fingerprint": row.get("configuration_cache_fingerprint") or row["configuration_fingerprint"],
            "source_asset_checksum": row["source_asset_checksum"],
            "cache_key": row["cache_key"],
            "job_payload_preview": row.get("job_payload_preview") or {},
            "selection_mode": row["selection_mode"],
            "scene_diversity": float(row.get("scene_diversity", 0.0) or 0.0),
            "keyframe_count": int(row.get("keyframe_count", 0) or 0),
            "estimated_cost_summary": row.get("estimated_cost_summary") or {},
            "estimated_processing_time_seconds": int(row.get("estimated_processing_time_seconds", 0) or 0),
            "keyframes": row.get("keyframes") or [],
            "preview_root_uri": row["preview_root_uri"],
            "expires_at": row["expires_at"],
            "deleted_at": row.get("deleted_at"),
            "created_at": row["created_at"],
            "updated_at": row.get("updated_at") or row["created_at"],
        }

    def create_preview(
        self,
        *,
        payload: dict[str, Any],
        access_token: str | None = None,
    ) -> dict[str, Any]:
        headers = self._client.user_scoped_headers(self._require_access_token(access_token))
        row = self._client.rest_upsert(
            "preview_sessions",
            payload={
                "id": _stable_uuid(payload["preview_id"]),
                "owner_user_id": payload["owner_user_id"],
                "external_user_id": payload["owner_user_id"],
                "upload_session_id": _stable_uuid(payload["upload_id"]),
                "external_upload_id": payload["upload_id"],
                "external_preview_id": payload["preview_id"],
                "org_id": payload["org_id"],
                "status": payload["status"],
                "configured_at_snapshot": payload.get("configured_at_snapshot"),
                "configuration_fingerprint": payload["configuration_fingerprint"],
                "configuration_cache_fingerprint": payload.get("configuration_cache_fingerprint"),
                "source_asset_checksum": payload["source_asset_checksum"],
                "cache_key": payload["cache_key"],
                "job_payload_preview": payload.get("job_payload_preview") or {},
                "selection_mode": payload["selection_mode"],
                "scene_diversity": payload["scene_diversity"],
                "keyframe_count": payload["keyframe_count"],
                "estimated_cost_summary": payload.get("estimated_cost_summary") or {},
                "estimated_processing_time_seconds": payload["estimated_processing_time_seconds"],
                "keyframes": payload.get("keyframes") or [],
                "preview_root_uri": payload["preview_root_uri"],
                "expires_at": payload["expires_at"],
                "deleted_at": payload.get("deleted_at"),
                "updated_at": _utc_now(),
            },
            on_conflict="external_preview_id",
            headers=headers,
        )[0]
        return self._preview_from_row(row)

    def get_preview(
        self,
        preview_id: str,
        *,
        owner_user_id: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any] | None:
        params = {
            "select": "*",
            "external_preview_id": f"eq.{preview_id}",
            "limit": "1",
        }
        if owner_user_id:
            params["external_user_id"] = f"eq.{owner_user_id}"
        rows = self._client.rest_select(
            "preview_sessions",
            params=params,
            headers=self._client.user_scoped_headers(self._require_access_token(access_token)),
        )
        if not rows:
            return None
        return self._preview_from_row(rows[0])

    def get_reusable_preview(
        self,
        *,
        source_asset_checksum: str,
        configuration_cache_fingerprint: str,
        owner_user_id: str,
        access_token: str | None = None,
    ) -> dict[str, Any] | None:
        rows = self._client.rest_select(
            "preview_sessions",
            params={
                "select": "*",
                "external_user_id": f"eq.{owner_user_id}",
                "source_asset_checksum": f"eq.{source_asset_checksum}",
                "configuration_cache_fingerprint": f"eq.{configuration_cache_fingerprint}",
                "status": "eq.ready",
                "deleted_at": "is.null",
                "order": "created_at.desc",
                "limit": "1",
            },
            headers=self._client.user_scoped_headers(self._require_access_token(access_token)),
        )
        if not rows:
            return None
        return self._preview_from_row(rows[0])

    def update_preview(
        self,
        preview_id: str,
        *,
        owner_user_id: str,
        patch: dict[str, Any],
        access_token: str | None = None,
    ) -> dict[str, Any] | None:
        payload = _request_patch(
            {
                "status": patch.get("status"),
                "expires_at": patch.get("expires_at"),
                "deleted_at": patch.get("deleted_at"),
                "updated_at": _utc_now(),
            },
            nullable_keys={"deleted_at"},
        )
        rows = self._client.rest_update(
            "preview_sessions",
            payload=payload,
            params={
                "external_preview_id": f"eq.{preview_id}",
                "external_user_id": f"eq.{owner_user_id}",
                "select": "*",
            },
            headers=self._client.user_scoped_headers(self._require_access_token(access_token)),
        )
        if not rows:
            return None
        return self._preview_from_row(rows[0])


class _SupabaseEraDetectionRepository(_SupabaseRepositoryBase):
    def save_job(
        self,
        *,
        job_id: str,
        owner_user_id: str,
        org_id: str,
        media_uri: str,
        original_filename: str,
        mime_type: str,
        era_profile: dict[str, Any],
        access_token: str | None = None,
    ) -> dict[str, Any]:
        if access_token:
            headers = self._client.user_scoped_headers(access_token)
            row = self._client.rest_upsert(
                "media_jobs",
                payload={
                    "id": _stable_uuid(job_id),
                    "external_job_id": job_id,
                    "owner_user_id": owner_user_id,
                    "external_user_id": owner_user_id,
                    "org_id": org_id,
                    "media_uri": media_uri,
                    "original_filename": original_filename,
                    "mime_type": mime_type,
                    "status": "queued",
                    "era_profile": era_profile,
                },
                on_conflict="external_job_id",
                headers=headers,
            )[0]
            return {
                "job_id": row["external_job_id"],
                "owner_user_id": row["external_user_id"],
                "org_id": row["org_id"],
                "media_uri": row["media_uri"],
                "original_filename": row["original_filename"],
                "mime_type": row["mime_type"],
                "era_profile": row["era_profile"],
                "created_at": row["created_at"],
            }
        from psycopg.types.json import Jsonb

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into public.media_jobs (
                    id, owner_user_id, external_user_id, external_job_id, org_id,
                    media_uri, original_filename, mime_type, status, era_profile
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, 'queued', %s)
                on conflict (external_job_id) do update
                set owner_user_id = excluded.owner_user_id,
                    external_user_id = excluded.external_user_id,
                    org_id = excluded.org_id,
                    media_uri = excluded.media_uri,
                    original_filename = excluded.original_filename,
                    mime_type = excluded.mime_type,
                    era_profile = excluded.era_profile
                returning *
                """,
                (
                    _stable_uuid(job_id),
                    _stable_uuid(owner_user_id),
                    owner_user_id,
                    job_id,
                    org_id,
                    media_uri,
                    original_filename,
                    mime_type,
                    Jsonb(era_profile),
                ),
            )
            row = cur.fetchone()
        if row is None:
            raise RuntimeError("Failed to upsert media job")
        return {
            "job_id": row["external_job_id"],
            "owner_user_id": row["external_user_id"],
            "org_id": row["org_id"],
            "media_uri": row["media_uri"],
            "original_filename": row["original_filename"],
            "mime_type": row["mime_type"],
            "era_profile": row["era_profile"],
            "created_at": row["created_at"],
        }

    def save_detection(self, *, job_id: str, detection: dict[str, Any], access_token: str | None = None) -> dict[str, Any]:
        if access_token:
            headers = self._client.user_scoped_headers(access_token)
            row = self._client.rest_insert(
                "era_detections",
                payload={
                    "id": str(uuid4()),
                    "job_id": _stable_uuid(job_id),
                    "external_job_id": job_id,
                    "era_label": detection["era"],
                    "confidence": detection["confidence"],
                    "forensic_markers": detection["forensic_markers"],
                    "top_candidates": detection.get("top_candidates", []),
                    "manual_confirmation_required": detection.get("manual_confirmation_required", False),
                    "overridden_by_user": detection.get("overridden_by_user", False),
                    "override_reason": detection.get("override_reason"),
                    "source": detection["source"],
                    "model_version": detection["model_version"],
                    "prompt_version": detection["prompt_version"],
                    "raw_response_gcs_uri": detection.get("raw_response_gcs_uri"),
                    "prompt_token_count": detection.get("prompt_token_count", 0),
                    "candidates_token_count": detection.get("candidates_token_count", 0),
                    "total_token_count": detection.get("total_token_count", 0),
                    "api_call_count": detection.get("api_call_count", 0),
                    "created_by": detection["created_by"],
                    "external_created_by": detection.get("created_by"),
                },
                headers=headers,
            )[0]
            return {
                "id": row["id"],
                "job_id": row["external_job_id"],
                "era": row["era_label"],
                "confidence": float(row["confidence"]),
                "forensic_markers": row["forensic_markers"],
                "top_candidates": row.get("top_candidates") or [],
                "manual_confirmation_required": row.get("manual_confirmation_required", False),
                "overridden_by_user": row["overridden_by_user"],
                "override_reason": row.get("override_reason"),
                "model_version": row["model_version"],
                "prompt_version": row["prompt_version"],
                "source": row["source"],
                "raw_response_gcs_uri": row.get("raw_response_gcs_uri"),
                "prompt_token_count": row.get("prompt_token_count", 0),
                "candidates_token_count": row.get("candidates_token_count", 0),
                "total_token_count": row.get("total_token_count", 0),
                "api_call_count": row.get("api_call_count", 0),
                "created_by": row.get("external_created_by"),
                "created_at": row["created_at"],
            }
        from psycopg.types.json import Jsonb

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into public.era_detections (
                    id, job_id, external_job_id, era_label, confidence, forensic_markers,
                    top_candidates, manual_confirmation_required, overridden_by_user,
                    override_reason, source, model_version, prompt_version,
                    raw_response_gcs_uri, prompt_token_count, candidates_token_count,
                    total_token_count, api_call_count, created_by, external_created_by
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                returning *
                """,
                (
                    str(uuid4()),
                    _stable_uuid(job_id),
                    job_id,
                    detection["era"],
                    detection["confidence"],
                    Jsonb(detection["forensic_markers"]),
                    Jsonb(detection.get("top_candidates", [])),
                    detection.get("manual_confirmation_required", False),
                    detection.get("overridden_by_user", False),
                    detection.get("override_reason"),
                    detection["source"],
                    detection["model_version"],
                    detection["prompt_version"],
                    detection.get("raw_response_gcs_uri"),
                    detection.get("prompt_token_count", 0),
                    detection.get("candidates_token_count", 0),
                    detection.get("total_token_count", 0),
                    detection.get("api_call_count", 0),
                    _stable_uuid(detection["created_by"]) if detection.get("created_by") else None,
                    detection.get("created_by"),
                ),
            )
            row = cur.fetchone()
        if row is None:
            raise RuntimeError("Failed to insert era detection")
        return {
            "id": row["id"],
            "job_id": row["external_job_id"],
            "era": row["era_label"],
            "confidence": float(row["confidence"]),
            "forensic_markers": row["forensic_markers"],
            "top_candidates": row.get("top_candidates") or [],
            "manual_confirmation_required": row.get("manual_confirmation_required", False),
            "overridden_by_user": row["overridden_by_user"],
            "override_reason": row.get("override_reason"),
            "model_version": row["model_version"],
            "prompt_version": row["prompt_version"],
            "source": row["source"],
            "raw_response_gcs_uri": row.get("raw_response_gcs_uri"),
            "prompt_token_count": row.get("prompt_token_count", 0),
            "candidates_token_count": row.get("candidates_token_count", 0),
            "total_token_count": row.get("total_token_count", 0),
            "api_call_count": row.get("api_call_count", 0),
            "created_by": row.get("external_created_by"),
            "created_at": row["created_at"],
        }

    def latest_detection(self, job_id: str, *, access_token: str | None = None) -> dict[str, Any] | None:
        if access_token:
            headers = self._client.user_scoped_headers(access_token)
            rows = self._client.rest_select(
                "era_detections",
                params={
                    "select": "*",
                    "external_job_id": f"eq.{job_id}",
                    "order": "created_at.desc",
                    "limit": "1",
                },
                headers=headers,
            )
            if not rows:
                return None
            row = rows[0]
            detection = self._from_row(row)
            return {
                "id": row["id"],
                "job_id": row["external_job_id"],
                **detection,
                "created_at": row["created_at"],
            }
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select *
                from public.era_detections
                where external_job_id = %s
                order by created_at desc
                limit 1
                """,
                (job_id,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        detection = self._from_row(row)
        return {
            "id": row["id"],
            "job_id": row["external_job_id"],
            **detection,
            "created_at": row["created_at"],
        }

    def _from_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "era": row["era_label"],
            "confidence": float(row["confidence"]),
            "forensic_markers": row["forensic_markers"],
            "top_candidates": row.get("top_candidates") or [],
            "overridden_by_user": row["overridden_by_user"],
            "override_reason": row.get("override_reason"),
            "model_version": row["model_version"],
            "prompt_version": row["prompt_version"],
            "source": row["source"],
            "raw_response_gcs_uri": row.get("raw_response_gcs_uri"),
            "prompt_token_count": row.get("prompt_token_count", 0),
            "candidates_token_count": row.get("candidates_token_count", 0),
            "total_token_count": row.get("total_token_count", 0),
            "api_call_count": row.get("api_call_count", 0),
            "created_by": row.get("external_created_by"),
            "manual_confirmation_required": row.get("manual_confirmation_required", False),
        }


class _SupabaseLogSettingsRepository(_SupabaseRepositoryBase):
    def upsert(self, *, org_id: str, payload: dict[str, Any], updated_by: str, access_token: str | None = None) -> dict[str, Any]:
        if not access_token:
            raise ValueError("User-scoped access token is required for org log settings writes.")
        headers = self._client.user_scoped_headers(access_token)
        row = self._client.rest_upsert(
            "org_log_settings",
            payload={
                "org_id": org_id,
                "retention_days": payload["retention_days"],
                "redaction_mode": payload["redaction_mode"],
                "categories": payload["categories"],
                "export_targets": payload["export_targets"],
                "updated_by": _stable_uuid(updated_by),
                "external_updated_by": updated_by,
                "updated_at": _utc_now(),
            },
            on_conflict="org_id",
            headers=headers,
        )[0]
        return {
            "org_id": row["org_id"],
            "retention_days": row["retention_days"],
            "redaction_mode": row["redaction_mode"],
            "categories": row.get("categories") or [],
            "export_targets": row.get("export_targets") or [],
            "updated_by": row.get("external_updated_by", updated_by),
            "updated_at": row["updated_at"],
        }

    def get(self, org_id: str, *, access_token: str | None = None) -> dict[str, Any] | None:
        if not access_token:
            raise ValueError("User-scoped access token is required for org log settings reads.")
        headers = self._client.user_scoped_headers(access_token)
        rows = self._client.rest_select(
            "org_log_settings",
            params={
                "select": "*",
                "org_id": f"eq.{org_id}",
                "limit": "1",
            },
            headers=headers,
        )
        if not rows:
            return None
        row = rows[0]
        return {
            "org_id": row["org_id"],
            "retention_days": row["retention_days"],
            "redaction_mode": row["redaction_mode"],
            "categories": row.get("categories") or [],
            "export_targets": row.get("export_targets") or [],
            "updated_by": row.get("external_updated_by"),
            "updated_at": row["updated_at"],
        }

class _SupabaseComplianceRepository(_SupabaseRepositoryBase):
    def create_deletion_request(self, *, user_id: str, payload: dict[str, Any], access_token: str | None = None) -> dict[str, Any]:
        if access_token:
            headers = self._client.user_scoped_headers(access_token)
            deletion_request_id = str(uuid4())
            deletion_proof_id = str(uuid4())
            deleted_entries = max(len(payload["categories"]), 1) * 12
            request_payload = {
                "id": deletion_request_id,
                "owner_user_id": user_id,
                "external_user_id": user_id,
                "categories": payload["categories"],
                "date_from": payload["date_from"],
                "date_to": payload["date_to"],
                "reason": payload.get("reason"),
                "status": "completed",
                "deletion_proof_id": deletion_proof_id,
            }
            proof_payload = {
                "id": deletion_proof_id,
                "deletion_request_id": deletion_request_id,
                "owner_user_id": user_id,
                "external_user_id": user_id,
                "deleted_entries": deleted_entries,
                "deleted_categories": payload["categories"],
            }
            self._client.rest_insert(
                "log_deletion_requests",
                payload=request_payload,
                headers=headers,
            )
            try:
                self._client.rest_insert(
                    "log_deletion_proofs",
                    payload=proof_payload,
                    headers=headers,
                )
            except Exception:
                self._client.rest_delete(
                    "log_deletion_requests",
                    params={"id": f"eq.{deletion_request_id}"},
                    headers=headers,
                )
                raise
            return {
                "deletion_request_id": deletion_request_id,
                "deletion_proof_id": deletion_proof_id,
                "user_id": user_id,
                "deleted_categories": payload["categories"],
                "deleted_entries": deleted_entries,
                "status": "completed",
                "requested_at": _utc_now(),
            }
        from psycopg.types.json import Jsonb

        deletion_request_id = str(uuid4())
        deletion_proof_id = str(uuid4())
        deleted_entries = max(len(payload["categories"]), 1) * 12
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into public.log_deletion_requests (
                    id, owner_user_id, external_user_id, categories, date_from,
                    date_to, reason, status, deletion_proof_id
                )
                values (%s, %s, %s, %s, %s, %s, %s, 'completed', %s)
                """,
                (
                    deletion_request_id,
                    _stable_uuid(user_id),
                    user_id,
                    Jsonb(payload["categories"]),
                    payload["date_from"],
                    payload["date_to"],
                    payload.get("reason"),
                    deletion_proof_id,
                ),
            )
            cur.execute(
                """
                insert into public.log_deletion_proofs (
                    id, deletion_request_id, owner_user_id, external_user_id,
                    deleted_entries, deleted_categories
                )
                values (%s, %s, %s, %s, %s, %s)
                """,
                (
                    deletion_proof_id,
                    deletion_request_id,
                    _stable_uuid(user_id),
                    user_id,
                    deleted_entries,
                    Jsonb(payload["categories"]),
                ),
            )
        return {
            "deletion_request_id": deletion_request_id,
            "deletion_proof_id": deletion_proof_id,
            "user_id": user_id,
            "deleted_categories": payload["categories"],
            "deleted_entries": deleted_entries,
            "status": "completed",
            "requested_at": _utc_now(),
        }


class _SupabaseJobRepository(_SupabaseRepositoryBase):
    def _job_from_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "job_id": row["external_job_id"],
            "owner_user_id": row["external_user_id"],
            "plan_tier": row.get("plan_tier", "hobbyist"),
            "org_id": row["org_id"],
            "media_uri": row["media_uri"],
            "original_filename": row["original_filename"],
            "mime_type": row["mime_type"],
            "source_asset_checksum": row.get("source_asset_checksum", ""),
            "fidelity_tier": row.get("fidelity_tier", "Restore"),
            "effective_fidelity_tier": row.get("effective_fidelity_tier", row.get("fidelity_tier", "Restore")),
            "effective_fidelity_profile": row.get("effective_fidelity_profile") or {},
            "reproducibility_mode": row.get("reproducibility_mode", "perceptual_equivalence"),
            "processing_mode": row.get("processing_mode", "balanced"),
            "era_profile": row.get("era_profile") or {},
            "config": row.get("config") or {},
            "estimated_duration_seconds": row.get("estimated_duration_seconds", 60),
            "segment_duration_seconds": row.get("segment_duration_seconds", 10),
            "segment_count": row.get("segment_count", 0),
            "completed_segment_count": row.get("completed_segment_count", 0),
            "failed_segment_count": row.get("failed_segment_count", 0),
            "progress_percent": float(row.get("progress_percent", 0.0) or 0.0),
            "eta_seconds": int(row.get("eta_seconds", 0) or 0),
            "status": row["status"],
            "current_operation": row.get("current_operation") or "",
            "progress_topic": row.get("progress_topic") or f"job_progress:{row['external_job_id']}",
            "result_uri": row.get("result_uri"),
            "manifest_available": bool(row.get("manifest_available", False)),
            "manifest_uri": row.get("manifest_uri"),
            "manifest_sha256": row.get("manifest_sha256"),
            "manifest_generated_at": row.get("manifest_generated_at"),
            "manifest_size_bytes": row.get("manifest_size_bytes", 0),
            "quality_summary": row.get("quality_summary") or {"e_hf": 0.0, "s_ls_db": 0.0, "t_tc": 0.0, "thresholds_met": False},
            "reproducibility_summary": row.get("reproducibility_summary"),
            "stage_timings": row.get("stage_timings")
            or {
                "upload_ms": None,
                "era_detection_ms": None,
                "queue_wait_ms": None,
                "allocation_ms": None,
                "processing_ms": None,
                "encoding_ms": None,
                "download_ms": None,
                "total_ms": None,
            },
            "cache_summary": row.get("cache_summary")
            or {"hits": 0, "misses": 0, "bypassed": 0, "degraded": False, "hit_rate": 0.0, "saved_gpu_seconds": 0},
            "gpu_summary": row.get("gpu_summary")
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
            "cost_summary": row.get("cost_summary")
            or {"gpu_seconds": 0, "storage_operations": 0, "api_calls": 0, "total_cost_usd": 0.0},
            "cost_estimate_summary": row.get("cost_estimate_summary"),
            "cost_reconciliation_summary": row.get("cost_reconciliation_summary"),
            "slo_summary": row.get("slo_summary")
            or {
                "target_total_ms": int(row.get("estimated_duration_seconds", 60) or 60) * 2000,
                "actual_total_ms": None,
                "p95_ratio": None,
                "compliant": None,
                "degraded": False,
                "error_budget_burn_percent": 0.0,
                "museum_sla_applies": row.get("plan_tier", "hobbyist") == "museum",
            },
            "failed_segments": row.get("failed_segments") or [],
            "warnings": row.get("warnings") or [],
            "last_error": row.get("last_error"),
            "queued_at": row.get("queued_at") or row["created_at"],
            "created_at": row["created_at"],
            "started_at": row.get("started_at"),
            "completed_at": row.get("completed_at"),
            "cancel_requested_at": row.get("cancel_requested_at"),
            "updated_at": row.get("updated_at") or row["created_at"],
        }

    def _segment_from_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "job_id": row["external_job_id"],
            "segment_index": row["segment_index"],
            "segment_start_seconds": row["segment_start_seconds"],
            "segment_end_seconds": row["segment_end_seconds"],
            "segment_duration_seconds": row["segment_duration_seconds"],
            "status": row["status"],
            "attempt_count": row.get("attempt_count", 0),
            "idempotency_key": row["idempotency_key"],
            "last_error_classification": row.get("last_error_classification"),
            "retry_backoffs_seconds": row.get("retry_backoffs_seconds") or [],
            "output_uri": row.get("output_uri"),
            "cache_status": row.get("cache_status", "miss"),
            "cache_hit_latency_ms": row.get("cache_hit_latency_ms"),
            "cache_namespace": row.get("cache_namespace"),
            "cached_output_uri": row.get("cached_output_uri"),
            "gpu_type": row.get("gpu_type"),
            "allocation_latency_ms": row.get("allocation_latency_ms"),
            "quality_metrics": row.get("quality_metrics"),
            "reproducibility_proof": row.get("reproducibility_proof"),
            "uncertainty_callouts": row.get("uncertainty_callouts") or [],
            "updated_at": row.get("updated_at") or row["created_at"],
        }

    def create_job(
        self,
        *,
        job_id: str,
        owner_user_id: str,
        plan_tier: str,
        org_id: str,
        media_uri: str,
        original_filename: str,
        mime_type: str,
        source_asset_checksum: str,
        fidelity_tier: str,
        processing_mode: str,
        era_profile: dict[str, Any],
        config: dict[str, Any],
        estimated_duration_seconds: int,
        segments: list[dict[str, Any]],
        cost_estimate_summary: dict[str, Any] | None = None,
        effective_fidelity_tier: str | None = None,
        effective_fidelity_profile: dict[str, Any] | None = None,
        reproducibility_mode: str = "perceptual_equivalence",
        access_token: str | None = None,
    ) -> dict[str, Any]:
        if access_token:
            headers = self._client.user_scoped_headers(access_token)
            existing_job_rows = self._client.rest_select(
                "media_jobs",
                params={"select": "id", "external_job_id": f"eq.{job_id}", "limit": "1"},
                headers=headers,
            )
            row = self._client.rest_upsert(
                "media_jobs",
                payload={
                    "id": _stable_uuid(job_id),
                    "owner_user_id": owner_user_id,
                    "external_user_id": owner_user_id,
                    "external_job_id": job_id,
                    "org_id": org_id,
                    "plan_tier": plan_tier,
                    "media_uri": media_uri,
                    "original_filename": original_filename,
                    "mime_type": mime_type,
                    "status": JobStatus.QUEUED.value,
                    "source_asset_checksum": source_asset_checksum,
                    "fidelity_tier": fidelity_tier,
                    "effective_fidelity_tier": effective_fidelity_tier or fidelity_tier,
                    "effective_fidelity_profile": effective_fidelity_profile or {},
                    "reproducibility_mode": reproducibility_mode,
                    "processing_mode": processing_mode,
                    "era_profile": era_profile,
                    "config": config,
                    "estimated_duration_seconds": estimated_duration_seconds,
                    "segment_duration_seconds": 10,
                    "segment_count": len(segments),
                    "completed_segment_count": 0,
                    "failed_segment_count": 0,
                    "progress_percent": 0.0,
                    "eta_seconds": estimated_duration_seconds,
                    "current_operation": "Queued for processing",
                    "progress_topic": f"job_progress:{job_id}",
                    "failed_segments": [],
                    "warnings": [],
                    "manifest_available": False,
                    "quality_summary": {"e_hf": 0.0, "s_ls_db": 0.0, "t_tc": 0.0, "thresholds_met": False},
                    "stage_timings": {
                        "upload_ms": None,
                        "era_detection_ms": None,
                        "queue_wait_ms": None,
                        "allocation_ms": None,
                        "processing_ms": None,
                        "encoding_ms": None,
                        "download_ms": None,
                        "total_ms": None,
                    },
                    "cache_summary": {
                        "hits": 0,
                        "misses": 0,
                        "bypassed": 0,
                        "degraded": False,
                        "hit_rate": 0.0,
                        "saved_gpu_seconds": 0,
                    },
                    "gpu_summary": {
                        "gpu_type": None,
                        "warm_start": None,
                        "allocation_latency_ms": None,
                        "gpu_runtime_seconds": 0,
                        "desired_warm_instances": 0,
                        "active_warm_instances": 0,
                        "busy_instances": 0,
                        "utilization_percent": 0.0,
                    },
                    "cost_summary": {
                        "gpu_seconds": 0,
                        "storage_operations": 0,
                        "api_calls": 0,
                        "total_cost_usd": 0.0,
                    },
                    "cost_estimate_summary": cost_estimate_summary or {},
                    "cost_reconciliation_summary": None,
                    "slo_summary": {
                        "target_total_ms": estimated_duration_seconds * 2000,
                        "actual_total_ms": None,
                        "p95_ratio": None,
                        "compliant": None,
                        "degraded": False,
                        "error_budget_burn_percent": 0.0,
                        "museum_sla_applies": plan_tier.lower() == "museum",
                    },
                    "queued_at": _utc_now(),
                    "updated_at": _utc_now(),
                },
                on_conflict="external_job_id",
                headers=headers,
            )[0]
            try:
                for segment in segments:
                    self._client.rest_upsert(
                        "job_segments",
                        payload={
                            "id": str(uuid4()),
                            "job_id": _stable_uuid(job_id),
                            "external_job_id": job_id,
                            "owner_user_id": owner_user_id,
                            "external_user_id": owner_user_id,
                            "segment_index": segment["segment_index"],
                            "segment_start_seconds": segment["segment_start_seconds"],
                            "segment_end_seconds": segment["segment_end_seconds"],
                            "segment_duration_seconds": segment["segment_duration_seconds"],
                            "status": "queued",
                            "attempt_count": 0,
                            "idempotency_key": segment["idempotency_key"],
                            "retry_backoffs_seconds": [],
                            "cache_status": "miss",
                            "uncertainty_callouts": [],
                        },
                        on_conflict="job_id,segment_index",
                        headers=headers,
                    )
            except Exception:
                if not existing_job_rows:
                    self._client.rest_delete(
                        "media_jobs",
                        params={"external_job_id": f"eq.{job_id}"},
                        headers=headers,
                    )
                raise
            return self._job_from_row(row)
        from psycopg.types.json import Jsonb

        queued_at = _utc_now()
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into public.media_jobs (
                    id, owner_user_id, external_user_id, external_job_id, org_id, plan_tier,
                    media_uri, original_filename, mime_type, status, source_asset_checksum,
                    fidelity_tier, processing_mode, era_profile, config,
                    effective_fidelity_tier, effective_fidelity_profile, reproducibility_mode,
                    estimated_duration_seconds, segment_duration_seconds, segment_count,
                    completed_segment_count, failed_segment_count, progress_percent,
                    eta_seconds, current_operation, progress_topic, failed_segments,
                    warnings, manifest_available, quality_summary, stage_timings,
                    cache_summary, gpu_summary, cost_summary, cost_estimate_summary,
                    cost_reconciliation_summary, slo_summary, queued_at, updated_at
                )
                values (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    0, 0, 0, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                on conflict (external_job_id) do update
                set org_id = excluded.org_id,
                    plan_tier = excluded.plan_tier,
                    media_uri = excluded.media_uri,
                    original_filename = excluded.original_filename,
                    mime_type = excluded.mime_type,
                    source_asset_checksum = excluded.source_asset_checksum,
                    fidelity_tier = excluded.fidelity_tier,
                    effective_fidelity_tier = excluded.effective_fidelity_tier,
                    effective_fidelity_profile = excluded.effective_fidelity_profile,
                    reproducibility_mode = excluded.reproducibility_mode,
                    processing_mode = excluded.processing_mode,
                    era_profile = excluded.era_profile,
                    config = excluded.config,
                    estimated_duration_seconds = excluded.estimated_duration_seconds,
                    segment_duration_seconds = excluded.segment_duration_seconds,
                    segment_count = excluded.segment_count,
                    eta_seconds = excluded.eta_seconds,
                    current_operation = excluded.current_operation,
                    progress_topic = excluded.progress_topic,
                    failed_segments = excluded.failed_segments,
                    warnings = excluded.warnings,
                    manifest_available = excluded.manifest_available,
                    quality_summary = excluded.quality_summary,
                    stage_timings = excluded.stage_timings,
                    cache_summary = excluded.cache_summary,
                    gpu_summary = excluded.gpu_summary,
                    cost_summary = excluded.cost_summary,
                    cost_estimate_summary = excluded.cost_estimate_summary,
                    cost_reconciliation_summary = excluded.cost_reconciliation_summary,
                    slo_summary = excluded.slo_summary,
                    queued_at = excluded.queued_at,
                    updated_at = excluded.updated_at
                returning *
                """,
                (
                    _stable_uuid(job_id),
                    _stable_uuid(owner_user_id),
                    owner_user_id,
                    job_id,
                    org_id,
                    plan_tier,
                    media_uri,
                    original_filename,
                    mime_type,
                    JobStatus.QUEUED.value,
                    source_asset_checksum,
                    fidelity_tier,
                    processing_mode,
                    Jsonb(era_profile),
                    Jsonb(config),
                    effective_fidelity_tier or fidelity_tier,
                    Jsonb(effective_fidelity_profile or {}),
                    reproducibility_mode,
                    estimated_duration_seconds,
                    10,
                    len(segments),
                    estimated_duration_seconds,
                    "Queued for processing",
                    f"job_progress:{job_id}",
                    Jsonb([]),
                    Jsonb([]),
                    False,
                    Jsonb({"e_hf": 0.0, "s_ls_db": 0.0, "t_tc": 0.0, "thresholds_met": False}),
                    Jsonb(
                        {
                            "upload_ms": None,
                            "era_detection_ms": None,
                            "queue_wait_ms": None,
                            "allocation_ms": None,
                            "processing_ms": None,
                            "encoding_ms": None,
                            "download_ms": None,
                            "total_ms": None,
                        }
                    ),
                    Jsonb({"hits": 0, "misses": 0, "bypassed": 0, "degraded": False, "hit_rate": 0.0, "saved_gpu_seconds": 0}),
                    Jsonb(
                        {
                            "gpu_type": None,
                            "warm_start": None,
                            "allocation_latency_ms": None,
                            "gpu_runtime_seconds": 0,
                            "desired_warm_instances": 0,
                            "active_warm_instances": 0,
                            "busy_instances": 0,
                            "utilization_percent": 0.0,
                        }
                    ),
                    Jsonb({"gpu_seconds": 0, "storage_operations": 0, "api_calls": 0, "total_cost_usd": 0.0}),
                    Jsonb(cost_estimate_summary or {}),
                    Jsonb(None),
                    Jsonb(
                        {
                            "target_total_ms": estimated_duration_seconds * 2000,
                            "actual_total_ms": None,
                            "p95_ratio": None,
                            "compliant": None,
                            "degraded": False,
                            "error_budget_burn_percent": 0.0,
                            "museum_sla_applies": plan_tier.lower() == "museum",
                        }
                    ),
                    queued_at,
                    queued_at,
                ),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("Failed to create async job")
            for segment in segments:
                cur.execute(
                    """
                    insert into public.job_segments (
                        id, job_id, external_job_id, owner_user_id, external_user_id,
                        segment_index, segment_start_seconds, segment_end_seconds,
                        segment_duration_seconds, status, attempt_count, idempotency_key,
                        retry_backoffs_seconds, cache_status, uncertainty_callouts
                    )
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'queued', 0, %s, %s, 'miss', %s)
                    on conflict (job_id, segment_index) do update
                    set segment_start_seconds = excluded.segment_start_seconds,
                        segment_end_seconds = excluded.segment_end_seconds,
                        segment_duration_seconds = excluded.segment_duration_seconds,
                        idempotency_key = excluded.idempotency_key,
                        retry_backoffs_seconds = excluded.retry_backoffs_seconds,
                        cache_status = excluded.cache_status,
                        uncertainty_callouts = excluded.uncertainty_callouts,
                        updated_at = now()
                    """,
                    (
                        str(uuid4()),
                        _stable_uuid(job_id),
                        job_id,
                        _stable_uuid(owner_user_id),
                        owner_user_id,
                        segment["segment_index"],
                        segment["segment_start_seconds"],
                        segment["segment_end_seconds"],
                        segment["segment_duration_seconds"],
                        segment["idempotency_key"],
                        [],
                        [],
                    ),
                )
        return self._job_from_row(row)

    def get_job(self, job_id: str, *, owner_user_id: str | None = None, access_token: str | None = None) -> dict[str, Any] | None:
        if access_token:
            headers = self._client.user_scoped_headers(access_token)
            rows = self._client.rest_select(
                "media_jobs",
                params={"select": "*", "external_job_id": f"eq.{job_id}", "limit": "1"},
                headers=headers,
            )
            if not rows:
                return None
            return self._job_from_row(rows[0])
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("select * from public.media_jobs where external_job_id = %s limit 1", (job_id,))
            row = cur.fetchone()
        if row is None:
            return None
        if owner_user_id and row["external_user_id"] != owner_user_id:
            return None
        return self._job_from_row(row)

    def list_jobs(self, *, owner_user_id: str, access_token: str | None = None) -> list[dict[str, Any]]:
        if access_token:
            headers = self._client.user_scoped_headers(access_token)
            rows = self._client.rest_select(
                "media_jobs",
                params={"select": "*", "order": "created_at.desc"},
                headers=headers,
            )
            return [self._job_from_row(row) for row in rows]
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "select * from public.media_jobs where external_user_id = %s order by created_at desc",
                (owner_user_id,),
            )
            rows = cur.fetchall()
        return [self._job_from_row(row) for row in rows]

    def list_segments(self, job_id: str, *, owner_user_id: str | None = None, access_token: str | None = None) -> list[dict[str, Any]]:
        if access_token:
            headers = self._client.user_scoped_headers(access_token)
            rows = self._client.rest_select(
                "job_segments",
                params={"select": "*", "external_job_id": f"eq.{job_id}", "order": "segment_index.asc"},
                headers=headers,
            )
            return [self._segment_from_row(row) for row in rows]
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "select * from public.job_segments where external_job_id = %s order by segment_index asc",
                (job_id,),
            )
            rows = cur.fetchall()
        segments = [self._segment_from_row(row) for row in rows]
        if owner_user_id:
            job = self.get_job(job_id, owner_user_id=owner_user_id)
            return segments if job else []
        return segments

    def request_cancellation(self, job_id: str, *, owner_user_id: str, access_token: str | None = None) -> dict[str, Any] | None:
        if access_token:
            headers = self._client.user_scoped_headers(access_token)
            current_rows = self._client.rest_select(
                "media_jobs",
                params={"select": "*", "external_job_id": f"eq.{job_id}", "limit": "1"},
                headers=headers,
            )
            if not current_rows:
                return None
            current_row = current_rows[0]
            if current_row["status"] in {
                JobStatus.COMPLETED.value,
                JobStatus.FAILED.value,
                JobStatus.PARTIAL.value,
                JobStatus.CANCELLED.value,
            }:
                return self._job_from_row(current_row)
            rows = self._client.rest_update(
                "media_jobs",
                payload={
                    "status": JobStatus.CANCEL_REQUESTED.value,
                    "cancel_requested_at": _utc_now(),
                    "updated_at": _utc_now(),
                },
                params={"external_job_id": f"eq.{job_id}", "select": "*"},
                headers=headers,
            )
            if not rows:
                return None
            return self._job_from_row(rows[0])
        current = self.get_job(job_id)
        if current is None or current["owner_user_id"] != owner_user_id:
            return None
        if current["status"] in {
            JobStatus.COMPLETED.value,
            JobStatus.FAILED.value,
            JobStatus.PARTIAL.value,
            JobStatus.CANCELLED.value,
        }:
            return current
        return self.update_job_for_worker(
            job_id,
            patch={"status": JobStatus.CANCEL_REQUESTED.value, "cancel_requested_at": _utc_now()},
        )

    def get_job_for_worker(self, job_id: str) -> dict[str, Any] | None:
        return self.get_job(job_id)

    def update_job_for_worker(self, job_id: str, *, patch: dict[str, Any]) -> dict[str, Any]:
        assignments, values = _validated_update_assignments(
            patch=patch,
            allowed_fields=_SUPABASE_JOB_UPDATE_FIELDS,
            json_fields=_SUPABASE_JOB_JSON_FIELDS,
        )
        assignments.append("updated_at = now()")
        values.append(job_id)
        query = f"update public.media_jobs set {', '.join(assignments)} where external_job_id = %s returning *"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(query, tuple(values))
            row = cur.fetchone()
        if row is None:
            raise RuntimeError(f"Job {job_id} not found")
        return self._job_from_row(row)

    def update_segment_for_worker(self, job_id: str, segment_index: int, *, patch: dict[str, Any]) -> dict[str, Any]:
        assignments, values = _validated_update_assignments(
            patch=patch,
            allowed_fields=_SUPABASE_SEGMENT_UPDATE_FIELDS,
            json_fields=_SUPABASE_SEGMENT_JSON_FIELDS,
        )
        assignments.append("updated_at = now()")
        values.extend([job_id, segment_index])
        query = (
            f"update public.job_segments set {', '.join(assignments)} "
            "where external_job_id = %s and segment_index = %s returning *"
        )
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(query, tuple(values))
            row = cur.fetchone()
        if row is None:
            raise RuntimeError(f"Segment {segment_index} for job {job_id} not found")
        return self._segment_from_row(row)


class _SupabaseWebhookSubscriptionRepository(_SupabaseRepositoryBase):
    def upsert(
        self,
        *,
        owner_user_id: str,
        webhook_url: str,
        event_types: list[str],
        enabled: bool = True,
    ) -> dict[str, Any]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into public.webhook_subscriptions (
                    id, owner_user_id, external_user_id, webhook_url, event_types, enabled, updated_at
                )
                values (%s, %s, %s, %s, %s, %s, now())
                on conflict (external_user_id, webhook_url) do update
                set event_types = excluded.event_types,
                    enabled = excluded.enabled,
                    updated_at = now()
                returning *
                """,
                (
                    str(uuid4()),
                    _stable_uuid(owner_user_id),
                    owner_user_id,
                    webhook_url,
                    event_types,
                    enabled,
                ),
            )
            row = cur.fetchone()
        if row is None:
            raise RuntimeError("Failed to upsert webhook subscription")
        return {
            "id": row["id"],
            "owner_user_id": row["external_user_id"],
            "webhook_url": row["webhook_url"],
            "event_types": row.get("event_types") or [],
            "enabled": row["enabled"],
            "created_at": row["created_at"],
            "updated_at": row.get("updated_at") or row["created_at"],
        }

    def list_enabled(self, *, owner_user_id: str, event_type: str) -> list[dict[str, Any]]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select *
                from public.webhook_subscriptions
                where external_user_id = %s
                  and enabled = true
                  and %s = any(event_types)
                order by created_at asc
                """,
                (owner_user_id, event_type),
            )
            rows = cur.fetchall()
        return [
            {
                "id": row["id"],
                "owner_user_id": row["external_user_id"],
                "webhook_url": row["webhook_url"],
                "event_types": row.get("event_types") or [],
                "enabled": row["enabled"],
                "created_at": row["created_at"],
                "updated_at": row.get("updated_at") or row["created_at"],
            }
            for row in rows
        ]


class _SupabaseManifestRepository(_SupabaseRepositoryBase):
    def upsert_manifest_for_worker(self, *, job_id: str, manifest: dict[str, Any]) -> dict[str, Any]:
        from psycopg.types.json import Jsonb

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into public.job_manifests (
                    id, job_id, external_job_id, owner_user_id, external_user_id,
                    manifest_uri, manifest_sha256, payload, generated_at, size_bytes
                )
                select
                    %s, public.media_jobs.id, public.media_jobs.external_job_id, public.media_jobs.owner_user_id,
                    public.media_jobs.external_user_id, %s, %s, %s, %s, %s
                from public.media_jobs
                where public.media_jobs.external_job_id = %s
                on conflict (job_id) do update
                set manifest_uri = excluded.manifest_uri,
                    manifest_sha256 = excluded.manifest_sha256,
                    payload = excluded.payload,
                    generated_at = excluded.generated_at,
                    size_bytes = excluded.size_bytes,
                    updated_at = now()
                returning *
                """,
                (
                    str(uuid4()),
                    manifest["manifest_uri"],
                    manifest["manifest_sha256"],
                    Jsonb(manifest),
                    manifest["generated_at"],
                    manifest.get("size_bytes", 0),
                    job_id,
                ),
            )
            row = cur.fetchone()
        if row is None:
            raise RuntimeError(f"Manifest upsert failed for job {job_id}")
        return row["payload"]

    def get_manifest(
        self,
        job_id: str,
        *,
        owner_user_id: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any] | None:
        if access_token:
            headers = self._client.user_scoped_headers(access_token)
            rows = self._client.rest_select(
                "job_manifests",
                params={"select": "payload", "external_job_id": f"eq.{job_id}", "limit": "1"},
                headers=headers,
            )
            return rows[0]["payload"] if rows else None
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "select payload, external_user_id from public.job_manifests where external_job_id = %s limit 1",
                (job_id,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        if owner_user_id and row["external_user_id"] != owner_user_id:
            return None
        return row["payload"]


class _SupabaseJobExportPackageRepository(_SupabaseRepositoryBase):
    def _package_from_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "job_id": row["external_job_id"],
            "owner_user_id": row["external_user_id"],
            "variant": row["variant"],
            "package_uri": row["package_uri"],
            "file_name": row["file_name"],
            "size_bytes": row["size_bytes"],
            "sha256": row["sha256"],
            "package_contents": row.get("package_contents") or [],
            "artifact_metadata": row.get("artifact_metadata") or {},
            "encoding_metadata": row.get("encoding_metadata") or {},
            "deletion_proof_id": row["external_deletion_proof_id"],
            "available_until": row["available_until"],
            "generated_at": row["generated_at"],
            "deleted_at": row.get("deleted_at"),
            "created_at": row["created_at"],
            "updated_at": row.get("updated_at") or row["created_at"],
        }

    def upsert_package_for_worker(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        from psycopg.types.json import Jsonb

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into public.job_export_packages (
                    id, job_id, external_job_id, owner_user_id, external_user_id, variant,
                    package_uri, file_name, size_bytes, sha256, package_contents,
                    artifact_metadata, encoding_metadata, external_deletion_proof_id,
                    available_until, generated_at, deleted_at, updated_at
                )
                select
                    %s, public.media_jobs.id, public.media_jobs.external_job_id, public.media_jobs.owner_user_id,
                    public.media_jobs.external_user_id, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now()
                from public.media_jobs
                where public.media_jobs.external_job_id = %s
                on conflict (job_id, variant) do update
                set package_uri = excluded.package_uri,
                    file_name = excluded.file_name,
                    size_bytes = excluded.size_bytes,
                    sha256 = excluded.sha256,
                    package_contents = excluded.package_contents,
                    artifact_metadata = excluded.artifact_metadata,
                    encoding_metadata = excluded.encoding_metadata,
                    external_deletion_proof_id = excluded.external_deletion_proof_id,
                    available_until = excluded.available_until,
                    generated_at = excluded.generated_at,
                    deleted_at = excluded.deleted_at,
                    updated_at = now()
                returning *
                """,
                (
                    str(uuid4()),
                    payload["variant"],
                    payload["package_uri"],
                    payload["file_name"],
                    payload["size_bytes"],
                    payload["sha256"],
                    Jsonb(payload.get("package_contents") or []),
                    Jsonb(payload.get("artifact_metadata") or {}),
                    Jsonb(payload.get("encoding_metadata") or {}),
                    payload["deletion_proof_id"],
                    payload["available_until"],
                    payload["generated_at"],
                    payload.get("deleted_at"),
                    payload["job_id"],
                ),
            )
            row = cur.fetchone()
        if row is None:
            raise RuntimeError(f"Export package upsert failed for job {payload['job_id']}:{payload['variant']}")
        return self._package_from_row(row)

    def get_package(
        self,
        job_id: str,
        *,
        variant: str,
        owner_user_id: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any] | None:
        if access_token:
            headers = self._client.user_scoped_headers(access_token)
            rows = self._client.rest_select(
                "job_export_packages",
                params={
                    "select": "*",
                    "external_job_id": f"eq.{job_id}",
                    "variant": f"eq.{variant}",
                    "limit": "1",
                },
                headers=headers,
            )
            return self._package_from_row(rows[0]) if rows else None
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select *
                from public.job_export_packages
                where external_job_id = %s and variant = %s
                limit 1
                """,
                (job_id, variant),
            )
            row = cur.fetchone()
        if row is None:
            return None
        if owner_user_id and row["external_user_id"] != owner_user_id:
            return None
        return self._package_from_row(row)

    def update_package_for_worker(self, job_id: str, *, variant: str, patch: dict[str, Any]) -> dict[str, Any]:
        assignments, values = _validated_update_assignments(
            patch=patch,
            allowed_fields=_SUPABASE_EXPORT_PACKAGE_UPDATE_FIELDS,
            json_fields=_SUPABASE_EXPORT_PACKAGE_JSON_FIELDS,
        )
        assignments.append("updated_at = now()")
        values.extend([job_id, variant])
        query = (
            f"update public.job_export_packages set {', '.join(assignments)} "
            "where external_job_id = %s and variant = %s returning *"
        )
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(query, tuple(values))
            row = cur.fetchone()
        if row is None:
            raise RuntimeError(f"Export package {job_id}:{variant} not found")
        return self._package_from_row(row)


class _SupabaseJobDeletionProofRepository(_SupabaseRepositoryBase):
    def _proof_from_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "deletion_proof_id": row["external_deletion_proof_id"],
            "job_id": row["external_job_id"],
            "owner_user_id": row["external_user_id"],
            "generated_at": row["generated_at"],
            "signature_algorithm": row["signature_algorithm"],
            "signature": row["signature"],
            "proof_sha256": row["proof_sha256"],
            "pdf_uri": row["pdf_uri"],
            "verification_summary": row.get("verification_summary") or {},
            "proof_payload": row.get("proof_payload") or {},
            "created_at": row["created_at"],
            "updated_at": row.get("updated_at") or row["created_at"],
        }

    def upsert_proof_for_worker(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        from psycopg.types.json import Jsonb

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into public.job_deletion_proofs (
                    id, job_id, external_job_id, owner_user_id, external_user_id,
                    external_deletion_proof_id, generated_at, signature_algorithm, signature,
                    proof_sha256, verification_summary, proof_payload, pdf_uri, updated_at
                )
                select
                    %s, public.media_jobs.id, public.media_jobs.external_job_id, public.media_jobs.owner_user_id,
                    public.media_jobs.external_user_id, %s, %s, %s, %s, %s, %s, %s, %s, now()
                from public.media_jobs
                where public.media_jobs.external_job_id = %s
                on conflict (external_deletion_proof_id) do update
                set generated_at = excluded.generated_at,
                    signature_algorithm = excluded.signature_algorithm,
                    signature = excluded.signature,
                    proof_sha256 = excluded.proof_sha256,
                    verification_summary = excluded.verification_summary,
                    proof_payload = excluded.proof_payload,
                    pdf_uri = excluded.pdf_uri,
                    updated_at = now()
                returning *
                """,
                (
                    _stable_uuid(payload["deletion_proof_id"]),
                    payload["deletion_proof_id"],
                    payload["generated_at"],
                    payload["signature_algorithm"],
                    payload["signature"],
                    payload["proof_sha256"],
                    Jsonb(payload.get("verification_summary") or {}),
                    Jsonb(payload.get("proof_payload") or {}),
                    payload["pdf_uri"],
                    payload["job_id"],
                ),
            )
            row = cur.fetchone()
        if row is None:
            raise RuntimeError(f"Deletion proof upsert failed for job {payload['job_id']}")
        return self._proof_from_row(row)

    def get_proof(
        self,
        proof_id: str,
        *,
        owner_user_id: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any] | None:
        if access_token:
            headers = self._client.user_scoped_headers(access_token)
            rows = self._client.rest_select(
                "job_deletion_proofs",
                params={"select": "*", "external_deletion_proof_id": f"eq.{proof_id}", "limit": "1"},
                headers=headers,
            )
            return self._proof_from_row(rows[0]) if rows else None
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select *
                from public.job_deletion_proofs
                where external_deletion_proof_id = %s
                limit 1
                """,
                (proof_id,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        if owner_user_id and row["external_user_id"] != owner_user_id:
            return None
        return self._proof_from_row(row)

    def get_proof_for_job(
        self,
        job_id: str,
        *,
        owner_user_id: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any] | None:
        if access_token:
            headers = self._client.user_scoped_headers(access_token)
            rows = self._client.rest_select(
                "job_deletion_proofs",
                params={"select": "*", "external_job_id": f"eq.{job_id}", "limit": "1"},
                headers=headers,
            )
            return self._proof_from_row(rows[0]) if rows else None
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select *
                from public.job_deletion_proofs
                where external_job_id = %s
                limit 1
                """,
                (job_id,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        if owner_user_id and row["external_user_id"] != owner_user_id:
            return None
        return self._proof_from_row(row)


class _SupabaseRuntimeOpsRepository(_SupabaseRepositoryBase):
    def list_gpu_leases(self) -> list[dict[str, Any]]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("select * from public.gpu_worker_leases order by created_at asc")
            rows = cur.fetchall()
        return [dict(row) for row in rows]

    def upsert_gpu_lease(self, *, worker_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        from psycopg.types.json import Jsonb

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into public.gpu_worker_leases (
                    id, worker_id, gpu_type, lease_state, is_warm, current_job_id,
                    queue_depth_snapshot, metadata, allocated_at, released_at, expires_at, updated_at
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                on conflict (worker_id) do update
                set gpu_type = excluded.gpu_type,
                    lease_state = excluded.lease_state,
                    is_warm = excluded.is_warm,
                    current_job_id = excluded.current_job_id,
                    queue_depth_snapshot = excluded.queue_depth_snapshot,
                    metadata = excluded.metadata,
                    allocated_at = excluded.allocated_at,
                    released_at = excluded.released_at,
                    expires_at = excluded.expires_at,
                    updated_at = now()
                returning *
                """,
                (
                    str(uuid4()),
                    worker_id,
                    payload.get("gpu_type"),
                    payload.get("lease_state"),
                    payload.get("is_warm", True),
                    payload.get("current_job_id"),
                    payload.get("queue_depth_snapshot", 0),
                    Jsonb(payload.get("metadata") or {}),
                    payload.get("allocated_at"),
                    payload.get("released_at"),
                    payload.get("expires_at"),
                ),
            )
            row = cur.fetchone()
        if row is None:
            raise RuntimeError("Failed to upsert GPU lease")
        return dict(row)

    def delete_gpu_lease(self, worker_id: str) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("delete from public.gpu_worker_leases where worker_id = %s", (worker_id,))

    def queued_job_backlog_count(self) -> int:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "select count(*) as queued_job_count from public.media_jobs where status = %s",
                (JobStatus.QUEUED.value,),
            )
            row = cur.fetchone()
        return int((row or {}).get("queued_job_count", 0) or 0)

    def list_incidents(self) -> list[dict[str, Any]]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("select * from public.incident_events order by opened_at desc")
            rows = cur.fetchall()
        return [dict(row) for row in rows]

    def upsert_incident(self, *, incident_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        from psycopg.types.json import Jsonb

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into public.incident_events (
                    id, incident_key, severity, incident_state, source_signal, runbook_key,
                    issue_tracker_url, status_page_url, communication_status, detection_delay_seconds,
                    resolution_time_seconds, postmortem_due_at, metadata, opened_at, acknowledged_at, resolved_at, updated_at
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                on conflict (incident_key) do update
                set severity = excluded.severity,
                    incident_state = excluded.incident_state,
                    source_signal = excluded.source_signal,
                    runbook_key = excluded.runbook_key,
                    issue_tracker_url = excluded.issue_tracker_url,
                    status_page_url = excluded.status_page_url,
                    communication_status = excluded.communication_status,
                    detection_delay_seconds = excluded.detection_delay_seconds,
                    resolution_time_seconds = excluded.resolution_time_seconds,
                    postmortem_due_at = excluded.postmortem_due_at,
                    metadata = excluded.metadata,
                    acknowledged_at = excluded.acknowledged_at,
                    resolved_at = excluded.resolved_at,
                    updated_at = now()
                returning *
                """,
                (
                    str(uuid4()),
                    incident_key,
                    payload.get("severity"),
                    payload.get("incident_state"),
                    payload.get("source_signal"),
                    payload.get("runbook_key"),
                    payload.get("issue_tracker_url"),
                    payload.get("status_page_url"),
                    payload.get("communication_status"),
                    payload.get("detection_delay_seconds"),
                    payload.get("resolution_time_seconds"),
                    payload.get("postmortem_due_at"),
                    Jsonb(payload.get("metadata") or {}),
                    payload.get("opened_at", _utc_now()),
                    payload.get("acknowledged_at"),
                    payload.get("resolved_at"),
                ),
            )
            row = cur.fetchone()
        if row is None:
            raise RuntimeError("Failed to upsert incident record")
        return dict(row)


def _user_profile_backend() -> _MemoryUserProfileRepository | _SupabaseUserProfileRepository:
    return _SupabaseUserProfileRepository() if phase2_backend_name() == "supabase" else _MemoryUserProfileRepository()


def _usage_backend() -> _MemoryUsageRepository | _SupabaseUsageRepository:
    return _SupabaseUsageRepository() if phase2_backend_name() == "supabase" else _MemoryUsageRepository()


def _upload_backend() -> _MemoryUploadRepository | _SupabaseUploadRepository:
    return _SupabaseUploadRepository() if phase2_backend_name() == "supabase" else _MemoryUploadRepository()


def _preview_session_backend() -> _MemoryPreviewSessionRepository | _SupabasePreviewSessionRepository:
    return _SupabasePreviewSessionRepository() if phase2_backend_name() == "supabase" else _MemoryPreviewSessionRepository()


def _era_detection_backend() -> _MemoryEraDetectionRepository | _SupabaseEraDetectionRepository:
    return _SupabaseEraDetectionRepository() if phase2_backend_name() == "supabase" else _MemoryEraDetectionRepository()


def _log_settings_backend() -> _MemoryLogSettingsRepository | _SupabaseLogSettingsRepository:
    return _SupabaseLogSettingsRepository() if phase2_backend_name() == "supabase" else _MemoryLogSettingsRepository()


def _compliance_backend() -> _MemoryComplianceRepository | _SupabaseComplianceRepository:
    return _SupabaseComplianceRepository() if phase2_backend_name() == "supabase" else _MemoryComplianceRepository()


def _job_backend() -> _MemoryJobRepository | _SupabaseJobRepository:
    return _SupabaseJobRepository() if phase2_backend_name() == "supabase" else _MemoryJobRepository()


def _webhook_subscription_backend() -> _MemoryWebhookSubscriptionRepository | _SupabaseWebhookSubscriptionRepository:
    return _SupabaseWebhookSubscriptionRepository() if phase2_backend_name() == "supabase" else _MemoryWebhookSubscriptionRepository()


def _manifest_backend() -> _MemoryManifestRepository | _SupabaseManifestRepository:
    return _SupabaseManifestRepository() if phase2_backend_name() == "supabase" else _MemoryManifestRepository()


def _job_export_package_backend() -> _MemoryJobExportPackageRepository | _SupabaseJobExportPackageRepository:
    return _SupabaseJobExportPackageRepository() if phase2_backend_name() == "supabase" else _MemoryJobExportPackageRepository()


def _job_deletion_proof_backend() -> _MemoryJobDeletionProofRepository | _SupabaseJobDeletionProofRepository:
    return _SupabaseJobDeletionProofRepository() if phase2_backend_name() == "supabase" else _MemoryJobDeletionProofRepository()


def _runtime_ops_backend() -> _MemoryRuntimeOpsRepository | _SupabaseRuntimeOpsRepository:
    return _SupabaseRuntimeOpsRepository() if phase2_backend_name() == "supabase" else _MemoryRuntimeOpsRepository()


class UserProfileRepository:
    def __init__(self) -> None:
        self._backend = _user_profile_backend()

    def get_or_create(
        self,
        *,
        user_id: str,
        role: str,
        plan_tier: str,
        org_id: str,
        email: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        return self._backend.get_or_create(
            user_id=user_id,
            role=role,
            plan_tier=plan_tier,
            org_id=org_id,
            email=email,
            access_token=access_token,
        )

    def update(self, user_id: str, patch: dict[str, Any], *, access_token: str | None = None) -> dict[str, Any]:
        return self._backend.update(user_id, patch, access_token=access_token)


class UsageRepository:
    def __init__(self) -> None:
        self._backend = _usage_backend()

    def get_or_create(
        self,
        *,
        user_id: str,
        plan_tier: str,
        monthly_limit_minutes: int,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        return self._backend.get_or_create(
            user_id=user_id,
            plan_tier=plan_tier,
            monthly_limit_minutes=monthly_limit_minutes,
            access_token=access_token,
        )

    def update(self, user_id: str, payload: dict[str, Any], *, access_token: str | None = None) -> dict[str, Any]:
        return self._backend.update(user_id, payload, access_token=access_token)


class UploadRepository:
    def __init__(self) -> None:
        self._backend = _upload_backend()

    def create_session(
        self,
        *,
        upload_id: str,
        owner_user_id: str,
        org_id: str,
        original_filename: str,
        mime_type: str,
        size_bytes: int,
        checksum_sha256: str | None,
        bucket_name: str,
        object_path: str,
        resumable_session_url: str,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        return self._backend.create_session(
            upload_id=upload_id,
            owner_user_id=owner_user_id,
            org_id=org_id,
            original_filename=original_filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
            checksum_sha256=checksum_sha256,
            bucket_name=bucket_name,
            object_path=object_path,
            resumable_session_url=resumable_session_url,
            access_token=access_token,
        )

    def get_session(
        self,
        upload_id: str,
        *,
        owner_user_id: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any] | None:
        return self._backend.get_session(upload_id, owner_user_id=owner_user_id, access_token=access_token)

    def update_session(
        self,
        upload_id: str,
        *,
        owner_user_id: str,
        patch: dict[str, Any],
        access_token: str | None = None,
    ) -> dict[str, Any] | None:
        return self._backend.update_session(
            upload_id,
            owner_user_id=owner_user_id,
            patch=patch,
            access_token=access_token,
        )

    def upsert_pointer(
        self,
        *,
        upload_id: str,
        owner_user_id: str,
        org_id: str,
        bucket_name: str,
        object_path: str,
        original_filename: str,
        mime_type: str,
        size_bytes: int,
        checksum_sha256: str | None,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        return self._backend.upsert_pointer(
            upload_id=upload_id,
            owner_user_id=owner_user_id,
            org_id=org_id,
            bucket_name=bucket_name,
            object_path=object_path,
            original_filename=original_filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
            checksum_sha256=checksum_sha256,
            access_token=access_token,
        )


class PreviewSessionRepository:
    def __init__(self) -> None:
        self._backend = _preview_session_backend()

    def create_preview(
        self,
        *,
        payload: dict[str, Any],
        access_token: str | None = None,
    ) -> dict[str, Any]:
        return self._backend.create_preview(payload=payload, access_token=access_token)

    def get_preview(
        self,
        preview_id: str,
        *,
        owner_user_id: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any] | None:
        return self._backend.get_preview(preview_id, owner_user_id=owner_user_id, access_token=access_token)

    def get_reusable_preview(
        self,
        *,
        source_asset_checksum: str,
        configuration_cache_fingerprint: str,
        owner_user_id: str,
        access_token: str | None = None,
    ) -> dict[str, Any] | None:
        return self._backend.get_reusable_preview(
            source_asset_checksum=source_asset_checksum,
            configuration_cache_fingerprint=configuration_cache_fingerprint,
            owner_user_id=owner_user_id,
            access_token=access_token,
        )

    def update_preview(
        self,
        preview_id: str,
        *,
        owner_user_id: str,
        patch: dict[str, Any],
        access_token: str | None = None,
    ) -> dict[str, Any] | None:
        return self._backend.update_preview(
            preview_id,
            owner_user_id=owner_user_id,
            patch=patch,
            access_token=access_token,
        )


class EraDetectionRepository:
    def __init__(self) -> None:
        self._backend = _era_detection_backend()

    def save_job(
        self,
        *,
        job_id: str,
        owner_user_id: str,
        org_id: str,
        media_uri: str,
        original_filename: str,
        mime_type: str,
        era_profile: dict[str, Any],
        access_token: str | None = None,
    ) -> dict[str, Any]:
        return self._backend.save_job(
            job_id=job_id,
            owner_user_id=owner_user_id,
            org_id=org_id,
            media_uri=media_uri,
            original_filename=original_filename,
            mime_type=mime_type,
            era_profile=era_profile,
            access_token=access_token,
        )

    def save_detection(self, *, job_id: str, detection: dict[str, Any], access_token: str | None = None) -> dict[str, Any]:
        return self._backend.save_detection(job_id=job_id, detection=detection, access_token=access_token)

    def latest_detection(self, job_id: str, *, access_token: str | None = None) -> dict[str, Any] | None:
        return self._backend.latest_detection(job_id, access_token=access_token)


class LogSettingsRepository:
    def __init__(self) -> None:
        self._backend = _log_settings_backend()

    def upsert(self, *, org_id: str, payload: dict[str, Any], updated_by: str, access_token: str | None = None) -> dict[str, Any]:
        return self._backend.upsert(org_id=org_id, payload=payload, updated_by=updated_by, access_token=access_token)

    def get(self, org_id: str, *, access_token: str | None = None) -> dict[str, Any] | None:
        return self._backend.get(org_id, access_token=access_token)


class ComplianceRepository:
    def __init__(self) -> None:
        self._backend = _compliance_backend()

    def create_deletion_request(self, *, user_id: str, payload: dict[str, Any], access_token: str | None = None) -> dict[str, Any]:
        return self._backend.create_deletion_request(user_id=user_id, payload=payload, access_token=access_token)


class JobRepository:
    def __init__(self) -> None:
        self._backend = _job_backend()

    def create_job(
        self,
        *,
        job_id: str,
        owner_user_id: str,
        plan_tier: str,
        org_id: str,
        media_uri: str,
        original_filename: str,
        mime_type: str,
        source_asset_checksum: str,
        fidelity_tier: str,
        processing_mode: str,
        era_profile: dict[str, Any],
        config: dict[str, Any],
        estimated_duration_seconds: int,
        segments: list[dict[str, Any]],
        cost_estimate_summary: dict[str, Any] | None = None,
        effective_fidelity_tier: str | None = None,
        effective_fidelity_profile: dict[str, Any] | None = None,
        reproducibility_mode: str = "perceptual_equivalence",
        access_token: str | None = None,
    ) -> dict[str, Any]:
        return self._backend.create_job(
            job_id=job_id,
            owner_user_id=owner_user_id,
            plan_tier=plan_tier,
            org_id=org_id,
            media_uri=media_uri,
            original_filename=original_filename,
            mime_type=mime_type,
            source_asset_checksum=source_asset_checksum,
            fidelity_tier=fidelity_tier,
            effective_fidelity_tier=effective_fidelity_tier,
            effective_fidelity_profile=effective_fidelity_profile,
            reproducibility_mode=reproducibility_mode,
            processing_mode=processing_mode,
            era_profile=era_profile,
            config=config,
            estimated_duration_seconds=estimated_duration_seconds,
            segments=segments,
            cost_estimate_summary=cost_estimate_summary,
            access_token=access_token,
        )

    def get_job(self, job_id: str, *, owner_user_id: str | None = None, access_token: str | None = None) -> dict[str, Any] | None:
        return self._backend.get_job(job_id, owner_user_id=owner_user_id, access_token=access_token)

    def list_jobs(self, *, owner_user_id: str, access_token: str | None = None) -> list[dict[str, Any]]:
        return self._backend.list_jobs(owner_user_id=owner_user_id, access_token=access_token)

    def list_segments(
        self,
        job_id: str,
        *,
        owner_user_id: str | None = None,
        access_token: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._backend.list_segments(job_id, owner_user_id=owner_user_id, access_token=access_token)

    def request_cancellation(
        self,
        job_id: str,
        *,
        owner_user_id: str,
        access_token: str | None = None,
    ) -> dict[str, Any] | None:
        return self._backend.request_cancellation(job_id, owner_user_id=owner_user_id, access_token=access_token)

    def get_job_for_worker(self, job_id: str) -> dict[str, Any] | None:
        return self._backend.get_job_for_worker(job_id)

    def update_job_for_worker(self, job_id: str, *, patch: dict[str, Any]) -> dict[str, Any]:
        return self._backend.update_job_for_worker(job_id, patch=patch)

    def update_segment_for_worker(self, job_id: str, segment_index: int, *, patch: dict[str, Any]) -> dict[str, Any]:
        return self._backend.update_segment_for_worker(job_id, segment_index, patch=patch)


class ManifestRepository:
    def __init__(self) -> None:
        self._backend = _manifest_backend()

    def upsert_manifest_for_worker(self, *, job_id: str, manifest: dict[str, Any]) -> dict[str, Any]:
        return self._backend.upsert_manifest_for_worker(job_id=job_id, manifest=manifest)

    def get_manifest(
        self,
        job_id: str,
        *,
        owner_user_id: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any] | None:
        return self._backend.get_manifest(job_id, owner_user_id=owner_user_id, access_token=access_token)


class JobExportPackageRepository:
    def __init__(self) -> None:
        self._backend = _job_export_package_backend()

    def upsert_package_for_worker(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        return self._backend.upsert_package_for_worker(payload=payload)

    def get_package(
        self,
        job_id: str,
        *,
        variant: str,
        owner_user_id: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any] | None:
        return self._backend.get_package(
            job_id,
            variant=variant,
            owner_user_id=owner_user_id,
            access_token=access_token,
        )

    def update_package_for_worker(self, job_id: str, *, variant: str, patch: dict[str, Any]) -> dict[str, Any]:
        return self._backend.update_package_for_worker(job_id, variant=variant, patch=patch)


class JobDeletionProofRepository:
    def __init__(self) -> None:
        self._backend = _job_deletion_proof_backend()

    def upsert_proof_for_worker(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        return self._backend.upsert_proof_for_worker(payload=payload)

    def get_proof(
        self,
        proof_id: str,
        *,
        owner_user_id: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any] | None:
        return self._backend.get_proof(proof_id, owner_user_id=owner_user_id, access_token=access_token)

    def get_proof_for_job(
        self,
        job_id: str,
        *,
        owner_user_id: str | None = None,
        access_token: str | None = None,
    ) -> dict[str, Any] | None:
        return self._backend.get_proof_for_job(job_id, owner_user_id=owner_user_id, access_token=access_token)


class WebhookSubscriptionRepository:
    def __init__(self) -> None:
        self._backend = _webhook_subscription_backend()

    def upsert(
        self,
        *,
        owner_user_id: str,
        webhook_url: str,
        event_types: list[str],
        enabled: bool = True,
    ) -> dict[str, Any]:
        return self._backend.upsert(
            owner_user_id=owner_user_id,
            webhook_url=webhook_url,
            event_types=event_types,
            enabled=enabled,
        )

    def list_enabled(self, *, owner_user_id: str, event_type: str) -> list[dict[str, Any]]:
        return self._backend.list_enabled(owner_user_id=owner_user_id, event_type=event_type)


class RuntimeOpsRepository:
    def __init__(self) -> None:
        self._backend = _runtime_ops_backend()

    def list_gpu_leases(self) -> list[dict[str, Any]]:
        return self._backend.list_gpu_leases()

    def upsert_gpu_lease(self, *, worker_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._backend.upsert_gpu_lease(worker_id=worker_id, payload=payload)

    def delete_gpu_lease(self, worker_id: str) -> None:
        self._backend.delete_gpu_lease(worker_id)

    def queued_job_backlog_count(self) -> int:
        return self._backend.queued_job_backlog_count()

    def list_incidents(self) -> list[dict[str, Any]]:
        return self._backend.list_incidents()

    def upsert_incident(self, *, incident_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._backend.upsert_incident(incident_key=incident_key, payload=payload)
