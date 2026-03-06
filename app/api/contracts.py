"""Phase 2 request/response contracts."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProblemDetail(StrictModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: str | None = None
    errors: list[dict[str, Any]] = Field(default_factory=list)
    request_id: str | None = None


class EraRangeInput(StrictModel):
    start_year: int
    end_year: int


class ArtifactPolicyInput(StrictModel):
    deinterlace: bool
    grain_intensity: str
    preserve_edge_fog: bool = False
    preserve_chromatic_aberration: bool = False


class EraProfileInput(StrictModel):
    capture_medium: str
    mode: str
    tier: str
    resolution_cap: str
    hallucination_limit: float
    artifact_policy: ArtifactPolicyInput
    era_range: EraRangeInput
    gemini_confidence: float = 1.0
    manual_confirmation_required: bool = False


class DetectEraRequest(StrictModel):
    job_id: str
    media_uri: str
    original_filename: str = ""
    mime_type: str = ""
    estimated_duration_seconds: int = 60
    era_profile: EraProfileInput
    manual_override_era: str | None = None
    override_reason: str | None = None


class CandidateEra(StrictModel):
    era: str
    confidence: float


class ForensicMarkers(StrictModel):
    grain_structure: str
    color_saturation: float
    format_artifacts: list[str]


class DetectEraResponse(StrictModel):
    detection_id: str
    job_id: str
    era: str
    confidence: float
    manual_confirmation_required: bool
    top_candidates: list[CandidateEra] = Field(default_factory=list)
    forensic_markers: ForensicMarkers
    warnings: list[str] = Field(default_factory=list)
    processing_timestamp: str
    source: str
    model_version: str
    prompt_version: str
    estimated_usage_minutes: int


class EraCatalogResponse(StrictModel):
    eras: list[str]


class HealthResponse(StrictModel):
    status: str
    components: dict[str, str]
    timestamp: str


class VersionResponse(StrictModel):
    version: str
    build_sha: str
    build_time: str


class UserProfileResponse(StrictModel):
    user_id: str
    email: str
    role: str
    plan_tier: str
    org_id: str
    display_name: str | None = None
    avatar_url: str | None = None
    preferences: dict[str, Any] = Field(default_factory=dict)


class UserProfileUpdateRequest(StrictModel):
    display_name: str | None = None
    avatar_url: str | None = None
    preferences: dict[str, Any] = Field(default_factory=dict)


class UsageResponse(StrictModel):
    user_id: str
    plan_tier: str
    used_minutes: int
    monthly_limit_minutes: int
    remaining_minutes: int
    estimated_next_job_minutes: int
    approved_overage_minutes: int
    remaining_approved_overage_minutes: int
    threshold_alerts: list[int]
    overage_approval_scope: str | None = None
    hard_stop: bool
    price_reference: str
    overage_price_reference: str
    reconciliation_source: str
    reconciliation_status: str


class OverageApprovalRequest(StrictModel):
    approval_scope: str
    requested_minutes: int = 0
    reason: str | None = None


class OverageApprovalResponse(StrictModel):
    user_id: str
    approval_scope: str
    approved_for_minutes: int
    remaining_approved_overage_minutes: int
    remaining_minutes: int
    threshold_alerts: list[int]
    overage_price_reference: str


class LogSettingsUpdateRequest(StrictModel):
    retention_days: int
    redaction_mode: str
    categories: list[str] = Field(default_factory=list)
    export_targets: list[str] = Field(default_factory=list)


class LogSettingsResponse(StrictModel):
    org_id: str
    retention_days: int
    redaction_mode: str
    categories: list[str]
    export_targets: list[str]
    updated_by: str


class DeleteLogsRequest(StrictModel):
    categories: list[str]
    date_from: str
    date_to: str
    reason: str | None = None


class DeleteLogsResponse(StrictModel):
    deletion_request_id: str
    deletion_proof_id: str
    deleted_categories: list[str]
    deleted_entries: int
    status: str
