"""Upload-scoped fidelity configuration orchestration for Packet 4B."""

from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.api.contracts import FidelityTier, GrainPreset, JobCreateRequest, UploadStatus, UserPersona
from app.api.problem_details import ProblemException
from app.db.phase2_store import UploadRepository, UserProfileRepository
from app.models.processing import ReproducibilityMode
from app.services.billing_service import billable_minutes_for_duration
from app.services.era_classifier import UNKNOWN_ERA, canonicalize_era_label, infer_capture_medium
from app.services.era_detection_service import EraDetectionService
from app.services.fidelity_profiles import (
    allowed_grain_presets_for_tier,
    default_tier_for_persona,
    fidelity_profile_for,
    persona_catalog,
    relative_cost_multiplier_for_tier,
    relative_processing_time_band_for_tier,
    resolve_fidelity_profile,
    tier_catalog,
)
from app.validation.schema_validation import validate_era_profile

_FIDELITY_PREFERENCE_KEY = "fidelity_configuration"
_DEFAULT_DETECTION_TIER = FidelityTier.RESTORE
_PLAN_TIER_CANONICAL = {
    "hobbyist": "Hobbyist",
    "pro": "Pro",
    "museum": "Museum",
}
_ERA_CAPTURE_MEDIUM = {
    "1840s Daguerreotype Plate": "daguerreotype",
    "1860s Albumen Print": "albumen",
    "1930s 16mm Film": "16mm",
    "1950s Kodachrome Film": "kodachrome",
    "1960s Kodachrome Film": "kodachrome",
    "1970s Super 8 Film": "super_8",
    "1980s VHS Tape": "vhs",
    "1990s VHS Tape": "vhs",
}
_ERA_RANGE = {
    "1840s Daguerreotype Plate": {"start_year": 1840, "end_year": 1849},
    "1860s Albumen Print": {"start_year": 1860, "end_year": 1869},
    "1930s 16mm Film": {"start_year": 1930, "end_year": 1939},
    "1950s Kodachrome Film": {"start_year": 1950, "end_year": 1959},
    "1960s Kodachrome Film": {"start_year": 1960, "end_year": 1969},
    "1970s Super 8 Film": {"start_year": 1970, "end_year": 1979},
    "1980s VHS Tape": {"start_year": 1980, "end_year": 1989},
    "1990s VHS Tape": {"start_year": 1990, "end_year": 1999},
}
_LOGGER = logging.getLogger("chronos.configuration")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_plan_tier(plan_tier: str) -> str:
    return _PLAN_TIER_CANONICAL.get(plan_tier.strip().lower(), "Pro")


def _preferences_from_profile(profile: dict[str, Any]) -> dict[str, Any]:
    preferences = profile.get("preferences")
    return dict(preferences) if isinstance(preferences, dict) else {}


def _fidelity_preferences(profile: dict[str, Any]) -> dict[str, Any]:
    preferences = _preferences_from_profile(profile)
    fidelity_preferences = preferences.get(_FIDELITY_PREFERENCE_KEY)
    return dict(fidelity_preferences) if isinstance(fidelity_preferences, dict) else {}


def _safe_persona(raw_persona: Any) -> UserPersona | None:
    if not raw_persona:
        return None
    try:
        return UserPersona(str(raw_persona))
    except ValueError:
        return None


def _safe_tier(raw_tier: Any) -> FidelityTier | None:
    if not raw_tier:
        return None
    try:
        return FidelityTier(str(raw_tier))
    except ValueError:
        return None


def _safe_grain(raw_grain: Any) -> GrainPreset | None:
    if not raw_grain:
        return None
    try:
        return GrainPreset(str(raw_grain))
    except ValueError:
        return None


def _persona_from_preferences(profile: dict[str, Any]) -> UserPersona | None:
    return _safe_persona(_fidelity_preferences(profile).get("persona"))


def _preferred_tier_from_preferences(profile: dict[str, Any]) -> FidelityTier | None:
    return _safe_tier(_fidelity_preferences(profile).get("preferred_fidelity_tier"))


def _preferred_grain_from_preferences(profile: dict[str, Any]) -> GrainPreset | None:
    return _safe_grain(_fidelity_preferences(profile).get("preferred_grain_preset"))


def _allowed_tiers_for_plan(plan_tier: str) -> list[FidelityTier]:
    if plan_tier.strip().lower() == "hobbyist":
        return [FidelityTier.ENHANCE]
    return list(FidelityTier)


def _coerce_tier_for_plan(
    tier: FidelityTier | None,
    *,
    plan_tier: str,
) -> FidelityTier | None:
    if tier is None:
        return None
    return tier if tier in _allowed_tiers_for_plan(plan_tier) else FidelityTier.ENHANCE


def _default_grain_preset_for_tier(tier: FidelityTier) -> GrainPreset:
    return GrainPreset(fidelity_profile_for(tier).grain_preset)


def _catalog_preferred_tier(profile: dict[str, Any], *, plan_tier: str) -> FidelityTier | None:
    preferred = _coerce_tier_for_plan(_preferred_tier_from_preferences(profile), plan_tier=plan_tier)
    if preferred is not None:
        return preferred
    if plan_tier.strip().lower() == "hobbyist":
        return FidelityTier.ENHANCE
    return None


def _catalog_preferred_grain(profile: dict[str, Any], *, plan_tier: str) -> GrainPreset | None:
    preferred_tier = _catalog_preferred_tier(profile, plan_tier=plan_tier)
    if preferred_tier is None:
        return None
    preferred_grain = _preferred_grain_from_preferences(profile)
    if preferred_grain in allowed_grain_presets_for_tier(preferred_tier):
        return preferred_grain
    return _default_grain_preset_for_tier(preferred_tier)


def _merge_fidelity_preferences(
    profile: dict[str, Any],
    *,
    persona: UserPersona,
    fidelity_tier: FidelityTier,
    grain_preset: GrainPreset,
) -> dict[str, Any]:
    preferences = _preferences_from_profile(profile)
    existing = _fidelity_preferences(profile)
    preferences[_FIDELITY_PREFERENCE_KEY] = {
        **existing,
        "persona": persona.value,
        "preferred_fidelity_tier": fidelity_tier.value,
        "preferred_grain_preset": grain_preset.value,
    }
    return preferences


def _resolve_detection_tier_hint(profile: dict[str, Any], *, plan_tier: str) -> FidelityTier:
    preferred = _coerce_tier_for_plan(_preferred_tier_from_preferences(profile), plan_tier=plan_tier)
    if preferred is not None:
        return preferred
    persona = _persona_from_preferences(profile)
    if persona is not None:
        return _coerce_tier_for_plan(default_tier_for_persona(persona), plan_tier=plan_tier) or FidelityTier.ENHANCE
    return _coerce_tier_for_plan(_DEFAULT_DETECTION_TIER, plan_tier=plan_tier) or FidelityTier.ENHANCE


def _require_completed_upload(session: dict[str, Any] | None) -> dict[str, Any]:
    if session is None:
        raise ProblemException(
            title="Not Found",
            detail="Upload session not found for the current user.",
            status_code=404,
        )
    if session["status"] != UploadStatus.COMPLETED.value:
        raise ProblemException(
            title="Upload Not Ready",
            detail="Finalize the upload before running era detection or saving configuration.",
            status_code=409,
        )
    return session


def _stored_detection_matches_request(stored: dict[str, Any], payload: dict[str, object]) -> bool:
    return (
        stored.get("estimated_duration_seconds") == int(payload["estimated_duration_seconds"])
        and stored.get("manual_override_era") == payload.get("manual_override_era")
        and stored.get("override_reason") == payload.get("override_reason")
    )


def _capture_medium_for_detection(session: dict[str, Any], detection_snapshot: dict[str, Any]) -> str:
    era = str(detection_snapshot.get("era") or "")
    if era and era != UNKNOWN_ERA and era in _ERA_CAPTURE_MEDIUM:
        return _ERA_CAPTURE_MEDIUM[era]
    top_candidates = detection_snapshot.get("top_candidates") or []
    if top_candidates:
        candidate_era = str(top_candidates[0].get("era") or "")
        if candidate_era in _ERA_CAPTURE_MEDIUM:
            return _ERA_CAPTURE_MEDIUM[candidate_era]
    return infer_capture_medium(
        media_uri=str(session["media_uri"]),
        original_filename=str(session["original_filename"]),
        mime_type=str(session["mime_type"]),
    )


def _era_range_for_detection(capture_medium: str, detection_snapshot: dict[str, Any]) -> dict[str, int]:
    era = str(detection_snapshot.get("era") or "")
    if era in _ERA_RANGE:
        return dict(_ERA_RANGE[era])
    top_candidates = detection_snapshot.get("top_candidates") or []
    if top_candidates:
        candidate_era = str(top_candidates[0].get("era") or "")
        if candidate_era in _ERA_RANGE:
            return dict(_ERA_RANGE[candidate_era])
    if capture_medium == "daguerreotype":
        return {"start_year": 1840, "end_year": 1849}
    if capture_medium == "albumen":
        return {"start_year": 1860, "end_year": 1869}
    if capture_medium == "16mm":
        return {"start_year": 1930, "end_year": 1939}
    if capture_medium == "kodachrome":
        return {"start_year": 1955, "end_year": 1969}
    if capture_medium == "vhs":
        return {"start_year": 1980, "end_year": 1999}
    return {"start_year": 1970, "end_year": 1979}


def _build_detection_snapshot(
    *,
    upload_id: str,
    detection: dict[str, object],
    session: dict[str, Any],
    estimated_duration_seconds: int,
    manual_override_era: str | None,
    override_reason: str | None,
    estimated_usage_minutes: int,
    capture_medium: str,
) -> dict[str, Any]:
    return {
        "detection_id": detection["detection_id"],
        "job_id": detection["job_id"],
        "upload_id": upload_id,
        "era": detection["era"],
        "confidence": detection["confidence"],
        "manual_confirmation_required": detection["manual_confirmation_required"],
        "top_candidates": detection["top_candidates"],
        "forensic_markers": detection["forensic_markers"],
        "warnings": detection["warnings"],
        "processing_timestamp": detection["processing_timestamp"],
        "source": detection["source"],
        "model_version": detection["model_version"],
        "prompt_version": detection["prompt_version"],
        "estimated_usage_minutes": estimated_usage_minutes,
        "estimated_duration_seconds": estimated_duration_seconds,
        "manual_override_era": manual_override_era,
        "override_reason": override_reason,
        "capture_medium": capture_medium,
        "media_uri": session["media_uri"],
        "original_filename": session["original_filename"],
        "mime_type": session["mime_type"],
    }


def _public_detection_response(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "upload_id": snapshot["upload_id"],
        "detection_id": snapshot["detection_id"],
        "job_id": snapshot["job_id"],
        "era": snapshot["era"],
        "confidence": snapshot["confidence"],
        "manual_confirmation_required": snapshot["manual_confirmation_required"],
        "top_candidates": snapshot["top_candidates"],
        "forensic_markers": snapshot["forensic_markers"],
        "warnings": snapshot["warnings"],
        "processing_timestamp": snapshot["processing_timestamp"],
        "source": snapshot["source"],
        "model_version": snapshot["model_version"],
        "prompt_version": snapshot["prompt_version"],
        "estimated_usage_minutes": snapshot["estimated_usage_minutes"],
    }


def _build_preview_era_profile(
    *,
    session: dict[str, Any],
    detection_snapshot: dict[str, Any],
    fidelity_tier: FidelityTier,
    grain_preset: GrainPreset,
    plan_tier: str,
) -> dict[str, Any]:
    capture_medium = _capture_medium_for_detection(session, detection_snapshot)
    fidelity_profile = fidelity_profile_for(fidelity_tier)
    era_profile = {
        "capture_medium": capture_medium,
        "mode": fidelity_tier.value,
        "tier": _canonical_plan_tier(plan_tier),
        "resolution_cap": "1080p" if plan_tier.strip().lower() == "hobbyist" else "4k",
        "hallucination_limit": fidelity_profile.hallucination_limit_max,
        "artifact_policy": {
            "deinterlace": capture_medium == "vhs",
            "grain_intensity": grain_preset.value,
            "preserve_edge_fog": fidelity_tier == FidelityTier.CONSERVE,
            "preserve_chromatic_aberration": fidelity_tier == FidelityTier.CONSERVE,
        },
        "era_range": _era_range_for_detection(capture_medium, detection_snapshot),
        "gemini_confidence": float(detection_snapshot["confidence"]),
        "manual_confirmation_required": bool(detection_snapshot["manual_confirmation_required"]),
    }
    validation = validate_era_profile(era_profile)
    if not validation.is_valid:
        raise ProblemException(
            title="Configuration Validation Failed",
            detail="The launch-ready configuration could not be validated against the canonical era profile schema.",
            status_code=400,
            errors=validation.as_problem_errors(),
        )
    return era_profile


def _ensure_plan_supports_capture_medium(*, capture_medium: str, plan_tier: str) -> None:
    if plan_tier.strip().lower() != "hobbyist":
        return
    if capture_medium not in {"daguerreotype", "albumen"}:
        return
    raise ProblemException(
        title="Plan Upgrade Required",
        detail="Early-photography assets require minimum 2k processing and therefore require Pro or higher.",
        status_code=403,
        errors=[
            {
                "field": "upload_id",
                "message": "Early-photography assets require Pro or higher because Hobbyist is limited to 1080p processing.",
                "rule_id": "FR-003",
            }
        ],
    )


def _ensure_plan_supports_fidelity_tier(*, fidelity_tier: FidelityTier, plan_tier: str) -> None:
    if plan_tier.strip().lower() != "hobbyist":
        return
    if fidelity_tier == FidelityTier.ENHANCE:
        return
    raise ProblemException(
        title="Plan Upgrade Required",
        detail="Hobbyist includes Enhance only in Packet 4B. Upgrade to Pro or higher to use Restore or Conserve.",
        status_code=403,
        errors=[
            {
                "field": "fidelity_tier",
                "message": "Hobbyist supports only the Enhance tier in Packet 4B.",
                "rule_id": "FR-003",
            }
        ],
    )


class ConfigurationService:
    def __init__(
        self,
        *,
        upload_repo: UploadRepository | None = None,
        user_profile_repo: UserProfileRepository | None = None,
        era_detection_service: EraDetectionService | None = None,
    ) -> None:
        self._upload_repo = upload_repo or UploadRepository()
        self._user_profile_repo = user_profile_repo or UserProfileRepository()
        self._era_detection_service = era_detection_service or EraDetectionService()

    def list_fidelity_tiers(
        self,
        *,
        user_id: str,
        role: str,
        plan_tier: str,
        org_id: str,
        access_token: str,
    ) -> dict[str, Any]:
        profile = self._user_profile_repo.get_or_create(
            user_id=user_id,
            role=role,
            plan_tier=plan_tier,
            org_id=org_id,
            access_token=access_token,
        )
        preferred_tier = _catalog_preferred_tier(profile, plan_tier=plan_tier)
        preferred_grain = _catalog_preferred_grain(profile, plan_tier=plan_tier)
        return {
            "personas": [item.model_dump() for item in persona_catalog()],
            "tiers": [item.model_dump() for item in tier_catalog() if item.tier in _allowed_tiers_for_plan(plan_tier)],
            "grain_presets": [preset.value for preset in GrainPreset],
            "current_persona": (_persona_from_preferences(profile).value if _persona_from_preferences(profile) else None),
            "preferred_fidelity_tier": preferred_tier.value if preferred_tier else None,
            "preferred_grain_preset": preferred_grain.value if preferred_grain else None,
        }

    def detect_upload_era(
        self,
        *,
        upload_id: str,
        user_id: str,
        role: str,
        plan_tier: str,
        org_id: str,
        payload: dict[str, object],
        access_token: str,
    ) -> dict[str, Any]:
        profile = self._user_profile_repo.get_or_create(
            user_id=user_id,
            role=role,
            plan_tier=plan_tier,
            org_id=org_id,
            access_token=access_token,
        )
        session = _require_completed_upload(
            self._upload_repo.get_session(upload_id, owner_user_id=user_id, access_token=access_token)
        )
        snapshot = self._detect_and_persist(
            upload_id=upload_id,
            session=session,
            profile=profile,
            payload=payload,
            owner_user_id=user_id,
            access_token=access_token,
        )
        return _public_detection_response(snapshot)

    def save_upload_configuration(
        self,
        *,
        upload_id: str,
        user_id: str,
        role: str,
        plan_tier: str,
        org_id: str,
        payload: dict[str, object],
        access_token: str,
    ) -> dict[str, Any]:
        profile = self._user_profile_repo.get_or_create(
            user_id=user_id,
            role=role,
            plan_tier=plan_tier,
            org_id=org_id,
            access_token=access_token,
        )
        session = _require_completed_upload(
            self._upload_repo.get_session(upload_id, owner_user_id=user_id, access_token=access_token)
        )

        persona = UserPersona(payload["persona"]) if payload.get("persona") else _persona_from_preferences(profile)
        if persona is None:
            raise ProblemException(
                title="Persona Required",
                detail="Select a persona before saving a launch-ready configuration.",
                status_code=400,
            )

        fidelity_tier = FidelityTier(payload["fidelity_tier"])
        grain_preset = GrainPreset(payload["grain_preset"])
        _ensure_plan_supports_fidelity_tier(fidelity_tier=fidelity_tier, plan_tier=plan_tier)
        if grain_preset not in allowed_grain_presets_for_tier(fidelity_tier):
            allowed = ", ".join(preset.value for preset in allowed_grain_presets_for_tier(fidelity_tier))
            raise ProblemException(
                title="Invalid Grain Preset",
                detail=f"{fidelity_tier.value} only supports these grain presets in Packet 4B: {allowed}.",
                status_code=400,
            )

        stored_snapshot = session.get("detection_snapshot") if isinstance(session.get("detection_snapshot"), dict) else {}
        if stored_snapshot and _stored_detection_matches_request(stored_snapshot, payload):
            detection_snapshot = stored_snapshot
        else:
            detection_snapshot = self._detect_and_persist(
                upload_id=upload_id,
                session=session,
                profile=profile,
                payload=payload,
                owner_user_id=user_id,
                access_token=access_token,
            )
            session = _require_completed_upload(
                self._upload_repo.get_session(upload_id, owner_user_id=user_id, access_token=access_token)
            )

        capture_medium = _capture_medium_for_detection(session, detection_snapshot)
        _ensure_plan_supports_capture_medium(capture_medium=capture_medium, plan_tier=plan_tier)
        preview_era_profile = _build_preview_era_profile(
            session=session,
            detection_snapshot=detection_snapshot,
            fidelity_tier=fidelity_tier,
            grain_preset=grain_preset,
            plan_tier=plan_tier,
        )
        resolved_profile = resolve_fidelity_profile(
            requested_tier=fidelity_tier,
            era_profile=preview_era_profile,
            config={
                "grain_preset": grain_preset.value,
                "fidelity_overrides": {
                    "grain_intensity": grain_preset.value,
                },
            },
        )
        relative_cost_multiplier = relative_cost_multiplier_for_tier(fidelity_tier)
        relative_processing_time_band = relative_processing_time_band_for_tier(fidelity_tier)
        job_payload_preview = JobCreateRequest.model_validate(
            {
                "media_uri": session["media_uri"],
                "original_filename": session["original_filename"],
                "mime_type": session["mime_type"],
                "estimated_duration_seconds": int(payload["estimated_duration_seconds"]),
                "source_asset_checksum": str(session.get("checksum_sha256") or str(upload_id).replace("-", "")),
                "fidelity_tier": fidelity_tier,
                "reproducibility_mode": ReproducibilityMode.PERCEPTUAL_EQUIVALENCE,
                "processing_mode": "balanced",
                "era_profile": preview_era_profile,
                "config": {
                    "persona": persona.value,
                    "grain_preset": grain_preset.value,
                    "relative_cost_multiplier": relative_cost_multiplier,
                    "relative_processing_time_band": relative_processing_time_band,
                    "detection_snapshot": {
                        "detection_id": detection_snapshot["detection_id"],
                        "era": detection_snapshot["era"],
                        "confidence": detection_snapshot["confidence"],
                        "source": detection_snapshot["source"],
                    },
                    "fidelity_overrides": {
                        "grain_intensity": grain_preset.value,
                    },
                },
            }
        )
        configured_at = _utc_now()
        launch_config = {
            "upload_id": upload_id,
            "persona": persona.value,
            "fidelity_tier": fidelity_tier.value,
            "grain_preset": grain_preset.value,
            "relative_cost_multiplier": relative_cost_multiplier,
            "relative_processing_time_band": relative_processing_time_band,
            "detection_snapshot": detection_snapshot,
            "job_payload_preview": job_payload_preview.model_dump(),
        }
        updated = self._upload_repo.update_session(
            upload_id,
            owner_user_id=user_id,
            patch={
                "detection_snapshot": detection_snapshot,
                "launch_config": launch_config,
                "configured_at": configured_at,
            },
            access_token=access_token,
        )
        if updated is None:
            raise ProblemException(
                title="Configuration Save Failed",
                detail="Upload configuration could not be persisted.",
                status_code=500,
            )

        merged_preferences = _merge_fidelity_preferences(
            profile,
            persona=persona,
            fidelity_tier=fidelity_tier,
            grain_preset=grain_preset,
        )
        try:
            self._user_profile_repo.update(
                user_id,
                {"preferences": merged_preferences},
                access_token=access_token,
            )
        except Exception as exc:
            _LOGGER.warning(
                "packet4b-preference-update-failed user_id=%s upload_id=%s error=%s",
                user_id,
                upload_id,
                exc,
            )

        return {
            "upload_id": upload_id,
            "status": updated["status"],
            "persona": persona.value,
            "fidelity_tier": fidelity_tier.value,
            "grain_preset": grain_preset.value,
            "detection_snapshot": _public_detection_response(detection_snapshot),
            "resolved_fidelity_profile": resolved_profile,
            "relative_cost_multiplier": relative_cost_multiplier,
            "relative_processing_time_band": relative_processing_time_band,
            "job_payload_preview": job_payload_preview.model_dump(),
            "configured_at": configured_at,
        }

    def _detect_and_persist(
        self,
        *,
        upload_id: str,
        session: dict[str, Any],
        profile: dict[str, Any],
        payload: dict[str, object],
        owner_user_id: str,
        access_token: str,
    ) -> dict[str, Any]:
        manual_override_era = str(payload["manual_override_era"]) if payload.get("manual_override_era") else None
        override_reason = str(payload["override_reason"]) if payload.get("override_reason") else None
        if manual_override_era and not override_reason:
            raise ProblemException(
                title="Override Reason Required",
                detail="Provide override_reason when manual_override_era is set.",
                status_code=400,
            )
        if manual_override_era and not self._era_detection_service.is_supported_era(manual_override_era):
            raise ProblemException(
                title="Unsupported Era Override",
                detail="Manual override era must match one of the supported eras returned by /v1/eras.",
                status_code=400,
            )

        base_detection = self._era_detection_service.analyze_media(
            job_id=f"upload:{upload_id}",
            media_uri=str(session["media_uri"]),
            original_filename=str(session["original_filename"]),
            mime_type=str(session["mime_type"]),
        )
        if manual_override_era and float(base_detection["confidence"]) >= 0.70:
            raise ProblemException(
                title="Manual Override Not Allowed",
                detail="Manual era override is only available when detection confidence is below 0.70.",
                status_code=400,
            )

        detection = base_detection
        if manual_override_era:
            detection = {
                **base_detection,
                "detection_id": str(uuid4()),
                "era": canonicalize_era_label(manual_override_era),
                "manual_confirmation_required": False,
                "warnings": ["Manual override applied to era classification."],
                "source": "user_override",
                "processing_timestamp": _utc_now(),
            }

        estimated_duration_seconds = int(payload["estimated_duration_seconds"])
        detection_tier_hint = _resolve_detection_tier_hint(profile, plan_tier=profile.get("plan_tier", "Pro"))
        estimated_usage_minutes = billable_minutes_for_duration(
            duration_seconds=estimated_duration_seconds,
            mode=detection_tier_hint.value,
        )
        capture_medium = _capture_medium_for_detection(session, detection)
        snapshot = _build_detection_snapshot(
            upload_id=upload_id,
            detection=detection,
            session=session,
            estimated_duration_seconds=estimated_duration_seconds,
            manual_override_era=manual_override_era,
            override_reason=override_reason,
            estimated_usage_minutes=estimated_usage_minutes,
            capture_medium=capture_medium,
        )
        updated = self._upload_repo.update_session(
            upload_id,
            owner_user_id=owner_user_id,
            patch={"detection_snapshot": snapshot},
            access_token=access_token,
        )
        if updated is None:
            raise ProblemException(
                title="Era Detection Failed",
                detail="Upload-scoped era detection could not be persisted.",
                status_code=500,
            )
        return snapshot
