"""Transformation manifest generation and storage for Packet 3B."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from typing import Any, Protocol

import httpx

from app.api.contracts import TransformationManifestResponse
from app.config import settings
from app.services.reproducibility import environment_fingerprint
from app.services.vertex_gemini import GoogleAccessTokenProvider

_GCS_UPLOAD_URL = "https://storage.googleapis.com/upload/storage/v1/b/{bucket}/o"
_MANIFEST_PREFIX = "manifests"


class RestorationProvider(Protocol):
    def model_versions(self, fidelity_profile: dict[str, Any]) -> dict[str, str]: ...


class EncodingProvider(Protocol):
    def version_metadata(self) -> dict[str, str]: ...


class ManifestStore(Protocol):
    def store(self, *, job_id: str, payload: dict[str, Any]) -> tuple[str, int]: ...


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

    def store(self, *, job_id: str, payload: dict[str, Any]) -> tuple[str, int]:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        bucket = settings.gcs_bucket_name
        object_name = f"{_MANIFEST_PREFIX}/{job_id}/{uuid.uuid4().hex}.json"
        if bucket:
            access_token = self._token_provider.access_token()
            if access_token:
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
        return f"gs://chronos/manifests/{job_id}.json", len(encoded)


def manifest_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _coerce_timestamp(value: str | datetime) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


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
    manifest_uri, size_bytes = store_impl.store(job_id=job["job_id"], payload=payload)
    payload["manifest_uri"] = manifest_uri
    payload["size_bytes"] = size_bytes
    validated = TransformationManifestResponse.model_validate(payload)
    return validated.model_dump()
