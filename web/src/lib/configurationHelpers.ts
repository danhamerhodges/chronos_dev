export type FidelityTier = "Enhance" | "Restore" | "Conserve";
export type UserPersona = "archivist" | "filmmaker" | "prosumer";
export type GrainPreset = "Matched" | "Subtle" | "Heavy";

export type FidelityPersonaOption = {
  persona: UserPersona;
  label: string;
  default_fidelity_tier: FidelityTier;
  description: string;
};

export type FidelityTierCatalogItem = {
  tier: FidelityTier;
  label: string;
  description: string;
  default_grain_preset: GrainPreset;
  allowed_grain_presets: GrainPreset[];
  relative_cost_multiplier: number;
  relative_processing_time_band: string;
  thresholds: Record<string, number>;
  identity_lock: boolean;
};

export type FidelityTierCatalogResponse = {
  personas: FidelityPersonaOption[];
  tiers: FidelityTierCatalogItem[];
  grain_presets: GrainPreset[];
  current_persona: UserPersona | null;
  preferred_fidelity_tier: FidelityTier | null;
  preferred_grain_preset: GrainPreset | null;
};

export type UploadDetectEraResponse = {
  upload_id: string;
  detection_id: string;
  job_id: string;
  era: string;
  confidence: number;
  manual_confirmation_required: boolean;
  top_candidates: Array<{ era: string; confidence: number }>;
  forensic_markers: {
    grain_structure: string;
    color_saturation: number;
    format_artifacts: string[];
  };
  warnings: string[];
  processing_timestamp: string;
  source: string;
  model_version: string;
  prompt_version: string;
  estimated_usage_minutes: number;
};

export type JobLaunchContext = {
  source: "approved_preview";
  upload_id: string;
  configuration_fingerprint: string;
};

export type JobPayloadPreview = {
  media_uri: string;
  original_filename: string;
  mime_type: string;
  estimated_duration_seconds: number;
  source_asset_checksum: string;
  fidelity_tier: FidelityTier;
  reproducibility_mode: string;
  processing_mode: string;
  era_profile: Record<string, unknown>;
  config: Record<string, unknown>;
  launch_context: JobLaunchContext;
};

export type UploadConfigurationResponse = {
  upload_id: string;
  status: "pending" | "uploading" | "completed" | "failed";
  persona: UserPersona;
  fidelity_tier: FidelityTier;
  grain_preset: GrainPreset;
  detection_snapshot: UploadDetectEraResponse;
  resolved_fidelity_profile: Record<string, unknown>;
  relative_cost_multiplier: number;
  relative_processing_time_band: string;
  job_payload_preview: JobPayloadPreview;
  configured_at: string;
  configuration_fingerprint: string;
};

type ProblemPayload = {
  detail?: string;
  title?: string;
};

const LEARN_MORE_URL =
  "https://github.com/danhamerhodges/chronos_dev/blob/main/docs/specs/chronosrefine_design_requirements.md#ds-001-fidelity-configuration-ux";

function apiUrl(baseUrl: string, path: string): string {
  return `${baseUrl.replace(/\/$/, "")}${path}`;
}

async function decodeProblem(response: Response, fallbackMessage: string): Promise<string> {
  try {
    const payload = (await response.clone().json()) as ProblemPayload;
    if (payload.detail || payload.title) {
      return payload.detail || payload.title || fallbackMessage;
    }
  } catch {
    // Fall back to raw text when the response is not JSON.
  }
  try {
    const text = (await response.text()).trim();
    return text || fallbackMessage;
  } catch {
    return fallbackMessage;
  }
}

export function learnMoreUrl(): string {
  return LEARN_MORE_URL;
}

export function canOverrideEra(detection: UploadDetectEraResponse | null): boolean {
  return Boolean(detection && detection.confidence < 0.7);
}

export function defaultTierForPersona(
  catalog: FidelityTierCatalogResponse,
  persona: UserPersona | null,
): FidelityTier | null {
  if (!persona) return null;
  return catalog.personas.find((item) => item.persona === persona)?.default_fidelity_tier ?? null;
}

export function defaultGrainPresetForTier(
  catalog: FidelityTierCatalogResponse,
  tier: FidelityTier | null,
): GrainPreset | null {
  if (!tier) return null;
  return catalog.tiers.find((item) => item.tier === tier)?.default_grain_preset ?? null;
}

export function allowedGrainPresetsForTier(
  catalog: FidelityTierCatalogResponse,
  tier: FidelityTier | null,
): GrainPreset[] {
  if (!tier) return [];
  return catalog.tiers.find((item) => item.tier === tier)?.allowed_grain_presets ?? [];
}

export async function fetchFidelityCatalog(
  apiBaseUrl: string,
  accessToken: string,
  fetchFn: typeof fetch = globalThis.fetch.bind(globalThis),
): Promise<FidelityTierCatalogResponse> {
  const response = await fetchFn(apiUrl(apiBaseUrl, "/v1/fidelity-tiers"), {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) {
    throw new Error(await decodeProblem(response, "Unable to load fidelity tiers."));
  }
  return (await response.json()) as FidelityTierCatalogResponse;
}

export async function detectUploadEra(
  apiBaseUrl: string,
  accessToken: string,
  uploadId: string,
  payload: {
    estimated_duration_seconds: number;
    manual_override_era?: string;
    override_reason?: string;
  },
  fetchFn: typeof fetch = globalThis.fetch.bind(globalThis),
): Promise<UploadDetectEraResponse> {
  const response = await fetchFn(apiUrl(apiBaseUrl, `/v1/upload/${uploadId}/detect-era`), {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await decodeProblem(response, "Unable to detect the media era."));
  }
  return (await response.json()) as UploadDetectEraResponse;
}

export async function saveUploadConfiguration(
  apiBaseUrl: string,
  accessToken: string,
  uploadId: string,
  payload: {
    persona?: UserPersona;
    fidelity_tier: FidelityTier;
    grain_preset: GrainPreset;
    estimated_duration_seconds: number;
    manual_override_era?: string;
    override_reason?: string;
  },
  fetchFn: typeof fetch = globalThis.fetch.bind(globalThis),
): Promise<UploadConfigurationResponse> {
  const response = await fetchFn(apiUrl(apiBaseUrl, `/v1/upload/${uploadId}/configuration`), {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await decodeProblem(response, "Unable to save the launch-ready configuration."));
  }
  return (await response.json()) as UploadConfigurationResponse;
}
