/**
 * Maps to:
 * - FR-006
 * - ENG-013
 * - NFR-008
 * - DS-006
 */

import React from "react";

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const {
  fetchFidelityCatalog,
  detectUploadEra,
  saveUploadConfiguration,
  executeUploadFlow,
  fetchJobEstimate,
  createPreview,
  reviewPreview,
  launchApprovedPreview,
  approveSingleJobOverage,
  fetchJobDetail,
  fetchUncertaintyCallouts,
  cancelProcessing,
  fetchCurrentUserProfile,
  fetchJobExport,
  fetchDeletionProof,
  fetchTransformationManifest,
} = vi.hoisted(() => ({
  fetchFidelityCatalog: vi.fn(),
  detectUploadEra: vi.fn(),
  saveUploadConfiguration: vi.fn(),
  executeUploadFlow: vi.fn(),
  fetchJobEstimate: vi.fn(),
  createPreview: vi.fn(),
  reviewPreview: vi.fn(),
  launchApprovedPreview: vi.fn(),
  approveSingleJobOverage: vi.fn(),
  fetchJobDetail: vi.fn(),
  fetchUncertaintyCallouts: vi.fn(),
  cancelProcessing: vi.fn(),
  fetchCurrentUserProfile: vi.fn(),
  fetchJobExport: vi.fn(),
  fetchDeletionProof: vi.fn(),
  fetchTransformationManifest: vi.fn(),
}));

vi.mock("../../web/src/lib/configurationHelpers", async () => {
  const actual = await vi.importActual<typeof import("../../web/src/lib/configurationHelpers")>(
    "../../web/src/lib/configurationHelpers",
  );
  return { ...actual, fetchFidelityCatalog, detectUploadEra, saveUploadConfiguration };
});

vi.mock("../../web/src/lib/costEstimateHelpers", async () => {
  const actual = await vi.importActual<typeof import("../../web/src/lib/costEstimateHelpers")>(
    "../../web/src/lib/costEstimateHelpers",
  );
  return { ...actual, fetchJobEstimate, approveSingleJobOverage };
});

vi.mock("../../web/src/lib/previewHelpers", async () => {
  const actual = await vi.importActual<typeof import("../../web/src/lib/previewHelpers")>(
    "../../web/src/lib/previewHelpers",
  );
  return { ...actual, createPreview, reviewPreview, launchApprovedPreview };
});

vi.mock("../../web/src/lib/uploadHelpers", async () => {
  const actual = await vi.importActual<typeof import("../../web/src/lib/uploadHelpers")>(
    "../../web/src/lib/uploadHelpers",
  );
  return { ...actual, executeUploadFlow };
});

vi.mock("../../web/src/lib/processingHelpers", async () => {
  const actual = await vi.importActual<typeof import("../../web/src/lib/processingHelpers")>(
    "../../web/src/lib/processingHelpers",
  );
  return { ...actual, fetchJobDetail, fetchUncertaintyCallouts, cancelProcessing };
});

vi.mock("../../web/src/lib/outputDeliveryHelpers", async () => {
  const actual = await vi.importActual<typeof import("../../web/src/lib/outputDeliveryHelpers")>(
    "../../web/src/lib/outputDeliveryHelpers",
  );
  return { ...actual, fetchCurrentUserProfile, fetchJobExport, fetchDeletionProof, fetchTransformationManifest };
});

vi.mock("../../web/src/lib/supabaseClient", () => ({
  supabase: {
    auth: {
      getSession: vi.fn(async () => ({
        data: { session: { access_token: "token-123" } },
      })),
    },
  },
}));

import { App } from "../../web/src/App";

function createDeferred<T>() {
  let resolve!: (value: T | PromiseLike<T>) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function buildCatalog() {
  return {
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
  };
}

function buildDetection() {
  return {
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
  };
}

function buildSavedConfiguration(configuredAt = "2026-03-14T00:05:00+00:00") {
  const configurationFingerprint = `fingerprint-${configuredAt}`;
  return {
    upload_id: "upload-1",
    status: "completed",
    persona: "filmmaker",
    fidelity_tier: "Restore",
    grain_preset: "Heavy",
    detection_snapshot: buildDetection(),
    resolved_fidelity_profile: { tier: "Restore", grain_preset: "Heavy" },
    relative_cost_multiplier: 1.5,
    relative_processing_time_band: "<4 min/min",
    job_payload_preview: {
      media_uri: "gs://chronos-test-bucket/uploads/cost-user/upload-1/archive.mov",
      original_filename: "archive.mov",
      mime_type: "video/quicktime",
      estimated_duration_seconds: 180,
      source_asset_checksum: "abc12345def67890",
      fidelity_tier: "Restore",
      reproducibility_mode: "perceptual_equivalence",
      processing_mode: "balanced",
      era_profile: {},
      config: { configured_at: configuredAt },
      launch_context: {
        source: "approved_preview",
        upload_id: "upload-1",
        configuration_fingerprint: configurationFingerprint,
      },
    },
    configured_at: configuredAt,
    configuration_fingerprint: configurationFingerprint,
  };
}

function buildEstimate(
  blocker: "none" | "overage_approval_required" = "none",
  configurationFingerprint = "fingerprint-2026-03-14T00:05:00+00:00",
) {
  return {
    configuration_fingerprint: configurationFingerprint,
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
      user_id: "cost-user",
      plan_tier: "pro",
      used_minutes: blocker === "none" ? 120 : 498,
      monthly_limit_minutes: 500,
      remaining_minutes: blocker === "none" ? 380 : 2,
      estimated_next_job_minutes: 5,
      approved_overage_minutes: 0,
      remaining_approved_overage_minutes: blocker === "none" ? 0 : 3,
      threshold_alerts: blocker === "none" ? [] : [100],
      overage_approval_scope: null,
      hard_stop: blocker === "none" ? false : true,
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

function buildPreview(
  reviewStatus: "pending" | "approved" | "rejected" = "pending",
  configurationFingerprint = "fingerprint-2026-03-14T00:05:00+00:00",
) {
  return {
    preview_id: "preview-1",
    upload_id: "upload-1",
    status: "ready" as const,
    configuration_fingerprint: configurationFingerprint,
    review_status: reviewStatus,
    reviewed_at: reviewStatus === "pending" ? null : "2026-03-14T00:05:30+00:00",
    launch_status: "not_launched" as const,
    launched_job_id: null,
    launched_at: null,
    stale: false,
    expires_at: "2026-03-15T00:00:00+00:00",
    selection_mode: "scene_aware" as const,
    scene_diversity: 0.88,
    keyframe_count: 10,
    estimated_cost_summary: buildEstimate("none", configurationFingerprint),
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

function buildQueuedJob() {
  return {
    job_id: "job-cost-1",
    media_uri: "gs://chronos-test-bucket/uploads/cost-user/upload-1/archive.mov",
    original_filename: "archive.mov",
    mime_type: "video/quicktime",
    fidelity_tier: "Restore",
    effective_fidelity_tier: "Restore",
    processing_mode: "balanced",
    reproducibility_mode: "perceptual_equivalence",
    estimated_duration_seconds: 180,
    status: "queued" as const,
    progress_topic: "job_progress:job-cost-1",
    result_uri: null,
    manifest_available: false,
    failed_segments: [],
    warnings: [],
    created_at: "2026-03-14T00:06:00+00:00",
    updated_at: "2026-03-14T00:06:00+00:00",
    queued_at: "2026-03-14T00:06:00+00:00",
    progress: {
      job_id: "job-cost-1",
      segment_index: 0,
      segment_count: 3,
      percent_complete: 0,
      eta_seconds: 180,
      status: "queued" as const,
      current_operation: "Queued",
      updated_at: "2026-03-14T00:06:00+00:00",
    },
    last_error: null,
    deletion_proof_id: null,
    cost_estimate_summary: null,
    cost_reconciliation_summary: null,
  };
}

async function prepareSavedConfiguration(user: ReturnType<typeof userEvent.setup>): Promise<void> {
  render(React.createElement(App));
  const file = new File(["12345"], "archive.mov", { type: "video/quicktime" });
  await user.upload(screen.getByLabelText("Media file"), file);
  await user.click(screen.getByRole("button", { name: "Start Upload" }));
  await waitFor(() => expect(fetchFidelityCatalog).toHaveBeenCalled());
  await user.click(await screen.findByRole("button", { name: "Detect Era" }));
  await waitFor(() => expect(detectUploadEra).toHaveBeenCalled());
  await user.click(screen.getByRole("button", { name: "Save Configuration" }));
  await waitFor(() => expect(saveUploadConfiguration).toHaveBeenCalled());
}

describe("Packet 5A preview review modal", () => {
  beforeEach(() => {
    fetchFidelityCatalog.mockReset();
    detectUploadEra.mockReset();
    saveUploadConfiguration.mockReset();
    executeUploadFlow.mockReset();
    fetchJobEstimate.mockReset();
    createPreview.mockReset();
    reviewPreview.mockReset();
    launchApprovedPreview.mockReset();
    approveSingleJobOverage.mockReset();
    fetchJobDetail.mockReset();
    fetchUncertaintyCallouts.mockReset();
    cancelProcessing.mockReset();
    fetchCurrentUserProfile.mockReset();
    fetchJobExport.mockReset();
    fetchDeletionProof.mockReset();
    fetchTransformationManifest.mockReset();

    fetchFidelityCatalog.mockResolvedValue(buildCatalog());
    detectUploadEra.mockResolvedValue(buildDetection());
    saveUploadConfiguration.mockResolvedValue(buildSavedConfiguration());
    createPreview.mockResolvedValue(buildPreview());
    reviewPreview.mockResolvedValue(buildPreview("approved"));
    executeUploadFlow.mockImplementation(async ({ handlers }) => {
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
        object_path: "uploads/cost-user/upload-1/archive.mov",
        media_uri: "gs://chronos-test-bucket/uploads/cost-user/upload-1/archive.mov",
        resumable_session_url: "https://example.invalid/resumable",
        created_at: "2026-03-14T00:00:00+00:00",
        updated_at: "2026-03-14T00:00:00+00:00",
        completed_at: "2026-03-14T00:00:00+00:00",
      });
    });
    approveSingleJobOverage.mockResolvedValue({
      user_id: "cost-user",
      approval_scope: "single_job",
      approved_for_minutes: 3,
      remaining_approved_overage_minutes: 3,
      remaining_minutes: 0,
      threshold_alerts: [],
      overage_price_reference: "price_overage",
    });
    launchApprovedPreview.mockResolvedValue(buildQueuedJob());
    fetchJobDetail.mockResolvedValue(buildQueuedJob());
    fetchUncertaintyCallouts.mockResolvedValue({ job_id: "job-cost-1", status: "queued", callouts: [] });
  });

  it("keeps launch blocked until preview approval is recorded, then starts processing", async () => {
    const user = userEvent.setup();
    const deferredEstimate = createDeferred<ReturnType<typeof buildEstimate>>();
    fetchJobEstimate.mockReturnValueOnce(deferredEstimate.promise);

    await prepareSavedConfiguration(user);
    await user.click(screen.getByRole("button", { name: "Review Preview & Start" }));

    const dialog = await screen.findByRole("dialog", { name: "Review Preview & Start" });
    expect(screen.getByRole("status")).toHaveTextContent("Loading the preview review gate...");
    expect(screen.getByRole("button", { name: "Start Processing" })).toBeDisabled();

    deferredEstimate.resolve(buildEstimate());

    await waitFor(() => expect(screen.getByText("Estimated usage: 5 minutes")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "Approve Preview" }));
    await waitFor(() => expect(reviewPreview).toHaveBeenCalledTimes(1));

    const startButton = screen.getByRole("button", { name: "Start Processing" });
    expect(startButton).toBeEnabled();

    await user.click(startButton);

    await waitFor(() => expect(launchApprovedPreview).toHaveBeenCalledTimes(1));
    expect(dialog).not.toBeInTheDocument();
  });

  it("retries modal loading and supports the single-job overage approval flow", async () => {
    const user = userEvent.setup();
    createPreview
      .mockResolvedValueOnce(buildPreview())
      .mockResolvedValueOnce(buildPreview("approved"))
      .mockResolvedValueOnce(buildPreview("approved"));
    fetchJobEstimate
      .mockRejectedValueOnce(new Error("Unable to load the cost estimate."))
      .mockResolvedValueOnce(buildEstimate("overage_approval_required"))
      .mockResolvedValueOnce(buildEstimate());

    await prepareSavedConfiguration(user);
    await user.click(screen.getByRole("button", { name: "Review Preview & Start" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to load the cost estimate.");
    expect(screen.getByRole("button", { name: "Start Processing" })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Refresh Preview" }));
    await waitFor(() => expect(screen.getByText("Estimated charge: $2.25")).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: "Approve Overage" }));

    await waitFor(() => expect(approveSingleJobOverage).toHaveBeenCalledWith("", "token-123", 3));
    await waitFor(() => expect(screen.getByRole("button", { name: "Start Processing" })).toBeEnabled());

    await user.click(screen.getByRole("button", { name: "Start Processing" }));
    await waitFor(() => expect(launchApprovedPreview).toHaveBeenCalledTimes(1));
  });

  it("keeps launch failures inside the modal as blocking errors", async () => {
    const user = userEvent.setup();
    createPreview.mockResolvedValue(buildPreview("approved"));
    fetchJobEstimate.mockResolvedValue(buildEstimate("none"));
    launchApprovedPreview.mockRejectedValueOnce(
      new Error("Pricing data is temporarily unavailable. Retry the request once billing metadata is available."),
    );

    await prepareSavedConfiguration(user);
    await user.click(screen.getByRole("button", { name: "Review Preview & Start" }));
    await waitFor(() => expect(screen.getByText("Estimated usage: 5 minutes")).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: "Start Processing" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Pricing data is temporarily unavailable. Retry the request once billing metadata is available.",
    );
    expect(screen.getByRole("dialog", { name: "Review Preview & Start" })).toBeInTheDocument();
    expect(launchApprovedPreview).toHaveBeenCalledTimes(1);
  });

  it("marks the open modal stale after re-saving configuration", async () => {
    const user = userEvent.setup();
    saveUploadConfiguration
      .mockResolvedValueOnce(buildSavedConfiguration("2026-03-14T00:05:00+00:00"))
      .mockResolvedValueOnce(buildSavedConfiguration("2026-03-14T00:10:00+00:00"));
    createPreview.mockResolvedValue(buildPreview());
    fetchJobEstimate.mockResolvedValue(buildEstimate());

    await prepareSavedConfiguration(user);
    await user.click(screen.getByRole("button", { name: "Review Preview & Start" }));
    await waitFor(() => expect(fetchJobEstimate).toHaveBeenCalledTimes(1));

    await user.click(screen.getByRole("button", { name: "Save Configuration" }));
    await waitFor(() => expect(saveUploadConfiguration).toHaveBeenCalledTimes(2));

    expect(await screen.findByText("Preview out of date - regenerate.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approve Preview" })).toBeDisabled();
  });
});
