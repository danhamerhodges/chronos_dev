/**
 * Maps to:
 * - FR-006
 * - NFR-008
 * - DS-006
 */

import React from "react";

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
      user_id: "preview-user",
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

function buildPreview(reviewStatus: "pending" | "approved" = "pending") {
  return {
    preview_id: "preview-1",
    upload_id: "upload-1",
    status: "ready" as const,
    configuration_fingerprint: "fingerprint-1",
    review_status: reviewStatus,
    reviewed_at: reviewStatus === "approved" ? "2026-04-04T00:00:30+00:00" : null,
    launch_status: "not_launched" as const,
    launched_job_id: null,
    launched_at: null,
    stale: false,
    expires_at: "2026-04-05T00:00:00+00:00",
    selection_mode: "scene_aware" as const,
    scene_diversity: 0.92,
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

describe("PreviewReviewModal", () => {
  it("supports keyframe inspection and blocks launch until approval", async () => {
    const user = userEvent.setup();
    render(
      React.createElement(PreviewReviewModal, {
        open: true,
        preview: buildPreview("pending"),
        estimate: buildEstimate(),
        previewLoading: false,
        estimateLoading: false,
        reviewing: false,
        approving: false,
        launching: false,
        invalidated: false,
        error: "",
        notice: "",
        onClose: vi.fn(),
        onRefresh: vi.fn(),
        onApprovePreview: vi.fn(),
        onRejectPreview: vi.fn(),
        onApproveOverage: vi.fn(),
        onLaunch: vi.fn(),
      }),
    );

    expect(screen.queryByRole("button", { name: "Start Processing" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Select preview keyframe 4" }));
    expect(screen.getByAltText("Selected preview frame 4")).toBeInTheDocument();
  });

  it("surfaces the stale-state banner and disables review actions", () => {
    render(
      React.createElement(PreviewReviewModal, {
        open: true,
        preview: buildPreview("pending"),
        estimate: buildEstimate(),
        previewLoading: false,
        estimateLoading: false,
        reviewing: false,
        approving: false,
        launching: false,
        invalidated: true,
        error: "",
        notice: "",
        onClose: vi.fn(),
        onRefresh: vi.fn(),
        onApprovePreview: vi.fn(),
        onRejectPreview: vi.fn(),
        onApproveOverage: vi.fn(),
        onLaunch: vi.fn(),
      }),
    );

    expect(screen.getByText("Preview out of date - regenerate.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approve Preview" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Reject Preview" })).toBeDisabled();
  });
});
