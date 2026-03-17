/**
 * Maps to:
 * - DS-002
 * - DS-005
 */

import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { renderConfiguredPhase4App, resetPhase4AppMocks } from "./support/phase4AppHarness";

describe("Packet 4G modal focus management", () => {
  beforeEach(() => {
    resetPhase4AppMocks();
  });

  it("traps focus in the keyboard shortcuts modal and returns focus to the trigger", async () => {
    const user = userEvent.setup();
    await renderConfiguredPhase4App(user);

    const trigger = screen.getByRole("button", { name: "Help & Keyboard Shortcuts" });
    trigger.focus();
    expect(trigger).toHaveFocus();

    await user.click(trigger);

    expect(await screen.findByRole("dialog", { name: "Keyboard Shortcuts" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Close" })).toHaveFocus();

    await user.tab();
    expect(screen.getByRole("button", { name: "Close" })).toHaveFocus();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog", { name: "Keyboard Shortcuts" })).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });
});
