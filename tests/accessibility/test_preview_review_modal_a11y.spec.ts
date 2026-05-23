/**
 * Maps to:
 * - FR-006
 * - NFR-008
 * - DS-002
 * - DS-003
 * - DS-006
 */

import React, { useState } from "react";

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { PreviewReviewModal } from "../../web/src/components/PreviewReviewModal";

function buildEstimate() {
  return {
    configuration_fingerprint: "fingerprint-1",
    estimated_usage_minutes: 5,
    operational_cost_breakdown_usd: { gpu_time: 2.16, storage: 0.04, api_calls: 0.0, total: 2.2 },
    billing_breakdown_usd: {
      included_usage: 5,
      overage_minutes: 0,
      overage_rate_usd_per_minute: 0.75,
      estimated_charge_total_usd: 0.0,
    },
    confidence_interval_usd: { low: 1.94, high: 2.46 },
    usage_snapshot: {
      user_id: "a11y-user",
      plan_tier: "pro",
      used_minutes: 120,
      monthly_limit_minutes: 500,
      remaining_minutes: 380,
      estimated_next_job_minutes: 5,
      approved_overage_minutes: 0,
      remaining_approved_overage_minutes: 0,
      threshold_alerts: [],
      overage_approval_scope: null,
      hard_stop: false,
      price_reference: "price_subscription",
      overage_price_reference: "price_overage",
      reconciliation_source: "user_usage_monthly",
      reconciliation_status: "estimate_pending",
    },
    launch_blocker: "none" as const,
    estimator_version: "packet4e-v1",
    generated_at: "2026-04-04T00:00:00+00:00",
  };
}

function buildPreview() {
  return {
    preview_id: "preview-1",
    upload_id: "upload-1",
    status: "ready" as const,
    configuration_fingerprint: "fingerprint-1",
    review_status: "pending" as const,
    reviewed_at: null,
    launch_status: "not_launched" as const,
    launched_job_id: null,
    launched_at: null,
    stale: false,
    expires_at: "2026-04-05T00:00:00+00:00",
    selection_mode: "scene_aware" as const,
    scene_diversity: 0.91,
    keyframe_count: 10,
    estimated_cost_summary: buildEstimate(),
    estimated_processing_time_seconds: 3,
    keyframes: Array.from({ length: 10 }, (_, index) => ({
      index,
      timestamp_seconds: index * 7 + 3,
      scene_number: index + 1,
      confidence_score: 0.82,
      thumbnail_url: `https://example.invalid/thumb-${index}.jpg`,
      frame_url: `https://example.invalid/frame-${index}.jpg`,
    })),
  };
}

function ModalHarness({
  invalidated = false,
  notice = "",
}: {
  invalidated?: boolean;
  notice?: string;
}) {
  const [open, setOpen] = useState(false);
  return React.createElement(
    React.Fragment,
    null,
    React.createElement("button", { type: "button" }, "Open Preview Modal"),
    React.createElement(
      "button",
      {
        onClick: () => setOpen(true),
        type: "button",
      },
      "Review Preview & Start",
    ),
    React.createElement(PreviewReviewModal, {
      open,
      preview: buildPreview(),
      estimate: buildEstimate(),
      previewLoading: false,
      estimateLoading: false,
      reviewing: false,
      approving: false,
      launching: false,
      invalidated,
      error: "",
      notice,
      onClose: () => setOpen(false),
      onRefresh: vi.fn(),
      onApprovePreview: vi.fn(),
      onRejectPreview: vi.fn(),
      onApproveOverage: vi.fn(),
      onLaunch: vi.fn(),
    }),
  );
}

describe("Packet 5A preview review modal accessibility", () => {
  it("uses dialog semantics, traps focus, and restores focus on close", async () => {
    const user = userEvent.setup();
    render(React.createElement(ModalHarness));

    const openButton = screen.getByRole("button", { name: "Review Preview & Start" });
    openButton.focus();
    expect(openButton).toHaveFocus();

    await user.click(openButton);

    const dialog = await screen.findByRole("dialog", { name: "Review Preview & Start" });
    expect(dialog).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Close" })).toHaveFocus();

    await user.tab();
    expect(screen.getByRole("button", { name: "Refresh Preview" })).toHaveFocus();
    await user.tab();
    expect(screen.getByRole("button", { name: "Reject Preview" })).toHaveFocus();
    await user.tab();
    expect(screen.getByRole("button", { name: "Approve Preview" })).toHaveFocus();
    await user.tab();
    expect(screen.getByRole("button", { name: "Select preview keyframe 1" })).toHaveFocus();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog", { name: "Review Preview & Start" })).not.toBeInTheDocument();
    expect(openButton).toHaveFocus();
  });

  it("announces stale state and keeps review actions disabled", async () => {
    const user = userEvent.setup();
    render(React.createElement(ModalHarness, { invalidated: true, notice: "Preview approved. Launch is ready when you are." }));

    await user.click(screen.getByRole("button", { name: "Review Preview & Start" }));

    expect(await screen.findByText("Preview out of date - regenerate.")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Preview approved. Launch is ready when you are.");
    expect(screen.getByRole("button", { name: "Approve Preview" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Reject Preview" })).toBeDisabled();
  });
});
