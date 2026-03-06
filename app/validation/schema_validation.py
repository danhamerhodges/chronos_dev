"""ENG-001 validation layer for Era Profile payloads."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


SCHEMA_DRAFT = "https://json-schema.org/draft/2020-12/schema"
CAPTURE_MEDIA = ("daguerreotype", "albumen", "16mm", "super_8", "kodachrome", "vhs")
MODES = ("Conserve", "Restore", "Enhance")
TIERS = ("Hobbyist", "Pro", "Museum")
RESOLUTION_CAPS = ("1080p", "2k", "4k", "native_scan")
GRAIN_INTENSITIES = ("Matched", "Subtle", "Heavy")


@dataclass(frozen=True)
class ValidationIssue:
    rule_id: str
    severity: str
    field: str
    message: str


@dataclass
class ValidationResult:
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    latency_ms: float = 0.0

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def as_problem_errors(self) -> list[dict[str, str]]:
        return [
            {
                "rule_id": issue.rule_id,
                "severity": issue.severity,
                "field": issue.field,
                "message": issue.message,
            }
            for issue in self.errors
        ]


def schema_path() -> Path:
    return Path(__file__).resolve().parents[2] / "schemas" / "era_profile_v2020-12.json"


def load_schema() -> dict[str, Any]:
    return json.loads(schema_path().read_text(encoding="utf-8"))


def _issue(rule_id: str, severity: str, field: str, message: str) -> ValidationIssue:
    return ValidationIssue(rule_id=rule_id, severity=severity, field=field, message=message)


def _mode_key(payload: Mapping[str, Any]) -> tuple[str, str]:
    return str(payload.get("tier", "")), str(payload.get("mode", ""))


def _artifact_policy(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    artifact_policy = payload.get("artifact_policy", {})
    return artifact_policy if isinstance(artifact_policy, Mapping) else {}


def _float_value(value: Any, field: str, result: ValidationResult) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        result.errors.append(_issue("VR-TYPE", "error", field, f"{field} must be numeric."))
        return None


def validate_era_profile(payload: Mapping[str, Any]) -> ValidationResult:
    started = time.perf_counter()
    result = ValidationResult()
    artifact_policy = _artifact_policy(payload)
    era_range = payload.get("era_range", {})
    era_range = era_range if isinstance(era_range, Mapping) else {}

    required_fields = {
        "capture_medium": payload.get("capture_medium"),
        "mode": payload.get("mode"),
        "tier": payload.get("tier"),
        "resolution_cap": payload.get("resolution_cap"),
        "hallucination_limit": payload.get("hallucination_limit"),
        "artifact_policy": payload.get("artifact_policy"),
        "era_range": payload.get("era_range"),
    }
    for field, value in required_fields.items():
        if value in (None, "", {}):
            result.errors.append(_issue("VR-REQUIRED", "error", field, f"{field} is required."))

    nested_required = {
        "artifact_policy.deinterlace": artifact_policy.get("deinterlace"),
        "artifact_policy.grain_intensity": artifact_policy.get("grain_intensity"),
        "artifact_policy.preserve_edge_fog": artifact_policy.get("preserve_edge_fog"),
        "artifact_policy.preserve_chromatic_aberration": artifact_policy.get("preserve_chromatic_aberration"),
        "era_range.start_year": era_range.get("start_year"),
        "era_range.end_year": era_range.get("end_year"),
    }
    for field, value in nested_required.items():
        if value in (None, ""):
            result.errors.append(_issue("VR-REQUIRED", "error", field, f"{field} is required."))

    if payload.get("capture_medium") not in CAPTURE_MEDIA:
        result.errors.append(
            _issue("VR-ENUM", "error", "capture_medium", "capture_medium must use a canonical enum value.")
        )
    if payload.get("mode") not in MODES:
        result.errors.append(_issue("VR-ENUM", "error", "mode", "mode must use a canonical enum value."))
    if payload.get("tier") not in TIERS:
        result.errors.append(_issue("VR-ENUM", "error", "tier", "tier must use a canonical enum value."))
    if payload.get("resolution_cap") not in RESOLUTION_CAPS:
        result.errors.append(
            _issue("VR-ENUM", "error", "resolution_cap", "resolution_cap must use a canonical enum value.")
        )
    if artifact_policy.get("grain_intensity") not in GRAIN_INTENSITIES:
        result.errors.append(
            _issue(
                "VR-ENUM",
                "error",
                "artifact_policy.grain_intensity",
                "grain_intensity must use a canonical enum value.",
            )
        )

    hallucination_limit = _float_value(payload.get("hallucination_limit", 0), "hallucination_limit", result)
    gemini_confidence = _float_value(payload.get("gemini_confidence", 1.0), "gemini_confidence", result)
    manual_confirmation_required = bool(payload.get("manual_confirmation_required", False))

    try:
        start_year = int(era_range.get("start_year"))
        end_year = int(era_range.get("end_year"))
        if start_year > end_year:
            result.errors.append(
                _issue(
                    "VR-008",
                    "error",
                    "era_range",
                    f"Era start_year ({start_year}) cannot be later than end_year ({end_year}).",
                )
            )
    except (TypeError, ValueError):
        result.errors.append(
            _issue("VR-TYPE", "error", "era_range", "era_range must contain integer start_year and end_year.")
        )

    if payload.get("capture_medium") == "vhs" and artifact_policy.get("deinterlace") is not True:
        result.errors.append(
            _issue(
                "VR-001",
                "error",
                "artifact_policy.deinterlace",
                "VHS media requires deinterlacing. Set artifact_policy.deinterlace to true.",
            )
        )
    if payload.get("mode") == "Conserve" and hallucination_limit is not None and hallucination_limit > 0.05:
        result.errors.append(
            _issue(
                "VR-002",
                "error",
                "hallucination_limit",
                f"Conserve mode limits AI-generated content to 5%. Current: {hallucination_limit}.",
            )
        )
    if gemini_confidence is not None and gemini_confidence < 0.70 and not manual_confirmation_required:
        result.errors.append(
            _issue(
                "VR-003",
                "error",
                "manual_confirmation_required",
                f"Era detection confidence is low ({gemini_confidence}). Manual confirmation required.",
            )
        )
    if payload.get("mode") == "Conserve" and artifact_policy.get("grain_intensity") != "Matched":
        result.errors.append(
            _issue(
                "VR-004",
                "error",
                "artifact_policy.grain_intensity",
                "Conserve mode requires grain_intensity='Matched' to preserve authenticity.",
            )
        )
    if payload.get("mode") == "Enhance" and hallucination_limit is not None and hallucination_limit < 0.15:
        result.warnings.append(
            _issue(
                "VR-005",
                "warning",
                "hallucination_limit",
                "Enhance mode typically uses hallucination_limit >= 0.15 for best results.",
            )
        )
    if payload.get("capture_medium") in {"daguerreotype", "albumen"} and payload.get("resolution_cap") not in {
        "2k",
        "4k",
        "native_scan",
    }:
        result.errors.append(
            _issue(
                "VR-006",
                "error",
                "resolution_cap",
                "Early photography formats require minimum 2K resolution to preserve detail.",
            )
        )
    if _mode_key(payload) == ("Museum", "Conserve") and (
        artifact_policy.get("preserve_edge_fog") is not True
        or artifact_policy.get("preserve_chromatic_aberration") is not True
    ):
        result.errors.append(
            _issue(
                "VR-007",
                "error",
                "artifact_policy",
                "Museum Conserve tier requires all artifact preservation flags set to true.",
            )
        )
    if payload.get("mode") == "Restore" and hallucination_limit is not None and not (0.05 < hallucination_limit <= 0.20):
        result.warnings.append(
            _issue(
                "VR-009",
                "warning",
                "hallucination_limit",
                "Restore mode typically uses hallucination_limit between 0.05 and 0.20.",
            )
        )
    if payload.get("tier") == "Hobbyist" and payload.get("resolution_cap") != "1080p":
        result.errors.append(
            _issue(
                "VR-010",
                "error",
                "resolution_cap",
                "Hobbyist tier is limited to 1080p resolution. Upgrade to Pro for 4K.",
            )
        )

    tier, mode = _mode_key(payload)
    if (tier, mode) == ("Hobbyist", "Enhance") and hallucination_limit is not None and hallucination_limit != 0.25:
        result.errors.append(
            _issue(
                "VR-MATRIX",
                "error",
                "hallucination_limit",
                "Hobbyist Enhance locks hallucination_limit to 0.25.",
            )
        )
    if tier == "Hobbyist" and (
        artifact_policy.get("preserve_edge_fog") is True or artifact_policy.get("preserve_chromatic_aberration") is True
    ):
        result.errors.append(
            _issue(
                "VR-MATRIX",
                "error",
                "artifact_policy",
                "Hobbyist tier locks artifact preservation flags to false.",
            )
        )
    if tier == "Hobbyist" and mode != "Enhance":
        result.errors.append(_issue("VR-MATRIX", "error", "mode", "Hobbyist tier locks mode to Enhance."))

    result.latency_ms = (time.perf_counter() - started) * 1000
    return result
