import React, { useEffect, useRef, useState } from "react";

import { Button } from "./components/Button";
import { Card } from "./components/Card";
import { EraOverrideModal } from "./components/EraOverrideModal";
import { FidelityTierSelector } from "./components/FidelityTierSelector";
import { InputField } from "./components/InputField";
import { Modal } from "./components/Modal";
import { PreviewReviewModal } from "./components/PreviewReviewModal";
import { ProgressBar } from "./components/ProgressBar";
import { UncertaintyCalloutsList } from "./components/UncertaintyCalloutsList";
import {
  approveSingleJobOverage,
  fetchJobEstimate,
  type JobCostEstimateResponse,
} from "./lib/costEstimateHelpers";
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
  cancelProcessing,
  fetchJobDetail,
  fetchUncertaintyCallouts,
  isActiveJobStatus,
  type JobDetailResponse,
  type JobUncertaintyCalloutsResponse,
} from "./lib/processingHelpers";
import {
  createPreview,
  launchApprovedPreview,
  reviewPreview,
  type PreviewSessionResponse,
} from "./lib/previewHelpers";
import {
  fetchCurrentUserProfile,
  fetchDeletionProof,
  fetchJobExport,
  fetchTransformationManifest,
  type DeliveryRequestError,
  type ExportVariant,
} from "./lib/outputDeliveryHelpers";
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

function processingLaunchKey(configuration: UploadConfigurationResponse | null): string | null {
  if (!configuration) {
    return null;
  }
  return `${configuration.upload_id}:${configuration.configuration_fingerprint}`;
}

type DeliveryActionKey = "av1" | "h264" | "manifest" | "proof";
type DeliveryRetryAction =
  | { type: "export"; variant: ExportVariant }
  | { type: "manifest" }
  | { type: "proof" };

type FormErrorTarget = "file" | "duration" | "persona" | "tier" | "grain" | "configuration";

function isExportReadyStatus(status: JobDetailResponse["status"] | null | undefined): boolean {
  return status === "completed" || status === "partial";
}

function deliveryActionLabel(action: DeliveryRetryAction | null): string {
  if (!action) {
    return "Retry";
  }
  if (action.type === "export") {
    return action.variant === "av1" ? "Retry AV1 Download" : "Retry Compatibility Download";
  }
  if (action.type === "manifest") {
    return "Retry Manifest";
  }
  return "Retry Deletion Proof";
}

function isEditableShortcutTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false;
  }
  if (target.isContentEditable) {
    return true;
  }
  return Boolean(target.closest("input, textarea, select, [contenteditable='true']"));
}

function isShortcutFocusableTarget(
  target: HTMLButtonElement | HTMLInputElement | HTMLSelectElement | null,
): target is HTMLButtonElement | HTMLInputElement | HTMLSelectElement {
  return Boolean(target) && !target.disabled;
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
  const [processingJob, setProcessingJob] = useState<JobDetailResponse | null>(null);
  const [jobCallouts, setJobCallouts] = useState<JobUncertaintyCalloutsResponse | null>(null);
  const [jobBusy, setJobBusy] = useState(false);
  const [statusNotice, setStatusNotice] = useState("");
  const [showPreviewReviewModal, setShowPreviewReviewModal] = useState(false);
  const [showKeyboardShortcutsModal, setShowKeyboardShortcutsModal] = useState(false);
  const [previewSession, setPreviewSession] = useState<PreviewSessionResponse | null>(null);
  const [previewBusy, setPreviewBusy] = useState(false);
  const [previewReviewBusy, setPreviewReviewBusy] = useState(false);
  const [previewModalExpectedFingerprint, setPreviewModalExpectedFingerprint] = useState<string | null>(null);
  const [costEstimate, setCostEstimate] = useState<JobCostEstimateResponse | null>(null);
  const [costEstimateBusy, setCostEstimateBusy] = useState(false);
  const [overageApprovalBusy, setOverageApprovalBusy] = useState(false);
  const [launchModalError, setLaunchModalError] = useState("");
  const [launchModalNotice, setLaunchModalNotice] = useState("");
  const [deliveryPlanTier, setDeliveryPlanTier] = useState<string | null>(null);
  const [deliveryRetentionDays, setDeliveryRetentionDays] = useState(7);
  const [deliveryBusy, setDeliveryBusy] = useState<Record<DeliveryActionKey, boolean>>({
    av1: false,
    h264: false,
    manifest: false,
    proof: false,
  });
  const [deliveryNotice, setDeliveryNotice] = useState("");
  const [deliveryError, setDeliveryError] = useState("");
  const [deliveryRetryAction, setDeliveryRetryAction] = useState<DeliveryRetryAction | null>(null);
  const [formErrorTarget, setFormErrorTarget] = useState<FormErrorTarget | null>(null);
  const [lastStartedConfigurationKey, setLastStartedConfigurationKey] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const durationInputRef = useRef<HTMLInputElement | null>(null);
  const personaSelectRef = useRef<HTMLSelectElement | null>(null);
  const grainSelectRef = useRef<HTMLSelectElement | null>(null);
  const saveConfigurationButtonRef = useRef<HTMLButtonElement | null>(null);
  const launchReviewButtonRef = useRef<HTMLButtonElement | null>(null);
  const primaryDeliveryButtonRef = useRef<HTMLButtonElement | null>(null);
  const appErrorRef = useRef<HTMLDivElement | null>(null);
  const activeUploadIdRef = useRef<string | null>(null);
  const activeJobIdRef = useRef<string | null>(null);
  const processingStatusRef = useRef<JobDetailResponse["status"] | null>(null);
  const latestRefreshTokenRef = useRef(0);
  const latestEstimateTokenRef = useRef(0);
  const latestPreviewTokenRef = useRef(0);
  const lastTerminalStatusRef = useRef<JobDetailResponse["status"] | null>(null);
  const terminalHeadingRef = useRef<HTMLHeadingElement | null>(null);
  const deliveryAlertRef = useRef<HTMLDivElement | null>(null);
  const deliveryPlanLoadedJobIdRef = useRef<string | null>(null);

  useEffect(() => {
    activeUploadIdRef.current = uploadSession?.upload_id ?? null;
  }, [uploadSession]);

  useEffect(() => {
    activeJobIdRef.current = processingJob?.job_id ?? null;
  }, [processingJob]);

  useEffect(() => {
    processingStatusRef.current = processingJob?.status ?? null;
  }, [processingJob?.status]);

  useEffect(() => {
    const nextStatus = processingJob?.status ?? null;
    const previousStatus = lastTerminalStatusRef.current;
    if (nextStatus && isExportReadyStatus(nextStatus) && previousStatus !== nextStatus) {
      terminalHeadingRef.current?.focus();
    }
    lastTerminalStatusRef.current = nextStatus;
  }, [processingJob?.status]);

  useEffect(() => {
    if (deliveryError) {
      deliveryAlertRef.current?.focus();
    }
  }, [deliveryError]);

  useEffect(() => {
    if (error && !formErrorTarget) {
      appErrorRef.current?.focus();
    }
  }, [error, formErrorTarget]);

  function resetConfigurationState(): void {
    setEstimatedDurationSeconds(180);
    setCatalog(null);
    setDetection(null);
    setSavedConfiguration(null);
    setLastStartedConfigurationKey(null);
    setSelectedPersona("");
    setSelectedTier(null);
    setSelectedGrainPreset(null);
    setShowOverrideModal(false);
    setManualOverrideEra("");
    setOverrideReason("");
    latestEstimateTokenRef.current += 1;
    latestPreviewTokenRef.current += 1;
    setShowPreviewReviewModal(false);
    setPreviewSession(null);
    setPreviewBusy(false);
    setPreviewReviewBusy(false);
    setPreviewModalExpectedFingerprint(null);
    setCostEstimate(null);
    setCostEstimateBusy(false);
    setOverageApprovalBusy(false);
    setLaunchModalError("");
    setLaunchModalNotice("");
  }

  function resetProcessingState(): void {
    latestRefreshTokenRef.current += 1;
    activeJobIdRef.current = null;
    processingStatusRef.current = null;
    deliveryPlanLoadedJobIdRef.current = null;
    setProcessingJob(null);
    setJobCallouts(null);
    setJobBusy(false);
    setStatusNotice("");
    setDeliveryPlanTier(null);
    setDeliveryRetentionDays(7);
    setDeliveryBusy({ av1: false, h264: false, manifest: false, proof: false });
    setDeliveryNotice("");
    setDeliveryError("");
    setDeliveryRetryAction(null);
  }

  function resetPreviewReviewState(options: { closeModal?: boolean } = {}): void {
    latestEstimateTokenRef.current += 1;
    latestPreviewTokenRef.current += 1;
    if (options.closeModal ?? true) {
      setShowPreviewReviewModal(false);
    }
    setPreviewSession(null);
    setPreviewBusy(false);
    setPreviewReviewBusy(false);
    setPreviewModalExpectedFingerprint(null);
    setCostEstimate(null);
    setCostEstimateBusy(false);
    setOverageApprovalBusy(false);
    setLaunchModalError("");
    setLaunchModalNotice("");
  }

  function focusFormTarget(target: FormErrorTarget): void {
    let targetElement: HTMLElement | null = null;
    switch (target) {
      case "file":
        targetElement = fileInputRef.current;
        break;
      case "duration":
        targetElement = durationInputRef.current;
        break;
      case "persona":
        targetElement = personaSelectRef.current;
        break;
      case "grain":
        targetElement = grainSelectRef.current;
        break;
      case "tier":
        targetElement = document.querySelector<HTMLElement>('input[name="fidelity-tier"]');
        break;
      case "configuration":
        targetElement = saveConfigurationButtonRef.current;
        break;
      default:
        targetElement = saveConfigurationButtonRef.current;
        break;
    }
    targetElement?.focus();
  }

  function setFormError(message: string, target: FormErrorTarget): void {
    setFormErrorTarget(target);
    setError(message);
    window.setTimeout(() => focusFormTarget(target), 0);
  }

  function setAppError(message: string): void {
    setFormErrorTarget(null);
    setError(message);
  }

  function clearFormError(): void {
    setFormErrorTarget(null);
    setError("");
  }

  const jobActive = isActiveJobStatus(processingJob?.status);
  const jobLocked = jobBusy || jobActive;
  const exportReady = isExportReadyStatus(processingJob?.status);
  const currentLaunchKey = processingLaunchKey(savedConfiguration);
  const canStartSavedConfiguration = Boolean(savedConfiguration) && (!processingJob || currentLaunchKey !== lastStartedConfigurationKey);
  const previewReviewInvalidated =
    Boolean(
      showPreviewReviewModal &&
        savedConfiguration &&
        previewModalExpectedFingerprint &&
        savedConfiguration.configuration_fingerprint !== previewModalExpectedFingerprint,
    ) ||
    Boolean(
      showPreviewReviewModal &&
        savedConfiguration &&
        previewSession &&
        previewSession.configuration_fingerprint !== savedConfiguration.configuration_fingerprint,
    ) ||
    Boolean(
      showPreviewReviewModal &&
        savedConfiguration &&
        costEstimate &&
        costEstimate.configuration_fingerprint !== savedConfiguration.configuration_fingerprint,
    );
  const isMuseumPlan = deliveryPlanTier === "museum";

  function setDeliveryBusyFor(action: DeliveryActionKey, value: boolean): void {
    setDeliveryBusy((current) => ({ ...current, [action]: value }));
  }

  function clearDeliveryFeedback(): void {
    setDeliveryNotice("");
    setDeliveryError("");
    setDeliveryRetryAction(null);
  }

  function openBrowserTarget(url: string, target: "_self" | "_blank"): void {
    window.setTimeout(() => {
      window.open(url, target, target === "_blank" ? "noopener,noreferrer" : undefined);
    }, 0);
  }

  function isCurrentDeliveryJob(jobId: string): boolean {
    return activeJobIdRef.current === jobId;
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
          setAppError(caught instanceof Error ? caught.message : "Unable to load Packet 4B configuration options.");
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

  useEffect(() => {
    if (!exportReady || !processingJob?.job_id || deliveryPlanLoadedJobIdRef.current === processingJob.job_id) {
      return;
    }
    let ignore = false;
    const requestJobId = processingJob.job_id;
    void (async () => {
      try {
        const accessToken = await currentAccessToken();
        const profile = await fetchCurrentUserProfile(API_BASE_URL, accessToken);
        if (ignore || !isCurrentDeliveryJob(requestJobId)) {
          return;
        }
        deliveryPlanLoadedJobIdRef.current = requestJobId;
        setDeliveryPlanTier(profile.plan_tier.toLowerCase());
      } catch (caught) {
        if (!ignore && isCurrentDeliveryJob(requestJobId)) {
          deliveryPlanLoadedJobIdRef.current = null;
          setDeliveryPlanTier(null);
          setDeliveryNotice(caught instanceof Error ? `${caught.message} Using the default 7-day retention window.` : "Using the default 7-day retention window.");
        }
      }
    })();
    return () => {
      ignore = true;
    };
  }, [exportReady, processingJob?.job_id]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (showOverrideModal || showPreviewReviewModal || showKeyboardShortcutsModal) {
        return;
      }
      if (isEditableShortcutTarget(event.target)) {
        return;
      }
      if (!(event.metaKey || event.ctrlKey) || !event.shiftKey) {
        return;
      }
      const key = event.key.toLowerCase();
      if (key === "u") {
        if (!isShortcutFocusableTarget(fileInputRef.current)) {
          return;
        }
        event.preventDefault();
        fileInputRef.current?.focus();
        return;
      }
      if (key === "s") {
        if (!isShortcutFocusableTarget(saveConfigurationButtonRef.current)) {
          return;
        }
        event.preventDefault();
        saveConfigurationButtonRef.current?.focus();
        return;
      }
      if (key === "l") {
        if (!isShortcutFocusableTarget(launchReviewButtonRef.current)) {
          return;
        }
        event.preventDefault();
        launchReviewButtonRef.current?.focus();
        return;
      }
      if (key === "e") {
        if (!isShortcutFocusableTarget(primaryDeliveryButtonRef.current)) {
          return;
        }
        event.preventDefault();
        primaryDeliveryButtonRef.current?.focus();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [showKeyboardShortcutsModal, showPreviewReviewModal, showOverrideModal]);

  async function runUpload(resumeExisting: boolean): Promise<void> {
    if (!selectedFile) {
      setFormError("Choose a file before starting an upload.", "file");
      return;
    }
    if (!isSupportedUploadFormat(selectedFile.name, selectedFile.type)) {
      setFormError("Supported formats are MP4, AVI, MOV, MKV, TIFF, PNG, and JPEG.", "file");
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
          setError: setAppError,
        },
      });
    } finally {
      setBusy(false);
    }
  }

  function handlePersonaChange(nextPersona: UserPersona): void {
    setSelectedPersona(nextPersona);
    if (formErrorTarget === "persona") {
      clearFormError();
    }
    if (!catalog) {
      return;
    }
    const nextTier = defaultTierForPersona(catalog, nextPersona);
    setSelectedTier(nextTier);
    setSelectedGrainPreset(defaultGrainPresetForTier(catalog, nextTier));
    setSavedConfiguration(null);
    resetPreviewReviewState();
  }

  function clearPersonaSelection(): void {
    setSelectedPersona("");
    setSavedConfiguration(null);
    resetPreviewReviewState();
  }

  function handleTierChange(nextTier: FidelityTier): void {
    setSelectedTier(nextTier);
    if (formErrorTarget === "tier") {
      clearFormError();
    }
    if (!catalog) {
      return;
    }
    const allowedPresets = allowedGrainPresetsForTier(catalog, nextTier);
    setSelectedGrainPreset(defaultGrainPresetForTier(catalog, nextTier) ?? allowedPresets[0] ?? null);
    setSavedConfiguration(null);
    resetPreviewReviewState();
  }

  async function handleDetectEra(
    overrides: { manual_override_era?: string; override_reason?: string } = {},
  ): Promise<void> {
    if (!uploadSession) {
      setFormError("Complete the upload before running era detection.", "file");
      return;
    }
    const requestUploadId = uploadSession.upload_id;
    setConfigBusy(true);
    try {
      const accessToken = await currentAccessToken();
      const nextDetection = await detectUploadEra(API_BASE_URL, accessToken, requestUploadId, {
        estimated_duration_seconds: estimatedDurationSeconds,
        ...overrides,
      });
      if (activeUploadIdRef.current !== requestUploadId) {
        return;
      }
      setDetection(nextDetection);
      setSavedConfiguration(null);
      resetPreviewReviewState();
      clearFormError();
      setManualOverrideEra(overrides.manual_override_era ?? "");
      setOverrideReason(overrides.override_reason ?? "");
      setShowOverrideModal(false);
    } catch (caught) {
      setAppError(caught instanceof Error ? caught.message : "Unable to detect the upload era.");
    } finally {
      setConfigBusy(false);
    }
  }

  async function handleSaveConfiguration(): Promise<void> {
    if (!uploadSession || !selectedTier || !selectedGrainPreset) {
      setFormError("Run era detection and choose a tier before saving the Packet 4B configuration.", "tier");
      return;
    }
    if (!selectedPersona) {
      setFormError("Select a persona before saving the Packet 4G configuration.", "persona");
      return;
    }
    const requestUploadId = uploadSession.upload_id;
    setConfigBusy(true);
    try {
      const accessToken = await currentAccessToken();
      const nextConfiguration = await saveUploadConfiguration(API_BASE_URL, accessToken, requestUploadId, {
        persona: selectedPersona,
        fidelity_tier: selectedTier,
        grain_preset: selectedGrainPreset,
        estimated_duration_seconds: estimatedDurationSeconds,
        manual_override_era: manualOverrideEra || undefined,
        override_reason: overrideReason || undefined,
      });
      if (activeUploadIdRef.current !== requestUploadId) {
        return;
      }
      setSavedConfiguration(nextConfiguration);
      setDetection(nextConfiguration.detection_snapshot);
      setSelectedPersona(nextConfiguration.persona);
      setSelectedTier(nextConfiguration.fidelity_tier);
      setSelectedGrainPreset(nextConfiguration.grain_preset);
      if (showPreviewReviewModal) {
        setLaunchModalError("");
        setLaunchModalNotice("");
      } else {
        resetPreviewReviewState();
      }
      clearFormError();
      setStatusNotice("");
    } catch (caught) {
      setAppError(caught instanceof Error ? caught.message : "Unable to save the launch-ready configuration.");
    } finally {
      setConfigBusy(false);
    }
  }

  async function refreshProcessingState(jobId: string, uploadId: string): Promise<void> {
    const refreshToken = latestRefreshTokenRef.current + 1;
    latestRefreshTokenRef.current = refreshToken;
    const isCurrentRefresh = (): boolean =>
      latestRefreshTokenRef.current === refreshToken && activeUploadIdRef.current === uploadId && activeJobIdRef.current === jobId;
    let accessToken: string;
    try {
      accessToken = await currentAccessToken();
    } catch (caught) {
      if (!isCurrentRefresh()) {
        return;
      }
      throw caught;
    }
    if (!isCurrentRefresh()) {
      return;
    }
    let nextJob: JobDetailResponse;
    try {
      nextJob = await fetchJobDetail(API_BASE_URL, accessToken, jobId);
    } catch (caught) {
      if (!isCurrentRefresh()) {
        return;
      }
      throw caught;
    }
    if (!isCurrentRefresh()) {
      return;
    }
    setProcessingJob(nextJob);
    setStatusNotice("");
    try {
      const nextCallouts = await fetchUncertaintyCallouts(API_BASE_URL, accessToken, jobId);
      if (!isCurrentRefresh()) {
        return;
      }
      setJobCallouts(nextCallouts);
    } catch (caught) {
      if (!isCurrentRefresh()) {
        return;
      }
      setStatusNotice(caught instanceof Error ? caught.message : "Unable to refresh uncertainty callouts.");
    }
  }

  async function loadPreviewReviewGate(configuration: UploadConfigurationResponse): Promise<void> {
    const estimateToken = latestEstimateTokenRef.current + 1;
    latestEstimateTokenRef.current = estimateToken;
    const previewToken = latestPreviewTokenRef.current + 1;
    latestPreviewTokenRef.current = previewToken;
    const launchKey = processingLaunchKey(configuration);
    const isCurrentRequest = (): boolean =>
      latestEstimateTokenRef.current === estimateToken &&
      latestPreviewTokenRef.current === previewToken &&
      processingLaunchKey(savedConfiguration) === launchKey;

    setPreviewBusy(true);
    setCostEstimateBusy(true);
    setLaunchModalError("");
    setLaunchModalNotice("");
    setPreviewModalExpectedFingerprint(configuration.configuration_fingerprint);
    try {
      const accessToken = await currentAccessToken();
      if (!isCurrentRequest()) {
        return;
      }
      const [nextPreview, nextEstimate] = await Promise.all([
        createPreview(API_BASE_URL, accessToken, configuration.upload_id),
        fetchJobEstimate(API_BASE_URL, accessToken, configuration.job_payload_preview),
      ]);
      if (!isCurrentRequest()) {
        return;
      }
      setPreviewSession(nextPreview);
      setCostEstimate(nextEstimate);
    } catch (caught) {
      if (!isCurrentRequest()) {
        return;
      }
      setPreviewSession(null);
      setCostEstimate(null);
      setLaunchModalError(
        caught instanceof Error ? caught.message : "Unable to load the preview review gate.",
      );
    } finally {
      if (isCurrentRequest()) {
        setPreviewBusy(false);
        setCostEstimateBusy(false);
      }
    }
  }

  async function handleOpenPreviewReviewModal(): Promise<void> {
    if (!savedConfiguration) {
      setFormError("Save a launch-ready configuration before reviewing the preview gate.", "configuration");
      return;
    }
    resetPreviewReviewState({ closeModal: false });
    setShowPreviewReviewModal(true);
    await loadPreviewReviewGate(savedConfiguration);
  }

  async function handleApprovePreview(): Promise<void> {
    if (!previewSession) {
      return;
    }
    setPreviewReviewBusy(true);
    setLaunchModalError("");
    try {
      const accessToken = await currentAccessToken();
      const nextPreview = await reviewPreview(
        API_BASE_URL,
        accessToken,
        previewSession.preview_id,
        "approved",
      );
      setPreviewSession(nextPreview);
      setLaunchModalNotice("Preview approved. Launch is ready when you are.");
    } catch (caught) {
      setLaunchModalError(caught instanceof Error ? caught.message : "Unable to approve the preview.");
    } finally {
      setPreviewReviewBusy(false);
    }
  }

  async function handleRejectPreview(): Promise<void> {
    if (!previewSession) {
      return;
    }
    setPreviewReviewBusy(true);
    setLaunchModalError("");
    try {
      const accessToken = await currentAccessToken();
      const nextPreview = await reviewPreview(
        API_BASE_URL,
        accessToken,
        previewSession.preview_id,
        "rejected",
      );
      setPreviewSession(nextPreview);
      setLaunchModalNotice("Preview rejected. Regenerate after saving an updated configuration.");
    } catch (caught) {
      setLaunchModalError(caught instanceof Error ? caught.message : "Unable to reject the preview.");
    } finally {
      setPreviewReviewBusy(false);
    }
  }

  async function handleApproveLaunchOverage(): Promise<void> {
    if (!costEstimate) {
      return;
    }
    setOverageApprovalBusy(true);
    setLaunchModalError("");
    try {
      const accessToken = await currentAccessToken();
      await approveSingleJobOverage(
        API_BASE_URL,
        accessToken,
        Math.max(costEstimate.billing_breakdown_usd.overage_minutes, 0),
      );
      setLaunchModalNotice("Single-job overage approval recorded. Refreshing the estimate now.");
      if (savedConfiguration) {
        await loadPreviewReviewGate(savedConfiguration);
      }
      setLaunchModalNotice("Launch approval recorded. Start processing when you’re ready.");
    } catch (caught) {
      setLaunchModalError(caught instanceof Error ? caught.message : "Unable to approve the projected overage.");
    } finally {
      setOverageApprovalBusy(false);
    }
  }

  async function handleLaunchFromPreview(): Promise<void> {
    if (!savedConfiguration || !uploadSession || !previewSession) {
      setLaunchModalError("Save a launch-ready configuration and load the preview before starting processing.");
      return;
    }
    const launchKey = processingLaunchKey(savedConfiguration);
    if (processingJob && !jobActive && launchKey && launchKey === lastStartedConfigurationKey) {
      setStatusNotice("Save the configuration again before starting another processing run.");
      return;
    }
    const requestUploadId = uploadSession.upload_id;
    setJobBusy(true);
    setLaunchModalError("");
    try {
      const accessToken = await currentAccessToken();
      const createdJob = await launchApprovedPreview(
        API_BASE_URL,
        accessToken,
        previewSession.preview_id,
        savedConfiguration.configuration_fingerprint,
      );
      if (activeUploadIdRef.current !== requestUploadId) {
        return;
      }
      activeJobIdRef.current = createdJob.job_id;
      deliveryPlanLoadedJobIdRef.current = null;
      setProcessingJob(createdJob);
      setJobCallouts(null);
      clearFormError();
      setStatusNotice("");
      setDeliveryPlanTier(null);
      setDeliveryRetentionDays(7);
      setDeliveryBusy({ av1: false, h264: false, manifest: false, proof: false });
      setDeliveryNotice("");
      setDeliveryError("");
      setDeliveryRetryAction(null);
      setLastStartedConfigurationKey(launchKey);
      resetPreviewReviewState();
    } catch (caught) {
      setLaunchModalError(caught instanceof Error ? caught.message : "Unable to start processing.");
    } finally {
      if (activeUploadIdRef.current === requestUploadId) {
        setJobBusy(false);
      }
    }
  }

  async function handleCancelProcessing(): Promise<void> {
    if (!processingJob || !uploadSession) {
      return;
    }
    const requestUploadId = uploadSession.upload_id;
    const requestJobId = processingJob.job_id;
    setJobBusy(true);
    try {
      const accessToken = await currentAccessToken();
      await cancelProcessing(API_BASE_URL, accessToken, requestJobId);
      if (activeUploadIdRef.current !== requestUploadId || activeJobIdRef.current !== requestJobId) {
        return;
      }
      clearFormError();
      try {
        await refreshProcessingState(requestJobId, requestUploadId);
      } catch (caught) {
        if (activeUploadIdRef.current !== requestUploadId || activeJobIdRef.current !== requestJobId) {
          return;
        }
        setStatusNotice(
          caught instanceof Error ? caught.message : "Cancellation was requested, but the latest processing status could not be refreshed.",
        );
      }
    } catch (caught) {
      setAppError(caught instanceof Error ? caught.message : "Unable to cancel processing.");
    } finally {
      if (activeUploadIdRef.current === requestUploadId && activeJobIdRef.current === requestJobId) {
        setJobBusy(false);
      }
    }
  }

  async function handleRetryProcessingRefresh(): Promise<void> {
    if (!processingJob || !uploadSession) {
      return;
    }
    try {
      await refreshProcessingState(processingJob.job_id, uploadSession.upload_id);
    } catch (caught) {
      setStatusNotice(caught instanceof Error ? caught.message : "Unable to refresh processing status.");
    }
  }

  async function handleDownloadPackage(variant: ExportVariant): Promise<void> {
    if (!processingJob) {
      return;
    }
    const requestJobId = processingJob.job_id;
    clearDeliveryFeedback();
    setDeliveryBusyFor(variant, true);
    try {
      const accessToken = await currentAccessToken();
      if (!isCurrentDeliveryJob(requestJobId)) {
        return;
      }
      const payload = await fetchJobExport(API_BASE_URL, accessToken, requestJobId, {
        variant,
        retentionDays: isMuseumPlan ? deliveryRetentionDays : 7,
      });
      if (!isCurrentDeliveryJob(requestJobId)) {
        return;
      }
      setDeliveryRetryAction(null);
      setDeliveryNotice(
        variant === "av1" ? "AV1 package download ready." : "Compatibility package download ready.",
      );
      openBrowserTarget(payload.download_url, "_self");
    } catch (caught) {
      if (!isCurrentDeliveryJob(requestJobId)) {
        return;
      }
      const deliveryErrorPayload = caught as DeliveryRequestError;
      if (deliveryErrorPayload.status === 409) {
        setDeliveryNotice(deliveryErrorPayload.message || "The delivery package is not ready yet.");
        setDeliveryRetryAction({ type: "export", variant });
        return;
      }
      if (deliveryErrorPayload.status === 410) {
        setDeliveryError(
          deliveryErrorPayload.message || "The delivery package has expired. Save a new configuration and run processing again.",
        );
        setDeliveryRetryAction(null);
        return;
      }
      if (deliveryErrorPayload.status === 403) {
        setDeliveryError(deliveryErrorPayload.message || "Extended retention is not available for the current plan.");
        setDeliveryRetryAction(null);
        return;
      }
      setDeliveryError(deliveryErrorPayload.message || "Unable to fetch the delivery package.");
      setDeliveryRetryAction({ type: "export", variant });
    } finally {
      if (isCurrentDeliveryJob(requestJobId)) {
        setDeliveryBusyFor(variant, false);
      }
    }
  }

  async function handleViewManifest(): Promise<void> {
    if (!processingJob) {
      return;
    }
    const requestJobId = processingJob.job_id;
    clearDeliveryFeedback();
    setDeliveryBusyFor("manifest", true);
    const manifestWindow = window.open("about:blank", "_blank", "noopener,noreferrer");
    try {
      const accessToken = await currentAccessToken();
      if (!isCurrentDeliveryJob(requestJobId)) {
        manifestWindow?.close();
        return;
      }
      const payload = await fetchTransformationManifest(API_BASE_URL, accessToken, requestJobId);
      if (!isCurrentDeliveryJob(requestJobId)) {
        manifestWindow?.close();
        return;
      }
      const manifestUrl = URL.createObjectURL(
        new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }),
      );
      setDeliveryNotice("Transformation manifest ready.");
      if (manifestWindow) {
        manifestWindow.location.href = manifestUrl;
      } else {
        openBrowserTarget(manifestUrl, "_blank");
      }
      window.setTimeout(() => URL.revokeObjectURL(manifestUrl), 60_000);
    } catch (caught) {
      manifestWindow?.close();
      if (!isCurrentDeliveryJob(requestJobId)) {
        return;
      }
      const deliveryErrorPayload = caught as DeliveryRequestError;
      if (deliveryErrorPayload.status === 409) {
        setDeliveryNotice(deliveryErrorPayload.message || "The transformation manifest is not ready yet.");
        setDeliveryRetryAction({ type: "manifest" });
        return;
      }
      if (deliveryErrorPayload.status === 410 || deliveryErrorPayload.status === 403) {
        setDeliveryError(deliveryErrorPayload.message || "Unable to fetch the transformation manifest.");
        setDeliveryRetryAction(null);
        return;
      }
      setDeliveryError(deliveryErrorPayload.message || "Unable to fetch the transformation manifest.");
      setDeliveryRetryAction({ type: "manifest" });
    } finally {
        if (isCurrentDeliveryJob(requestJobId)) {
          setDeliveryBusyFor("manifest", false);
      }
    }
  }

  async function handleDownloadDeletionProof(): Promise<void> {
    if (!processingJob) {
      return;
    }
    const requestJobId = processingJob.job_id;
    const deletionProofId = processingJob.deletion_proof_id;
    clearDeliveryFeedback();
    setDeliveryBusyFor("proof", true);
    try {
      if (!deletionProofId) {
        setDeliveryError("Deletion proof metadata is not available yet.");
        setDeliveryRetryAction({ type: "proof" });
        return;
      }
      const accessToken = await currentAccessToken();
      if (!isCurrentDeliveryJob(requestJobId)) {
        return;
      }
      const proofPayload = await fetchDeletionProof(API_BASE_URL, accessToken, deletionProofId);
      if (!isCurrentDeliveryJob(requestJobId)) {
        return;
      }
      setDeliveryNotice("Deletion proof download ready.");
      setDeliveryRetryAction(null);
      openBrowserTarget(proofPayload.pdf_download_url, "_self");
    } catch (caught) {
      if (!isCurrentDeliveryJob(requestJobId)) {
        return;
      }
      const deliveryErrorPayload = caught as DeliveryRequestError;
      if (deliveryErrorPayload.status === 409) {
        setDeliveryNotice(deliveryErrorPayload.message || "The deletion proof is not ready yet.");
        setDeliveryRetryAction({ type: "proof" });
        return;
      }
      if (deliveryErrorPayload.status === 410 || deliveryErrorPayload.status === 403) {
        setDeliveryError(deliveryErrorPayload.message || "Unable to fetch the deletion proof.");
        setDeliveryRetryAction(null);
        return;
      }
      setDeliveryError(deliveryErrorPayload.message || "Unable to fetch the deletion proof.");
      setDeliveryRetryAction({ type: "proof" });
    } finally {
      if (isCurrentDeliveryJob(requestJobId)) {
        setDeliveryBusyFor("proof", false);
      }
    }
  }

  async function handleRetryDeliveryAction(): Promise<void> {
    if (!deliveryRetryAction) {
      return;
    }
    if (deliveryRetryAction.type === "export") {
      await handleDownloadPackage(deliveryRetryAction.variant);
      return;
    }
    if (deliveryRetryAction.type === "manifest") {
      await handleViewManifest();
      return;
    }
    await handleDownloadDeletionProof();
  }

  useEffect(() => {
    if (!processingJob?.job_id || !uploadSession?.upload_id) {
      return;
    }
    let cancelled = false;
    let intervalId: number | null = null;
    const currentJobId = processingJob.job_id;
    const currentUploadId = uploadSession.upload_id;

    const poll = async () => {
      try {
        await refreshProcessingState(currentJobId, currentUploadId);
      } catch (caught) {
        if (!cancelled) {
          setStatusNotice(caught instanceof Error ? caught.message : "Unable to refresh processing status.");
        }
      }
    };

    void poll();

    intervalId = window.setInterval(() => {
      if (!isActiveJobStatus(processingStatusRef.current)) {
        if (intervalId !== null) {
          window.clearInterval(intervalId);
          intervalId = null;
        }
        return;
      }
      void poll();
    }, 1000);

    return () => {
      cancelled = true;
      if (intervalId !== null) {
        window.clearInterval(intervalId);
      }
    };
  }, [processingJob?.job_id, uploadSession?.upload_id]);

  const grainOptions = catalog ? allowedGrainPresetsForTier(catalog, selectedTier) : [];
  const activeFormErrorId = formErrorTarget ? "packet4g-form-error" : undefined;

  return (
    <>
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <main
        id="main-content"
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
        <header style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "var(--spacing-md)", flexWrap: "wrap" }}>
          <div>
            <h1 style={{ marginBottom: "var(--spacing-xs)" }}>ChronosRefine Phase 4 Workspace</h1>
            <p style={{ color: "var(--color-text-muted)", marginTop: 0, marginBottom: 0 }}>
              Keyboard-friendly upload, configuration, launch, processing, and export flow.
            </p>
          </div>
          <Button onClick={() => setShowKeyboardShortcutsModal(true)} type="button" variant="secondary">
            Help & Keyboard Shortcuts
          </Button>
        </header>
        <Card title="Packet 4B Configuration Flow">
          <p style={{ color: "var(--color-text-muted)", marginTop: 0 }}>
            Upload the media, detect its era, choose the right persona and fidelity settings, then save a launch-ready
            configuration for Packet 4C.
          </p>
          <div style={{ display: "grid", gap: "var(--spacing-md)" }}>
            <label>
              <div style={{ marginBottom: "var(--spacing-xs)" }}>Media file</div>
              <InputField
                aria-describedby={formErrorTarget === "file" ? activeFormErrorId : undefined}
                aria-invalid={formErrorTarget === "file"}
                type="file"
                accept=".mp4,.avi,.mov,.mkv,.tif,.tiff,.png,.jpg,.jpeg"
                ref={fileInputRef}
                onChange={(event) => {
                  const file = event.target.files?.[0] ?? null;
                  setSelectedFile(file);
                  setUploadSession(null);
                  setProgress(0);
                  setEtaSeconds(0);
                  setStatus("pending");
                  clearFormError();
                  setCanResume(false);
                  resetConfigurationState();
                  resetProcessingState();
                }}
                disabled={busy || jobLocked}
              />
            </label>
            <div style={{ display: "flex", gap: "var(--spacing-sm)", flexWrap: "wrap" }}>
              <Button onClick={() => void runUpload(false)} disabled={busy || jobLocked || !selectedFile}>
                {busy ? "Uploading..." : "Start Upload"}
              </Button>
              <Button variant="secondary" onClick={() => void runUpload(true)} disabled={busy || jobLocked || !selectedFile || !canResume}>
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
                  aria-describedby={formErrorTarget === "duration" ? activeFormErrorId : undefined}
                  aria-invalid={formErrorTarget === "duration"}
                  min={1}
                  onChange={(event) => {
                    setEstimatedDurationSeconds(Math.max(Number(event.target.value || 0), 1));
                    if (formErrorTarget === "duration") {
                      clearFormError();
                    }
                  }}
                  ref={durationInputRef}
                  type="number"
                  value={estimatedDurationSeconds}
                  disabled={configBusy || jobLocked}
                />
              </label>
              {catalog ? (
                <>
                  <label>
                    <div style={{ marginBottom: "var(--spacing-xs)" }}>Persona</div>
                    <select
                      aria-label="Select user persona"
                      aria-describedby={formErrorTarget === "persona" ? activeFormErrorId : undefined}
                      aria-invalid={formErrorTarget === "persona"}
                      className="chronos-select"
                      id="packet4g-persona-select"
                      ref={personaSelectRef}
                      onChange={(event) => {
                        const nextPersona = event.target.value;
                        if (!nextPersona) {
                          clearPersonaSelection();
                          return;
                        }
                        handlePersonaChange(nextPersona as UserPersona);
                      }}
                      value={selectedPersona}
                      disabled={configBusy || jobLocked}
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
                      describedBy={formErrorTarget === "tier" ? activeFormErrorId : undefined}
                      onSelect={handleTierChange}
                      selectedTier={selectedTier}
                      tiers={catalog.tiers}
                      disabled={configBusy || jobLocked}
                    />
                  </div>
                  <label>
                    <div style={{ marginBottom: "var(--spacing-xs)" }}>Grain preset</div>
                    <select
                      aria-label="Select grain preset"
                      aria-describedby={formErrorTarget === "grain" ? activeFormErrorId : undefined}
                      aria-invalid={formErrorTarget === "grain"}
                      className="chronos-select"
                      id="packet4g-grain-select"
                      ref={grainSelectRef}
                      onChange={(event) => {
                        setSelectedGrainPreset(event.target.value as GrainPreset);
                        if (formErrorTarget === "grain") {
                          clearFormError();
                        }
                      }}
                      value={selectedGrainPreset ?? ""}
                      disabled={configBusy || jobLocked}
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
                <Button disabled={configBusy || jobLocked} onClick={() => void handleDetectEra()}>
                  {configBusy ? "Working..." : detection ? "Refresh Detection" : "Detect Era"}
                </Button>
                <Button
                  disabled={configBusy || jobLocked || !canOverrideEra(detection)}
                  onClick={() => setShowOverrideModal(true)}
                  type="button"
                  variant="secondary"
                >
                  Override Era
                </Button>
                <Button
                  aria-describedby={formErrorTarget === "configuration" ? activeFormErrorId : undefined}
                  disabled={configBusy || jobLocked || !detection || !selectedTier || !selectedGrainPreset}
                  onClick={() => void handleSaveConfiguration()}
                  ref={saveConfigurationButtonRef}
                  type="button"
                >
                  Save Configuration
                </Button>
              </div>
              {detection ? (
                <div
                  className="chronos-card-note"
                  style={{
                    background: "#f7fafc",
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
                  {(detection.warnings ?? []).length ? (
                    <ul style={{ marginBottom: 0 }}>
                      {(detection.warnings ?? []).map((warning) => (
                        <li key={warning}>{warning}</li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              ) : null}
              {savedConfiguration ? (
                <div
                  className="chronos-card-note"
                  style={{
                    background: "#edf7ef",
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

        {savedConfiguration || processingJob ? (
          <Card title="Packet 4C Processing Flow">
            <div style={{ display: "grid", gap: "var(--spacing-md)" }}>
              <p style={{ color: "var(--color-text-muted)", marginTop: 0 }}>
                Review the saved preview and live estimate from the Packet 4B configuration, then launch processing
                from the approved preview without leaving this flow.
              </p>
              {savedConfiguration ? (
                <div
                  style={{
                    borderRadius: "var(--radius-md)",
                    background: "#f7fafc",
                    padding: "var(--spacing-md)",
                  }}
                >
                  <div>
                    <strong>Saved upload:</strong> {savedConfiguration.upload_id}
                  </div>
                  <div>
                    <strong>Launch tier:</strong> {savedConfiguration.fidelity_tier}
                  </div>
                  <div>
                    <strong>Launch grain preset:</strong> {savedConfiguration.grain_preset}
                  </div>
                </div>
              ) : null}

              {!processingJob ? (
                <div style={{ display: "flex", gap: "var(--spacing-sm)", flexWrap: "wrap" }}>
                  <Button
                    disabled={jobBusy || !canStartSavedConfiguration}
                    onClick={() => void handleOpenPreviewReviewModal()}
                    ref={launchReviewButtonRef}
                  >
                    {jobBusy ? "Starting..." : "Review Preview & Start"}
                  </Button>
                </div>
              ) : (
                <>
                  <div
                    className="chronos-card-note"
                    style={{
                      background: "#edf5fb",
                    }}
                  >
                    <div>
                      <strong>Job ID:</strong> {processingJob.job_id}
                    </div>
                    <div>
                      <strong>Status:</strong> {processingJob.status}
                    </div>
                    <div>
                      <strong>Operation:</strong> {processingJob.progress.current_operation}
                    </div>
                    <div style={{ marginTop: "var(--spacing-sm)" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "var(--spacing-xs)" }}>
                        <span>Progress</span>
                        <span>{Math.round(processingJob.progress.percent_complete)}%</span>
                      </div>
                      <ProgressBar value={Math.round(processingJob.progress.percent_complete)} />
                      <div style={{ marginTop: "var(--spacing-xs)", color: "var(--color-text-muted)" }}>
                        ETA: {processingJob.progress.eta_seconds}s
                      </div>
                    </div>
                  </div>

                  {statusNotice ? (
                    <div
                      aria-live="polite"
                      role="status"
                      className="chronos-status-banner"
                      style={{ background: "#eef5ff", borderColor: "#0f4c81" }}
                    >
                      <div>{statusNotice}</div>
                      <div style={{ marginTop: "var(--spacing-sm)" }}>
                        <Button variant="secondary" onClick={() => void handleRetryProcessingRefresh()}>
                          Retry Status Refresh
                        </Button>
                      </div>
                    </div>
                  ) : null}

                  <div style={{ display: "flex", gap: "var(--spacing-sm)", flexWrap: "wrap" }}>
                    {jobActive ? (
                      <Button variant="secondary" disabled={jobBusy} onClick={() => void handleCancelProcessing()}>
                        {jobBusy ? "Cancelling..." : "Cancel Processing"}
                      </Button>
                    ) : (
                      <Button
                        disabled={jobBusy || !canStartSavedConfiguration}
                        onClick={() => void handleOpenPreviewReviewModal()}
                        ref={launchReviewButtonRef}
                      >
                        {jobBusy ? "Starting..." : "Review Preview & Start Again"}
                      </Button>
                    )}
                  </div>

                  {processingJob.result_uri ? (
                    <div>
                      <strong>Result URI:</strong> {processingJob.result_uri}
                    </div>
                  ) : null}
                  {processingJob.last_error ? (
                    <div>
                      <strong>Last error:</strong> {processingJob.last_error}
                    </div>
                  ) : null}
                  {processingJob.warnings.length ? (
                    <div>
                      <strong>Warnings</strong>
                      <ul>
                        {processingJob.warnings.map((warning) => (
                          <li key={warning}>{warning}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  <UncertaintyCalloutsList callouts={jobCallouts?.callouts ?? []} />

                  {exportReady ? (
                    <section aria-labelledby="packet-4d-delivery-heading" style={{ display: "grid", gap: "var(--spacing-md)" }}>
                      <h3
                        id="packet-4d-delivery-heading"
                        ref={terminalHeadingRef}
                        tabIndex={-1}
                        style={{ marginBottom: 0 }}
                      >
                        Packet 4D Delivery
                      </h3>
                      <p style={{ color: "var(--color-text-muted)", margin: 0 }}>
                        Download the encoded delivery packages, open the transformation manifest, and retrieve the
                        deletion proof once processing reaches a terminal state.
                      </p>

                      {isMuseumPlan ? (
                        <label>
                          <div style={{ marginBottom: "var(--spacing-xs)" }}>Retention window</div>
                          <select
                            aria-label="Select retention window"
                            className="chronos-select"
                            onChange={(event) => setDeliveryRetentionDays(Number(event.target.value))}
                            value={deliveryRetentionDays}
                          >
                            <option value={7}>7 days</option>
                            <option value={30}>30 days</option>
                            <option value={90}>90 days</option>
                          </select>
                        </label>
                      ) : null}

                      <div style={{ display: "flex", gap: "var(--spacing-sm)", flexWrap: "wrap" }}>
                        <Button
                          aria-label="Download AV1 Package"
                          disabled={deliveryBusy.av1}
                          onClick={() => void handleDownloadPackage("av1")}
                          ref={primaryDeliveryButtonRef}
                        >
                          {deliveryBusy.av1 ? "Preparing AV1..." : "Download AV1 Package"}
                        </Button>
                        <Button
                          aria-label="Download Compatibility Package"
                          disabled={deliveryBusy.h264}
                          onClick={() => void handleDownloadPackage("h264")}
                          variant="secondary"
                        >
                          {deliveryBusy.h264 ? "Preparing Compatibility..." : "Download Compatibility Package"}
                        </Button>
                        <Button
                          aria-label="View Manifest JSON"
                          disabled={deliveryBusy.manifest}
                          onClick={() => void handleViewManifest()}
                          variant="secondary"
                        >
                          {deliveryBusy.manifest ? "Loading Manifest..." : "View Manifest JSON"}
                        </Button>
                        <Button
                          aria-label="Download Deletion Proof PDF"
                          disabled={deliveryBusy.proof}
                          onClick={() => void handleDownloadDeletionProof()}
                          variant="secondary"
                        >
                          {deliveryBusy.proof ? "Loading Proof..." : "Download Deletion Proof PDF"}
                        </Button>
                      </div>

                      {deliveryNotice ? (
                        <div
                          aria-live="polite"
                          role="status"
                          className="chronos-status-banner"
                          style={{ background: "#eef5ff", borderColor: "#0f4c81" }}
                        >
                          <div>{deliveryNotice}</div>
                          {deliveryRetryAction ? (
                            <div style={{ marginTop: "var(--spacing-sm)" }}>
                              <Button variant="secondary" onClick={() => void handleRetryDeliveryAction()}>
                                {deliveryActionLabel(deliveryRetryAction)}
                              </Button>
                            </div>
                          ) : null}
                        </div>
                      ) : null}

                      {deliveryError ? (
                        <div
                          ref={deliveryAlertRef}
                          aria-live="assertive"
                          role="alert"
                          tabIndex={-1}
                          className="chronos-alert-banner"
                          style={{ background: "#fff0f0", color: "#8a1f1f", borderColor: "#b42318" }}
                        >
                          <div>{deliveryError}</div>
                          {deliveryRetryAction ? (
                            <div style={{ marginTop: "var(--spacing-sm)" }}>
                              <Button variant="secondary" onClick={() => void handleRetryDeliveryAction()}>
                                {deliveryActionLabel(deliveryRetryAction)}
                              </Button>
                            </div>
                          ) : null}
                        </div>
                      ) : null}
                    </section>
                  ) : null}
                </>
              )}
            </div>
          </Card>
        ) : null}

        {error ? (
          <div
            id="packet4g-form-error"
            ref={appErrorRef}
            role="alert"
            tabIndex={-1}
            className="chronos-alert-banner"
            style={{ background: "#fff0f0", color: "#8a1f1f", borderColor: "#b42318" }}
          >
            {error}
          </div>
        ) : null}
      </div>

      <PreviewReviewModal
        approving={overageApprovalBusy}
        error={launchModalError}
        estimate={costEstimate}
        estimateLoading={costEstimateBusy}
        invalidated={previewReviewInvalidated}
        notice={launchModalNotice}
        onApproveOverage={() => void handleApproveLaunchOverage()}
        onApprovePreview={() => void handleApprovePreview()}
        onClose={() => resetPreviewReviewState()}
        onLaunch={() => void handleLaunchFromPreview()}
        onRefresh={() => {
          if (savedConfiguration) {
            void loadPreviewReviewGate(savedConfiguration);
          }
        }}
        onRejectPreview={() => void handleRejectPreview()}
        open={showPreviewReviewModal}
        preview={previewSession}
        previewLoading={previewBusy}
        reviewing={previewReviewBusy}
        launching={jobBusy}
      />
      <Modal
        open={showKeyboardShortcutsModal}
        onClose={() => setShowKeyboardShortcutsModal(false)}
        labelledBy="keyboard-shortcuts-title"
        describedBy="keyboard-shortcuts-description"
      >
        <div style={{ display: "grid", gap: "var(--spacing-md)", maxWidth: 520 }}>
          <div>
            <h2 id="keyboard-shortcuts-title" style={{ marginBottom: "var(--spacing-xs)" }}>
              Keyboard Shortcuts
            </h2>
            <p id="keyboard-shortcuts-description" style={{ marginTop: 0, marginBottom: 0 }}>
              Packet 4G documents safe keyboard shortcuts for the current Phase 4 flow without triggering processing
              automatically.
            </p>
          </div>
          <dl style={{ margin: 0, display: "grid", gridTemplateColumns: "auto 1fr", gap: "var(--spacing-xs) var(--spacing-md)" }}>
            <dt><strong>Cmd/Ctrl + Shift + U</strong></dt>
            <dd style={{ margin: 0 }}>Focus the media file input.</dd>
            <dt><strong>Cmd/Ctrl + Shift + S</strong></dt>
            <dd style={{ margin: 0 }}>Focus the Save Configuration action.</dd>
            <dt><strong>Cmd/Ctrl + Shift + L</strong></dt>
            <dd style={{ margin: 0 }}>Focus the launch cost review action.</dd>
            <dt><strong>Cmd/Ctrl + Shift + E</strong></dt>
            <dd style={{ margin: 0 }}>Jump to the primary delivery action when exports are available.</dd>
            <dt><strong>Tab / Shift + Tab</strong></dt>
            <dd style={{ margin: 0 }}>Move forward or backward through interactive controls.</dd>
            <dt><strong>Escape</strong></dt>
            <dd style={{ margin: 0 }}>Close the currently open modal or dialog.</dd>
          </dl>
          <div className="chronos-status-banner" role="note">
            Shortcuts only move focus or open review surfaces. Use Enter or Space to activate the focused control.
          </div>
          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <Button data-autofocus="true" onClick={() => setShowKeyboardShortcutsModal(false)} type="button" variant="secondary">
              Close
            </Button>
          </div>
        </div>
      </Modal>
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
    </>
  );
}
