/**
 * Maps to:
 * - DS-001
 */

import React from "react";

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { EraOverrideModal } from "../../web/src/components/EraOverrideModal";

describe("EraOverrideModal", () => {
  it("renders dialog semantics, warning copy, link, and confirm/cancel interactions", async () => {
    const onSelectEra = vi.fn();
    const onChangeReason = vi.fn();
    const onClose = vi.fn();
    const onConfirm = vi.fn();
    const user = userEvent.setup();

    render(
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
        onSelectEra,
        onChangeReason,
        onClose,
        onConfirm,
      }),
    );

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText(/current confidence: 61%/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Learn More" })).toHaveAttribute("href", "https://example.test/learn-more");

    await user.selectOptions(screen.getByLabelText("Manual era override"), "1970s Super 8 Film");
    expect(onSelectEra).toHaveBeenCalledWith("1970s Super 8 Film");

    await user.type(screen.getByLabelText("Override reason"), "Visible sprocket pattern");
    expect(onChangeReason).toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onClose).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole("button", { name: "Apply Override" }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });
});
