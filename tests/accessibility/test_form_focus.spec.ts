/**
 * Maps to:
 * - DS-003
 * - DS-005
 */

import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { phase4Mocks, renderPhase4App, resetPhase4AppMocks } from "./support/phase4AppHarness";

describe("Packet 4G form focus handling", () => {
  beforeEach(() => {
    resetPhase4AppMocks();
  });

  it("moves focus to the file input when upload validation fails", async () => {
    const user = userEvent.setup();
    renderPhase4App();

    const fileInput = screen.getByLabelText("Media file");
    const badFile = new File(["12345"], "archive.exe", { type: "application/octet-stream" });
    fireEvent.change(fileInput, { target: { files: [badFile] } });
    await user.click(screen.getByRole("button", { name: "Start Upload" }));

    await waitFor(() => expect(fileInput).toHaveFocus());
    expect(fileInput).toHaveAttribute("aria-invalid", "true");
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Supported formats are MP4, AVI, MOV, MKV, TIFF, PNG, and JPEG.");
    expect(alert).not.toHaveFocus();
  });

  it("moves focus to the first invalid configuration field when saving without a persona", async () => {
    const user = userEvent.setup();
    renderPhase4App();

    const file = new File(["12345"], "archive.mov", { type: "video/quicktime" });
    await user.upload(screen.getByLabelText("Media file"), file);
    await user.click(screen.getByRole("button", { name: "Start Upload" }));
    await waitFor(() => expect(phase4Mocks.fetchFidelityCatalog).toHaveBeenCalled());
    await user.click(await screen.findByRole("button", { name: "Detect Era" }));
    await waitFor(() => expect(phase4Mocks.detectUploadEra).toHaveBeenCalled());

    await user.selectOptions(screen.getByLabelText("Select user persona"), "");
    await user.click(screen.getByRole("button", { name: "Save Configuration" }));

    const personaSelect = screen.getByLabelText("Select user persona");
    await waitFor(() => expect(personaSelect).toHaveFocus());
    expect(personaSelect).toHaveAttribute("aria-invalid", "true");
    expect(personaSelect).toHaveAttribute("aria-describedby", "packet4g-form-error");
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Select a persona before saving the Packet 4G configuration.");
    expect(alert).not.toHaveFocus();
  });

  it("clears stale field targeting before surfacing runtime configuration errors", async () => {
    const user = userEvent.setup();
    renderPhase4App();

    const file = new File(["12345"], "archive.mov", { type: "video/quicktime" });
    await user.upload(screen.getByLabelText("Media file"), file);
    await user.click(screen.getByRole("button", { name: "Start Upload" }));
    await waitFor(() => expect(phase4Mocks.fetchFidelityCatalog).toHaveBeenCalled());
    await user.click(await screen.findByRole("button", { name: "Detect Era" }));
    await waitFor(() => expect(phase4Mocks.detectUploadEra).toHaveBeenCalled());

    const personaSelect = screen.getByLabelText("Select user persona");
    await user.selectOptions(personaSelect, "");
    await user.click(screen.getByRole("button", { name: "Save Configuration" }));
    await waitFor(() => expect(personaSelect).toHaveFocus());
    expect(personaSelect).toHaveAttribute("aria-invalid", "true");

    phase4Mocks.saveUploadConfiguration.mockRejectedValueOnce(new Error("Unable to save the launch-ready configuration."));

    await user.selectOptions(personaSelect, "filmmaker");
    await user.click(screen.getByRole("button", { name: "Save Configuration" }));

    const alert = await screen.findByRole("alert");
    await waitFor(() => expect(alert).toHaveFocus());
    expect(alert).toHaveTextContent("Unable to save the launch-ready configuration.");
    expect(personaSelect).not.toHaveAttribute("aria-invalid", "true");
    expect(personaSelect).not.toHaveAttribute("aria-describedby", "packet4g-form-error");
  });
});
