/**
 * Maps to:
 * - DS-002
 * - DS-003
 * - DS-004
 * - DS-005
 */

import React from "react";

import { render, screen, waitFor } from "@testing-library/react";
import { expect, vi } from "vitest";

const phase4Mocks = vi.hoisted(() => ({
  fetchFidelityCatalog: vi.fn(),
  detectUploadEra: vi.fn(),
  saveUploadConfiguration: vi.fn(),
  executeUploadFlow: vi.fn(),
  fetchJobEstimate: vi.fn(),
  createPreview: vi.fn(),
  reviewPreview: vi.fn(),
  approveSingleJobOverage: vi.fn(),
  startProcessing: vi.fn(),
  fetchJobDetail: vi.fn(),
  fetchUncertaintyCallouts: vi.fn(),
  cancelProcessing: vi.fn(),
  fetchCurrentUserProfile: vi.fn(),
  fetchJobExport: vi.fn(),
  fetchDeletionProof: vi.fn(),
  fetchTransformationManifest: vi.fn(),
}));

vi.mock("../../../web/src/lib/costEstimateHelpers", async () => {
  const actual = await vi.importActual<typeof import("../../../web/src/lib/costEstimateHelpers")>(
    "../../../web/src/lib/costEstimateHelpers",
  );
  return { ...actual, fetchJobEstimate: phase4Mocks.fetchJobEstimate, approveSingleJobOverage: phase4Mocks.approveSingleJobOverage };
});

vi.mock("../../../web/src/lib/previewHelpers", async () => {
  const actual = await vi.importActual<typeof import("../../../web/src/lib/previewHelpers")>(
    "../../../web/src/lib/previewHelpers",
  );
  return {
    ...actual,
    createPreview: phase4Mocks.createPreview,
    reviewPreview: phase4Mocks.reviewPreview,
    launchApprovedPreview: phase4Mocks.startProcessing,
  };
});

vi.mock("../../../web/src/lib/configurationHelpers", async () => {
  const actual = await vi.importActual<typeof import("../../../web/src/lib/configurationHelpers")>(
    "../../../web/src/lib/configurationHelpers",
  );
  return {
    ...actual,
    fetchFidelityCatalog: phase4Mocks.fetchFidelityCatalog,
    detectUploadEra: phase4Mocks.detectUploadEra,
    saveUploadConfiguration: phase4Mocks.saveUploadConfiguration,
  };
});

vi.mock("../../../web/src/lib/uploadHelpers", async () => {
  const actual = await vi.importActual<typeof import("../../../web/src/lib/uploadHelpers")>("../../../web/src/lib/uploadHelpers");
  return { ...actual, executeUploadFlow: phase4Mocks.executeUploadFlow };
});

vi.mock("../../../web/src/lib/processingHelpers", async () => {
  const actual = await vi.importActual<typeof import("../../../web/src/lib/processingHelpers")>(
    "../../../web/src/lib/processingHelpers",
  );
  return {
    ...actual,
    startProcessing: phase4Mocks.startProcessing,
    fetchJobDetail: phase4Mocks.fetchJobDetail,
    fetchUncertaintyCallouts: phase4Mocks.fetchUncertaintyCallouts,
    cancelProcessing: phase4Mocks.cancelProcessing,
  };
});

vi.mock("../../../web/src/lib/outputDeliveryHelpers", async () => {
  const actual = await vi.importActual<typeof import("../../../web/src/lib/outputDeliveryHelpers")>(
    "../../../web/src/lib/outputDeliveryHelpers",
  );
  return {
    ...actual,
    fetchCurrentUserProfile: phase4Mocks.fetchCurrentUserProfile,
    fetchJobExport: phase4Mocks.fetchJobExport,
    fetchDeletionProof: phase4Mocks.fetchDeletionProof,
    fetchTransformationManifest: phase4Mocks.fetchTransformationManifest,
  };
});

vi.mock("../../../web/src/lib/supabaseClient", () => ({
  supabase: {
    auth: {
      getSession: vi.fn(async () => ({
        data: { session: { access_token: "token-123" } },
      })),
    },
  },
}));

import { App } from "../../../web/src/App";

type PlanTier = "hobbyist" | "pro" | "museum";

export function buildEstimate(blocker: "none" | "overage_approval_required" = "none", planTier: PlanTier = "museum") {
  return {
    configuration_fingerprint: "fingerprint-2026-03-13T00:05:00+00:00",
    estimated_usage_minutes: 5,
    operational_cost_breakdown_usd: { gpu_time: 2.16, storage: 0.04, api_calls: 0.0, total: 2.2 },
    billing_breakdown_usd: {
      included_usage: blocker === "none" ? 5 : 2,
      overage_minutes: blocker === "none" ? 0 : 3,
      overage_rate_usd_per_minute: 0.75,
      estimated_charge_total_usd: blocker === "none" ? 0.0 : 2.25,
    },
    confidence_interval_usd: { low: 1.94, high: 2.46 },
    usage_snapshot: {
      user_id: "phase4-user",
      plan_tier: planTier,
      used_minutes: 120,
      monthly_limit_minutes: planTier === "museum" ? 2000 : 500,
      remaining_minutes: planTier === "museum" ? 1880 : 380,
      estimated_next_job_minutes: 5,
      approved_overage_minutes: 0,
      remaining_approved_overage_minutes: 0,
      threshold_alerts: [],
      overage_approval_scope: null,
      hard_stop: blocker !== "none",
      price_reference: "price_subscription",
      overage_price_reference: "price_overage",
      reconciliation_source: "user_usage_monthly",
      reconciliation_status: "estimate_pending",
    },
    launch_blocker: blocker,
    estimator_version: "packet4e-v1",
    generated_at: "2026-03-14T00:05:00+00:00",
  };
}

function buildPreview(reviewStatus: "pending" | "approved" | "rejected" = "pending") {
  return {
    preview_id: "preview-phase4-1",
    upload_id: "upload-1",
    status: "ready" as const,
    configuration_fingerprint: "fingerprint-2026-03-13T00:05:00+00:00",
    review_status: reviewStatus,
    reviewed_at: reviewStatus === "pending" ? null : "2026-03-13T00:05:30+00:00",
    launch_status: "not_launched" as const,
    launched_job_id: null,
    launched_at: null,
    stale: false,
    expires_at: "2026-03-14T00:05:00+00:00",
    selection_mode: "scene_aware" as const,
    scene_diversity: 0.88,
    keyframe_count: 10,
    estimated_cost_summary: buildEstimate(),
    estimated_processing_time_seconds: 3,
    keyframes: Array.from({ length: 10 }, (_, index) => ({
      index,
      timestamp_seconds: index * 9 + 4,
      scene_number: index + 1,
      confidence_score: 0.85,
      thumbnail_url: `https://example.invalid/thumb-${index}.jpg`,
      frame_url: `https://example.invalid/frame-${index}.jpg`,
    })),
  };
}

export function buildCompletedJob() {
  return {
    job_id: "job-phase4-1",
    media_uri: "gs://chronos-test-bucket/uploads/phase4-user/upload-1/archive.mov",
    original_filename: "archive.mov",
    mime_type: "video/quicktime",
    fidelity_tier: "Restore" as const,
    effective_fidelity_tier: "Restore" as const,
    processing_mode: "balanced" as const,
    reproducibility_mode: "perceptual_equivalence" as const,
    estimated_duration_seconds: 180,
    status: "completed" as const,
    progress_topic: "job_progress:job-phase4-1",
    result_uri: "gs://chronos-test-bucket/results/job-phase4-1/result.mp4",
    manifest_available: true,
    failed_segments: [],
    warnings: [],
    created_at: "2026-03-13T00:06:00+00:00",
    updated_at: "2026-03-13T00:07:00+00:00",
    deletion_proof_id: "proof-phase4-1",
    progress: {
      job_id: "job-phase4-1",
      segment_index: 2,
      segment_count: 3,
      percent_complete: 100,
      eta_seconds: 0,
      status: "completed" as const,
      current_operation: "Completed",
      updated_at: "2026-03-13T00:07:00+00:00",
    },
    last_error: null,
  };
}

export function buildSavedConfiguration(configuredAt = "2026-03-13T00:05:00+00:00") {
  const configurationFingerprint = `fingerprint-${configuredAt}`;
  return {
    upload_id: "upload-1",
    status: "completed",
    persona: "filmmaker",
    fidelity_tier: "Restore",
    grain_preset: "Heavy",
    detection_snapshot: {
      upload_id: "upload-1",
      detection_id: "detect-1",
      job_id: "upload:upload-1",
      era: "1970s Super 8 Film",
      confidence: 0.61,
      manual_confirmation_required: true,
      top_candidates: [],
      forensic_markers: { grain_structure: "consumer film grain", color_saturation: 0.58, format_artifacts: ["frame_jitter"] },
      warnings: [],
      processing_timestamp: "2026-03-13T00:00:00+00:00",
      source: "system",
      model_version: "deterministic-fallback",
      prompt_version: "v1",
      estimated_usage_minutes: 3,
    },
    resolved_fidelity_profile: { tier: "Restore", grain_preset: "Heavy" },
    relative_cost_multiplier: 1.5,
    relative_processing_time_band: "<4 min/min",
    job_payload_preview: {
      media_uri: "gs://chronos-test-bucket/uploads/phase4-user/upload-1/archive.mov",
      original_filename: "archive.mov",
      mime_type: "video/quicktime",
      estimated_duration_seconds: 180,
      source_asset_checksum: "abc12345def67890",
      fidelity_tier: "Restore",
      reproducibility_mode: "perceptual_equivalence",
      processing_mode: "balanced",
      era_profile: {},
      config: { configured_at: configuredAt },
    },
    configured_at: configuredAt,
    configuration_fingerprint: configurationFingerprint,
  };
}

export function resetPhase4AppMocks(options: { planTier?: PlanTier } = {}) {
  const planTier = options.planTier ?? "museum";
  vi.restoreAllMocks();
  Object.values(phase4Mocks).forEach((mock) => {
    mock.mockReset();
  });
  vi.spyOn(window, "open").mockImplementation(() => null);

  phase4Mocks.fetchJobEstimate.mockResolvedValue(buildEstimate("none", planTier));
  phase4Mocks.approveSingleJobOverage.mockResolvedValue({
    user_id: "phase4-user",
    approval_scope: "single_job",
    approved_for_minutes: 5,
    remaining_approved_overage_minutes: 5,
    remaining_minutes: 0,
    threshold_alerts: [],
    overage_price_reference: "price_overage",
  });
  phase4Mocks.fetchFidelityCatalog.mockResolvedValue({
    personas: [{ persona: "filmmaker", label: "Filmmaker", default_fidelity_tier: "Restore", description: "Preserve era texture." }],
    tiers: [
      {
        tier: "Restore",
        label: "Restore",
        description: "Best for documentaries.",
        default_grain_preset: "Matched",
        allowed_grain_presets: ["Matched", "Subtle", "Heavy"],
        relative_cost_multiplier: 1.5,
        relative_processing_time_band: "<4 min/min",
        thresholds: { e_hf_min: 0.7, s_ls_band_db: 4.0, t_tc_min: 0.9, hallucination_limit_max: 0.15 },
        identity_lock: false,
      },
    ],
    grain_presets: ["Matched", "Subtle", "Heavy"],
    current_persona: "filmmaker",
    preferred_fidelity_tier: "Restore",
    preferred_grain_preset: "Heavy",
  });
  phase4Mocks.detectUploadEra.mockResolvedValue({
    upload_id: "upload-1",
    detection_id: "detect-1",
    job_id: "upload:upload-1",
    era: "1970s Super 8 Film",
    confidence: 0.61,
    manual_confirmation_required: true,
    top_candidates: [],
    forensic_markers: { grain_structure: "consumer film grain", color_saturation: 0.58, format_artifacts: ["frame_jitter"] },
    warnings: [],
    processing_timestamp: "2026-03-13T00:00:00+00:00",
    source: "system",
    model_version: "deterministic-fallback",
    prompt_version: "v1",
    estimated_usage_minutes: 3,
  });
  phase4Mocks.saveUploadConfiguration.mockResolvedValue(buildSavedConfiguration());
  phase4Mocks.executeUploadFlow.mockImplementation(async ({ handlers }) => {
    handlers.setStatus("completed");
    handlers.setProgress(100);
    handlers.setEtaSeconds(0);
    handlers.setCanResume(false);
    handlers.setError("");
    handlers.setUploadSession({
      upload_id: "upload-1",
      status: "completed",
      original_filename: "archive.mov",
      mime_type: "video/quicktime",
      size_bytes: 1024,
      checksum_sha256: "abc12345def67890",
      bucket_name: "chronos-test-bucket",
      object_path: "uploads/phase4-user/upload-1/archive.mov",
      media_uri: "gs://chronos-test-bucket/uploads/phase4-user/upload-1/archive.mov",
      resumable_session_url: "https://example.invalid/resumable",
      created_at: "2026-03-13T00:00:00+00:00",
      updated_at: "2026-03-13T00:00:00+00:00",
      completed_at: "2026-03-13T00:00:00+00:00",
    });
  });
  phase4Mocks.createPreview.mockResolvedValue(buildPreview());
  phase4Mocks.reviewPreview.mockResolvedValue(buildPreview("approved"));
  phase4Mocks.startProcessing.mockResolvedValue(buildCompletedJob());
  phase4Mocks.fetchJobDetail.mockResolvedValue(buildCompletedJob());
  phase4Mocks.fetchUncertaintyCallouts.mockResolvedValue({ job_id: "job-phase4-1", status: "completed", callouts: [] });
  phase4Mocks.fetchCurrentUserProfile.mockResolvedValue({ user_id: "phase4-user", plan_tier: planTier });
  phase4Mocks.fetchJobExport.mockResolvedValue({
    job_id: "job-phase4-1",
    status: "completed",
    variant: "av1",
    download_url: "https://example.invalid/delivery.zip",
    expires_at: "2026-03-20T00:00:00+00:00",
    file_name: "delivery.zip",
    size_bytes: 2048,
    sha256: "abc123",
    deletion_proof_id: "proof-phase4-1",
    package_contents: [],
  });
  phase4Mocks.fetchDeletionProof.mockResolvedValue({
    deletion_proof_id: "proof-phase4-1",
    job_id: "job-phase4-1",
    generated_at: "2026-03-14T00:10:00+00:00",
    signature_algorithm: "ed25519",
    signature: "signed",
    proof_sha256: "def456",
    pdf_download_url: "https://example.invalid/proof.pdf",
    pdf_expires_at: "2026-03-20T00:00:00+00:00",
    verification_summary: { status: "verified" },
  });
  phase4Mocks.fetchTransformationManifest.mockResolvedValue({
    job_id: "job-phase4-1",
    manifest_version: "1.0",
    created_at: "2026-03-14T00:10:00+00:00",
    media: { source_uri: "gs://chronos-test-bucket/uploads/phase4-user/upload-1/archive.mov" },
    transformations: [],
    quality_summary: { overall_quality_score: 0.95 },
  });
}

export function renderPhase4App() {
  return render(React.createElement(App));
}

export async function renderConfiguredPhase4App(user: { upload: Function; click: Function }) {
  renderPhase4App();
  const file = new File(["12345"], "archive.mov", { type: "video/quicktime" });
  await user.upload(screen.getByLabelText("Media file"), file);
  await user.click(screen.getByRole("button", { name: "Start Upload" }));
  await waitFor(() => expect(phase4Mocks.fetchFidelityCatalog).toHaveBeenCalled());
  await user.click(await screen.findByRole("button", { name: "Detect Era" }));
  await waitFor(() => expect(phase4Mocks.detectUploadEra).toHaveBeenCalled());
  await user.click(screen.getByRole("button", { name: "Save Configuration" }));
  await waitFor(() => expect(phase4Mocks.saveUploadConfiguration).toHaveBeenCalled());
}

export async function renderCompletedDelivery(user: { upload: Function; click: Function }, options: { planTier?: PlanTier } = {}) {
  resetPhase4AppMocks(options);
  await renderConfiguredPhase4App(user);
  await user.click(screen.getByRole("button", { name: "Review Preview & Start" }));
  await waitFor(() => expect(phase4Mocks.createPreview).toHaveBeenCalled());
  await waitFor(() => expect(phase4Mocks.fetchJobEstimate).toHaveBeenCalled());
  await user.click(screen.getByRole("button", { name: "Approve Preview" }));
  await waitFor(() => expect(phase4Mocks.reviewPreview).toHaveBeenCalled());
  await user.click(screen.getByRole("button", { name: "Start Processing" }));
  await waitFor(() => expect(screen.getByRole("heading", { name: "Packet 4D Delivery" })).toBeInTheDocument());
}

export { App, phase4Mocks };
