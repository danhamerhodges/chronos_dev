/**
 * Maps to:
 * - FR-005
 * - ENG-015
 * - DS-002
 * - DS-003
 * - DS-004
 * - DS-005
 * - DS-006
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
  fetchCurrentUserProfile,
  fetchJobExport,
  fetchDeletionProof,
  fetchTransformationManifest,
} = vi.hoisted(() => ({
  fetchFidelityCatalog: vi.fn(),
  detectUploadEra: vi.fn(),
  saveUploadConfiguration: vi.fn(),
  executeUploadFlow: vi.fn(),
  startProcessing: vi.fn(),
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

vi.mock("../../web/src/lib/outputDeliveryHelpers", async () => {
  const actual = await vi.importActual<typeof import("../../web/src/lib/outputDeliveryHelpers")>(
    "../../web/src/lib/outputDeliveryHelpers",
  );
  return {
    ...actual,
    fetchCurrentUserProfile,
    fetchJobExport,
    fetchDeletionProof,
    fetchTransformationManifest,
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
      media_uri: "gs://chronos-test-bucket/uploads/export-user/upload-1/archive.mov",
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

function buildCompletedJob() {
  return {
    job_id: "job-export-1",
    media_uri: "gs://chronos-test-bucket/uploads/export-user/upload-1/archive.mov",
    original_filename: "archive.mov",
    mime_type: "video/quicktime",
    fidelity_tier: "Restore",
    effective_fidelity_tier: "Restore",
    processing_mode: "balanced",
    reproducibility_mode: "perceptual_equivalence",
    estimated_duration_seconds: 180,
    status: "completed" as const,
    progress_topic: "job_progress:job-export-1",
    result_uri: "gs://chronos-test-bucket/results/job-export-1/result.mp4",
    manifest_available: true,
    deletion_proof_id: "proof-1",
    failed_segments: [],
    warnings: ["One segment was retried before completion."],
    created_at: "2026-03-13T00:06:00+00:00",
    updated_at: "2026-03-13T00:07:00+00:00",
    progress: {
      job_id: "job-export-1",
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

async function renderCompletedDelivery(user: ReturnType<typeof userEvent.setup>): Promise<void> {
  render(React.createElement(App));
  const file = new File(["12345"], "archive.mov", { type: "video/quicktime" });
  await user.upload(screen.getByLabelText("Media file"), file);
  await user.click(screen.getByRole("button", { name: "Start Upload" }));
  await waitFor(() => expect(fetchFidelityCatalog).toHaveBeenCalled());
  await user.click(await screen.findByRole("button", { name: "Detect Era" }));
  await waitFor(() => expect(detectUploadEra).toHaveBeenCalled());
  await user.click(screen.getByRole("button", { name: "Save Configuration" }));
  await waitFor(() => expect(saveUploadConfiguration).toHaveBeenCalled());
  await user.click(screen.getByRole("button", { name: "Start Processing" }));
  await waitFor(() => expect(screen.getByRole("heading", { name: "Packet 4D Delivery" })).toBeInTheDocument());
}

describe("Packet 4D delivery flow", () => {
  let windowOpenSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    fetchFidelityCatalog.mockReset();
    detectUploadEra.mockReset();
    saveUploadConfiguration.mockReset();
    executeUploadFlow.mockReset();
    startProcessing.mockReset();
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
        object_path: "uploads/export-user/upload-1/archive.mov",
        media_uri: "gs://chronos-test-bucket/uploads/export-user/upload-1/archive.mov",
        resumable_session_url: "https://example.invalid/resumable",
        created_at: "2026-03-13T00:00:00+00:00",
        updated_at: "2026-03-13T00:00:00+00:00",
        completed_at: "2026-03-13T00:00:00+00:00",
      });
    });
    startProcessing.mockResolvedValue(buildCompletedJob());
    fetchJobDetail.mockResolvedValue(buildCompletedJob());
    fetchUncertaintyCallouts.mockResolvedValue({ job_id: "job-export-1", status: "completed", callouts: [] });
    fetchCurrentUserProfile.mockResolvedValue({ user_id: "export-user", plan_tier: "museum" });
    fetchJobExport.mockResolvedValue({
      job_id: "job-export-1",
      status: "completed",
      variant: "av1",
      download_url: "https://storage.googleapis.com/downloads/job-export-1-av1.zip",
      expires_at: "2026-03-20T00:00:00+00:00",
      file_name: "chronos-job-export-1-av1.zip",
      size_bytes: 123456,
      sha256: "abc123",
      deletion_proof_id: "proof-1",
      package_contents: [
        "job-export-1-av1.mp4",
        "transformation_manifest.json",
        "uncertainty_callouts.json",
        "quality_report.pdf",
        "deletion_proof.pdf",
      ],
    });
    fetchDeletionProof.mockResolvedValue({
      deletion_proof_id: "proof-1",
      job_id: "job-export-1",
      generated_at: "2026-03-13T00:07:00+00:00",
      signature_algorithm: "HMAC-SHA256",
      signature: "sig-1",
      proof_sha256: "hash-1",
      pdf_download_url: "https://storage.googleapis.com/downloads/proof-1.pdf",
      pdf_expires_at: "2026-03-13T01:07:00+00:00",
      verification_summary: { status: "verified" },
    });
    fetchTransformationManifest.mockResolvedValue({ job_id: "job-export-1", manifest_sha256: "manifest-sha" });
    windowOpenSpy = vi.spyOn(window, "open").mockImplementation(() => null);
  });

  afterEach(() => {
    windowOpenSpy.mockRestore();
  });

  it("shows delivery actions after terminal completion and limits retention controls to museum users", async () => {
    const user = userEvent.setup();
    await renderCompletedDelivery(user);

    expect(screen.getByRole("button", { name: "Download AV1 Package" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Download Compatibility Package" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "View Manifest JSON" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Download Deletion Proof PDF" })).toBeInTheDocument();
    expect(screen.getByLabelText("Select retention window")).toBeInTheDocument();
  });

  it("keeps loading local to the clicked export action and announces when the download is ready", async () => {
    const user = userEvent.setup();
    let resolveExport: ((value: Awaited<ReturnType<typeof fetchJobExport>>) => void) | undefined;
    fetchJobExport.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveExport = resolve as typeof resolveExport;
        }),
    );

    await renderCompletedDelivery(user);
    await user.click(screen.getByRole("button", { name: "Download AV1 Package" }));

    const av1Button = screen.getByRole("button", { name: "Download AV1 Package" });
    expect(av1Button).toBeDisabled();
    expect(av1Button).toHaveTextContent("Preparing AV1...");
    expect(screen.getByRole("button", { name: "Download Compatibility Package" })).toBeEnabled();

    resolveExport?.({
      job_id: "job-export-1",
      status: "completed",
      variant: "av1",
      download_url: "https://storage.googleapis.com/downloads/job-export-1-av1.zip",
      expires_at: "2026-03-20T00:00:00+00:00",
      file_name: "chronos-job-export-1-av1.zip",
      size_bytes: 123456,
      sha256: "abc123",
      deletion_proof_id: "proof-1",
      package_contents: [
        "job-export-1-av1.mp4",
        "transformation_manifest.json",
        "uncertainty_callouts.json",
        "quality_report.pdf",
        "deletion_proof.pdf",
      ],
    });

    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("AV1 package download ready."));
    await waitFor(() => expect(windowOpenSpy).toHaveBeenCalledWith("https://storage.googleapis.com/downloads/job-export-1-av1.zip", "_self", undefined));
  });

  it("downloads the deletion proof directly from terminal job detail metadata", async () => {
    const user = userEvent.setup();
    await renderCompletedDelivery(user);

    await user.click(screen.getByRole("button", { name: "Download Deletion Proof PDF" }));

    await waitFor(() => expect(fetchDeletionProof).toHaveBeenCalledWith(expect.any(String), "token-123", "proof-1"));
    expect(fetchJobExport).not.toHaveBeenCalled();
    await waitFor(() =>
      expect(windowOpenSpy).toHaveBeenCalledWith("https://storage.googleapis.com/downloads/proof-1.pdf", "_self", undefined),
    );
    expect(screen.getByRole("status")).toHaveTextContent("Deletion proof download ready.");
  });

  it("shows a retryable delivery error when terminal proof metadata is missing", async () => {
    const user = userEvent.setup();
    startProcessing.mockResolvedValue({
      ...buildCompletedJob(),
      deletion_proof_id: null,
    });
    fetchJobDetail.mockResolvedValue({
      ...buildCompletedJob(),
      deletion_proof_id: null,
    });

    await renderCompletedDelivery(user);
    await user.click(screen.getByRole("button", { name: "Download Deletion Proof PDF" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Deletion proof metadata is not available yet.");
    expect(screen.getByRole("button", { name: "Retry Deletion Proof" })).toBeInTheDocument();
    expect(fetchDeletionProof).not.toHaveBeenCalled();
    expect(fetchJobExport).not.toHaveBeenCalled();
  });
});
