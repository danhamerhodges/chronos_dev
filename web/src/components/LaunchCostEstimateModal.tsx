import React from "react";

import { Button } from "./Button";
import { Modal } from "./Modal";
import type { JobCostEstimateResponse } from "../lib/costEstimateHelpers";

type LaunchCostEstimateModalProps = {
  open: boolean;
  estimate: JobCostEstimateResponse | null;
  loading: boolean;
  approving: boolean;
  starting: boolean;
  error: string;
  notice: string;
  onClose: () => void;
  onRetryEstimate: () => void;
  onApproveOverage: () => void;
  onStartProcessing: () => void;
};

function currency(value: number): string {
  return `$${value.toFixed(2)}`;
}

export function LaunchCostEstimateModal({
  open,
  estimate,
  loading,
  approving,
  starting,
  error,
  notice,
  onClose,
  onRetryEstimate,
  onApproveOverage,
  onStartProcessing,
}: LaunchCostEstimateModalProps) {
  const launchBlocked = estimate?.launch_blocker === "overage_approval_required";

  return (
    <Modal open={open} onClose={onClose} labelledBy="launch-cost-title" describedBy="launch-cost-description">
      <div style={{ display: "grid", gap: "var(--spacing-md)", maxWidth: 520 }}>
        <div>
          <h4 id="launch-cost-title" style={{ margin: 0 }}>
            Review Cost & Start
          </h4>
          <p id="launch-cost-description" style={{ marginBottom: 0 }}>
            Packet 4E adds a launch-time cost estimate so we can review projected usage and charges before processing
            starts.
          </p>
        </div>

        {loading ? (
          <div aria-live="polite" role="status">
            Loading the latest estimate...
          </div>
        ) : estimate ? (
          <>
            <section aria-labelledby="estimate-operational-heading" style={{ display: "grid", gap: "var(--spacing-xs)" }}>
              <strong id="estimate-operational-heading">Operational cost breakdown</strong>
              <div>GPU time: {currency(estimate.operational_cost_breakdown_usd.gpu_time)}</div>
              <div>Storage: {currency(estimate.operational_cost_breakdown_usd.storage)}</div>
              <div>API calls: {currency(estimate.operational_cost_breakdown_usd.api_calls)}</div>
              <div>Total: {currency(estimate.operational_cost_breakdown_usd.total)}</div>
            </section>

            <section aria-labelledby="estimate-billing-heading" style={{ display: "grid", gap: "var(--spacing-xs)" }}>
              <strong id="estimate-billing-heading">Customer charge breakdown</strong>
              <div>Estimated usage: {estimate.estimated_usage_minutes} minutes</div>
              <div>Included usage: {estimate.billing_breakdown_usd.included_usage} minutes</div>
              <div>Overage minutes: {estimate.billing_breakdown_usd.overage_minutes} minutes</div>
              <div>Overage rate: {currency(estimate.billing_breakdown_usd.overage_rate_usd_per_minute)}/min</div>
              <div>Estimated charge: {currency(estimate.billing_breakdown_usd.estimated_charge_total_usd)}</div>
              <div>
                Confidence interval: {currency(estimate.confidence_interval_usd.low)} to{" "}
                {currency(estimate.confidence_interval_usd.high)}
              </div>
            </section>

            <section aria-labelledby="estimate-usage-heading" style={{ display: "grid", gap: "var(--spacing-xs)" }}>
              <strong id="estimate-usage-heading">Current usage posture</strong>
              <div>Plan: {estimate.usage_snapshot.plan_tier}</div>
              <div>
                Used this month: {estimate.usage_snapshot.used_minutes} / {estimate.usage_snapshot.monthly_limit_minutes} minutes
              </div>
              <div>Remaining included minutes: {estimate.usage_snapshot.remaining_minutes}</div>
              <div>Approved overage remaining: {estimate.usage_snapshot.remaining_approved_overage_minutes}</div>
            </section>

            {launchBlocked ? (
              <div
                className="chronos-warning-banner"
                style={{ background: "#fff7e6", color: "#7a4b00", borderColor: "#9a6700" }}
              >
                This launch needs single-job overage approval before processing can start.
              </div>
            ) : null}
          </>
        ) : null}

        {notice ? (
          <div
            aria-live="polite"
            role="status"
            className="chronos-status-banner"
            style={{ background: "#eef5ff", borderColor: "#0f4c81" }}
          >
            {notice}
          </div>
        ) : null}

        {error ? (
          <div
            aria-live="assertive"
            role="alert"
            className="chronos-alert-banner"
            style={{ background: "#fff0f0", color: "#8a1f1f", borderColor: "#b42318" }}
          >
            {error}
          </div>
        ) : null}

        <div style={{ display: "flex", gap: "var(--spacing-sm)", justifyContent: "flex-end", flexWrap: "wrap" }}>
          <Button onClick={onClose} type="button" variant="secondary">
            Close
          </Button>
          <Button disabled={loading || approving || starting} onClick={onRetryEstimate} type="button" variant="secondary">
            {loading ? "Refreshing..." : "Refresh Estimate"}
          </Button>
          {launchBlocked ? (
            <Button disabled={loading || approving || starting} onClick={onApproveOverage} type="button">
              {approving ? "Approving..." : "Approve Overage"}
            </Button>
          ) : (
            <Button disabled={loading || !estimate || starting} onClick={onStartProcessing} type="button">
              {starting ? "Starting..." : "Start Processing"}
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
}
