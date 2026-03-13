import React, { useEffect, useState } from "react";

import { Button } from "./components/Button";
import { Card } from "./components/Card";
import { EraOverrideModal } from "./components/EraOverrideModal";
import { FidelityTierSelector } from "./components/FidelityTierSelector";
import { InputField } from "./components/InputField";
import { ProgressBar } from "./components/ProgressBar";
import {
  allowedGrainPresetsForTier,
  canOverrideEra,
  defaultGrainPresetForTier,
  defaultTierForPersona,
  detectUploadEra,
  fetchFidelityCatalog,
  learnMoreUrl,
  saveUploadConfiguration,
  type FidelityTier,
  type FidelityTierCatalogResponse,
  type GrainPreset,
  type UploadConfigurationResponse,
  type UploadDetectEraResponse,
  type UserPersona,
} from "./lib/configurationHelpers";
import {
  UploadResponse,
  executeUploadFlow,
  isSupportedUploadFormat,
} from "./lib/uploadHelpers";
import { supabase } from "./lib/supabaseClient";

const API_BASE_URL =
  ((import.meta as unknown as { env?: Record<string, string> }).env?.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

async function currentAccessToken(): Promise<string> {
  const result = await supabase.auth.getSession();
  const token = result.data.session?.access_token;
  if (!token) {
    throw new Error("Sign in before starting an upload.");
  }
  return token;
}

export function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadSession, setUploadSession] = useState<UploadResponse | null>(null);
  const [progress, setProgress] = useState(0);
  const [etaSeconds, setEtaSeconds] = useState(0);
  const [status, setStatus] = useState<UploadResponse["status"]>("pending");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [canResume, setCanResume] = useState(false);
  const [catalog, setCatalog] = useState<FidelityTierCatalogResponse | null>(null);
  const [detection, setDetection] = useState<UploadDetectEraResponse | null>(null);
  const [savedConfiguration, setSavedConfiguration] = useState<UploadConfigurationResponse | null>(null);
  const [configBusy, setConfigBusy] = useState(false);
  const [estimatedDurationSeconds, setEstimatedDurationSeconds] = useState(180);
  const [selectedPersona, setSelectedPersona] = useState<UserPersona | "">("");
  const [selectedTier, setSelectedTier] = useState<FidelityTier | null>(null);
  const [selectedGrainPreset, setSelectedGrainPreset] = useState<GrainPreset | null>(null);
  const [showOverrideModal, setShowOverrideModal] = useState(false);
  const [manualOverrideEra, setManualOverrideEra] = useState("");
  const [overrideReason, setOverrideReason] = useState("");

  function resetConfigurationState(): void {
    setCatalog(null);
    setDetection(null);
    setSavedConfiguration(null);
    setSelectedPersona("");
    setSelectedTier(null);
    setSelectedGrainPreset(null);
    setShowOverrideModal(false);
    setManualOverrideEra("");
    setOverrideReason("");
  }

  useEffect(() => {
    if (!uploadSession || uploadSession.status !== "completed" || catalog) {
      return;
    }
    let ignore = false;
    void (async () => {
      try {
        setConfigBusy(true);
        const accessToken = await currentAccessToken();
        const nextCatalog = await fetchFidelityCatalog(API_BASE_URL, accessToken);
        if (ignore) {
          return;
        }
        setCatalog(nextCatalog);
        const nextPersona = nextCatalog.current_persona ?? "";
        const tierFromPersona = defaultTierForPersona(nextCatalog, nextPersona || null);
        const nextTier = nextCatalog.preferred_fidelity_tier ?? tierFromPersona;
        const nextGrain = nextCatalog.preferred_grain_preset ?? defaultGrainPresetForTier(nextCatalog, nextTier);
        setSelectedPersona(nextPersona);
        setSelectedTier(nextTier);
        setSelectedGrainPreset(nextGrain);
      } catch (caught) {
        if (!ignore) {
          setError(caught instanceof Error ? caught.message : "Unable to load Packet 4B configuration options.");
        }
      } finally {
        if (!ignore) {
          setConfigBusy(false);
        }
      }
    })();
    return () => {
      ignore = true;
    };
  }, [catalog, uploadSession]);

  async function runUpload(resumeExisting: boolean): Promise<void> {
    if (!selectedFile) {
      setError("Choose a file before starting an upload.");
      return;
    }
    if (!isSupportedUploadFormat(selectedFile.name, selectedFile.type)) {
      setError("Supported formats are MP4, AVI, MOV, MKV, TIFF, PNG, and JPEG.");
      return;
    }

    setBusy(true);
    try {
      await executeUploadFlow({
        apiBaseUrl: API_BASE_URL,
        file: selectedFile,
        resumeExisting,
        existingSession: uploadSession,
        dependencies: {
          getAccessToken: currentAccessToken,
        },
        handlers: {
          setUploadSession,
          setStatus,
          setProgress,
          setEtaSeconds,
          setCanResume,
          setError,
        },
      });
    } finally {
      setBusy(false);
    }
  }

  function handlePersonaChange(nextPersona: UserPersona): void {
    setSelectedPersona(nextPersona);
    if (!catalog) {
      return;
    }
    const nextTier = defaultTierForPersona(catalog, nextPersona);
    setSelectedTier(nextTier);
    setSelectedGrainPreset(defaultGrainPresetForTier(catalog, nextTier));
    setSavedConfiguration(null);
  }

  function clearPersonaSelection(): void {
    setSelectedPersona("");
    setSavedConfiguration(null);
  }

  function handleTierChange(nextTier: FidelityTier): void {
    setSelectedTier(nextTier);
    if (!catalog) {
      return;
    }
    const allowedPresets = allowedGrainPresetsForTier(catalog, nextTier);
    setSelectedGrainPreset(defaultGrainPresetForTier(catalog, nextTier) ?? allowedPresets[0] ?? null);
    setSavedConfiguration(null);
  }

  async function handleDetectEra(
    overrides: { manual_override_era?: string; override_reason?: string } = {},
  ): Promise<void> {
    if (!uploadSession) {
      setError("Complete the upload before running era detection.");
      return;
    }
    setConfigBusy(true);
    try {
      const accessToken = await currentAccessToken();
      const nextDetection = await detectUploadEra(API_BASE_URL, accessToken, uploadSession.upload_id, {
        estimated_duration_seconds: estimatedDurationSeconds,
        ...overrides,
      });
      setDetection(nextDetection);
      setSavedConfiguration(null);
      setError("");
      setManualOverrideEra(overrides.manual_override_era ?? "");
      setOverrideReason(overrides.override_reason ?? "");
      setShowOverrideModal(false);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to detect the upload era.");
    } finally {
      setConfigBusy(false);
    }
  }

  async function handleSaveConfiguration(): Promise<void> {
    if (!uploadSession || !selectedTier || !selectedGrainPreset) {
      setError("Run era detection and choose a tier before saving the Packet 4B configuration.");
      return;
    }
    if (!selectedPersona) {
      setError("Select a persona before saving the Packet 4B configuration.");
      return;
    }
    setConfigBusy(true);
    try {
      const accessToken = await currentAccessToken();
      const nextConfiguration = await saveUploadConfiguration(API_BASE_URL, accessToken, uploadSession.upload_id, {
        persona: selectedPersona,
        fidelity_tier: selectedTier,
        grain_preset: selectedGrainPreset,
        estimated_duration_seconds: estimatedDurationSeconds,
        manual_override_era: manualOverrideEra || undefined,
        override_reason: overrideReason || undefined,
      });
      setSavedConfiguration(nextConfiguration);
      setDetection(nextConfiguration.detection_snapshot);
      setSelectedPersona(nextConfiguration.persona);
      setSelectedTier(nextConfiguration.fidelity_tier);
      setSelectedGrainPreset(nextConfiguration.grain_preset);
      setError("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to save the launch-ready configuration.");
    } finally {
      setConfigBusy(false);
    }
  }

  const grainOptions = catalog ? allowedGrainPresetsForTier(catalog, selectedTier) : [];

  return (
    <main
      style={{
        minHeight: "100vh",
        background:
          "radial-gradient(circle at top left, rgba(22,119,179,0.18), transparent 32%), linear-gradient(180deg, #f5f8fb 0%, #e9f0f7 100%)",
        color: "var(--color-text-primary)",
        fontFamily: "var(--font-family-base)",
        padding: "var(--spacing-xl)",
      }}
    >
      <div style={{ maxWidth: 920, margin: "0 auto", display: "grid", gap: "var(--spacing-lg)" }}>
        <Card title="Packet 4B Configuration Flow">
          <p style={{ color: "var(--color-text-muted)", marginTop: 0 }}>
            Upload the media, detect its era, choose the right persona and fidelity settings, then save a launch-ready
            configuration for Packet 4C.
          </p>
          <div style={{ display: "grid", gap: "var(--spacing-md)" }}>
            <label>
              <div style={{ marginBottom: "var(--spacing-xs)" }}>Media file</div>
              <InputField
                type="file"
                accept=".mp4,.avi,.mov,.mkv,.tif,.tiff,.png,.jpg,.jpeg"
                onChange={(event) => {
                  const file = event.target.files?.[0] ?? null;
                  setSelectedFile(file);
                  setUploadSession(null);
                  setProgress(0);
                  setEtaSeconds(0);
                  setStatus("pending");
                  setError("");
                  setCanResume(false);
                  resetConfigurationState();
                }}
              />
            </label>
            <div style={{ display: "flex", gap: "var(--spacing-sm)", flexWrap: "wrap" }}>
              <Button onClick={() => void runUpload(false)} disabled={busy || !selectedFile}>
                {busy ? "Uploading..." : "Start Upload"}
              </Button>
              <Button variant="secondary" onClick={() => void runUpload(true)} disabled={busy || !selectedFile || !canResume}>
                Resume Upload
              </Button>
            </div>
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "var(--spacing-xs)" }}>
                <span>Status: {status}</span>
                <span>{progress}%</span>
              </div>
              <ProgressBar value={progress} />
              <div style={{ marginTop: "var(--spacing-xs)", color: "var(--color-text-muted)" }}>
                ETA: {etaSeconds}s
              </div>
            </div>
            {uploadSession ? (
              <div
                style={{
                  borderRadius: "var(--radius-md)",
                  background: "#edf5fb",
                  padding: "var(--spacing-md)",
                  color: "var(--color-text-muted)",
                }}
              >
                <div>Upload ID: {uploadSession.upload_id}</div>
                <div>Media URI: {uploadSession.media_uri}</div>
                <div>Object path: {uploadSession.object_path}</div>
              </div>
            ) : null}
          </div>
        </Card>

        {uploadSession?.status === "completed" ? (
          <Card title="Launch-Ready Configuration">
            <div style={{ display: "grid", gap: "var(--spacing-md)" }}>
              <ol style={{ margin: 0, paddingLeft: "1.2rem", color: "var(--color-text-muted)" }}>
                <li>Upload complete</li>
                <li>Detect era</li>
                <li>Select persona</li>
                <li>Select fidelity tier</li>
                <li>Adjust grain preset</li>
                <li>Optional era override</li>
                <li>Confirm and save</li>
              </ol>
              <label>
                <div style={{ marginBottom: "var(--spacing-xs)" }}>Estimated duration (seconds)</div>
                <InputField
                  min={1}
                  onChange={(event) => setEstimatedDurationSeconds(Math.max(Number(event.target.value || 0), 1))}
                  type="number"
                  value={estimatedDurationSeconds}
                />
              </label>
              {catalog ? (
                <>
                  <label>
                    <div style={{ marginBottom: "var(--spacing-xs)" }}>Persona</div>
                    <select
                      aria-label="Select user persona"
                      onChange={(event) => {
                        const nextPersona = event.target.value;
                        if (!nextPersona) {
                          clearPersonaSelection();
                          return;
                        }
                        handlePersonaChange(nextPersona as UserPersona);
                      }}
                      value={selectedPersona}
                    >
                      <option value="">Select a persona</option>
                      {catalog.personas.map((persona) => (
                        <option key={persona.persona} value={persona.persona}>
                          {persona.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <div>
                    <div style={{ marginBottom: "var(--spacing-xs)" }}>Fidelity tier</div>
                    <FidelityTierSelector
                      onSelect={handleTierChange}
                      selectedTier={selectedTier}
                      tiers={catalog.tiers}
                    />
                  </div>
                  <label>
                    <div style={{ marginBottom: "var(--spacing-xs)" }}>Grain preset</div>
                    <select
                      aria-label="Select grain preset"
                      onChange={(event) => setSelectedGrainPreset(event.target.value as GrainPreset)}
                      value={selectedGrainPreset ?? ""}
                    >
                      <option value="">Select a grain preset</option>
                      {grainOptions.map((preset) => (
                        <option key={preset} value={preset}>
                          {preset}
                        </option>
                      ))}
                    </select>
                  </label>
                </>
              ) : (
                <div>Loading configuration options...</div>
              )}
              <div style={{ display: "flex", gap: "var(--spacing-sm)", flexWrap: "wrap" }}>
                <Button disabled={configBusy} onClick={() => void handleDetectEra()}>
                  {configBusy ? "Working..." : detection ? "Refresh Detection" : "Detect Era"}
                </Button>
                <Button
                  disabled={configBusy || !canOverrideEra(detection)}
                  onClick={() => setShowOverrideModal(true)}
                  type="button"
                  variant="secondary"
                >
                  Override Era
                </Button>
                <Button
                  disabled={configBusy || !detection || !selectedTier || !selectedGrainPreset}
                  onClick={() => void handleSaveConfiguration()}
                  type="button"
                >
                  Save Configuration
                </Button>
              </div>
              {detection ? (
                <div
                  style={{
                    borderRadius: "var(--radius-md)",
                    background: "#f7fafc",
                    padding: "var(--spacing-md)",
                  }}
                >
                  <div>
                    <strong>Detected era:</strong> {detection.era}
                  </div>
                  <div>
                    <strong>Confidence:</strong> {Math.round(detection.confidence * 100)}%
                  </div>
                  <div>
                    <strong>Processing estimate:</strong> {detection.estimated_usage_minutes} billable minutes
                  </div>
                  {detection.warnings.length ? (
                    <ul style={{ marginBottom: 0 }}>
                      {detection.warnings.map((warning) => (
                        <li key={warning}>{warning}</li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              ) : null}
              {savedConfiguration ? (
                <div
                  style={{
                    borderRadius: "var(--radius-md)",
                    background: "#edf7ef",
                    padding: "var(--spacing-md)",
                  }}
                >
                  <div>
                    <strong>Persona:</strong> {savedConfiguration.persona}
                  </div>
                  <div>
                    <strong>Tier:</strong> {savedConfiguration.fidelity_tier}
                  </div>
                  <div>
                    <strong>Grain preset:</strong> {savedConfiguration.grain_preset}
                  </div>
                  <div>
                    <strong>Era:</strong> {savedConfiguration.detection_snapshot.era}
                  </div>
                  <div>
                    <strong>Relative cost:</strong> {savedConfiguration.relative_cost_multiplier}x
                  </div>
                  <div>
                    <strong>Relative time:</strong> {savedConfiguration.relative_processing_time_band}
                  </div>
                </div>
              ) : null}
            </div>
          </Card>
        ) : null}

        {error ? (
          <div
            role="alert"
            style={{
              borderRadius: "var(--radius-md)",
              background: "#fff0f0",
              color: "#8a1f1f",
              padding: "var(--spacing-sm) var(--spacing-md)",
            }}
          >
            {error}
          </div>
        ) : null}
      </div>

      <EraOverrideModal
        detection={detection}
        learnMoreUrl={learnMoreUrl()}
        onChangeReason={setOverrideReason}
        onClose={() => setShowOverrideModal(false)}
        onConfirm={() =>
          void handleDetectEra({
            manual_override_era: manualOverrideEra || undefined,
            override_reason: overrideReason || undefined,
          })
        }
        onSelectEra={setManualOverrideEra}
        open={showOverrideModal}
        overrideReason={overrideReason}
        selectedEra={manualOverrideEra}
      />
    </main>
  );
}
