"""Phase 2 request/response contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.processing import ReproducibilityMode
from app.models.status import JobStatus, UploadStatus


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


class UploadCreateRequest(StrictModel):
    original_filename: str = Field(min_length=1)
    mime_type: str = Field(min_length=1)
    size_bytes: int = Field(ge=0)
    checksum_sha256: str | None = Field(default=None, min_length=8)


class UploadFinalizeRequest(StrictModel):
    size_bytes: int = Field(ge=0)
    checksum_sha256: str | None = Field(default=None, min_length=8)


class UploadResponse(StrictModel):
    upload_id: str
    status: UploadStatus
    original_filename: str
    mime_type: str
    size_bytes: int
    checksum_sha256: str | None = None
    bucket_name: str
    object_path: str
    media_uri: str
    resumable_session_url: str
    created_at: str
    updated_at: str
    completed_at: str | None = None


class UploadResumeResponse(StrictModel):
    upload_id: str
    status: UploadStatus
    resumable_session_url: str
    next_byte_offset: int = 0
    upload_complete: bool = False
    session_regenerated: bool = False
    object_path: str
    media_uri: str


class UserPersona(StrEnum):
    ARCHIVIST = "archivist"
    FILMMAKER = "filmmaker"
    PROSUMER = "prosumer"


class GrainPreset(StrEnum):
    MATCHED = "Matched"
    SUBTLE = "Subtle"
    HEAVY = "Heavy"


class FidelityPersonaOption(StrictModel):
    persona: UserPersona
    label: str
    default_fidelity_tier: FidelityTier
    description: str


class FidelityTierCatalogItem(StrictModel):
    tier: FidelityTier
    label: str
    description: str
    default_grain_preset: GrainPreset
    allowed_grain_presets: list[GrainPreset]
    relative_cost_multiplier: float
    relative_processing_time_band: str
    thresholds: dict[str, float]
    identity_lock: bool


class FidelityTierCatalogResponse(StrictModel):
    personas: list[FidelityPersonaOption]
    tiers: list[FidelityTierCatalogItem]
    grain_presets: list[GrainPreset]
    current_persona: UserPersona | None = None
    preferred_fidelity_tier: FidelityTier | None = None
    preferred_grain_preset: GrainPreset | None = None


class UploadDetectEraRequest(StrictModel):
    estimated_duration_seconds: int = Field(default=60, ge=1)
    manual_override_era: str | None = None
    override_reason: str | None = None


class UploadDetectEraResponse(DetectEraResponse):
    upload_id: str


class UploadConfigurationRequest(StrictModel):
    persona: UserPersona | None = None
    fidelity_tier: FidelityTier
    grain_preset: GrainPreset
    estimated_duration_seconds: int = Field(default=60, ge=1)
    manual_override_era: str | None = None
    override_reason: str | None = None


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


class OperationalCostBreakdownResponse(StrictModel):
    gpu_time: float = 0.0
    storage: float = 0.0
    api_calls: float = 0.0
    total: float = 0.0


class BillingBreakdownResponse(StrictModel):
    included_usage: int = 0
    overage_minutes: int = 0
    overage_rate_usd_per_minute: float = 0.0
    estimated_charge_total_usd: float = 0.0


class ConfidenceIntervalResponse(StrictModel):
    low: float = 0.0
    high: float = 0.0


class CostEstimateSummaryResponse(StrictModel):
    estimated_usage_minutes: int = 0
    operational_cost_breakdown_usd: OperationalCostBreakdownResponse = Field(
        default_factory=OperationalCostBreakdownResponse
    )
    billing_breakdown_usd: BillingBreakdownResponse = Field(default_factory=BillingBreakdownResponse)
    confidence_interval_usd: ConfidenceIntervalResponse = Field(default_factory=ConfidenceIntervalResponse)
    usage_snapshot: UsageResponse
    launch_blocker: Literal["none", "overage_approval_required"] = "none"
    estimator_version: str
    generated_at: str


class CostReconciliationSummaryResponse(StrictModel):
    estimated_total_cost_usd: float = 0.0
    actual_total_cost_usd: float = 0.0
    delta_usd: float = 0.0
    delta_percent: float = 0.0
    estimated_charge_total_usd: float = 0.0
    actual_charge_total_usd: float = 0.0
    actual_usage_minutes: int = 0
    outlier_threshold_percent: float = 20.0
    outlier_flagged: bool = False
    estimator_version: str = ""
    reconciled_at: str | None = None


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


class FidelityTier(StrEnum):
    ENHANCE = "Enhance"
    RESTORE = "Restore"
    CONSERVE = "Conserve"


class SegmentStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WebhookEventType(StrEnum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


class ExportVariant(StrEnum):
    AV1 = "av1"
    H264 = "h264"


class PreviewStatus(StrEnum):
    READY = "ready"
    FAILED = "failed"


class PreviewSelectionMode(StrEnum):
    SCENE_AWARE = "scene_aware"
    UNIFORM_FALLBACK = "uniform_fallback"


class QualitySummaryResponse(StrictModel):
    e_hf: float = 0.0
    s_ls_db: float = 0.0
    t_tc: float = 0.0
    thresholds_met: bool = False


class StageTimingResponse(StrictModel):
    upload_ms: int | None = None
    era_detection_ms: int | None = None
    queue_wait_ms: int | None = None
    allocation_ms: int | None = None
    processing_ms: int | None = None
    encoding_ms: int | None = None
    download_ms: int | None = None
    total_ms: int | None = None


class ReproducibilitySummaryResponse(StrictModel):
    mode: ReproducibilityMode
    verification_status: str
    failed_segment_count: int = 0
    rerun_count: int = 0
    rollup: str = "pass"
    metric_epsilon_percent: float = 0.5
    environment_fingerprint: str = ""


class ManifestSummaryResponse(StrictModel):
    manifest_id: str
    manifest_uri: str
    manifest_sha256: str
    generated_at: str
    size_bytes: int = 0


class CacheSummaryResponse(StrictModel):
    hits: int = 0
    misses: int = 0
    bypassed: int = 0
    degraded: bool = False
    hit_rate: float = 0.0
    saved_gpu_seconds: int = 0


class GpuSummaryResponse(StrictModel):
    gpu_type: str | None = None
    warm_start: bool | None = None
    allocation_latency_ms: int | None = None
    gpu_runtime_seconds: int = 0
    desired_warm_instances: int = 0
    active_warm_instances: int = 0
    busy_instances: int = 0
    utilization_percent: float = 0.0


class CostSummaryResponse(StrictModel):
    gpu_seconds: int = 0
    storage_operations: int = 0
    api_calls: int = 0
    total_cost_usd: float = 0.0


class SloSummaryResponse(StrictModel):
    target_total_ms: int
    actual_total_ms: int | None = None
    p95_ratio: float | None = None
    compliant: bool | None = None
    degraded: bool = False
    error_budget_burn_percent: float = 0.0
    museum_sla_applies: bool = False


class PerformanceSummaryResponse(StrictModel):
    stage_timings: StageTimingResponse = Field(default_factory=StageTimingResponse)
    queue_wait_ms: int | None = None
    allocation_ms: int | None = None
    total_ms: int | None = None
    throughput_ratio: float | None = None


class JobCreateRequest(StrictModel):
    media_uri: str
    original_filename: str = ""
    mime_type: str = ""
    estimated_duration_seconds: int = Field(default=60, ge=1)
    source_asset_checksum: str = Field(min_length=8)
    fidelity_tier: FidelityTier = FidelityTier.RESTORE
    reproducibility_mode: ReproducibilityMode = ReproducibilityMode.PERCEPTUAL_EQUIVALENCE
    processing_mode: str = Field(default="balanced", min_length=3)
    era_profile: EraProfileInput
    config: dict[str, Any] = Field(default_factory=dict)


class UploadConfigurationResponse(StrictModel):
    upload_id: str
    status: UploadStatus
    persona: UserPersona
    fidelity_tier: FidelityTier
    grain_preset: GrainPreset
    detection_snapshot: UploadDetectEraResponse
    resolved_fidelity_profile: dict[str, Any]
    relative_cost_multiplier: float
    relative_processing_time_band: str
    job_payload_preview: JobCreateRequest
    configured_at: str


class JobProgressResponse(StrictModel):
    job_id: str
    segment_index: int = 0
    segment_count: int = 0
    percent_complete: float = 0.0
    eta_seconds: int = 0
    status: JobStatus
    current_operation: str = ""
    updated_at: str


class JobSegmentResponse(StrictModel):
    job_id: str
    segment_index: int
    segment_start_seconds: int
    segment_end_seconds: int
    segment_duration_seconds: int
    status: SegmentStatus
    attempt_count: int = 0
    idempotency_key: str
    last_error_classification: str | None = None
    retry_backoffs_seconds: list[int] = Field(default_factory=list)
    output_uri: str | None = None
    cache_status: str = "miss"
    cache_hit_latency_ms: int | None = None
    cache_namespace: str | None = None
    cached_output_uri: str | None = None
    gpu_type: str | None = None
    allocation_latency_ms: int | None = None
    updated_at: str


class JobSummaryResponse(StrictModel):
    job_id: str
    media_uri: str
    original_filename: str
    mime_type: str
    fidelity_tier: FidelityTier
    effective_fidelity_tier: FidelityTier
    processing_mode: str
    reproducibility_mode: ReproducibilityMode
    estimated_duration_seconds: int
    status: JobStatus
    progress_topic: str
    result_uri: str | None = None
    manifest_available: bool = False
    manifest: ManifestSummaryResponse | None = None
    performance_summary: PerformanceSummaryResponse
    quality_summary: QualitySummaryResponse = Field(default_factory=QualitySummaryResponse)
    reproducibility_summary: ReproducibilitySummaryResponse | None = None
    stage_timings: StageTimingResponse = Field(default_factory=StageTimingResponse)
    cache_summary: CacheSummaryResponse = Field(default_factory=CacheSummaryResponse)
    gpu_summary: GpuSummaryResponse = Field(default_factory=GpuSummaryResponse)
    cost_summary: CostSummaryResponse = Field(default_factory=CostSummaryResponse)
    cost_estimate_summary: CostEstimateSummaryResponse | None = None
    cost_reconciliation_summary: CostReconciliationSummaryResponse | None = None
    slo_summary: SloSummaryResponse
    failed_segments: list[int] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str
    progress: JobProgressResponse


class JobCreateResponse(JobSummaryResponse):
    queued_at: str


class JobEstimateResponse(CostEstimateSummaryResponse):
    pass


class PreviewCreateRequest(StrictModel):
    upload_id: str = Field(min_length=1)


class PreviewKeyframeResponse(StrictModel):
    index: int = Field(ge=0)
    timestamp_seconds: float = Field(ge=0)
    scene_number: int = Field(ge=1)
    confidence_score: float = Field(ge=0.0, le=1.0)
    thumbnail_url: str
    frame_url: str


class PreviewSessionResponse(StrictModel):
    preview_id: str
    upload_id: str
    status: PreviewStatus
    configuration_fingerprint: str
    stale: bool = False
    expires_at: str
    selection_mode: PreviewSelectionMode
    scene_diversity: float = 0.0
    keyframe_count: int = 0
    estimated_cost_summary: CostEstimateSummaryResponse
    estimated_processing_time_seconds: int = 0
    keyframes: list[PreviewKeyframeResponse] = Field(default_factory=list)


class JobDetailResponse(JobSummaryResponse):
    started_at: str | None = None
    completed_at: str | None = None
    cancel_requested_at: str | None = None
    last_error: str | None = None
    deletion_proof_id: str | None = None
    segments: list[JobSegmentResponse] = Field(default_factory=list)


class JobListResponse(StrictModel):
    jobs: list[JobSummaryResponse] = Field(default_factory=list)


class JobCancelResponse(StrictModel):
    job_id: str
    status: JobStatus
    cancel_requested_at: str | None = None


class UncertaintyCalloutTimeRangeResponse(StrictModel):
    start: float
    end: float


class UncertaintyCalloutSourceResponse(StrictModel):
    segment_index: int | None = None
    metric_key: str | None = None


class UncertaintyCalloutResponse(StrictModel):
    callout_id: str
    code: str
    severity: Literal["warning", "critical"]
    title: str
    message: str
    scope: Literal["segment", "global"]
    time_range_seconds: UncertaintyCalloutTimeRangeResponse
    source: UncertaintyCalloutSourceResponse = Field(default_factory=UncertaintyCalloutSourceResponse)


class JobUncertaintyCalloutsResponse(StrictModel):
    job_id: str
    status: JobStatus
    callouts: list[UncertaintyCalloutResponse] = Field(default_factory=list)


class JobExportResponse(StrictModel):
    job_id: str
    status: JobStatus
    variant: ExportVariant
    download_url: str
    expires_at: str
    file_name: str
    size_bytes: int
    sha256: str
    deletion_proof_id: str
    package_contents: list[str] = Field(default_factory=list)


class DeletionProofResponse(StrictModel):
    deletion_proof_id: str
    job_id: str
    generated_at: str
    signature_algorithm: str
    signature: str
    proof_sha256: str
    pdf_download_url: str
    pdf_expires_at: str
    verification_summary: dict[str, Any] = Field(default_factory=dict)


class TransformationManifestSamplingProtocol(StrictModel):
    frames_per_second: float
    frames_sampled: int
    sampled_timestamps_seconds: list[float] = Field(default_factory=list)
    downscale_rule: str
    roi_256: dict[str, int]
    roi_512: dict[str, int]
    roi_full_frame: dict[str, int]
    roi_source: str = "center_crop"


class TransformationManifestSegment(StrictModel):
    segment_index: int
    frame_range: str
    quality_summary: QualitySummaryResponse
    uncertainty_callouts: list[str] = Field(default_factory=list)
    sampling_protocol: TransformationManifestSamplingProtocol
    reproducibility_proof: dict[str, Any] = Field(default_factory=dict)
    output_uri: str | None = None


class TransformationManifestResponse(StrictModel):
    manifest_id: str
    job_id: str
    generated_at: str
    user_id: str
    era_profile: dict[str, Any]
    fidelity_tier: FidelityTier
    effective_fidelity_profile: dict[str, Any]
    reproducibility_mode: ReproducibilityMode
    job_status: JobStatus
    quality_summary: QualitySummaryResponse
    reproducibility_summary: ReproducibilitySummaryResponse
    stage_timings: StageTimingResponse
    processing_time_ms: int = 0
    gpu_usage: dict[str, Any] = Field(default_factory=dict)
    cache_summary: CacheSummaryResponse = Field(default_factory=CacheSummaryResponse)
    cost_summary: CostSummaryResponse = Field(default_factory=CostSummaryResponse)
    slo_summary: SloSummaryResponse
    model_versions: dict[str, str] = Field(default_factory=dict)
    environment: dict[str, Any] = Field(default_factory=dict)
    segments: list[TransformationManifestSegment] = Field(default_factory=list)
    uncertainty_callouts: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    result_uri: str | None = None
    manifest_uri: str
    manifest_sha256: str
    size_bytes: int = 0


class IncidentResponse(StrictModel):
    incident_id: str
    incident_key: str
    severity: str
    incident_state: str
    source_signal: str
    runbook_key: str
    issue_tracker_url: str | None = None
    status_page_url: str | None = None
    communication_status: str = "drafted"
    detection_delay_seconds: int = 0
    resolution_time_seconds: int | None = None
    postmortem_due_at: str | None = None
    opened_at: str
    acknowledged_at: str | None = None
    resolved_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeOpsSnapshotResponse(StrictModel):
    queue_depth: int = 0
    queue_age_seconds: float = 0.0
    desired_warm_instances: int = 0
    active_warm_instances: int = 0
    busy_instances: int = 0
    idle_instances: int = 0
    utilization_percent: float = 0.0
    alert_routes: dict[str, str] = Field(default_factory=dict)
    incidents: list[IncidentResponse] = Field(default_factory=list)
    alerts: list[dict[str, Any]] = Field(default_factory=list)
    training_calendar_url: str | None = None
