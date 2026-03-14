import React from "react";

import { Button } from "./Button";
import { Modal } from "./Modal";
import type { UploadDetectEraResponse } from "../lib/configurationHelpers";

type EraOverrideModalProps = {
  open: boolean;
  detection: UploadDetectEraResponse | null;
  selectedEra: string;
  overrideReason: string;
  learnMoreUrl: string;
  onSelectEra: (value: string) => void;
  onChangeReason: (value: string) => void;
  onClose: () => void;
  onConfirm: () => void;
};

export function EraOverrideModal({
  open,
  detection,
  selectedEra,
  overrideReason,
  learnMoreUrl,
  onSelectEra,
  onChangeReason,
  onClose,
  onConfirm,
}: EraOverrideModalProps) {
  const candidateOptions = detection ? [detection.era, ...detection.top_candidates.map((candidate) => candidate.era)] : [];
  const uniqueOptions = Array.from(new Set(candidateOptions.filter(Boolean)));
  const canApplyOverride = Boolean(selectedEra.trim() && overrideReason.trim());
  return (
    <Modal open={open} onClose={onClose} labelledBy="era-override-title">
      <div style={{ display: "grid", gap: "var(--spacing-md)" }}>
        <div>
          <h4 id="era-override-title" style={{ margin: 0 }}>
            Override Era Detection
          </h4>
          <p style={{ marginBottom: 0 }}>
            Current confidence: {detection ? Math.round(detection.confidence * 100) : 0}%. Review the candidates, then
            choose a manual era if the visible evidence supports it.
          </p>
        </div>
        <label>
          <div style={{ marginBottom: "var(--spacing-xs)" }}>Manual era</div>
          <select
            aria-label="Manual era override"
            onChange={(event) => onSelectEra(event.target.value)}
            required
            value={selectedEra}
          >
            <option value="">Select an era</option>
            {uniqueOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
        <label>
          <div style={{ marginBottom: "var(--spacing-xs)" }}>Override reason</div>
          <textarea
            aria-label="Override reason"
            onChange={(event) => onChangeReason(event.target.value)}
            required
            rows={3}
            value={overrideReason}
          />
        </label>
        <a href={learnMoreUrl} rel="noreferrer" target="_blank">
          Learn More
        </a>
        <div style={{ display: "flex", gap: "var(--spacing-sm)", justifyContent: "flex-end" }}>
          <Button onClick={onClose} type="button" variant="secondary">
            Cancel
          </Button>
          <Button disabled={!canApplyOverride} onClick={onConfirm} type="button">
            Apply Override
          </Button>
        </div>
      </div>
    </Modal>
  );
}
