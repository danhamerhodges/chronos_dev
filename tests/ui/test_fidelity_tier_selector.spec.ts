/**
 * Maps to:
 * - FR-003
 * - DS-001
 */

import React from "react";

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { FidelityTierSelector } from "../../web/src/components/FidelityTierSelector";

describe("FidelityTierSelector", () => {
  it("renders all tiers with descriptions, cost/time copy, and selection state", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();

    render(
      React.createElement(FidelityTierSelector, {
        selectedTier: "Restore",
        onSelect,
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
    expect(screen.getByText("Best for family videos. Reduces grain for a cleaner look.")).toBeInTheDocument();
    expect(screen.getByText("Cost 1.5x · Time <4 min/min")).toBeInTheDocument();

    await user.click(screen.getByLabelText("Enhance"));
    expect(onSelect).toHaveBeenCalledWith("Enhance");
  });
});
