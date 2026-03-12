/**
 * Maps to:
 * - FR-003
 * - DS-001
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
} = vi.hoisted(() => ({
  fetchFidelityCatalog: vi.fn(),
  detectUploadEra: vi.fn(),
  saveUploadConfiguration: vi.fn(),
  executeUploadFlow: vi.fn(),
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
    current_persona: null,
    preferred_fidelity_tier: null,
    preferred_grain_preset: null,
  } as const;
}

describe("Packet 4B App flow", () => {
  beforeEach(() => {
    fetchFidelityCatalog.mockReset();
    detectUploadEra.mockReset();
    saveUploadConfiguration.mockReset();
    executeUploadFlow.mockReset();
  });

  it("renders the save flow and confirmation screen after a completed upload", async () => {
    const user = userEvent.setup();
    fetchFidelityCatalog.mockResolvedValue(buildCatalog());
    detectUploadEra.mockResolvedValue({
      upload_id: "upload-1",
      detection_id: "detect-1",
      job_id: "upload:upload-1",
      era: "1970s Super 8 Film",
      confidence: 0.94,
      manual_confirmation_required: false,
      top_candidates: [],
      forensic_markers: { grain_structure: "consumer film grain", color_saturation: 0.58, format_artifacts: ["frame_jitter"] },
      warnings: [],
      processing_timestamp: "2026-03-11T00:00:00+00:00",
      source: "system",
      model_version: "deterministic-fallback",
      prompt_version: "v1",
      estimated_usage_minutes: 3,
    });
    saveUploadConfiguration.mockResolvedValue({
      upload_id: "upload-1",
      status: "completed",
      persona: "filmmaker",
      fidelity_tier: "Enhance",
      grain_preset: "Heavy",
      detection_snapshot: {
        upload_id: "upload-1",
        detection_id: "detect-1",
        job_id: "upload:upload-1",
        era: "1970s Super 8 Film",
        confidence: 0.94,
        manual_confirmation_required: false,
        top_candidates: [],
        forensic_markers: { grain_structure: "consumer film grain", color_saturation: 0.58, format_artifacts: ["frame_jitter"] },
        warnings: [],
        processing_timestamp: "2026-03-11T00:00:00+00:00",
        source: "system",
        model_version: "deterministic-fallback",
        prompt_version: "v1",
        estimated_usage_minutes: 3,
      },
      resolved_fidelity_profile: { tier: "Enhance", grain_preset: "Heavy" },
      relative_cost_multiplier: 1.0,
      relative_processing_time_band: "<2 min/min",
      job_payload_preview: {
        media_uri: "gs://chronos-test-bucket/uploads/flow-user/upload-1/archive.mov",
        original_filename: "archive.mov",
        mime_type: "video/quicktime",
        estimated_duration_seconds: 180,
        source_asset_checksum: "abc12345def67890",
        fidelity_tier: "Enhance",
        reproducibility_mode: "perceptual_equivalence",
        processing_mode: "balanced",
        era_profile: {},
        config: {},
      },
      configured_at: "2026-03-11T00:05:00+00:00",
    });
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
        created_at: "2026-03-11T00:00:00+00:00",
        updated_at: "2026-03-11T00:00:00+00:00",
        completed_at: "2026-03-11T00:00:00+00:00",
      });
    });

    render(React.createElement(App));

    const fileInput = screen.getAllByLabelText("Media file")[0];
    const file = new File(["12345"], "archive.mov", { type: "video/quicktime" });
    await user.upload(fileInput, file);
    await user.click(screen.getAllByRole("button", { name: "Start Upload" })[0]);

    await waitFor(() => expect(fetchFidelityCatalog).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByText("Launch-Ready Configuration")).toBeInTheDocument());

    await user.selectOptions(await screen.findByLabelText("Select user persona"), "filmmaker");
    await user.click(screen.getByRole("radio", { name: "Enhance" }));
    await waitFor(() =>
      expect((screen.getByLabelText("Select grain preset") as HTMLSelectElement).value).toBe("Subtle"),
    );
    await user.selectOptions(await screen.findByLabelText("Select grain preset"), "Heavy");
    await user.click(screen.getByRole("button", { name: "Detect Era" }));

    await waitFor(() => expect(detectUploadEra).toHaveBeenCalledWith(
      "",
      "token-123",
      "upload-1",
      { estimated_duration_seconds: 180 },
    ));
    expect(screen.getByText("1970s Super 8 Film")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Save Configuration" }));

    await waitFor(() => expect(saveUploadConfiguration).toHaveBeenCalledWith(
      "",
      "token-123",
      "upload-1",
      {
        persona: "filmmaker",
        fidelity_tier: "Enhance",
        grain_preset: "Heavy",
        estimated_duration_seconds: 180,
        manual_override_era: undefined,
        override_reason: undefined,
      },
    ));
    expect(screen.getByText((_, element) => element?.textContent === "Persona: filmmaker")).toBeInTheDocument();
    expect(screen.getByText((_, element) => element?.textContent === "Tier: Enhance")).toBeInTheDocument();
    expect(screen.getByText((_, element) => element?.textContent === "Grain preset: Heavy")).toBeInTheDocument();
    expect(screen.getByText((_, element) => element?.textContent === "Relative time: <2 min/min")).toBeInTheDocument();
  });

  it("clears stale manual override state after a normal detection refresh", async () => {
    const user = userEvent.setup();
    fetchFidelityCatalog.mockResolvedValue(buildCatalog());
    detectUploadEra
      .mockResolvedValueOnce({
        upload_id: "upload-1",
        detection_id: "detect-low",
        job_id: "upload:upload-1",
        era: "1970s Super 8 Film",
        confidence: 0.64,
        manual_confirmation_required: true,
        top_candidates: [{ era: "1980s VHS Tape", confidence: 0.52 }],
        forensic_markers: { grain_structure: "consumer film grain", color_saturation: 0.58, format_artifacts: ["frame_jitter"] },
        warnings: ["Manual confirmation required due to low confidence."],
        processing_timestamp: "2026-03-11T00:00:00+00:00",
        source: "system",
        model_version: "deterministic-fallback",
        prompt_version: "v1",
        estimated_usage_minutes: 3,
      })
      .mockResolvedValueOnce({
        upload_id: "upload-1",
        detection_id: "detect-override",
        job_id: "upload:upload-1",
        era: "1980s VHS Tape",
        confidence: 0.63,
        manual_confirmation_required: true,
        top_candidates: [{ era: "1970s Super 8 Film", confidence: 0.51 }],
        forensic_markers: { grain_structure: "magnetic noise smear", color_saturation: 0.41, format_artifacts: ["head_switching_noise"] },
        warnings: ["Manual override recorded."],
        processing_timestamp: "2026-03-11T00:01:00+00:00",
        source: "user_override",
        model_version: "deterministic-fallback",
        prompt_version: "v1",
        estimated_usage_minutes: 3,
      })
      .mockResolvedValueOnce({
        upload_id: "upload-1",
        detection_id: "detect-refresh",
        job_id: "upload:upload-1",
        era: "1970s Super 8 Film",
        confidence: 0.91,
        manual_confirmation_required: false,
        top_candidates: [],
        forensic_markers: { grain_structure: "consumer film grain", color_saturation: 0.58, format_artifacts: ["frame_jitter"] },
        warnings: [],
        processing_timestamp: "2026-03-11T00:02:00+00:00",
        source: "system",
        model_version: "deterministic-fallback",
        prompt_version: "v1",
        estimated_usage_minutes: 3,
      });
    saveUploadConfiguration.mockResolvedValue({
      upload_id: "upload-1",
      status: "completed",
      persona: "filmmaker",
      fidelity_tier: "Enhance",
      grain_preset: "Subtle",
      detection_snapshot: {
        upload_id: "upload-1",
        detection_id: "detect-refresh",
        job_id: "upload:upload-1",
        era: "1970s Super 8 Film",
        confidence: 0.91,
        manual_confirmation_required: false,
        top_candidates: [],
        forensic_markers: { grain_structure: "consumer film grain", color_saturation: 0.58, format_artifacts: ["frame_jitter"] },
        warnings: [],
        processing_timestamp: "2026-03-11T00:02:00+00:00",
        source: "system",
        model_version: "deterministic-fallback",
        prompt_version: "v1",
        estimated_usage_minutes: 3,
      },
      resolved_fidelity_profile: { tier: "Enhance", grain_preset: "Subtle" },
      relative_cost_multiplier: 1.0,
      relative_processing_time_band: "<2 min/min",
      job_payload_preview: {
        media_uri: "gs://chronos-test-bucket/uploads/flow-user/upload-1/archive.mov",
        original_filename: "archive.mov",
        mime_type: "video/quicktime",
        estimated_duration_seconds: 180,
        source_asset_checksum: "abc12345def67890",
        fidelity_tier: "Enhance",
        reproducibility_mode: "perceptual_equivalence",
        processing_mode: "balanced",
        era_profile: {},
        config: {},
      },
      configured_at: "2026-03-11T00:05:00+00:00",
    });
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
        created_at: "2026-03-11T00:00:00+00:00",
        updated_at: "2026-03-11T00:00:00+00:00",
        completed_at: "2026-03-11T00:00:00+00:00",
      });
    });

    render(React.createElement(App));

    const fileInput = screen.getAllByLabelText("Media file")[0];
    const file = new File(["12345"], "archive.mov", { type: "video/quicktime" });
    await user.upload(fileInput, file);
    await user.click(screen.getAllByRole("button", { name: "Start Upload" })[0]);

    await waitFor(() => expect(fetchFidelityCatalog).toHaveBeenCalled());
    await user.selectOptions(await screen.findByLabelText("Select user persona"), "filmmaker");
    await user.click(screen.getByRole("button", { name: "Detect Era" }));
    await waitFor(() => expect(detectUploadEra).toHaveBeenCalledTimes(1));

    await user.click(screen.getByRole("button", { name: "Override Era" }));
    await user.selectOptions(await screen.findByLabelText("Manual era override"), "1980s VHS Tape");
    await user.type(await screen.findByLabelText("Override reason"), "Tape noise pattern matches VHS");
    await user.click(screen.getByRole("button", { name: "Apply Override" }));
    await waitFor(() =>
      expect(detectUploadEra).toHaveBeenNthCalledWith(2, "", "token-123", "upload-1", {
        estimated_duration_seconds: 180,
        manual_override_era: "1980s VHS Tape",
        override_reason: "Tape noise pattern matches VHS",
      }),
    );

    await user.click(screen.getByRole("button", { name: "Refresh Detection" }));
    await waitFor(() =>
      expect(detectUploadEra).toHaveBeenNthCalledWith(3, "", "token-123", "upload-1", {
        estimated_duration_seconds: 180,
      }),
    );

    await user.click(screen.getByRole("button", { name: "Save Configuration" }));
    await waitFor(() =>
      expect(saveUploadConfiguration).toHaveBeenCalledWith("", "token-123", "upload-1", {
        persona: "filmmaker",
        fidelity_tier: "Restore",
        grain_preset: "Matched",
        estimated_duration_seconds: 180,
        manual_override_era: undefined,
        override_reason: undefined,
      }),
    );
  });

  it("surfaces the explicit upgrade-required error from the configuration route", async () => {
    const user = userEvent.setup();
    fetchFidelityCatalog.mockResolvedValue(buildCatalog());
    detectUploadEra.mockResolvedValue({
      upload_id: "upload-1",
      detection_id: "detect-1",
      job_id: "upload:upload-1",
      era: "1860s Albumen Print",
      confidence: 0.92,
      manual_confirmation_required: false,
      top_candidates: [],
      forensic_markers: { grain_structure: "paper fiber bloom", color_saturation: 0.58, format_artifacts: ["albumen_sheen"] },
      warnings: [],
      processing_timestamp: "2026-03-11T00:00:00+00:00",
      source: "system",
      model_version: "deterministic-fallback",
      prompt_version: "v1",
      estimated_usage_minutes: 3,
    });
    saveUploadConfiguration.mockRejectedValue(
      new Error("Early-photography assets require minimum 2k processing and therefore require Pro or higher."),
    );
    executeUploadFlow.mockImplementation(async ({ handlers }) => {
      handlers.setStatus("completed");
      handlers.setProgress(100);
      handlers.setCanResume(false);
      handlers.setEtaSeconds(0);
      handlers.setError("");
      handlers.setUploadSession({
        upload_id: "upload-1",
        status: "completed",
        original_filename: "albumen-portrait.tif",
        mime_type: "image/tiff",
        size_bytes: 1024,
        checksum_sha256: "abc12345def67890",
        bucket_name: "chronos-test-bucket",
        object_path: "uploads/flow-user/upload-1/albumen-portrait.tif",
        media_uri: "gs://chronos-test-bucket/uploads/flow-user/upload-1/albumen-portrait.tif",
        resumable_session_url: "https://example.invalid/resumable",
        created_at: "2026-03-11T00:00:00+00:00",
        updated_at: "2026-03-11T00:00:00+00:00",
        completed_at: "2026-03-11T00:00:00+00:00",
      });
    });

    render(React.createElement(App));

    const fileInput = screen.getAllByLabelText("Media file")[0];
    const file = new File(["12345"], "albumen-portrait.tif", { type: "image/tiff" });
    await user.upload(fileInput, file);
    await user.click(screen.getAllByRole("button", { name: "Start Upload" })[0]);
    await waitFor(() => expect(fetchFidelityCatalog).toHaveBeenCalled());
    await user.selectOptions(await screen.findByLabelText("Select user persona"), "archivist");
    await user.click(screen.getByRole("button", { name: "Detect Era" }));
    await waitFor(() => expect(detectUploadEra).toHaveBeenCalled());
    await user.click(screen.getByRole("button", { name: "Save Configuration" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Early-photography assets require minimum 2k processing and therefore require Pro or higher.",
    );
  });
});
