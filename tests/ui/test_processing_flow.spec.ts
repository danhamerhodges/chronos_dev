/**
 * Maps to:
 * - FR-004
 * - DS-006
 */

import React from "react";

import { render, screen, waitFor, within } from "@testing-library/react";
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
      { persona: "archivist", label: "Archivist", default_fidelity_tier: "Conserve", description: "Preserve authenticity." },
      { persona: "filmmaker", label: "Filmmaker", default_fidelity_tier: "Restore", description: "Preserve era texture." },
      { persona: "prosumer", label: "Prosumer", default_fidelity_tier: "Enhance", description: "Clean up family footage." },
    ],
    tiers: [
      {
        tier: "Enhance",
        label: "Enhance",
        description: "Best for family videos. Reduces grain for a cleaner look.",
        default_grain_preset: "Subtle",
        allowed_grain_presets: ["Matched", "Subtle", "Heavy"],
        relative_cost_multiplier: 1.0,
        relative_processing_time_band: "<2 min/min",
        thresholds: { e_hf_min: 0.55, s_ls_band_db: 6.0, t_tc_min: 0.9, hallucination_limit_max: 0.3 },
        identity_lock: false,
      },
      {
        tier: "Restore",
        label: "Restore",
        description: "Best for documentaries. Preserves era-accurate texture.",
        default_grain_preset: "Matched",
        allowed_grain_presets: ["Matched", "Subtle", "Heavy"],
        relative_cost_multiplier: 1.5,
        relative_processing_time_band: "<4 min/min",
        thresholds: { e_hf_min: 0.7, s_ls_band_db: 4.0, t_tc_min: 0.9, hallucination_limit_max: 0.15 },
        identity_lock: false,
      },
      {
        tier: "Conserve",
        label: "Conserve",
        description: "Best for archival work. Maximum authenticity with full audit trail.",
        default_grain_preset: "Matched",
        allowed_grain_presets: ["Matched", "Subtle", "Heavy"],
        relative_cost_multiplier: 2.0,
        relative_processing_time_band: "<8 min/min",
        thresholds: { e_hf_min: 0.85, s_ls_band_db: 2.0, t_tc_min: 0.9, hallucination_limit_max: 0.05 },
        identity_lock: true,
      },
    ],
    grain_presets: ["Matched", "Subtle", "Heavy"],
    current_persona: "filmmaker",
    preferred_fidelity_tier: "Restore",
    preferred_grain_preset: "Heavy",
  } as const;
}

function buildDetection() {
  return {
    upload_id: "upload-1",
    detection_id: "detect-1",
    job_id: "upload:upload-1",
    era: "1970s Super 8 Film",
    confidence: 0.61,
    manual_confirmation_required: true,
    top_candidates: [{ era: "1970s Super 8 Film", confidence: 0.61 }],
    forensic_markers: { grain_structure: "consumer film grain", color_saturation: 0.58, format_artifacts: ["frame_jitter"] },
    warnings: ["Manual confirmation required due to low confidence."],
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
      media_uri: "gs://chronos-test-bucket/uploads/flow-user/upload-1/archive.mov",
      original_filename: "archive.mov",
      mime_type: "video/quicktime",
      estimated_duration_seconds: 180,
      source_asset_checksum: "abc12345def67890",
      fidelity_tier: "Restore",
      reproducibility_mode: "perceptual_equivalence",
      processing_mode: "balanced",
      era_profile: {
        capture_medium: "super_8",
        mode: "Restore",
        tier: "Pro",
        resolution_cap: "4k",
        hallucination_limit: 0.15,
        artifact_policy: {
          deinterlace: false,
          grain_intensity: "Heavy",
          preserve_edge_fog: false,
          preserve_chromatic_aberration: false,
        },
        era_range: { start_year: 1970, end_year: 1979 },
        gemini_confidence: 0.61,
        manual_confirmation_required: true,
      },
      config: {
        persona: "filmmaker",
        grain_preset: "Heavy",
        detection_snapshot: {
          detection_id: "detect-1",
          era: "1970s Super 8 Film",
          confidence: 0.61,
          source: "system",
        },
        fidelity_overrides: {
          grain_intensity: "Heavy",
        },
      },
    },
    configured_at: "2026-03-13T00:05:00+00:00",
  };
}

function buildJob(status: "queued" | "processing" | "completed") {
  const progress = status === "queued" ? 0 : status === "processing" ? 42 : 100;
  const eta = status === "completed" ? 0 : 65;
  return {
    job_id: "job-1",
    media_uri: "gs://chronos-test-bucket/uploads/flow-user/upload-1/archive.mov",
    original_filename: "archive.mov",
    mime_type: "video/quicktime",
    fidelity_tier: "Restore",
    effective_fidelity_tier: "Restore",
    processing_mode: "balanced",
    reproducibility_mode: "perceptual_equivalence",
    estimated_duration_seconds: 180,
    status,
    progress_topic: "job_progress:job-1",
    result_uri: status === "completed" ? "gs://chronos-test-bucket/results/job-1/result.mp4" : null,
    manifest_available: status === "completed",
    failed_segments: [],
    warnings: status === "completed" ? ["One segment was retried before completion."] : [],
    created_at: "2026-03-13T00:06:00+00:00",
    updated_at: "2026-03-13T00:07:00+00:00",
    progress: {
      job_id: "job-1",
      segment_index: status === "completed" ? 2 : 1,
      segment_count: 3,
      percent_complete: progress,
      eta_seconds: eta,
      status,
      current_operation: status === "completed" ? "Completed" : "Processing segment 2",
      updated_at: "2026-03-13T00:07:00+00:00",
    },
    last_error: null,
  };
}

function buildCallouts(status: "processing" | "completed") {
  return {
    job_id: "job-1",
    status,
    callouts: [
      {
        callout_id: "job-1:global:low-confidence-era",
        code: "low_confidence_era_classification",
        severity: "warning",
        title: "Low-confidence era classification",
        message: "Era detection confidence remained below 0.70. Review the restored output carefully.",
        scope: "global",
        time_range_seconds: { start: 0, end: 180 },
        source: { metric_key: "gemini_confidence" },
      },
      {
        callout_id: "job-1:segment:1:texture-loss",
        code: "texture_loss_risk",
        severity: "warning",
        title: "Texture loss risk",
        message: "Texture-energy metrics are close to the acceptance threshold for this segment.",
        scope: "segment",
        time_range_seconds: { start: 10, end: 20 },
        source: { segment_index: 1, metric_key: "e_hf" },
      },
    ],
  };
}

async function completePacket4BConfiguration(user: ReturnType<typeof userEvent.setup>) {
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
      object_path: "uploads/flow-user/upload-1/archive.mov",
      media_uri: "gs://chronos-test-bucket/uploads/flow-user/upload-1/archive.mov",
      resumable_session_url: "https://example.invalid/resumable",
      created_at: "2026-03-13T00:00:00+00:00",
      updated_at: "2026-03-13T00:00:00+00:00",
      completed_at: "2026-03-13T00:00:00+00:00",
    });
  });

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

describe("Packet 4C processing flow", () => {
  beforeEach(() => {
    fetchFidelityCatalog.mockReset();
    detectUploadEra.mockReset();
    saveUploadConfiguration.mockReset();
    executeUploadFlow.mockReset();
    startProcessing.mockReset();
    fetchJobDetail.mockReset();
    fetchUncertaintyCallouts.mockReset();
    cancelProcessing.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("launches processing, polls to a terminal summary, and renders uncertainty callouts", async () => {
    const user = userEvent.setup();
    startProcessing.mockResolvedValue(buildJob("queued"));
    fetchJobDetail
      .mockResolvedValueOnce(buildJob("processing"))
      .mockResolvedValueOnce(buildJob("completed"));
    fetchUncertaintyCallouts
      .mockResolvedValueOnce(buildCallouts("processing"))
      .mockResolvedValueOnce(buildCallouts("completed"));

    await completePacket4BConfiguration(user);
    await user.click(screen.getByRole("button", { name: "Start Processing" }));

    await waitFor(() => expect(startProcessing).toHaveBeenCalled());
    await waitFor(() => expect(fetchJobDetail).toHaveBeenCalledTimes(1));
    const processingCard = screen.getByRole("heading", { name: "Packet 4C Processing Flow" }).closest("section");
    expect(processingCard).not.toBeNull();
    expect(
      await within(processingCard as HTMLElement).findByText((_, element) => element?.textContent === "Status: processing"),
    ).toBeInTheDocument();

    await waitFor(() => expect(fetchJobDetail).toHaveBeenCalledTimes(2), { timeout: 2500 });
    expect(
      await within(processingCard as HTMLElement).findByText((_, element) => element?.textContent === "Status: completed"),
    ).toBeInTheDocument();
    expect(screen.getByText(/Result URI:/)).toBeInTheDocument();
    expect(screen.getByText("Low-confidence era classification")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start Processing Again" })).toBeInTheDocument();
  });
});
