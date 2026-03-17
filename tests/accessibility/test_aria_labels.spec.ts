/**
 * Maps to:
 * - DS-003
 * - DS-006
 */

import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { renderCompletedDelivery, renderConfiguredPhase4App, resetPhase4AppMocks } from "./support/phase4AppHarness";

describe("Packet 4G ARIA labels", () => {
  beforeEach(() => {
    resetPhase4AppMocks();
  });

  it("exposes labelled controls across upload and configuration flows", async () => {
    const user = userEvent.setup();
    await renderConfiguredPhase4App(user);

    expect(screen.getByLabelText("Media file")).toBeInTheDocument();
    expect(screen.getByLabelText("Select user persona")).toBeInTheDocument();
    expect(screen.getByRole("radiogroup", { name: "Select restoration intensity: Conserve, Restore, or Enhance" })).toBeInTheDocument();
    expect(screen.getByLabelText("Select grain preset")).toBeInTheDocument();
  });

  it("keeps descriptive labels on terminal delivery actions", async () => {
    const user = userEvent.setup();
    await renderCompletedDelivery(user);

    expect(screen.getByLabelText("Select retention window")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Download AV1 Package" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Download Compatibility Package" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "View Manifest JSON" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Download Deletion Proof PDF" })).toBeInTheDocument();
  });
});
