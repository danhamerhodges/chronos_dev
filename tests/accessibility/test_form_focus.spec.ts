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

    expect(fileInput).toHaveFocus();
    expect(fileInput).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("alert")).toHaveTextContent("Supported formats are MP4, AVI, MOV, MKV, TIFF, PNG, and JPEG.");
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
    expect(personaSelect).toHaveFocus();
    expect(personaSelect).toHaveAttribute("aria-invalid", "true");
    expect(personaSelect).toHaveAttribute("aria-describedby", "packet4g-form-error");
    expect(screen.getByRole("alert")).toHaveTextContent("Select a persona before saving the Packet 4G configuration.");
  });
});
