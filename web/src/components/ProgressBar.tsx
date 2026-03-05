import React from "react";

type ProgressBarProps = {
  value: number;
};

export function ProgressBar({ value }: ProgressBarProps) {
  const safe = Math.max(0, Math.min(value, 100));
  return (
    <div style={{ width: "100%", background: "#dde6ef", borderRadius: "999px" }}>
      <div
        style={{
          width: `${safe}%`,
          height: 10,
          borderRadius: "999px",
          background: "var(--color-brand-secondary)",
        }}
      />
    </div>
  );
}
