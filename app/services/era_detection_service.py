"""Era-detection orchestration for Packet C."""

from __future__ import annotations

import logging
import time
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx

from app.config import settings
from app.db.phase2_store import EraDetectionRepository
from app.observability.monitoring import record_era_detection
from app.services.era_classifier import (
    ClassifierError,
    ERA_CATALOG,
    UNKNOWN_ERA,
    DeterministicFallbackEraClassifier,
    EraClassification,
    EraClassifier,
    build_default_era_profile,
    canonicalize_era_label,
    normalize_top_candidates,
)
from app.services.vertex_gemini import VertexGeminiEraClassifier

_LOGGER = logging.getLogger("chronos.era_detection")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _primary_classifier() -> EraClassifier:
    if settings.enable_real_gemini:
        return VertexGeminiEraClassifier()
    return DeterministicFallbackEraClassifier()


class EraDetectionService:
    def __init__(self) -> None:
        self._repo = EraDetectionRepository()
        self._classifier = _primary_classifier()
        self._fallback_classifier = DeterministicFallbackEraClassifier()

    def supported_eras(self) -> list[str]:
        return list(ERA_CATALOG)

    def is_supported_era(self, era: str | None) -> bool:
        return canonicalize_era_label(era) in ERA_CATALOG

    def detect(
        self,
        *,
        job_id: str,
        user_id: str,
        org_id: str,
        media_uri: str,
        original_filename: str,
        mime_type: str,
        payload: dict[str, object],
        access_token: str | None = None,
    ) -> dict[str, object]:
        started = time.perf_counter()
        era_profile = payload["era_profile"]
        self._repo.save_job(
            job_id=job_id,
            owner_user_id=user_id,
            org_id=org_id,
            media_uri=media_uri,
            original_filename=original_filename,
            mime_type=mime_type,
            era_profile=era_profile,
            access_token=access_token,
        )

        provider_warning: str | None = None
        classification = self._classify(
            job_id=job_id,
            media_uri=media_uri,
            original_filename=original_filename,
            mime_type=mime_type,
            era_profile=era_profile,
        )
        if classification.provider_error:
            provider_warning = classification.provider_error

        system_detection = self._persist_system_detection(
            job_id=job_id,
            user_id=user_id,
            classification=classification,
            provider_warning=provider_warning,
            access_token=access_token,
        )

        response_detection = system_detection
        manual_override_era = payload.get("manual_override_era")
        if manual_override_era:
            canonical_override_era = canonicalize_era_label(str(manual_override_era))
            if canonical_override_era is None:
                raise ValueError("Manual override era must use a supported catalog value.")
            response_detection = self._persist_override_detection(
                job_id=job_id,
                user_id=user_id,
                selected_era=canonical_override_era,
                override_reason=str(payload.get("override_reason") or "Manual era override"),
                classification=classification,
                access_token=access_token,
            )

        latency_ms = (time.perf_counter() - started) * 1000
        record_era_detection(
            latency_ms=latency_ms,
            confidence=float(classification.confidence),
            manual_override=bool(manual_override_era),
            api_calls=classification.usage.api_call_count,
            total_tokens=classification.usage.total_token_count,
            provider_fallback=provider_warning is not None,
        )
        _LOGGER.info(
            "era-detection-complete job_id=%s user_id=%s era=%s confidence=%.2f latency_ms=%.2f",
            job_id,
            user_id,
            response_detection["era"],
            response_detection["confidence"],
            latency_ms,
        )
        warnings = list(response_detection["warnings"])
        if manual_override_era:
            warnings.append("Manual override applied to era classification.")
        return {
            "detection_id": response_detection["detection_id"],
            "job_id": job_id,
            "era": response_detection["era"],
            "confidence": response_detection["confidence"],
            "manual_confirmation_required": response_detection["manual_confirmation_required"],
            "top_candidates": response_detection["top_candidates"],
            "forensic_markers": response_detection["forensic_markers"],
            "warnings": warnings,
            "processing_timestamp": _utc_now(),
            "source": response_detection["source"],
            "model_version": response_detection["model_version"],
            "prompt_version": response_detection["prompt_version"],
        }

    def analyze_media(
        self,
        *,
        job_id: str,
        media_uri: str,
        original_filename: str,
        mime_type: str,
        manual_override_era: str | None = None,
        override_reason: str | None = None,
        era_profile: dict[str, Any] | None = None,
    ) -> dict[str, object]:
        resolved_era_profile = era_profile or build_default_era_profile(
            media_uri=media_uri,
            original_filename=original_filename,
            mime_type=mime_type,
        )
        classification = self._classify(
            job_id=job_id,
            media_uri=media_uri,
            original_filename=original_filename,
            mime_type=mime_type,
            era_profile=resolved_era_profile,
        )
        provider_warning = classification.provider_error
        low_confidence = classification.confidence < 0.70
        warnings: list[str] = []
        if provider_warning:
            warnings.append(provider_warning)
        elif low_confidence:
            warnings.append("Manual confirmation required due to low confidence.")

        if manual_override_era:
            canonical_override_era = canonicalize_era_label(manual_override_era)
            if canonical_override_era is None:
                raise ValueError("Manual override era must use a supported catalog value.")
            if not override_reason:
                raise ValueError("override_reason is required when manual_override_era is set.")
            return {
                "detection_id": str(uuid4()),
                "job_id": job_id,
                "era": canonical_override_era,
                "confidence": round(classification.confidence, 2),
                "manual_confirmation_required": False,
                "top_candidates": classification.top_candidates if low_confidence else [],
                "forensic_markers": classification.forensic_markers,
                "warnings": ["Manual override applied to era classification."],
                "processing_timestamp": _utc_now(),
                "source": "user_override",
                "model_version": classification.model_version,
                "prompt_version": classification.prompt_version,
            }

        return {
            "detection_id": str(uuid4()),
            "job_id": job_id,
            "era": UNKNOWN_ERA if provider_warning or low_confidence else classification.era,
            "confidence": round(classification.confidence, 2),
            "manual_confirmation_required": provider_warning is not None or low_confidence,
            "top_candidates": classification.top_candidates if (provider_warning or low_confidence) else [],
            "forensic_markers": classification.forensic_markers,
            "warnings": warnings,
            "processing_timestamp": _utc_now(),
            "source": "system",
            "model_version": classification.model_version,
            "prompt_version": classification.prompt_version,
        }

    def _classify(
        self,
        *,
        job_id: str,
        media_uri: str,
        original_filename: str,
        mime_type: str,
        era_profile: dict[str, Any],
    ) -> EraClassification:
        try:
            classification = self._classifier.classify(
                job_id=job_id,
                media_uri=media_uri,
                original_filename=original_filename,
                mime_type=mime_type,
                era_profile=era_profile,
            )
            return self._normalize_classification(
                classification=classification,
                job_id=job_id,
                media_uri=media_uri,
                original_filename=original_filename,
                mime_type=mime_type,
                era_profile=era_profile,
            )
        except (ClassifierError, httpx.HTTPError) as exc:
            fallback = self._fallback_classifier.classify(
                job_id=job_id,
                media_uri=media_uri,
                original_filename=original_filename,
                mime_type=mime_type,
                era_profile=era_profile,
            )
            _LOGGER.warning("era-detection-provider-fallback job_id=%s reason=%s", job_id, exc)
            return EraClassification(
                era=fallback.era,
                confidence=fallback.confidence,
                forensic_markers=fallback.forensic_markers,
                top_candidates=fallback.top_candidates,
                model_version=fallback.model_version,
                prompt_version=fallback.prompt_version,
                raw_response=fallback.raw_response,
                raw_response_gcs_uri=fallback.raw_response_gcs_uri,
                usage=fallback.usage,
                provider_error="Primary Gemini classifier failed. Manual confirmation required.",
            )

    def _normalize_classification(
        self,
        *,
        classification: EraClassification,
        job_id: str,
        media_uri: str,
        original_filename: str,
        mime_type: str,
        era_profile: dict[str, Any],
    ) -> EraClassification:
        fallback = self._fallback_classifier.classify(
            job_id=job_id,
            media_uri=media_uri,
            original_filename=original_filename,
            mime_type=mime_type,
            era_profile=era_profile,
        )
        normalized_era = canonicalize_era_label(classification.era)
        review_candidates = self._review_candidates(
            classification=classification,
            fallback_candidates=fallback.top_candidates,
            primary_era=normalized_era,
        )
        if normalized_era is None:
            provider_error = classification.provider_error or (
                "Primary Gemini classifier returned an unsupported era label. Manual confirmation required."
            )
            return replace(
                classification,
                era=UNKNOWN_ERA,
                top_candidates=review_candidates,
                provider_error=provider_error,
            )
        return replace(
            classification,
            era=normalized_era,
            top_candidates=review_candidates,
        )

    def _review_candidates(
        self,
        *,
        classification: EraClassification,
        fallback_candidates: list[dict[str, Any]],
        primary_era: str | None,
    ) -> list[dict[str, Any]]:
        normalized = normalize_top_candidates(classification.top_candidates)
        if primary_era and primary_era in ERA_CATALOG and all(item["era"] != primary_era for item in normalized):
            normalized.insert(0, {"era": primary_era, "confidence": round(classification.confidence, 2)})
        fallback_normalized = normalize_top_candidates(fallback_candidates)
        for item in fallback_normalized:
            if all(existing["era"] != item["era"] for existing in normalized):
                normalized.append(item)
            if len(normalized) == 3:
                break
        return normalized[:3]

    def _persist_system_detection(
        self,
        *,
        job_id: str,
        user_id: str,
        classification: EraClassification,
        provider_warning: str | None,
        access_token: str | None,
    ) -> dict[str, object]:
        _ = user_id
        low_confidence = classification.confidence < 0.70
        warnings: list[str] = []
        if provider_warning:
            warnings.append(provider_warning)
        elif low_confidence:
            warnings.append("Manual confirmation required due to low confidence.")
        detection = self._repo.save_detection(
            job_id=job_id,
            detection={
                "job_id": job_id,
                "era": UNKNOWN_ERA if provider_warning or low_confidence else classification.era,
                "confidence": round(classification.confidence, 2),
                "forensic_markers": classification.forensic_markers,
                "overridden_by_user": False,
                "override_reason": None,
                "model_version": classification.model_version,
                "prompt_version": classification.prompt_version,
                "source": "system",
                "raw_response_gcs_uri": classification.raw_response_gcs_uri,
                "created_by": None,
                "manual_confirmation_required": provider_warning is not None or low_confidence,
                "top_candidates": classification.top_candidates if (provider_warning or low_confidence) else [],
                "prompt_token_count": classification.usage.prompt_token_count,
                "candidates_token_count": classification.usage.candidates_token_count,
                "total_token_count": classification.usage.total_token_count,
                "api_call_count": classification.usage.api_call_count,
            },
            access_token=access_token,
        )
        return {
            "detection_id": detection["id"],
            "era": detection["era"],
            "confidence": round(float(detection["confidence"]), 2),
            "manual_confirmation_required": detection.get("manual_confirmation_required", False),
            "top_candidates": detection.get("top_candidates") or [],
            "forensic_markers": detection["forensic_markers"],
            "warnings": warnings,
            "source": detection["source"],
            "model_version": detection["model_version"],
            "prompt_version": detection["prompt_version"],
        }

    def _persist_override_detection(
        self,
        *,
        job_id: str,
        user_id: str,
        selected_era: str,
        override_reason: str,
        classification: EraClassification,
        access_token: str | None,
    ) -> dict[str, object]:
        detection = self._repo.save_detection(
            job_id=job_id,
            detection={
                "job_id": job_id,
                "era": selected_era,
                "confidence": round(classification.confidence, 2),
                "forensic_markers": classification.forensic_markers,
                "overridden_by_user": True,
                "override_reason": override_reason,
                "model_version": classification.model_version,
                "prompt_version": classification.prompt_version,
                "source": "user_override",
                "raw_response_gcs_uri": classification.raw_response_gcs_uri,
                "created_by": user_id,
                "manual_confirmation_required": False,
                "top_candidates": classification.top_candidates if classification.confidence < 0.70 else [],
                "prompt_token_count": 0,
                "candidates_token_count": 0,
                "total_token_count": 0,
                "api_call_count": 0,
            },
            access_token=access_token,
        )
        return {
            "detection_id": detection["id"],
            "era": detection["era"],
            "confidence": round(float(detection["confidence"]), 2),
            "manual_confirmation_required": False,
            "top_candidates": detection.get("top_candidates") or [],
            "forensic_markers": detection["forensic_markers"],
            "warnings": [],
            "source": detection["source"],
            "model_version": detection["model_version"],
            "prompt_version": detection["prompt_version"],
        }
