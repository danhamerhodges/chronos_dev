"""Transformation manifest generation and storage for Packet 3B."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Protocol
from urllib.parse import quote

import httpx

from app.api.contracts import TransformationManifestResponse
from app.config import settings
from app.api.problem_details import ProblemException
from app.services.data_classification import ARTIFACT_TRANSFORMATION_MANIFEST, DataClassificationService, is_local_environment
from app.services.manifest_retention import ManifestRetentionService, RETENTION_CLASS_ZERO
from app.services.reproducibility import environment_fingerprint
from app.services.vertex_gemini import GoogleAccessTokenProvider

_GCS_UPLOAD_URL = "https://storage.googleapis.com/upload/storage/v1/b/{bucket}/o"
_GCS_OBJECT_METADATA_URL = "https://storage.googleapis.com/storage/v1/b/{bucket}/o/{object_path}"
_MANIFEST_PREFIX = "manifests"


class RestorationProvider(Protocol):
    def model_versions(self, fidelity_profile: dict[str, Any]) -> dict[str, str]: ...


class EncodingProvider(Protocol):
    def version_metadata(self) -> dict[str, str]: ...


class ManifestStore(Protocol):
    def store(
        self,
        *,
        job_id: str,
        payload: dict[str, Any],
        retention_class: str,
        object_basename: str,
        variant: str = "full",
    ) -> tuple[str, int]: ...


class ReferenceRestorationProvider:
    def model_versions(self, fidelity_profile: dict[str, Any]) -> dict[str, str]:
        return {
            "codeformer": f"reference-codeformer-contract-{fidelity_profile['tier'].lower()}-v1",
            "identity_lock": "enabled" if fidelity_profile["identity_lock"] else "disabled",
        }


class ReferenceEncodingProvider:
    def version_metadata(self) -> dict[str, str]:
        return {
            "av1_encoder": "reference-av1-fgs-contract-v1",
            "encoding_profile": "reference-balanced-profile",
        }


class GcsManifestStore:
    def __init__(self) -> None:
        self._token_provider = GoogleAccessTokenProvider()

    def store(
        self,
        *,
        job_id: str,
        payload: dict[str, Any],
        retention_class: str,
        object_basename: str,
        variant: str = "full",
    ) -> tuple[str, int]:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        bucket = settings.gcs_bucket_name
        suffix = ".redacted.json" if variant == "redacted" else ".json"
        object_name = f"{_MANIFEST_PREFIX}/{retention_class}/{job_id}/{object_basename}{suffix}"
        if is_local_environment(settings.environment):
            return f"gs://{bucket or 'chronos'}/{object_name}", len(encoded)
        if not bucket:
            raise ProblemException(
                title="Manifest Storage Unavailable",
                detail="GCS bucket configuration is required to store transformation manifests.",
                status_code=500,
            )
        access_token = self._token_provider.access_token()
        if not access_token:
            raise ProblemException(
                title="Manifest Storage Unavailable",
                detail="GCP access token is required to store transformation manifests.",
                status_code=500,
            )
        response = httpx.post(
            _GCS_UPLOAD_URL.format(bucket=bucket),
            params={"uploadType": "media", "name": object_name},
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            content=encoded,
            timeout=10.0,
        )
        response.raise_for_status()
        return f"gs://{bucket}/{object_name}", len(encoded)

    def delete_object(self, *, object_uri: str) -> bool:
        if is_local_environment(settings.environment):
            return False
        if not settings.gcs_bucket_name:
            raise ProblemException(
                title="Manifest Storage Unavailable",
                detail="GCS bucket configuration is required to delete expired transformation manifests.",
                status_code=500,
            )
        bucket, object_path = _parse_gs_uri(object_uri)
        if not bucket or not object_path:
            raise ProblemException(
                title="Manifest Storage Unavailable",
                detail="Transformation manifest deletion requires a valid GCS object URI.",
                status_code=500,
            )
        access_token = self._token_provider.access_token()
        if not access_token:
            raise ProblemException(
                title="Manifest Storage Unavailable",
                detail="GCP access token is required to delete expired transformation manifests.",
                status_code=500,
            )
        try:
            response = httpx.delete(
                _GCS_OBJECT_METADATA_URL.format(bucket=bucket, object_path=quote(object_path, safe="")),
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProblemException(
                title="Manifest Storage Unavailable",
                detail="Expired transformation manifest could not be deleted.",
                status_code=500,
            ) from exc
        return True

    def patch_object_metadata(self, *, object_uri: str, metadata: dict[str, str]) -> bool:
        if is_local_environment(settings.environment):
            return False
        if not settings.gcs_bucket_name:
            raise ProblemException(
                title="Manifest Storage Unavailable",
                detail="GCS bucket configuration is required to classify transformation manifests.",
                status_code=500,
            )
        bucket, object_path = _parse_gs_uri(object_uri)
        if not bucket or not object_path:
            raise ProblemException(
                title="Manifest Storage Unavailable",
                detail="Transformation manifest classification requires a valid GCS object URI.",
                status_code=500,
            )
        access_token = self._token_provider.access_token()
        if not access_token:
            raise ProblemException(
                title="Manifest Storage Unavailable",
                detail="GCP access token is required to classify transformation manifests.",
                status_code=500,
            )
        try:
            response = httpx.patch(
                _GCS_OBJECT_METADATA_URL.format(bucket=bucket, object_path=quote(object_path, safe="")),
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json; charset=UTF-8",
                },
                json={"metadata": metadata},
                timeout=10.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProblemException(
                title="Manifest Storage Unavailable",
                detail="Transformation manifest classification metadata could not be applied.",
                status_code=500,
            ) from exc
        return True


def manifest_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _coerce_timestamp(value: str | datetime) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _parse_gs_uri(object_uri: str) -> tuple[str, str]:
    if not object_uri.startswith("gs://"):
        return "", ""
    without_scheme = object_uri.removeprefix("gs://")
    bucket, _, object_path = without_scheme.partition("/")
    return bucket, object_path


def build_manifest_payload(
    *,
    manifest_id: str,
    generated_at: str | datetime,
    job: dict[str, Any],
    segments: list[dict[str, Any]],
) -> dict[str, Any]:
    restoration = ReferenceRestorationProvider()
    encoding = ReferenceEncodingProvider()
    environment = environment_fingerprint()
    payload = {
        "manifest_id": manifest_id,
        "job_id": job["job_id"],
        "generated_at": _coerce_timestamp(generated_at),
        "user_id": job["owner_user_id"],
        "era_profile": job["era_profile"],
        "fidelity_tier": job["effective_fidelity_tier"],
        "effective_fidelity_profile": job["effective_fidelity_profile"],
        "reproducibility_mode": job["reproducibility_mode"],
        "job_status": job["status"],
        "quality_summary": job["quality_summary"],
        "reproducibility_summary": job["reproducibility_summary"],
        "stage_timings": job["stage_timings"],
        "processing_time_ms": int(job["stage_timings"].get("processing_ms") or 0),
        "gpu_usage": {
            "gpu_type": (job.get("gpu_summary") or {}).get("gpu_type", "reference-cpu-path"),
            "gpu_seconds": (job.get("cost_summary") or {}).get("gpu_seconds", 0),
            "warm_start": (job.get("gpu_summary") or {}).get("warm_start"),
            "allocation_latency_ms": (job.get("gpu_summary") or {}).get("allocation_latency_ms"),
        },
        "cache_summary": job.get("cache_summary") or {},
        "cost_summary": job.get("cost_summary") or {},
        "slo_summary": job.get("slo_summary") or {},
        "model_versions": {
            **restoration.model_versions(job["effective_fidelity_profile"]),
            **encoding.version_metadata(),
            "gemini": settings.gemini_model,
        },
        "environment": environment,
        "segments": [
            {
                "segment_index": segment["segment_index"],
                "frame_range": (
                    f"{segment['segment_start_seconds']:.0f}s-{segment['segment_end_seconds']:.0f}s"
                ),
                "quality_summary": {
                    "e_hf": (segment.get("quality_metrics") or {}).get("e_hf", 0.0),
                    "s_ls_db": (segment.get("quality_metrics") or {}).get("s_ls_db", 0.0),
                    "t_tc": (segment.get("quality_metrics") or {}).get("t_tc", 0.0),
                    "thresholds_met": (segment.get("quality_metrics") or {}).get("thresholds_met", False),
                }
                if segment.get("quality_metrics")
                else {
                    "e_hf": 0.0,
                    "s_ls_db": 0.0,
                    "t_tc": 0.0,
                    "thresholds_met": False,
                },
                "uncertainty_callouts": segment.get("uncertainty_callouts") or [],
                "sampling_protocol": (segment.get("quality_metrics") or {}).get("sampling_protocol")
                or {
                    "frames_per_second": 1.0,
                    "frames_sampled": 0,
                    "sampled_timestamps_seconds": [],
                    "downscale_rule": "720p for optical flow if source > 720p",
                    "roi_256": {"x": 0, "y": 0, "width": 256, "height": 256},
                    "roi_512": {"x": 0, "y": 0, "width": 512, "height": 512},
                    "roi_full_frame": {"x": 0, "y": 0, "width": 1280, "height": 720},
                    "roi_source": "center_crop",
                },
                "reproducibility_proof": segment.get("reproducibility_proof") or {},
                "output_uri": segment.get("output_uri"),
            }
            for segment in segments
        ],
        "uncertainty_callouts": sorted(
            {item for segment in segments for item in (segment.get("uncertainty_callouts") or [])}
        ),
        "warnings": job.get("warnings") or [],
        "result_uri": job.get("result_uri"),
        "manifest_uri": "",
        "manifest_sha256": "",
    }
    return payload


def build_redacted_manifest_payload(*, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "manifest_id": payload["manifest_id"],
        "job_id": payload["job_id"],
        "redaction_version": "sec-005-v1",
        "era_profile": payload.get("era_profile") or {},
        "fidelity_tier": payload.get("fidelity_tier"),
        "effective_fidelity_profile": payload.get("effective_fidelity_profile") or {},
        "reproducibility_mode": payload.get("reproducibility_mode"),
        "quality_summary": payload.get("quality_summary") or {},
        "reproducibility_summary": payload.get("reproducibility_summary") or {},
        "model_versions": payload.get("model_versions") or {},
        "segments": [
            {
                "segment_index": segment.get("segment_index"),
                "frame_range": segment.get("frame_range"),
                "quality_summary": segment.get("quality_summary") or {},
                "sampling_protocol": segment.get("sampling_protocol") or {},
                "reproducibility_proof": segment.get("reproducibility_proof") or {},
            }
            for segment in payload.get("segments", [])
        ],
    }


def delete_manifest_objects(*, object_uris: list[str], store: GcsManifestStore | None = None) -> None:
    store_impl = store or GcsManifestStore()
    for object_uri in object_uris:
        store_impl.delete_object(object_uri=object_uri)


def finalize_manifest_payload(
    *,
    manifest_id: str,
    generated_at: str | datetime,
    job: dict[str, Any],
    segments: list[dict[str, Any]],
    store: ManifestStore | None = None,
) -> dict[str, Any]:
    payload = build_manifest_payload(
        manifest_id=manifest_id,
        generated_at=generated_at,
        job=job,
        segments=segments,
    )
    manifest_hash = manifest_sha256(payload)
    payload["manifest_sha256"] = manifest_hash
    store_impl = store or GcsManifestStore()
    retention_policy = ManifestRetentionService().resolve_policy(
        org_id=job.get("org_id"),
        plan_tier=str(job["plan_tier"]),
        generated_at=payload["generated_at"],
    )
    object_basename = uuid.uuid4().hex
    manifest_uri, size_bytes = store_impl.store(
        job_id=job["job_id"],
        payload=payload,
        retention_class=retention_policy.retention_class,
        object_basename=object_basename,
        variant="full",
    )
    payload["manifest_uri"] = manifest_uri
    payload["size_bytes"] = size_bytes
    classification_service = DataClassificationService()
    classification = classification_service.classify(
        artifact_type=ARTIFACT_TRANSFORMATION_MANIFEST,
        object_uri=manifest_uri,
        plan_tier=str(job["plan_tier"]),
        anchor_time=payload["generated_at"],
        retention_days_override=retention_policy.retention_days,
        use_retention_override=True,
    )
    classification_service.record_event(classification, event_type="classification_assigned")
    patcher = getattr(store_impl, "patch_object_metadata", None)
    if patcher is None:
        classification_service.record_event(classification, event_type="gcs_metadata_patch_skipped")
    else:
        try:
            patched = bool(patcher(object_uri=manifest_uri, metadata=classification.metadata))
        except ProblemException:
            classification_service.record_event(classification, event_type="gcs_metadata_patch_failed")
            raise
        classification_service.record_event(
            classification,
            event_type="gcs_metadata_patched" if patched else "gcs_metadata_patch_skipped",
        )
    redaction: dict[str, Any] = {}
    if retention_policy.manifest_redaction_enabled:
        redacted_payload = build_redacted_manifest_payload(payload=payload)
        redacted_payload["source_manifest_sha256"] = payload["manifest_sha256"]
        redacted_hash = manifest_sha256(redacted_payload)
        redacted_payload["redacted_manifest_sha256"] = redacted_hash
        redacted_uri, redacted_size_bytes = store_impl.store(
            job_id=job["job_id"],
            payload=redacted_payload,
            retention_class=retention_policy.retention_class,
            object_basename=object_basename,
            variant="redacted",
        )
        redaction = {
            "redacted_payload": redacted_payload,
            "redacted_manifest_uri": redacted_uri,
            "redacted_manifest_sha256": redacted_hash,
            "redacted_size_bytes": redacted_size_bytes,
        }
        redacted_classification = classification_service.classify(
            artifact_type=ARTIFACT_TRANSFORMATION_MANIFEST,
            object_uri=redacted_uri,
            plan_tier=str(job["plan_tier"]),
            anchor_time=payload["generated_at"],
            retention_days_override=retention_policy.retention_days,
            use_retention_override=True,
        )
        classification_service.record_event(redacted_classification, event_type="classification_assigned")
        if patcher is None:
            classification_service.record_event(redacted_classification, event_type="gcs_metadata_patch_skipped")
        else:
            try:
                redacted_patched = bool(patcher(object_uri=redacted_uri, metadata=redacted_classification.metadata))
            except ProblemException:
                classification_service.record_event(redacted_classification, event_type="gcs_metadata_patch_failed")
                raise
            classification_service.record_event(
                redacted_classification,
                event_type="gcs_metadata_patched" if redacted_patched else "gcs_metadata_patch_skipped",
            )
    retention_fields = dict(retention_policy.persistence_fields)
    deletion: dict[str, Any] = {}
    if retention_policy.retention_class == RETENTION_CLASS_ZERO:
        retention_fields["retention_delete_status"] = "pending"
        retention_fields["retention_delete_attempted_at"] = datetime.now(timezone.utc).isoformat()
        deletion["object_uris"] = [
            uri
            for uri in [manifest_uri, redaction.get("redacted_manifest_uri")]
            if isinstance(uri, str) and uri
        ]
    validated = TransformationManifestResponse.model_validate(payload)
    return {
        "payload": validated.model_dump(),
        "classification": {**classification.persistence_fields, **retention_fields},
        "retention": retention_fields,
        "redaction": redaction,
        "deletion": deletion,
    }
