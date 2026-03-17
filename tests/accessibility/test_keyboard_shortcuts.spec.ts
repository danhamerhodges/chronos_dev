/**
 * Maps to:
 * - DS-002
 * - DS-005
 */

import { fireEvent, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import {
  buildSavedConfiguration,
  phase4Mocks,
  renderCompletedDelivery,
  renderConfiguredPhase4App,
  resetPhase4AppMocks,
} from "./support/phase4AppHarness";

const packet4gShortcutKeys = ["u", "s", "l", "e"] as const;

function expectShortcutsIgnored(activeElement: HTMLElement, dispatchTarget: EventTarget = window) {
  for (const key of packet4gShortcutKeys) {
    fireEvent.keyDown(dispatchTarget, { key, ctrlKey: true, shiftKey: true });
    expect(activeElement).toHaveFocus();
    fireEvent.keyDown(dispatchTarget, { key, metaKey: true, shiftKey: true });
    expect(activeElement).toHaveFocus();
  }
}

describe("Packet 4G keyboard shortcuts", () => {
  beforeEach(() => {
    resetPhase4AppMocks();
  });

  it("documents the supported Phase 4 shortcuts in the help dialog", async () => {
    const user = userEvent.setup();
    await renderConfiguredPhase4App(user);

    const helpButton = screen.getByRole("button", { name: "Help & Keyboard Shortcuts" });
    await user.click(helpButton);

    expect(await screen.findByRole("dialog", { name: "Keyboard Shortcuts" })).toBeInTheDocument();
    expect(screen.getByText("Cmd/Ctrl + Shift + U")).toBeInTheDocument();
    expect(screen.getByText("Cmd/Ctrl + Shift + S")).toBeInTheDocument();
    expect(screen.getByText("Cmd/Ctrl + Shift + L")).toBeInTheDocument();
    expect(screen.getByText("Cmd/Ctrl + Shift + E")).toBeInTheDocument();
  });

  it("moves focus to current Phase 4 controls through shortcut keys", async () => {
    const user = userEvent.setup();
    await renderConfiguredPhase4App(user);

    fireEvent.keyDown(window, { key: "u", ctrlKey: true, shiftKey: true });
    expect(screen.getByLabelText("Media file")).toHaveFocus();

    fireEvent.keyDown(window, { key: "s", ctrlKey: true, shiftKey: true });
    expect(screen.getByRole("button", { name: "Save Configuration" })).toHaveFocus();

    fireEvent.keyDown(window, { key: "l", ctrlKey: true, shiftKey: true });
    expect(screen.getByRole("button", { name: "Review Cost & Start" })).toHaveFocus();
  });

  it("focuses the rerun launch action when the completed job state exposes it", async () => {
    const user = userEvent.setup();
    await renderCompletedDelivery(user);

    phase4Mocks.saveUploadConfiguration.mockResolvedValueOnce(buildSavedConfiguration("2026-03-13T00:08:00+00:00"));
    await user.click(screen.getByRole("button", { name: "Save Configuration" }));

    fireEvent.keyDown(window, { key: "l", ctrlKey: true, shiftKey: true });
    expect(screen.getByRole("button", { name: "Review Cost & Start Again" })).toHaveFocus();
  });

  it("jumps to the primary delivery action once exports are available", async () => {
    const user = userEvent.setup();
    await renderCompletedDelivery(user);

    fireEvent.keyDown(window, { key: "e", ctrlKey: true, shiftKey: true });
    expect(screen.getByRole("button", { name: "Download AV1 Package" })).toHaveFocus();
  });

  it("ignores global shortcuts while the keyboard shortcuts modal is open", async () => {
    const user = userEvent.setup();
    await renderConfiguredPhase4App(user);

    await user.click(screen.getByRole("button", { name: "Help & Keyboard Shortcuts" }));

    const closeButton = await screen.findByRole("button", { name: "Close" });
    expect(closeButton).toHaveFocus();

    expectShortcutsIgnored(closeButton);
  });

  it("ignores global shortcuts while the launch cost modal is open", async () => {
    const user = userEvent.setup();
    await renderConfiguredPhase4App(user);

    await user.click(screen.getByRole("button", { name: "Review Cost & Start" }));

    const closeButton = await screen.findByRole("button", { name: "Close" });
    expect(closeButton).toHaveFocus();

    expectShortcutsIgnored(closeButton);
  });

  it("ignores global shortcuts while the era override modal is open", async () => {
    const user = userEvent.setup();
    await renderConfiguredPhase4App(user);

    await user.click(screen.getByRole("button", { name: "Override Era" }));

    const manualEraSelect = await screen.findByRole("combobox", { name: "Manual era override" });
    expect(manualEraSelect).toHaveFocus();

    expectShortcutsIgnored(manualEraSelect);
  });

  it("ignores global shortcuts while focus is inside editable controls", async () => {
    const user = userEvent.setup();
    await renderConfiguredPhase4App(user);

    const durationInput = screen.getByRole("spinbutton", { name: "Estimated duration (seconds)" });
    durationInput.focus();
    expect(durationInput).toHaveFocus();

    expectShortcutsIgnored(durationInput, durationInput);
  });
});
