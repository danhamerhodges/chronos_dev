/**
 * Maps to:
 * - DS-001
 */

import React from "react";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EraOverrideModal } from "../../web/src/components/EraOverrideModal";
import { FidelityTierSelector } from "../../web/src/components/FidelityTierSelector";

describe("Packet 4B accessibility baseline", () => {
  it("renders actual DS-001 controls with dialog and label semantics", () => {
    const { rerender } = render(
      React.createElement(FidelityTierSelector, {
        selectedTier: "Restore",
        onSelect: () => {},
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
      }),
    );

    expect(screen.getByRole("radiogroup", { name: /select restoration intensity/i })).toBeInTheDocument();
    expect(screen.getByLabelText("Restore")).toBeChecked();

    rerender(
      React.createElement(EraOverrideModal, {
        open: true,
        detection: {
          upload_id: "upload-1",
          detection_id: "detect-1",
          job_id: "upload:upload-1",
          era: "Unknown Era",
          confidence: 0.61,
          manual_confirmation_required: true,
          top_candidates: [{ era: "1970s Super 8 Film", confidence: 0.54 }],
          forensic_markers: {
            grain_structure: "consumer film grain",
            color_saturation: 0.58,
            format_artifacts: ["frame_jitter"],
          },
          warnings: ["Manual confirmation required due to low confidence."],
          processing_timestamp: "2026-03-11T00:00:00+00:00",
          source: "system",
          model_version: "deterministic-fallback",
          prompt_version: "v1",
          estimated_usage_minutes: 3,
        },
        selectedEra: "",
        overrideReason: "",
        learnMoreUrl: "https://example.test/learn-more",
        onSelectEra: () => {},
        onChangeReason: () => {},
        onClose: () => {},
        onConfirm: () => {},
      }),
    );

    expect(screen.getByRole("dialog")).toHaveAttribute("aria-modal", "true");
    expect(screen.getByLabelText("Manual era override")).toBeInTheDocument();
    expect(screen.getByLabelText("Override reason")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Apply Override" })).toBeDisabled();
  });
});
