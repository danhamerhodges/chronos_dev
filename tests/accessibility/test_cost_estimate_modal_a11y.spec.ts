/**
 * Maps to:
 * - ENG-013
 * - NFR-003
 * - DS-002
 * - DS-003
 * - DS-005
 * - DS-006
 */

import React, { useState } from "react";

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { LaunchCostEstimateModal } from "../../web/src/components/LaunchCostEstimateModal";

function buildEstimate(blocker: "none" | "overage_approval_required" = "none") {
  return {
    estimated_usage_minutes: 5,
    operational_cost_breakdown_usd: { gpu_time: 2.16, storage: 0.04, api_calls: 0.0, total: 2.2 },
    billing_breakdown_usd: {
      included_usage: blocker === "none" ? 5 : 2,
      overage_minutes: blocker === "none" ? 0 : 3,
      overage_rate_usd_per_minute: 0.75,
      estimated_charge_total_usd: blocker === "none" ? 0.0 : 2.25,
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
      hard_stop: blocker !== "none",
      price_reference: "price_subscription",
      overage_price_reference: "price_overage",
      reconciliation_source: "user_usage_monthly",
      reconciliation_status: "estimate_pending",
    },
    launch_blocker: blocker,
    estimator_version: "packet4e-v1",
    generated_at: "2026-03-14T00:05:00+00:00",
  };
}

function ModalHarness({
  error = "",
  estimate = buildEstimate(),
  loading = false,
  notice = "",
}: {
  error?: string;
  estimate?: ReturnType<typeof buildEstimate> | null;
  loading?: boolean;
  notice?: string;
}) {
  const [open, setOpen] = useState(false);
  return React.createElement(
    React.Fragment,
    null,
    React.createElement("button", { type: "button" }, "Open Launch Modal"),
    React.createElement(
      "button",
      {
        onClick: () => setOpen(true),
        type: "button",
      },
      "Review Launch Cost",
    ),
    React.createElement(LaunchCostEstimateModal, {
      open,
      estimate,
      loading,
      approving: false,
      starting: false,
      error,
      notice,
      onClose: () => setOpen(false),
      onRetryEstimate: vi.fn(),
      onApproveOverage: vi.fn(),
      onStartProcessing: vi.fn(),
    }),
  );
}

describe("Packet 4E launch cost modal accessibility", () => {
  it("uses dialog semantics, traps focus, and restores focus on close", async () => {
    const user = userEvent.setup();
    render(React.createElement(ModalHarness));

    const openButton = screen.getByRole("button", { name: "Review Launch Cost" });
    openButton.focus();
    expect(openButton).toHaveFocus();

    await user.click(openButton);

    const dialog = await screen.findByRole("dialog", { name: "Review Cost & Start" });
    expect(dialog).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Close" })).toHaveFocus();

    await user.tab();
    expect(screen.getByRole("button", { name: "Refresh Estimate" })).toHaveFocus();
    await user.tab();
    expect(screen.getByRole("button", { name: "Start Processing" })).toHaveFocus();
    await user.tab();
    expect(screen.getByRole("button", { name: "Close" })).toHaveFocus();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog", { name: "Review Cost & Start" })).not.toBeInTheDocument();
    expect(openButton).toHaveFocus();
  });

  it("exposes retryable estimate failures as alerts and approval updates as polite status messages", async () => {
    const user = userEvent.setup();
    const { rerender } = render(
      React.createElement(ModalHarness, {
        estimate: null,
        error: "Unable to load the cost estimate.",
      }),
    );

    await user.click(screen.getByRole("button", { name: "Review Launch Cost" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Unable to load the cost estimate.");
    expect(screen.getByRole("button", { name: "Start Processing" })).toBeDisabled();

    rerender(
      React.createElement(ModalHarness, {
        estimate: buildEstimate("overage_approval_required"),
        notice: "Launch approval recorded. Start processing when you’re ready.",
      }),
    );

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Launch approval recorded. Start processing when you’re ready.",
    );
    expect(screen.getByRole("button", { name: "Approve Overage" })).toBeInTheDocument();
  });
});
