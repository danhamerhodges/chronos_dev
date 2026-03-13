/**
 * Maps to:
 * - DS-006
 * - FR-004
 */

import React from "react";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { UncertaintyCalloutsList } from "../../web/src/components/UncertaintyCalloutsList";

describe("Packet 4C uncertainty callouts accessibility", () => {
  it("renders an accessible callout list with severity and time range labels", () => {
    render(
      React.createElement(UncertaintyCalloutsList, {
        callouts: [
          {
            callout_id: "job-1:global:low-confidence-era",
            code: "low_confidence_era_classification",
            severity: "warning",
            title: "Low-confidence era classification",
            message: "Review the restored output carefully.",
            scope: "global",
            time_range_seconds: { start: 0, end: 180 },
            source: { metric_key: "gemini_confidence" },
          },
          {
            callout_id: "job-1:segment:1:texture-loss",
            code: "texture_loss_risk",
            severity: "critical",
            title: "Texture loss risk",
            message: "Texture-energy metrics are close to the acceptance threshold for this segment.",
            scope: "segment",
            time_range_seconds: { start: 10, end: 20 },
            source: { segment_index: 1, metric_key: "e_hf" },
          },
        ],
      }),
    );

    expect(screen.getByRole("heading", { name: "Uncertainty Callouts" })).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Uncertainty callouts" })).toBeInTheDocument();
    expect(screen.getByLabelText("Severity warning")).toBeInTheDocument();
    expect(screen.getByLabelText("Severity critical")).toBeInTheDocument();
    expect(screen.getByText("0s-180s")).toBeInTheDocument();
    expect(screen.getByText("10s-20s")).toBeInTheDocument();
  });
});
