import React from "react";

import { formatTimeRange, type UncertaintyCallout } from "../lib/processingHelpers";

type UncertaintyCalloutsListProps = {
  callouts: UncertaintyCallout[];
};

export function UncertaintyCalloutsList({ callouts }: UncertaintyCalloutsListProps) {
  if (!callouts.length) {
    return null;
  }

  return (
    <section aria-labelledby="uncertainty-callouts-heading">
      <h3 id="uncertainty-callouts-heading" style={{ marginBottom: "var(--spacing-sm)" }}>
        Uncertainty Callouts
      </h3>
      <ul
        aria-label="Uncertainty callouts"
        style={{ display: "grid", gap: "var(--spacing-sm)", listStyle: "none", margin: 0, padding: 0 }}
      >
        {callouts.map((callout) => (
          <li
            key={callout.callout_id}
            style={{
              borderRadius: "var(--radius-md)",
              background: callout.severity === "critical" ? "#fff1e6" : "#fdf7e7",
              padding: "var(--spacing-sm) var(--spacing-md)",
            }}
          >
            <div style={{ display: "flex", gap: "var(--spacing-sm)", flexWrap: "wrap" }}>
              <strong>{callout.title}</strong>
              <span aria-label={`Severity ${callout.severity}`}>{callout.severity}</span>
              <span>{formatTimeRange(callout.time_range_seconds.start, callout.time_range_seconds.end)}</span>
            </div>
            <div style={{ color: "var(--color-text-muted)", marginTop: "var(--spacing-xs)" }}>{callout.message}</div>
          </li>
        ))}
      </ul>
    </section>
  );
}
