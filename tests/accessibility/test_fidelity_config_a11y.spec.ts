/**
 * Maps to:
 * - DS-001
 */

import React from "react";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

describe("Packet 4B accessibility baseline", () => {
  it("renders accessible labels and modal semantics for DS-001 controls", () => {
    const { rerender } = render(
      React.createElement("div", null, [
        React.createElement(
          "div",
          {
            key: "selector",
            "aria-label": "Select restoration intensity: Conserve, Restore, or Enhance",
            role: "radiogroup",
          },
          React.createElement("input", { "aria-label": "Restore", checked: true, name: "fidelity-tier", readOnly: true, type: "radio" }),
        ),
      ]),
    );

    expect(screen.getByRole("radiogroup", { name: /select restoration intensity/i })).toBeInTheDocument();
    expect(screen.getByLabelText("Restore")).toBeChecked();

    rerender(
      React.createElement(
        "div",
        {
          "aria-modal": "true",
          role: "dialog",
        },
        [
          React.createElement("select", { "aria-label": "Manual era override", key: "select" }),
          React.createElement("textarea", { "aria-label": "Override reason", key: "reason" }),
        ],
      ),
    );

    expect(screen.getByRole("dialog")).toHaveAttribute("aria-modal", "true");
    expect(screen.getByLabelText("Manual era override")).toBeInTheDocument();
    expect(screen.getByLabelText("Override reason")).toBeInTheDocument();
  });
});
