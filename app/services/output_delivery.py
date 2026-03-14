"""Deterministic Packet 4D output delivery and export signing."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote
from uuid import uuid4

from app.api.problem_details import ProblemException
from app.config import settings
from app.db.phase2_store import JobDeletionProofRepository, JobExportPackageRepository, JobRepository
from app.models.status import JobStatus
from app.services.uncertainty_callouts import UncertaintyCalloutService

_EXPORT_VARIANTS = ("av1", "h264")
_SUCCESSFUL_EXPORTABLE_STATUSES = {JobStatus.COMPLETED.value, JobStatus.PARTIAL.value}
_DEFAULT_RETENTION_DAYS = 7
_PDF_URL_TTL_HOURS = 1


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _isoformat(value: datetime) -> str:
    return value.isoformat()


def _canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _sha256_hex(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


def _sign_value(value: str) -> str:
    digest = hmac.new(
        settings.output_delivery_signing_secret.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return digest


def max_retention_days_for_plan(plan_tier: str) -> int:
    return 90 if str(plan_tier).lower() == "museum" else _DEFAULT_RETENTION_DAYS


def resolve_output_encoding(*, plan_tier: str, variant: str) -> dict[str, Any]:
    normalized_plan = str(plan_tier).lower()
    if normalized_plan not in {"hobbyist", "pro", "museum"}:
        raise ValueError(f"Unsupported plan tier for output delivery: {plan_tier}")
    if variant not in _EXPORT_VARIANTS:
        raise ValueError(f"Unsupported export variant: {variant}")

    bitrate_mbps = {
        "hobbyist": 8,
        "pro": 16,
        "museum": 32,
    }[normalized_plan]
    resolution_target = {
        "hobbyist": "1080p",
        "pro": "4K",
        "museum": "native_scan",
    }[normalized_plan]
    codec = "av1" if variant == "av1" else "h264"
    return {
        "variant": variant,
        "codec": codec,
        "container": "mp4",
        "bitrate_mbps": bitrate_mbps,
        "resolution_target": resolution_target,
        "frame_rate": "source_preserved",
        "color_space": "bt709_preserved",
        "metadata_preservation": {
            "timecode": True,
            "aspect_ratio": True,
            "color_primaries": True,
            "source_filename": True,
        },
    }


class OutputDeliveryService:
    def __init__(self) -> None:
        self._jobs = JobRepository()
        self._packages = JobExportPackageRepository()
        self._proofs = JobDeletionProofRepository()
        self._callouts = UncertaintyCalloutService()

    def materialize_delivery_artifacts(
        self,
        *,
        job: dict[str, Any],
        segments: list[dict[str, Any]],
        manifest_payload: dict[str, Any],
    ) -> dict[str, Any]:
        if str(job.get("status")) not in _SUCCESSFUL_EXPORTABLE_STATUSES:
            return {"deletion_proof": None, "packages": []}

        generated_at = _utc_now()
        callouts = self._callouts.build_callouts(job, segments)
        deletion_proof = self._build_deletion_proof(
            job=job,
            manifest_payload=manifest_payload,
            callouts=callouts,
            generated_at=generated_at,
        )
        persisted_proof = self._proofs.upsert_proof_for_worker(payload=deletion_proof)

        persisted_packages: list[dict[str, Any]] = []
        for variant in _EXPORT_VARIANTS:
            package_payload = self._build_export_package(
                job=job,
                manifest_payload=manifest_payload,
                callouts=callouts,
                deletion_proof=persisted_proof,
                generated_at=generated_at,
                variant=variant,
            )
            persisted_packages.append(self._packages.upsert_package_for_worker(payload=package_payload))

        return {
            "deletion_proof": persisted_proof,
            "packages": persisted_packages,
        }

    def get_export(
        self,
        job_id: str,
        *,
        owner_user_id: str,
        plan_tier: str,
        variant: str,
        retention_days: int,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        job = self._jobs.get_job(job_id, owner_user_id=owner_user_id, access_token=access_token)
        if job is None:
            raise ProblemException(
                title="Not Found",
                detail="Job not found for the current user.",
                status_code=404,
            )
        if job["status"] not in _SUCCESSFUL_EXPORTABLE_STATUSES:
            raise ProblemException(
                title="Export Not Ready",
                detail="Exports are only available after processing completes or yields partial results.",
                status_code=409,
            )
        self._validate_retention_days(plan_tier=plan_tier, retention_days=retention_days)
        package = self._packages.get_package(
            job_id,
            variant=variant,
            owner_user_id=owner_user_id,
            access_token=access_token,
        )
        if package is None:
            raise ProblemException(
                title="Not Found",
                detail="Export package not found for the current user.",
                status_code=404,
            )
        package = self._expire_package_if_needed(package)
        if package.get("deleted_at"):
            raise ProblemException(
                title="Download Expired",
                detail="The delivery package has expired and been deleted. Start a new processing run to generate a fresh package.",
                status_code=410,
            )

        requested_expiry = _utc_now() + timedelta(days=retention_days)
        available_until = datetime.fromisoformat(str(package["available_until"]))
        expires_at = min(requested_expiry, available_until)
        return {
            "job_id": job_id,
            "status": job["status"],
            "variant": variant,
            "download_url": self._signed_download_url(
                object_uri=str(package["package_uri"]),
                file_name=str(package["file_name"]),
                expires_at=expires_at,
            ),
            "expires_at": _isoformat(expires_at),
            "file_name": package["file_name"],
            "size_bytes": int(package["size_bytes"]),
            "sha256": package["sha256"],
            "deletion_proof_id": package["deletion_proof_id"],
            "package_contents": package["package_contents"],
        }

    def get_deletion_proof(
        self,
        proof_id: str,
        *,
        owner_user_id: str,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        proof = self._proofs.get_proof(proof_id, owner_user_id=owner_user_id, access_token=access_token)
        if proof is None:
            raise ProblemException(
                title="Not Found",
                detail="Deletion proof not found for the current user.",
                status_code=404,
            )
        expires_at = _utc_now() + timedelta(hours=_PDF_URL_TTL_HOURS)
        return {
            "deletion_proof_id": proof["deletion_proof_id"],
            "job_id": proof["job_id"],
            "generated_at": proof["generated_at"],
            "signature_algorithm": proof["signature_algorithm"],
            "signature": proof["signature"],
            "proof_sha256": proof["proof_sha256"],
            "pdf_download_url": self._signed_download_url(
                object_uri=str(proof["pdf_uri"]),
                file_name=f"{proof['deletion_proof_id']}.pdf",
                expires_at=expires_at,
            ),
            "pdf_expires_at": _isoformat(expires_at),
            "verification_summary": proof["verification_summary"],
        }

    def _validate_retention_days(self, *, plan_tier: str, retention_days: int) -> None:
        normalized_plan = str(plan_tier).lower()
        if normalized_plan != "museum" and retention_days > _DEFAULT_RETENTION_DAYS:
            raise ProblemException(
                title="Plan Upgrade Required",
                detail="Extended export retention beyond 7 days requires Museum tier.",
                status_code=403,
                errors=[
                    {
                        "field": "retention_days",
                        "message": "Extended export retention beyond 7 days requires Museum tier.",
                        "rule_id": "FR-005",
                    }
                ],
            )
        if normalized_plan == "museum" and retention_days > 90:
            raise ProblemException(
                title="Invalid Retention Window",
                detail="Museum retention requests must stay within 1 to 90 days.",
                status_code=400,
                errors=[
                    {
                        "field": "retention_days",
                        "message": "Museum retention requests must stay within 1 to 90 days.",
                        "rule_id": "FR-005",
                    }
                ],
            )

    def _expire_package_if_needed(self, package: dict[str, Any]) -> dict[str, Any]:
        available_until = datetime.fromisoformat(str(package["available_until"]))
        if package.get("deleted_at") or available_until >= _utc_now():
            return package
        deleted_at = _isoformat(_utc_now())
        updated = self._packages.update_package_for_worker(
            str(package["job_id"]),
            variant=str(package["variant"]),
            patch={"deleted_at": deleted_at},
        )
        return updated

    def _build_deletion_proof(
        self,
        *,
        job: dict[str, Any],
        manifest_payload: dict[str, Any],
        callouts: list[dict[str, Any]],
        generated_at: datetime,
    ) -> dict[str, Any]:
        deletion_proof_id = str(uuid4())
        proof_payload = {
            "job_id": job["job_id"],
            "user_id": job["owner_user_id"],
            "generated_at": _isoformat(generated_at),
            "source_asset_checksum": job["source_asset_checksum"],
            "result_uri": job.get("result_uri"),
            "manifest_sha256": manifest_payload["manifest_sha256"],
            "callout_codes": [item["code"] for item in callouts],
            "fidelity_tier": job["fidelity_tier"],
            "effective_fidelity_tier": job.get("effective_fidelity_tier", job["fidelity_tier"]),
        }
        proof_sha256 = _sha256_hex(proof_payload)
        signature = _sign_value(f"{deletion_proof_id}:{proof_sha256}")
        return {
            "deletion_proof_id": deletion_proof_id,
            "job_id": job["job_id"],
            "owner_user_id": job["owner_user_id"],
            "generated_at": _isoformat(generated_at),
            "signature_algorithm": "HMAC-SHA256",
            "signature": signature,
            "proof_sha256": proof_sha256,
            "verification_summary": {
                "status": "verified",
                "result_uri": job.get("result_uri"),
                "manifest_sha256": manifest_payload["manifest_sha256"],
                "original_checksum": job["source_asset_checksum"],
            },
            "pdf_uri": self._bucket_uri(f"deletion-proofs/{job['job_id']}/{deletion_proof_id}.pdf"),
            "proof_payload": proof_payload,
        }

    def _build_export_package(
        self,
        *,
        job: dict[str, Any],
        manifest_payload: dict[str, Any],
        callouts: list[dict[str, Any]],
        deletion_proof: dict[str, Any],
        generated_at: datetime,
        variant: str,
    ) -> dict[str, Any]:
        encoding = resolve_output_encoding(plan_tier=str(job["plan_tier"]), variant=variant)
        package_uri = self._bucket_uri(f"downloads/{job['job_id']}/{variant}/{job['job_id']}-{variant}.zip")
        media_file_name = f"{job['job_id']}-{variant}.mp4"
        package_contents = [
            media_file_name,
            "transformation_manifest.json",
            "uncertainty_callouts.json",
            "quality_report.pdf",
            "deletion_proof.pdf",
        ]
        artifact_metadata = {
            "restored_media": {
                "file_name": media_file_name,
                "uri": job.get("result_uri") or self._bucket_uri(f"jobs/{job['job_id']}/{media_file_name}"),
            },
            "transformation_manifest": {
                "file_name": "transformation_manifest.json",
                "uri": manifest_payload["manifest_uri"],
                "sha256": manifest_payload["manifest_sha256"],
            },
            "uncertainty_callouts": {
                "file_name": "uncertainty_callouts.json",
                "sha256": hashlib.sha256(json.dumps(callouts, sort_keys=True).encode("utf-8")).hexdigest(),
            },
            "quality_report": {
                "file_name": "quality_report.pdf",
                "uri": self._bucket_uri(f"downloads/{job['job_id']}/{variant}/quality_report.pdf"),
            },
            "deletion_proof": {
                "file_name": "deletion_proof.pdf",
                "uri": deletion_proof["pdf_uri"],
                "deletion_proof_id": deletion_proof["deletion_proof_id"],
            },
        }
        payload = {
            "job_id": job["job_id"],
            "variant": variant,
            "package_uri": package_uri,
            "file_name": f"chronos-{job['job_id']}-{variant}.zip",
            "package_contents": package_contents,
            "artifact_metadata": artifact_metadata,
            "encoding_metadata": encoding,
            "deletion_proof_id": deletion_proof["deletion_proof_id"],
            "available_until": _isoformat(generated_at + timedelta(days=max_retention_days_for_plan(str(job["plan_tier"])))),
        }
        payload["sha256"] = _sha256_hex(payload)
        payload["size_bytes"] = self._estimate_package_size(
            duration_seconds=int(job["estimated_duration_seconds"]),
            encoding=encoding,
            package_contents=package_contents,
        )
        return {
            **payload,
            "owner_user_id": job["owner_user_id"],
            "generated_at": _isoformat(generated_at),
            "deleted_at": None,
        }

    def _estimate_package_size(
        self,
        *,
        duration_seconds: int,
        encoding: dict[str, Any],
        package_contents: list[str],
    ) -> int:
        video_bytes = int(max(duration_seconds, 1) * int(encoding["bitrate_mbps"]) * 125_000)
        metadata_bytes = (len(package_contents) * 3_000) + 8_192
        if encoding["variant"] == "av1":
            video_bytes = int(video_bytes * 0.82)
        return video_bytes + metadata_bytes

    def _bucket_uri(self, path: str) -> str:
        bucket_name = settings.gcs_bucket_name or "chronos-refine-downloads"
        return f"gs://{bucket_name}/{path}"

    def _signed_download_url(self, *, object_uri: str, file_name: str, expires_at: datetime) -> str:
        if object_uri.startswith("gs://"):
            _, _, path = object_uri.partition("gs://")
            bucket_name, _, object_path = path.partition("/")
        else:
            bucket_name = settings.gcs_bucket_name or "chronos-refine-downloads"
            object_path = object_uri.lstrip("/")
        request_time = _utc_now()
        request_date = request_time.strftime("%Y%m%d")
        request_timestamp = request_time.strftime("%Y%m%dT%H%M%SZ")
        expires_seconds = max(int((expires_at - request_time).total_seconds()), 1)
        credential = f"chronos-output-delivery/{request_date}/auto/storage/goog4_request"
        signature = _sign_value(f"{object_uri}:{file_name}:{request_timestamp}:{expires_seconds}")
        encoded_object = quote(object_path, safe="/")
        return (
            f"https://storage.googleapis.com/{bucket_name}/{encoded_object}"
            f"?X-Goog-Algorithm=GOOG4-HMAC-SHA256"
            f"&X-Goog-Credential={quote(credential, safe='')}"
            f"&X-Goog-Date={request_timestamp}"
            f"&X-Goog-Expires={expires_seconds}"
            f"&X-Goog-SignedHeaders=host"
            f"&response-content-disposition=attachment%3Bfilename%3D{quote(file_name)}"
            f"&X-Goog-Signature={signature}"
        )
