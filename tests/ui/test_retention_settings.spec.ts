/**
 * Maps to:
 * - SEC-005
 * - SEC-001
 * - SEC-013
 */

import React from "react";

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { fetchCurrentUserProfile, fetchManifestRetentionSettings, updateManifestRetentionSettings } = vi.hoisted(() => ({
  fetchCurrentUserProfile: vi.fn(),
  fetchManifestRetentionSettings: vi.fn(),
  updateManifestRetentionSettings: vi.fn(),
}));

vi.mock("../../web/src/lib/outputDeliveryHelpers", async () => {
  const actual = await vi.importActual<typeof import("../../web/src/lib/outputDeliveryHelpers")>(
    "../../web/src/lib/outputDeliveryHelpers",
  );
  return {
    ...actual,
    fetchCurrentUserProfile,
    fetchManifestRetentionSettings,
    updateManifestRetentionSettings,
  };
});

vi.mock("../../web/src/lib/supabaseClient", () => ({
  supabase: {
    auth: {
      getSession: vi.fn(async () => ({
        data: {
          session: {
            access_token: "token-123",
          },
        },
      })),
    },
  },
}));

import { App } from "../../web/src/App";

describe("SEC-005 retention settings UI", () => {
  beforeEach(() => {
    fetchCurrentUserProfile.mockReset();
    fetchManifestRetentionSettings.mockReset();
    updateManifestRetentionSettings.mockReset();
  });

  it("lets Museum admins save manifest retention and redaction settings", async () => {
    const user = userEvent.setup();
    fetchCurrentUserProfile.mockResolvedValue({
      user_id: "museum-admin",
      role: "admin",
      plan_tier: "museum",
      org_id: "museum-org",
    });
    fetchManifestRetentionSettings.mockResolvedValue({
      org_id: "museum-org",
      plan_tier: "museum",
      manifest_retention_days: 90,
      manifest_redaction_enabled: false,
      retention_class: "90d",
      updated_by: "previous-admin",
      updated_at: "2026-06-02T00:00:00+00:00",
    });
    updateManifestRetentionSettings.mockResolvedValue({
      org_id: "museum-org",
      plan_tier: "museum",
      manifest_retention_days: 365,
      manifest_redaction_enabled: true,
      retention_class: "365d",
      updated_by: "museum-admin",
      updated_at: "2026-06-03T00:00:00+00:00",
    });

    render(React.createElement(App));
    await user.click(screen.getByRole("button", { name: "Settings" }));

    expect(await screen.findByRole("dialog", { name: "Settings > Data Retention" })).toBeInTheDocument();
    await waitFor(() => expect(fetchManifestRetentionSettings).toHaveBeenCalledWith("", "token-123", "museum-org"));
    expect(screen.getByLabelText("Manifest retention window")).toHaveValue("90");
    expect(screen.getByRole("button", { name: "Save Retention Settings" })).toBeDisabled();
    await user.selectOptions(screen.getByLabelText("Manifest retention window"), "365");
    await user.click(screen.getByRole("checkbox", { name: "Manifest redaction" }));
    expect(screen.getByRole("button", { name: "Save Retention Settings" })).toBeEnabled();
    await user.click(screen.getByRole("button", { name: "Save Retention Settings" }));

    await waitFor(() =>
      expect(updateManifestRetentionSettings).toHaveBeenCalledWith("", "token-123", "museum-org", {
        manifestRetentionDays: 365,
        manifestRedactionEnabled: true,
      }),
    );
    expect(await screen.findByRole("status")).toHaveTextContent("Retention settings saved.");
  });

  it("does not save unchanged loaded retention settings", async () => {
    const user = userEvent.setup();
    fetchCurrentUserProfile.mockResolvedValue({
      user_id: "museum-admin",
      role: "admin",
      plan_tier: "museum",
      org_id: "museum-org",
    });
    fetchManifestRetentionSettings.mockResolvedValue({
      org_id: "museum-org",
      plan_tier: "museum",
      manifest_retention_days: 1825,
      manifest_redaction_enabled: true,
      retention_class: "1825d",
      updated_by: "previous-admin",
      updated_at: "2026-06-02T00:00:00+00:00",
    });

    render(React.createElement(App));
    await user.click(screen.getByRole("button", { name: "Settings" }));

    expect(await screen.findByRole("dialog", { name: "Settings > Data Retention" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByLabelText("Manifest retention window")).toHaveValue("1825"));
    expect(screen.getByRole("checkbox", { name: "Manifest redaction" })).toBeChecked();
    expect(screen.getByRole("button", { name: "Save Retention Settings" })).toBeDisabled();
    expect(updateManifestRetentionSettings).not.toHaveBeenCalled();
  });

  it("shows the settings modal but disables saves for users without Museum admin access", async () => {
    const user = userEvent.setup();
    fetchCurrentUserProfile.mockResolvedValue({
      user_id: "museum-member",
      role: "member",
      plan_tier: "museum",
      org_id: "museum-org",
    });

    render(React.createElement(App));
    await user.click(screen.getByRole("button", { name: "Settings" }));

    expect(await screen.findByRole("dialog", { name: "Settings > Data Retention" })).toBeInTheDocument();
    expect(await screen.findByRole("alert")).toHaveTextContent("Retention settings require Museum admin access.");
    expect(screen.getByRole("button", { name: "Save Retention Settings" })).toBeDisabled();
    expect(fetchManifestRetentionSettings).not.toHaveBeenCalled();
    expect(updateManifestRetentionSettings).not.toHaveBeenCalled();
  });
});
