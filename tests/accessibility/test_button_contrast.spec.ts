/**
 * Maps to:
 * - DS-004
 */

import React from "react";

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Button } from "../../web/src/components/Button";

describe("Packet 4G button contrast tokens", () => {
  it("renders primary and secondary buttons with high-contrast foreground colors", () => {
    render(
      React.createElement(
        React.Fragment,
        null,
        React.createElement(Button, null, "Primary Action"),
        React.createElement(Button, { variant: "secondary" }, "Secondary Action"),
      ),
    );

    expect(screen.getByRole("button", { name: "Primary Action" })).toHaveStyle({
      background: "var(--color-brand-primary)",
      color: "#ffffff",
    });
    expect(screen.getByRole("button", { name: "Secondary Action" })).toHaveStyle({
      background: "var(--color-brand-secondary)",
      color: "#ffffff",
    });
  });
});
