import React from "react";

import type { FidelityTier, FidelityTierCatalogItem } from "../lib/configurationHelpers";

type FidelityTierSelectorProps = {
  tiers: FidelityTierCatalogItem[];
  selectedTier: FidelityTier | null;
  onSelect: (tier: FidelityTier) => void;
  disabled?: boolean;
  describedBy?: string;
};

export function FidelityTierSelector({
  tiers,
  selectedTier,
  onSelect,
  disabled = false,
  describedBy,
}: FidelityTierSelectorProps) {
  return (
    <div aria-describedby={describedBy} aria-label="Select restoration intensity: Conserve, Restore, or Enhance" role="radiogroup">
      <div style={{ display: "grid", gap: "var(--spacing-sm)", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
        {tiers.map((tier) => {
          const checked = tier.tier === selectedTier;
          const inputId = `fidelity-tier-${tier.tier.toLowerCase()}`;
          return (
            <label
              className={[
                "chronos-radio-card",
                checked ? "chronos-radio-card--selected" : "",
                disabled ? "chronos-radio-card--disabled" : "",
              ]
                .filter(Boolean)
                .join(" ")}
              htmlFor={inputId}
              key={tier.tier}
            >
              <span style={{ display: "flex", alignItems: "center", gap: "var(--spacing-xs)" }}>
                <input
                  aria-label={tier.label}
                  checked={checked}
                  disabled={disabled}
                  id={inputId}
                  name="fidelity-tier"
                  onChange={() => onSelect(tier.tier)}
                  type="radio"
                  value={tier.tier}
                />
                <strong>{tier.label}</strong>
              </span>
              <span>{tier.description}</span>
              <span style={{ color: "var(--color-text-muted)" }}>
                Cost {tier.relative_cost_multiplier}x · Time {tier.relative_processing_time_band}
              </span>
            </label>
          );
        })}
      </div>
    </div>
  );
}
