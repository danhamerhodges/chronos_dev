import React, { useEffect, useState } from "react";

import { Button } from "./Button";
import { Modal } from "./Modal";
import type { JobCostEstimateResponse } from "../lib/costEstimateHelpers";
import type { PreviewSessionResponse } from "../lib/previewHelpers";

type PreviewReviewModalProps = {
  open: boolean;
  preview: PreviewSessionResponse | null;
  estimate: JobCostEstimateResponse | null;
  previewLoading: boolean;
  estimateLoading: boolean;
  reviewing: boolean;
  approving: boolean;
  launching: boolean;
  invalidated: boolean;
  error: string;
  notice: string;
  onClose: () => void;
  onRefresh: () => void;
  onApprovePreview: () => void;
  onRejectPreview: () => void;
  onApproveOverage: () => void;
  onLaunch: () => void;
};

function currency(value: number): string {
  return `$${value.toFixed(2)}`;
}

function previewTimestampLabel(timestampSeconds: number): string {
  return `${Math.round(timestampSeconds)}s`;
}

export function PreviewReviewModal({
  open,
  preview,
  estimate,
  previewLoading,
  estimateLoading,
  reviewing,
  approving,
  launching,
  invalidated,
  error,
  notice,
  onClose,
  onRefresh,
  onApprovePreview,
  onRejectPreview,
  onApproveOverage,
  onLaunch,
}: PreviewReviewModalProps) {
  const [selectedKeyframeIndex, setSelectedKeyframeIndex] = useState(0);

  useEffect(() => {
    if (!preview?.keyframes?.length) {
      setSelectedKeyframeIndex(0);
      return;
    }
    setSelectedKeyframeIndex((current) => Math.min(current, preview.keyframes.length - 1));
  }, [preview?.keyframes]);

  const selectedKeyframe = preview?.keyframes?.[selectedKeyframeIndex] ?? preview?.keyframes?.[0] ?? null;
  const loading = previewLoading || estimateLoading;
  const previewStale = invalidated || preview?.stale === true;
  const reviewPending = preview ? preview.review_status !== "approved" : false;
  const reviewLocked = preview?.launch_status === "launched";
  const overageApprovalRequired = estimate?.launch_blocker === "overage_approval_required";
  const effectivePricing = estimate?.effective_pricing ?? estimate?.usage_snapshot.effective_pricing ?? null;
  const canReview = Boolean(preview) && !loading && !reviewing && !launching && !previewStale && !reviewLocked;
  const canStart =
    Boolean(preview) &&
    Boolean(estimate) &&
    !loading &&
    !launching &&
    !reviewPending &&
    !previewStale &&
    !overageApprovalRequired;

  return (
    <Modal open={open} onClose={onClose} labelledBy="preview-review-title" describedBy="preview-review-description">
      <div style={{ display: "grid", gap: "var(--spacing-md)", maxWidth: 900 }}>
        <div>
          <h4 id="preview-review-title" style={{ margin: 0 }}>
            Review Preview & Start
          </h4>
          <p id="preview-review-description" style={{ marginBottom: 0 }}>
            Packet 5A adds a preview approval gate so we can inspect representative keyframes, confirm the live
            estimate, and then launch from the approved preview only.
          </p>
        </div>

        {loading ? (
          <div aria-live="polite" role="status">
            Loading the preview review gate...
          </div>
        ) : null}

        {preview ? (
          <section aria-labelledby="preview-session-heading" style={{ display: "grid", gap: "var(--spacing-md)" }}>
            <div style={{ display: "flex", gap: "var(--spacing-md)", justifyContent: "space-between", flexWrap: "wrap" }}>
              <strong id="preview-session-heading">Preview review</strong>
              <span>
                Review status: {preview.review_status}
                {preview.reviewed_at ? ` (${new Date(preview.reviewed_at).toLocaleString()})` : ""}
              </span>
            </div>

            {selectedKeyframe ? (
              <div style={{ display: "grid", gap: "var(--spacing-sm)" }}>
                <div
                  style={{
                    borderRadius: "var(--radius-md)",
                    border: "1px solid rgba(15, 76, 129, 0.18)",
                    background: "#f7fafc",
                    padding: "var(--spacing-sm)",
                  }}
                >
                  <img
                    alt={`Selected preview frame ${selectedKeyframe.index + 1}`}
                    src={selectedKeyframe.frame_url}
                    style={{ display: "block", width: "100%", borderRadius: "var(--radius-sm)", objectFit: "cover" }}
                  />
                </div>
                <div style={{ color: "var(--color-text-muted)" }}>
                  Frame {selectedKeyframe.index + 1} at {previewTimestampLabel(selectedKeyframe.timestamp_seconds)} from scene{" "}
                  {selectedKeyframe.scene_number}
                </div>
              </div>
            ) : null}

            <div
              aria-label="Preview keyframes"
              style={{
                display: "grid",
                gap: "var(--spacing-sm)",
                gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))",
              }}
            >
              {preview.keyframes.map((keyframe) => {
                const selected = keyframe.index === selectedKeyframe?.index;
                return (
                  <button
                    key={keyframe.index}
                    type="button"
                    aria-label={`Select preview keyframe ${keyframe.index + 1}`}
                    aria-pressed={selected}
                    onClick={() => setSelectedKeyframeIndex(keyframe.index)}
                    style={{
                      display: "grid",
                      gap: "var(--spacing-xs)",
                      padding: "var(--spacing-xs)",
                      borderRadius: "var(--radius-md)",
                      border: selected ? "2px solid #0f4c81" : "1px solid rgba(15, 76, 129, 0.18)",
                      background: selected ? "#eef5ff" : "#ffffff",
                    }}
                  >
                    <img
                      alt={`Preview keyframe ${keyframe.index + 1}`}
                      src={keyframe.thumbnail_url}
                      style={{ width: "100%", borderRadius: "var(--radius-sm)", objectFit: "cover" }}
                    />
                    <span style={{ fontSize: "0.9rem" }}>{previewTimestampLabel(keyframe.timestamp_seconds)}</span>
                  </button>
                );
              })}
            </div>
          </section>
        ) : !previewLoading ? (
          <div className="chronos-warning-banner">Preview artifacts are unavailable right now. Refresh the preview to retry.</div>
        ) : null}

        {estimate ? (
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
              {preview ? <div>Estimated preview-backed launch time: {preview.estimated_processing_time_seconds}s</div> : null}
            </section>

            {effectivePricing ? (
              <section aria-labelledby="estimate-effective-pricing-heading" style={{ display: "grid", gap: "var(--spacing-xs)" }}>
                <strong id="estimate-effective-pricing-heading">Effective configured pricing</strong>
                <div>Pricebook version: {effectivePricing.pricebook_version}</div>
                <div>
                  Subscription price: {effectivePricing.subscription_price_id} ({currency(effectivePricing.subscription_price_usd)}/month)
                </div>
                <div>Included minutes: {effectivePricing.included_minutes_monthly} per month</div>
                <div>
                  Overage: {effectivePricing.overage_enabled ? `${effectivePricing.overage_price_id} at ${currency(effectivePricing.overage_rate_usd_per_minute)}/min` : "disabled"}
                </div>
              </section>
            ) : null}
          </>
        ) : null}

        {previewStale ? (
          <div className="chronos-warning-banner">Preview out of date - regenerate.</div>
        ) : null}
        {overageApprovalRequired ? (
          <div className="chronos-warning-banner">
            This launch needs single-job overage approval before processing can start.
          </div>
        ) : null}
        {reviewLocked ? (
          <div className="chronos-status-banner">This preview has already been launched.</div>
        ) : null}

        {notice ? (
          <div aria-live="polite" role="status" className="chronos-status-banner">
            {notice}
          </div>
        ) : null}

        {error ? (
          <div aria-live="assertive" role="alert" className="chronos-alert-banner">
            {error}
          </div>
        ) : null}

        <div style={{ display: "flex", gap: "var(--spacing-sm)", justifyContent: "flex-end", flexWrap: "wrap" }}>
          <Button data-autofocus="true" onClick={onClose} type="button" variant="secondary">
            Close
          </Button>
          <Button disabled={loading || reviewing || approving || launching} onClick={onRefresh} type="button" variant="secondary">
            {loading ? "Refreshing..." : "Refresh Preview"}
          </Button>
          {reviewPending ? (
            <>
              <Button disabled={!canReview} onClick={onRejectPreview} type="button" variant="secondary">
                {reviewing ? "Updating..." : "Reject Preview"}
              </Button>
              <Button disabled={!canReview} onClick={onApprovePreview} type="button">
                {reviewing ? "Updating..." : "Approve Preview"}
              </Button>
            </>
          ) : overageApprovalRequired ? (
            <Button disabled={loading || approving || launching || previewStale} onClick={onApproveOverage} type="button">
              {approving ? "Approving..." : "Approve Overage"}
            </Button>
          ) : (
            <Button disabled={!canStart} onClick={onLaunch} type="button">
              {launching ? "Starting..." : "Start Processing"}
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
}
