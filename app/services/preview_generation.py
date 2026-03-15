"""Packet 4F preview session generation and reread service."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from time import perf_counter
from typing import Any
from urllib.parse import quote

from app.api.problem_details import ProblemException
from app.config import settings
from app.db.phase2_store import (
    PreviewSessionRepository,
    UploadRepository,
    _preview_configuration_cache_fingerprint,
    _stable_uuid,
)
from app.models.status import UploadStatus
from app.observability.monitoring import record_preview_generation
from app.services.cost_estimation import BillingPricingUnavailableError, CostEstimationService

_TARGET_KEYFRAME_COUNT = 10
_PREVIEW_URL_TTL_HOURS = 1
_PREVIEW_RETENTION_HOURS = 24


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
def _isoformat(value: datetime) -> str: return value.isoformat()
def _canonical_json(payload: dict[str, Any]) -> str: return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
def _sha256(value: str) -> str: return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _preview_id_for_snapshot(*, upload_id: str, configured_at_snapshot: str) -> str:
    return _stable_uuid(f"preview-session:{upload_id}:{configured_at_snapshot}")


class PreviewStorageUnavailableError(RuntimeError):
    """Raised when preview signing/storage cannot produce usable URLs."""
@dataclass(frozen=True)
class _SelectionSnapshot:
    selection_mode: str
    scene_diversity: float
    keyframes: list[dict[str, Any]]


class PreviewGenerationService:
    def __init__(
        self,
        *,
        uploads: UploadRepository | None = None,
        previews: PreviewSessionRepository | None = None,
        estimator: CostEstimationService | None = None,
    ) -> None:
        self._uploads = uploads or UploadRepository()
        self._previews = previews or PreviewSessionRepository()
        self._estimator = estimator or CostEstimationService()

    def create_preview(
        self,
        *,
        upload_id: str,
        owner_user_id: str,
        plan_tier: str,
        access_token: str,
    ) -> dict[str, Any]:
        session = self._require_preview_ready_upload(
            self._uploads.get_session(upload_id, owner_user_id=owner_user_id, access_token=access_token)
        )
        snapshot = self._saved_launch_snapshot(session)
        exact = self._previews.get_preview(
            str(snapshot["preview_id"]),
            owner_user_id=owner_user_id,
            access_token=access_token,
        )
        if exact is not None:
            exact = self._expire_if_needed(exact, owner_user_id=owner_user_id, access_token=access_token)
            if self._is_active_preview(
                exact,
                expected_configuration_fingerprint=str(snapshot["configuration_fingerprint"]),
            ):
                record_preview_generation(
                    outcome="cache_hit",
                    latency_ms=0.0,
                    selection_mode=str(exact.get("selection_mode") or "scene_aware"),
                    fallback_used=str(exact.get("selection_mode")) == "uniform_fallback",
                )
                return self._response_payload(exact, current_session=session)

        started = perf_counter()
        try:
            estimate = self._estimator.estimate_launch(
                user_id=owner_user_id,
                plan_tier=plan_tier,
                payload=snapshot["job_payload_preview"],
                access_token=access_token,
            )
        except BillingPricingUnavailableError as exc:
            raise ProblemException(
                title="Billing Pricing Unavailable",
                detail="Pricing data is temporarily unavailable. Retry preview generation once billing metadata is available.",
                status_code=503,
            ) from exc

        reusable = self._previews.get_reusable_preview(
            source_asset_checksum=str(snapshot["source_asset_checksum"]),
            configuration_cache_fingerprint=str(snapshot["configuration_cache_fingerprint"]),
            owner_user_id=owner_user_id,
            access_token=access_token,
        )
        if reusable is not None:
            reusable = self._expire_if_needed(reusable, owner_user_id=owner_user_id, access_token=access_token)
            if not self._is_active_preview(reusable):
                reusable = None

        try:
            preview = self._build_preview_record(
                session=session,
                snapshot=snapshot,
                owner_user_id=owner_user_id,
                estimate_summary=estimate.summary,
                reusable_preview=reusable,
            )
            persisted = self._previews.create_preview(payload=preview, access_token=access_token)
        except PreviewStorageUnavailableError as exc:
            raise ProblemException(
                title="Preview Storage Unavailable",
                detail="Preview storage or signing is temporarily unavailable. Retry the request once preview delivery is available.",
                status_code=503,
            ) from exc
        except Exception:
            record_preview_generation(
                outcome="failure",
                latency_ms=(perf_counter() - started) * 1000,
                selection_mode="scene_aware",
                fallback_used=False,
            )
            raise

        response = self._response_payload(persisted, current_session=session)
        record_preview_generation(
            outcome="cache_hit" if reusable is not None else "cache_miss",
            latency_ms=(perf_counter() - started) * 1000,
            selection_mode=str(persisted["selection_mode"]),
            fallback_used=str(persisted["selection_mode"]) == "uniform_fallback",
        )
        return response

    def get_preview(
        self,
        preview_id: str,
        *,
        owner_user_id: str,
        access_token: str,
    ) -> dict[str, Any]:
        preview = self._previews.get_preview(preview_id, owner_user_id=owner_user_id, access_token=access_token)
        if preview is None:
            raise ProblemException(
                title="Not Found",
                detail="Preview session not found for the current user.",
                status_code=404,
            )
        preview = self._expire_if_needed(preview, owner_user_id=owner_user_id, access_token=access_token)
        if preview.get("deleted_at"):
            raise ProblemException(
                title="Preview Expired",
                detail="The preview session has expired and its artifacts were deleted. Generate a fresh preview from the saved configuration.",
                status_code=410,
            )
        current_session = self._uploads.get_session(
            str(preview["upload_id"]),
            owner_user_id=owner_user_id,
            access_token=access_token,
        )
        return self._response_payload(preview, current_session=current_session)

    def _require_preview_ready_upload(self, session: dict[str, Any] | None) -> dict[str, Any]:
        if session is None:
            raise ProblemException(
                title="Not Found",
                detail="Upload session not found for the current user.",
                status_code=404,
            )
        if session["status"] != UploadStatus.COMPLETED.value:
            raise ProblemException(
                title="Upload Not Ready",
                detail="Preview generation requires a completed upload and a saved launch configuration.",
                status_code=409,
            )
        return session

    def _saved_launch_snapshot(self, session: dict[str, Any]) -> dict[str, Any]:
        launch_config = session.get("launch_config") if isinstance(session.get("launch_config"), dict) else {}
        job_payload_preview = launch_config.get("job_payload_preview")
        configured_at = session.get("configured_at")
        if not isinstance(job_payload_preview, dict) or not job_payload_preview or not configured_at:
            raise ProblemException(
                title="Configuration Not Ready",
                detail="Preview generation requires the latest saved Packet 4B configuration.",
                status_code=409,
            )
        checksum = str(job_payload_preview.get("source_asset_checksum") or session.get("checksum_sha256") or "")
        if not checksum:
            raise ProblemException(
                title="Configuration Not Ready",
                detail="Preview generation requires a saved source checksum from the upload session.",
                status_code=409,
            )
        configured_at_snapshot = str(configured_at)
        configuration_fingerprint = _sha256(
            _canonical_json({"configured_at": configured_at_snapshot, "job_payload_preview": job_payload_preview})
        )
        configuration_cache_fingerprint = _preview_configuration_cache_fingerprint(job_payload_preview)
        if configuration_cache_fingerprint is None:
            raise ProblemException(
                title="Configuration Not Ready",
                detail="Preview generation requires a saved launch payload from the latest configuration.",
                status_code=409,
            )
        cache_key = _sha256(
            _canonical_json(
                {
                    "upload_id": session["upload_id"],
                    "configured_at_snapshot": configured_at_snapshot,
                }
            )
        )
        return {
            "job_payload_preview": job_payload_preview,
            "configured_at": configured_at_snapshot,
            "configured_at_snapshot": configured_at_snapshot,
            "source_asset_checksum": checksum,
            "preview_id": _preview_id_for_snapshot(
                upload_id=str(session["upload_id"]),
                configured_at_snapshot=configured_at_snapshot,
            ),
            "configuration_fingerprint": configuration_fingerprint,
            "configuration_cache_fingerprint": configuration_cache_fingerprint,
            "cache_key": cache_key,
        }

    def _build_preview_record(
        self,
        *,
        session: dict[str, Any],
        snapshot: dict[str, Any],
        owner_user_id: str,
        estimate_summary: dict[str, Any],
        reusable_preview: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        preview_id = str(snapshot["preview_id"])
        duration_seconds = int(snapshot["job_payload_preview"]["estimated_duration_seconds"])
        if reusable_preview is None:
            selection = self._select_keyframes(
                source_asset_checksum=str(snapshot["source_asset_checksum"]),
                duration_seconds=duration_seconds,
                preview_id=preview_id,
            )
            keyframes = selection.keyframes
            selection_mode = selection.selection_mode
            scene_diversity = selection.scene_diversity
            preview_root_uri = self._bucket_uri(f"previews/{preview_id}/")
        else:
            keyframes = list(reusable_preview.get("keyframes") or [])
            selection_mode = str(reusable_preview["selection_mode"])
            scene_diversity = float(reusable_preview.get("scene_diversity", 0.0) or 0.0)
            preview_root_uri = str(reusable_preview["preview_root_uri"])
        expires_at = _utc_now() + timedelta(hours=_PREVIEW_RETENTION_HOURS)
        return {
            "preview_id": preview_id,
            "upload_id": session["upload_id"],
            "owner_user_id": owner_user_id,
            "org_id": session["org_id"],
            "status": "ready",
            "configured_at_snapshot": snapshot["configured_at_snapshot"],
            "configuration_fingerprint": snapshot["configuration_fingerprint"],
            "configuration_cache_fingerprint": snapshot["configuration_cache_fingerprint"],
            "source_asset_checksum": snapshot["source_asset_checksum"],
            "cache_key": snapshot["cache_key"],
            "job_payload_preview": snapshot["job_payload_preview"],
            "selection_mode": selection_mode,
            "scene_diversity": scene_diversity,
            "keyframe_count": len(keyframes),
            "estimated_cost_summary": estimate_summary,
            "estimated_processing_time_seconds": self._estimated_processing_time_seconds(duration_seconds),
            "keyframes": keyframes,
            "preview_root_uri": preview_root_uri,
            "expires_at": _isoformat(expires_at),
            "deleted_at": None,
        }

    def _select_keyframes(
        self,
        *,
        source_asset_checksum: str,
        duration_seconds: int,
        preview_id: str,
    ) -> _SelectionSnapshot:
        try:
            return self._scene_aware_selection(
                source_asset_checksum=source_asset_checksum,
                duration_seconds=duration_seconds,
                preview_id=preview_id,
            )
        except Exception:
            return self._uniform_selection(duration_seconds=duration_seconds, preview_id=preview_id)

    def _scene_aware_selection(
        self,
        *,
        source_asset_checksum: str,
        duration_seconds: int,
        preview_id: str,
    ) -> _SelectionSnapshot:
        scene_centers = self._detect_scene_centers(
            source_asset_checksum=source_asset_checksum,
            duration_seconds=duration_seconds,
        )
        selected_indexes = self._spread_indexes(len(scene_centers), _TARGET_KEYFRAME_COUNT)
        keyframes = [
            self._build_keyframe(
                preview_id=preview_id,
                index=keyframe_index,
                timestamp_seconds=scene_centers[scene_index],
                scene_number=scene_index + 1,
                confidence_score=self._confidence_for(source_asset_checksum, scene_index),
            )
            for keyframe_index, scene_index in enumerate(selected_indexes)
        ]
        return _SelectionSnapshot(
            selection_mode="scene_aware",
            scene_diversity=self._scene_diversity(keyframes),
            keyframes=keyframes,
        )

    def _uniform_selection(self, *, duration_seconds: int, preview_id: str) -> _SelectionSnapshot:
        interval = max(duration_seconds / _TARGET_KEYFRAME_COUNT, 0.1)
        keyframes = [
            self._build_keyframe(
                preview_id=preview_id,
                index=index,
                timestamp_seconds=round(min((interval * index) + (interval / 2), max(duration_seconds - 0.01, 0.0)), 3),
                scene_number=index + 1,
                confidence_score=0.55,
            )
            for index in range(_TARGET_KEYFRAME_COUNT)
        ]
        return _SelectionSnapshot(
            selection_mode="uniform_fallback",
            scene_diversity=self._scene_diversity(keyframes),
            keyframes=keyframes,
        )

    def _detect_scene_centers(self, *, source_asset_checksum: str, duration_seconds: int) -> list[float]:
        digest = hashlib.sha256(source_asset_checksum.encode("utf-8")).digest()
        scene_count = max(_TARGET_KEYFRAME_COUNT + 4, 12)
        centers: list[float] = []
        slot_width = max(duration_seconds / scene_count, 0.1)
        for idx in range(scene_count):
            slot_start = slot_width * idx
            slot_end = min(slot_width * (idx + 1), float(duration_seconds))
            midpoint = (slot_start + slot_end) / 2
            jitter_window = max((slot_end - slot_start) * 0.22, 0.02)
            jitter = ((digest[idx % len(digest)] / 255.0) - 0.5) * 2 * jitter_window
            timestamp = max(min(midpoint + jitter, max(slot_end - 0.01, 0.0)), min(slot_start + 0.01, slot_end))
            centers.append(round(timestamp, 3))
        return centers

    def _spread_indexes(self, total_items: int, desired_items: int) -> list[int]:
        if total_items <= desired_items:
            return list(range(total_items))
        indexes: list[int] = []
        for item in range(desired_items):
            raw = round(item * (total_items - 1) / max(desired_items - 1, 1))
            candidate = int(raw)
            if indexes and candidate <= indexes[-1]:
                candidate = min(indexes[-1] + 1, total_items - 1)
            indexes.append(candidate)
        return indexes[:desired_items]

    def _confidence_for(self, checksum: str, scene_index: int) -> float:
        digest = hashlib.sha256(f"{checksum}:{scene_index}".encode("utf-8")).digest()
        return round(0.65 + ((digest[0] / 255.0) * 0.3), 3)

    def _scene_diversity(self, keyframes: list[dict[str, Any]]) -> float:
        if len(keyframes) < 2:
            return 0.0
        timestamps = sorted(float(item["timestamp_seconds"]) for item in keyframes)
        gaps = [timestamps[idx + 1] - timestamps[idx] for idx in range(len(timestamps) - 1)]
        average_gap = sum(gaps) / len(gaps)
        if average_gap <= 0:
            return 0.0
        mean_abs_deviation = sum(abs(gap - average_gap) for gap in gaps) / len(gaps)
        diversity = max(0.0, min(1.0, 1.0 - (mean_abs_deviation / (average_gap * 1.5))))
        return round(diversity, 3)

    def _build_keyframe(
        self,
        *,
        preview_id: str,
        index: int,
        timestamp_seconds: float,
        scene_number: int,
        confidence_score: float,
    ) -> dict[str, Any]:
        return {
            "index": index,
            "timestamp_seconds": round(timestamp_seconds, 3),
            "scene_number": scene_number,
            "confidence_score": round(confidence_score, 3),
            "thumbnail_uri": self._bucket_uri(
                f"previews/{preview_id}/thumbnails/keyframe-{index:02d}-320x180.jpg"
            ),
            "frame_uri": self._bucket_uri(
                f"previews/{preview_id}/frames/keyframe-{index:02d}.jpg"
            ),
        }

    def _response_payload(
        self,
        preview: dict[str, Any],
        *,
        current_session: dict[str, Any] | None,
    ) -> dict[str, Any]:
        current_fingerprint = None
        if current_session is not None:
            try:
                current_fingerprint = self._saved_launch_snapshot(current_session)["configuration_fingerprint"]
            except ProblemException:
                current_fingerprint = None
        expires_at = datetime.fromisoformat(str(preview["expires_at"]))
        try:
            keyframes = [
                {
                    "index": item["index"],
                    "timestamp_seconds": item["timestamp_seconds"],
                    "scene_number": item["scene_number"],
                    "confidence_score": item["confidence_score"],
                    "thumbnail_url": self._signed_preview_url(
                        object_uri=str(item["thumbnail_uri"]),
                        file_name=f"preview-{preview['preview_id']}-thumbnail-{item['index']:02d}.jpg",
                        expires_at=expires_at,
                    ),
                    "frame_url": self._signed_preview_url(
                        object_uri=str(item["frame_uri"]),
                        file_name=f"preview-{preview['preview_id']}-frame-{item['index']:02d}.jpg",
                        expires_at=expires_at,
                    ),
                }
                for item in preview.get("keyframes") or []
            ]
        except PreviewStorageUnavailableError as exc:
            raise ProblemException(
                title="Preview Storage Unavailable",
                detail="Preview storage or signing is temporarily unavailable. Retry the request once preview delivery is available.",
                status_code=503,
            ) from exc
        return {
            "preview_id": preview["preview_id"],
            "upload_id": preview["upload_id"],
            "status": preview["status"],
            "configuration_fingerprint": preview["configuration_fingerprint"],
            "stale": current_fingerprint is not None and current_fingerprint != preview["configuration_fingerprint"],
            "expires_at": preview["expires_at"],
            "selection_mode": preview["selection_mode"],
            "scene_diversity": preview["scene_diversity"],
            "keyframe_count": preview["keyframe_count"],
            "estimated_cost_summary": preview["estimated_cost_summary"],
            "estimated_processing_time_seconds": preview["estimated_processing_time_seconds"],
            "keyframes": keyframes,
        }

    def _expire_if_needed(
        self,
        preview: dict[str, Any],
        *,
        owner_user_id: str,
        access_token: str,
    ) -> dict[str, Any]:
        expires_at = datetime.fromisoformat(str(preview["expires_at"]))
        if preview.get("deleted_at") or expires_at >= _utc_now():
            return preview
        updated = self._previews.update_preview(
            str(preview["preview_id"]),
            owner_user_id=owner_user_id,
            patch={"deleted_at": _isoformat(_utc_now())},
            access_token=access_token,
        )
        if updated is not None:
            return updated
        expired_preview = dict(preview)
        expired_preview["deleted_at"] = _isoformat(_utc_now())
        return expired_preview

    def _is_active_preview(
        self,
        preview: dict[str, Any] | None,
        *,
        expected_configuration_fingerprint: str | None = None,
    ) -> bool:
        if not preview:
            return False
        if preview.get("status") != "ready" or preview.get("deleted_at") is not None:
            return False
        if (
            expected_configuration_fingerprint is not None
            and str(preview.get("configuration_fingerprint"))
            != expected_configuration_fingerprint
        ):
            return False
        expires_at_raw = preview.get("expires_at")
        if not expires_at_raw:
            return False
        return datetime.fromisoformat(str(expires_at_raw)) > _utc_now()

    def _estimated_processing_time_seconds(self, duration_seconds: int) -> int:
        return max(2, min(6, int(round(max(duration_seconds, 1) / 90.0)) + 1))
    def _bucket_uri(self, path: str) -> str:
        bucket_name = settings.gcs_bucket_name or "chronos-refine-previews"
        return f"gs://{bucket_name}/{path}"
    def _sign_value(self, value: str) -> str:
        insecure_defaults = {"", "chronos-output-delivery-test-secret", "chronos-output-delivery-dev-secret"}
        if settings.environment not in {"test", "dev", "development"} and settings.output_delivery_signing_secret in insecure_defaults:
            raise PreviewStorageUnavailableError("Preview signing secret is unavailable.")
        return hmac.new(settings.output_delivery_signing_secret.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()
    def _signed_preview_url(self, *, object_uri: str, file_name: str, expires_at: datetime) -> str:
        if object_uri.startswith("gs://"):
            _, _, path = object_uri.partition("gs://")
            bucket_name, _, object_path = path.partition("/")
        else:
            bucket_name = settings.gcs_bucket_name or "chronos-refine-previews"
            object_path = object_uri.lstrip("/")
        request_time = _utc_now()
        request_timestamp = request_time.strftime("%Y%m%dT%H%M%SZ")
        credential_date = request_time.strftime("%Y%m%d")
        expires_seconds = max(
            min(int((expires_at - request_time).total_seconds()), _PREVIEW_URL_TTL_HOURS * 3600),
            1,
        )
        credential = f"preview-signer/{credential_date}/auto/storage/goog4_request"
        canonical_path = f"/download/storage/v1/b/{bucket_name}/o/{quote(object_path, safe='')}"
        string_to_sign = "\n".join(
            [
                "GOOG4-HMAC-SHA256",
                request_timestamp,
                credential,
                f"{bucket_name}/{object_path}/{file_name}/{expires_seconds}",
            ]
        )
        signature = self._sign_value(string_to_sign)
        return (
            f"https://storage.googleapis.com{canonical_path}"
            f"?response-content-disposition=attachment%3B%20filename%3D%22{quote(file_name)}%22"
            f"&X-Goog-Algorithm=GOOG4-HMAC-SHA256"
            f"&X-Goog-Credential={quote(credential, safe='')}"
            f"&X-Goog-Date={request_timestamp}"
            f"&X-Goog-Expires={expires_seconds}"
            f"&X-Goog-SignedHeaders=host"
            f"&X-Goog-Signature={signature}"
        )
