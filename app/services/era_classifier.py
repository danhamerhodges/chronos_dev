"""Era-classifier interfaces, canonical era helpers, and deterministic fallback logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


UNKNOWN_ERA = "Unknown Era"
ERA_CATALOG = [
    "1840s Daguerreotype Plate",
    "1860s Albumen Print",
    "1930s 16mm Film",
    "1950s Kodachrome Film",
    "1960s Kodachrome Film",
    "1970s Super 8 Film",
    "1980s VHS Tape",
    "1990s VHS Tape",
]
_CANONICAL_ERA_BY_KEY = {era.casefold(): era for era in ERA_CATALOG}
_ERA_ALIASES = {
    "daguerreotype": "1840s Daguerreotype Plate",
    "daguerreotype plate": "1840s Daguerreotype Plate",
    "albumen": "1860s Albumen Print",
    "albumen print": "1860s Albumen Print",
    "16mm": "1930s 16mm Film",
    "16mm film": "1930s 16mm Film",
    "1930s 16mm": "1930s 16mm Film",
    "1930s 16mm film": "1930s 16mm Film",
    "1950s kodachrome": "1950s Kodachrome Film",
    "1950s kodachrome film": "1950s Kodachrome Film",
    "1960s kodachrome": "1960s Kodachrome Film",
    "1960s kodachrome film": "1960s Kodachrome Film",
    "super 8": "1970s Super 8 Film",
    "super 8 film": "1970s Super 8 Film",
    "super 8mm": "1970s Super 8 Film",
    "super 8mm film": "1970s Super 8 Film",
    "1970s super 8": "1970s Super 8 Film",
    "1970s super 8 film": "1970s Super 8 Film",
    "1980s vhs": "1980s VHS Tape",
    "1980s vhs tape": "1980s VHS Tape",
    "1990s vhs": "1990s VHS Tape",
    "1990s vhs tape": "1990s VHS Tape",
    "vhs": "1980s VHS Tape",
    "vhs tape": "1980s VHS Tape",
}

_MEDIUM_DEFAULTS = {
    "daguerreotype": ("1840s Daguerreotype Plate", 0.94, "fine silver mirroring", ["plate_edges", "tonal_falloff"]),
    "albumen": ("1860s Albumen Print", 0.92, "paper fiber bloom", ["sepia_cast", "albumen_sheen"]),
    "16mm": ("1930s 16mm Film", 0.81, "coarse film grain", ["gate_weave", "flicker"]),
    "super_8": ("1970s Super 8 Film", 0.79, "consumer film grain", ["splices", "frame_jitter"]),
    "kodachrome": ("1960s Kodachrome Film", 0.88, "dense color grain", ["saturated_reds", "dye_stability"]),
    "vhs": ("1980s VHS Tape", 0.76, "magnetic noise smear", ["head_switching_noise", "chroma_bleed"]),
}


def _fallback_top_candidates(primary_era: str, *, default_era: str) -> list[dict[str, Any]]:
    if primary_era in ERA_CATALOG:
        start_index = (ERA_CATALOG.index(primary_era) + 1) % len(ERA_CATALOG)
        ordered_eras = [ERA_CATALOG[(start_index + offset) % len(ERA_CATALOG)] for offset in range(len(ERA_CATALOG))]
    else:
        default_index = ERA_CATALOG.index(default_era) if default_era in ERA_CATALOG else 0
        ordered_eras = [default_era]
        ordered_eras.extend(
            ERA_CATALOG[(default_index + offset) % len(ERA_CATALOG)]
            for offset in range(1, len(ERA_CATALOG))
        )
    ordered_eras = [era for era in ordered_eras if era != primary_era]
    fallback_eras = ordered_eras[:2]
    while len(fallback_eras) < 2:
        fallback_eras.append(default_era)
    return [
        {"era": fallback_eras[0], "confidence": 0.52},
        {"era": fallback_eras[1], "confidence": 0.41},
    ]


@dataclass(frozen=True)
class EraClassifierUsage:
    prompt_token_count: int = 0
    candidates_token_count: int = 0
    total_token_count: int = 0
    api_call_count: int = 0


@dataclass(frozen=True)
class EraClassification:
    era: str
    confidence: float
    forensic_markers: dict[str, Any]
    top_candidates: list[dict[str, Any]]
    model_version: str
    prompt_version: str
    raw_response: dict[str, Any] | None = None
    raw_response_gcs_uri: str | None = None
    usage: EraClassifierUsage = field(default_factory=EraClassifierUsage)
    provider_error: str | None = None


class EraClassifier(Protocol):
    def classify(
        self,
        *,
        job_id: str,
        media_uri: str,
        original_filename: str,
        mime_type: str,
        era_profile: dict[str, Any] | None = None,
    ) -> EraClassification: ...


class ClassifierError(RuntimeError):
    """Expected classifier/provider failure that should trigger fallback handling."""


def canonicalize_era_label(label: str | None) -> str | None:
    normalized = str(label or "").strip()
    if not normalized:
        return None
    direct_match = _CANONICAL_ERA_BY_KEY.get(normalized.casefold())
    if direct_match:
        return direct_match
    return _ERA_ALIASES.get(normalized.casefold())


def is_supported_era(label: str | None) -> bool:
    return canonicalize_era_label(label) in ERA_CATALOG


def normalize_top_candidates(
    candidates: list[dict[str, Any]],
    *,
    include_unknown: bool = False,
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in candidates:
        era = canonicalize_era_label(item.get("era"))
        if era is None:
            continue
        if era == UNKNOWN_ERA and not include_unknown:
            continue
        if era in seen:
            continue
        seen.add(era)
        try:
            confidence = float(item.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        normalized.append({"era": era, "confidence": max(0.0, min(confidence, 1.0))})
    return normalized


def infer_capture_medium(*, media_uri: str, original_filename: str, mime_type: str) -> str:
    hints = " ".join([media_uri, original_filename, mime_type]).casefold()
    if "daguerreotype" in hints:
        return "daguerreotype"
    if "albumen" in hints:
        return "albumen"
    if "16mm" in hints:
        return "16mm"
    if "super 8" in hints or "super_8" in hints or "8mm" in hints:
        return "super_8"
    if "kodachrome" in hints:
        return "kodachrome"
    if "vhs" in hints:
        return "vhs"

    extension = Path(original_filename).suffix.casefold()
    if mime_type.startswith("image/") or extension in {".tif", ".tiff", ".jpg", ".jpeg", ".png"}:
        return "albumen"
    if mime_type in {"video/x-msvideo", "video/avi"} or extension == ".avi":
        return "vhs"
    return "super_8"


def build_default_era_profile(*, media_uri: str, original_filename: str, mime_type: str) -> dict[str, Any]:
    capture_medium = infer_capture_medium(
        media_uri=media_uri,
        original_filename=original_filename,
        mime_type=mime_type,
    )
    if capture_medium == "daguerreotype":
        return {
            "capture_medium": capture_medium,
            "mode": "Conserve",
            "tier": "Pro",
            "resolution_cap": "4k",
            "hallucination_limit": 0.05,
            "artifact_policy": {
                "deinterlace": False,
                "grain_intensity": "Matched",
                "preserve_edge_fog": True,
                "preserve_chromatic_aberration": True,
            },
            "era_range": {"start_year": 1840, "end_year": 1849},
            "gemini_confidence": 1.0,
            "manual_confirmation_required": False,
        }
    if capture_medium == "albumen":
        return {
            "capture_medium": capture_medium,
            "mode": "Conserve",
            "tier": "Pro",
            "resolution_cap": "4k",
            "hallucination_limit": 0.05,
            "artifact_policy": {
                "deinterlace": False,
                "grain_intensity": "Matched",
                "preserve_edge_fog": True,
                "preserve_chromatic_aberration": True,
            },
            "era_range": {"start_year": 1860, "end_year": 1869},
            "gemini_confidence": 1.0,
            "manual_confirmation_required": False,
        }
    if capture_medium == "16mm":
        return {
            "capture_medium": capture_medium,
            "mode": "Restore",
            "tier": "Pro",
            "resolution_cap": "4k",
            "hallucination_limit": 0.15,
            "artifact_policy": {
                "deinterlace": False,
                "grain_intensity": "Matched",
                "preserve_edge_fog": True,
                "preserve_chromatic_aberration": True,
            },
            "era_range": {"start_year": 1930, "end_year": 1939},
            "gemini_confidence": 1.0,
            "manual_confirmation_required": False,
        }
    if capture_medium == "kodachrome":
        return {
            "capture_medium": capture_medium,
            "mode": "Restore",
            "tier": "Pro",
            "resolution_cap": "4k",
            "hallucination_limit": 0.15,
            "artifact_policy": {
                "deinterlace": False,
                "grain_intensity": "Matched",
                "preserve_edge_fog": True,
                "preserve_chromatic_aberration": True,
            },
            "era_range": {"start_year": 1955, "end_year": 1969},
            "gemini_confidence": 1.0,
            "manual_confirmation_required": False,
        }
    if capture_medium == "vhs":
        return {
            "capture_medium": capture_medium,
            "mode": "Restore",
            "tier": "Pro",
            "resolution_cap": "1080p",
            "hallucination_limit": 0.15,
            "artifact_policy": {
                "deinterlace": True,
                "grain_intensity": "Matched",
                "preserve_edge_fog": False,
                "preserve_chromatic_aberration": False,
            },
            "era_range": {"start_year": 1980, "end_year": 1999},
            "gemini_confidence": 1.0,
            "manual_confirmation_required": False,
        }
    return {
        "capture_medium": "super_8",
        "mode": "Restore",
        "tier": "Pro",
        "resolution_cap": "4k",
        "hallucination_limit": 0.15,
        "artifact_policy": {
            "deinterlace": False,
            "grain_intensity": "Matched",
            "preserve_edge_fog": True,
            "preserve_chromatic_aberration": True,
        },
        "era_range": {"start_year": 1970, "end_year": 1979},
        "gemini_confidence": 1.0,
        "manual_confirmation_required": False,
    }


class DeterministicFallbackEraClassifier:
    def classify(
        self,
        *,
        job_id: str,
        media_uri: str,
        original_filename: str,
        mime_type: str,
        era_profile: dict[str, Any] | None = None,
    ) -> EraClassification:
        resolved_era_profile = era_profile or build_default_era_profile(
            media_uri=media_uri,
            original_filename=original_filename,
            mime_type=mime_type,
        )
        capture_medium = str(resolved_era_profile["capture_medium"])
        era, confidence, grain_structure, artifacts = _MEDIUM_DEFAULTS.get(
            capture_medium,
            (UNKNOWN_ERA, 0.55, "unknown grain signature", ["insufficient_signal"]),
        )
        if "mystery" in f"{media_uri} {original_filename}".lower():
            confidence = min(confidence, 0.61)
        top_candidates = [{"era": era, "confidence": round(confidence, 2)}]
        top_candidates.extend(_fallback_top_candidates(era, default_era="1970s Super 8 Film"))
        return EraClassification(
            era=era,
            confidence=round(confidence, 2),
            forensic_markers={
                "grain_structure": grain_structure,
                "color_saturation": 0.82 if capture_medium == "kodachrome" else 0.58,
                "format_artifacts": artifacts,
            },
            top_candidates=top_candidates,
            model_version="deterministic-fallback-v1",
            prompt_version="phase2-era-detection-fallback-v1",
        )
