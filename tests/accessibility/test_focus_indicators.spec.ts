/**
 * Maps to:
 * - DS-002
 * - DS-005
 */

import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { renderConfiguredPhase4App, resetPhase4AppMocks } from "./support/phase4AppHarness";

describe("Packet 4G focus indicators", () => {
  beforeEach(() => {
    resetPhase4AppMocks();
  });

  it("applies the shared focus-ready classes to core interactive controls", async () => {
    const user = userEvent.setup();
    await renderConfiguredPhase4App(user);

    expect(screen.getByRole("button", { name: "Start Upload" })).toHaveClass("chronos-button");
    expect(screen.getByLabelText("Media file")).toHaveClass("chronos-input");
    expect(screen.getByLabelText("Select user persona")).toHaveClass("chronos-select");
    expect(screen.getByText("Skip to main content")).toHaveClass("skip-link");
  });
});
