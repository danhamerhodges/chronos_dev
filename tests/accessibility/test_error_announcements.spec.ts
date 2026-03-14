/**
 * Maps to:
 * - DS-006
 * - FR-004
 */

import React from "react";

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const {
  fetchFidelityCatalog,
  detectUploadEra,
  saveUploadConfiguration,
  executeUploadFlow,
  startProcessing,
  fetchJobDetail,
  fetchUncertaintyCallouts,
  cancelProcessing,
} = vi.hoisted(() => ({
  fetchFidelityCatalog: vi.fn(),
  detectUploadEra: vi.fn(),
  saveUploadConfiguration: vi.fn(),
  executeUploadFlow: vi.fn(),
  startProcessing: vi.fn(),
  fetchJobDetail: vi.fn(),
  fetchUncertaintyCallouts: vi.fn(),
  cancelProcessing: vi.fn(),
}));

vi.mock("../../web/src/lib/configurationHelpers", async () => {
  const actual = await vi.importActual<typeof import("../../web/src/lib/configurationHelpers")>(
    "../../web/src/lib/configurationHelpers",
  );
  return {
    ...actual,
    fetchFidelityCatalog,
    detectUploadEra,
    saveUploadConfiguration,
  };
});

vi.mock("../../web/src/lib/uploadHelpers", async () => {
  const actual = await vi.importActual<typeof import("../../web/src/lib/uploadHelpers")>("../../web/src/lib/uploadHelpers");
  return {
    ...actual,
    executeUploadFlow,
  };
});

vi.mock("../../web/src/lib/processingHelpers", async () => {
  const actual = await vi.importActual<typeof import("../../web/src/lib/processingHelpers")>(
    "../../web/src/lib/processingHelpers",
  );
  return {
    ...actual,
    startProcessing,
    fetchJobDetail,
    fetchUncertaintyCallouts,
    cancelProcessing,
  };
});

vi.mock("../../web/src/lib/supabaseClient", () => ({
  supabase: {
    auth: {
      getSession: vi.fn(async () => ({
        data: {
          session: {
            access_token: "token-123",
          },
        },
      })),
    },
  },
}));

import { App } from "../../web/src/App";

function buildCatalog() {
  return {
    personas: [
      { persona: "filmmaker", label: "Filmmaker", default_fidelity_tier: "Restore", description: "Preserve era texture." },
    ],
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

function buildSavedConfiguration() {
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
      media_uri: "gs://chronos-test-bucket/uploads/error-user/upload-1/archive.mov",
      original_filename: "archive.mov",
      mime_type: "video/quicktime",
      estimated_duration_seconds: 180,
      source_asset_checksum: "abc12345def67890",
      fidelity_tier: "Restore",
      reproducibility_mode: "perceptual_equivalence",
      processing_mode: "balanced",
      era_profile: {},
      config: {},
    },
    configured_at: "2026-03-13T00:05:00+00:00",
  };
}

function buildProcessingJob() {
  return {
    job_id: "job-1",
    media_uri: "gs://chronos-test-bucket/uploads/error-user/upload-1/archive.mov",
    original_filename: "archive.mov",
    mime_type: "video/quicktime",
    fidelity_tier: "Restore",
    effective_fidelity_tier: "Restore",
    processing_mode: "balanced",
    reproducibility_mode: "perceptual_equivalence",
    estimated_duration_seconds: 180,
    status: "processing" as const,
    progress_topic: "job_progress:job-1",
    manifest_available: false,
    failed_segments: [],
    warnings: [],
    created_at: "2026-03-13T00:06:00+00:00",
    updated_at: "2026-03-13T00:06:10+00:00",
    progress: {
      job_id: "job-1",
      segment_index: 0,
      segment_count: 3,
      percent_complete: 12,
      eta_seconds: 80,
      status: "processing" as const,
      current_operation: "Processing segment 1",
      updated_at: "2026-03-13T00:06:10+00:00",
    },
  };
}

function buildCallouts() {
  return {
    job_id: "job-1",
    status: "processing" as const,
    callouts: [
      {
        callout_id: "job-1:global:low-confidence-era",
        code: "low_confidence_era_classification",
        severity: "warning" as const,
        title: "Low-confidence era classification",
        message: "Review the restored output carefully.",
        scope: "global" as const,
        time_range_seconds: { start: 0, end: 180 },
        source: { metric_key: "gemini_confidence" },
      },
    ],
  };
}

async function completeConfiguration(user: ReturnType<typeof userEvent.setup>) {
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

describe("Packet 4C status announcements", () => {
  beforeEach(() => {
    fetchFidelityCatalog.mockReset();
    detectUploadEra.mockReset();
    saveUploadConfiguration.mockReset();
    executeUploadFlow.mockReset();
    startProcessing.mockReset();
    fetchJobDetail.mockReset();
    fetchUncertaintyCallouts.mockReset();
    cancelProcessing.mockReset();

    fetchFidelityCatalog.mockResolvedValue(buildCatalog());
    detectUploadEra.mockResolvedValue(buildDetection());
    saveUploadConfiguration.mockResolvedValue(buildSavedConfiguration());
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
        object_path: "uploads/error-user/upload-1/archive.mov",
        media_uri: "gs://chronos-test-bucket/uploads/error-user/upload-1/archive.mov",
        resumable_session_url: "https://example.invalid/resumable",
        created_at: "2026-03-13T00:00:00+00:00",
        updated_at: "2026-03-13T00:00:00+00:00",
        completed_at: "2026-03-13T00:00:00+00:00",
      });
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("announces non-blocking callout refresh failures and supports manual retry", async () => {
    const user = userEvent.setup();
    startProcessing.mockResolvedValue(buildProcessingJob());
    fetchJobDetail.mockResolvedValue(buildProcessingJob());
    fetchUncertaintyCallouts.mockRejectedValueOnce(new Error("Unable to refresh uncertainty callouts.")).mockResolvedValueOnce(buildCallouts());

    await completeConfiguration(user);
    await user.click(screen.getByRole("button", { name: "Start Processing" }));

    const statusRegion = await screen.findByRole("status");
    expect(statusRegion).toHaveAttribute("aria-live", "polite");
    expect(statusRegion).toHaveTextContent("Unable to refresh uncertainty callouts.");

    await user.click(screen.getByRole("button", { name: "Retry Status Refresh" }));

    await waitFor(() => expect(fetchUncertaintyCallouts).toHaveBeenCalledTimes(2));
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(screen.getByText("Low-confidence era classification")).toBeInTheDocument();
  });

  it("keeps retry available when cancel succeeds but the follow-up refresh fails", async () => {
    const user = userEvent.setup();
    startProcessing.mockResolvedValue(buildProcessingJob());
    fetchJobDetail
      .mockResolvedValueOnce(buildProcessingJob())
      .mockRejectedValueOnce(new Error("Unable to refresh processing status."))
      .mockResolvedValue(buildProcessingJob());
    fetchUncertaintyCallouts.mockResolvedValue(buildCallouts());
    cancelProcessing.mockResolvedValue({
      job_id: "job-1",
      status: "cancel_requested",
      cancel_requested_at: "2026-03-13T00:06:30+00:00",
    });

    await completeConfiguration(user);
    await user.click(screen.getByRole("button", { name: "Start Processing" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Cancel Processing" })).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "Cancel Processing" }));

    const statusRegion = await screen.findByRole("status");
    expect(cancelProcessing).toHaveBeenCalledTimes(1);
    expect(statusRegion).toHaveTextContent("Unable to refresh processing status.");
    expect(screen.getByRole("button", { name: "Retry Status Refresh" })).toBeInTheDocument();
  });
});
