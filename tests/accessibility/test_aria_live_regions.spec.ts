/**
 * Maps to:
 * - DS-003
 * - DS-006
 * - FR-005
 */

import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { phase4Mocks, renderCompletedDelivery, resetPhase4AppMocks } from "./support/phase4AppHarness";

describe("Packet 4G aria-live regions", () => {
  beforeEach(() => {
    resetPhase4AppMocks();
  });

  it("announces successful export readiness through a polite status region", async () => {
    const user = userEvent.setup();
    await renderCompletedDelivery(user);

    await user.click(screen.getByRole("button", { name: "Download AV1 Package" }));

    const status = await screen.findByRole("status");
    expect(status).toHaveAttribute("aria-live", "polite");
    expect(status).toHaveTextContent("AV1 package download ready.");
  });

  it("announces delivery failures through an assertive alert region", async () => {
    const user = userEvent.setup();
    await renderCompletedDelivery(user);
    phase4Mocks.fetchJobExport.mockRejectedValueOnce({ status: 410, message: "The delivery package has expired." });

    await user.click(screen.getByRole("button", { name: "Download AV1 Package" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveAttribute("aria-live", "assertive");
    expect(alert).toHaveTextContent("The delivery package has expired.");
  });
});
