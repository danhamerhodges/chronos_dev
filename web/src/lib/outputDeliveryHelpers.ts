export type ExportVariant = "av1" | "h264";

export type DeliveryRequestError = Error & {
  status?: number;
};

export type UserProfileSummary = {
  user_id: string;
  plan_tier: string;
};

export type JobExportResponse = {
  job_id: string;
  status: string;
  variant: ExportVariant;
  download_url: string;
  expires_at: string;
  file_name: string;
  size_bytes: number;
  sha256: string;
  deletion_proof_id: string;
  package_contents: string[];
};

export type DeletionProofResponse = {
  deletion_proof_id: string;
  job_id: string;
  generated_at: string;
  signature_algorithm: string;
  signature: string;
  proof_sha256: string;
  pdf_download_url: string;
  pdf_expires_at: string;
  verification_summary: Record<string, unknown>;
};

export type TransformationManifestResponse = Record<string, unknown>;

type ProblemPayload = {
  detail?: string;
  title?: string;
  status?: number;
};

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

async function throwDeliveryError(response: Response, fallbackMessage: string): Promise<never> {
  const message = await decodeProblem(response, fallbackMessage);
  const error = new Error(message) as DeliveryRequestError;
  error.status = response.status;
  throw error;
}

export async function fetchCurrentUserProfile(
  apiBaseUrl: string,
  accessToken: string,
  fetchFn: typeof fetch = globalThis.fetch.bind(globalThis),
): Promise<UserProfileSummary> {
  const response = await fetchFn(apiUrl(apiBaseUrl, "/v1/users/me"), {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
  if (!response.ok) {
    await throwDeliveryError(response, "Unable to load delivery settings.");
  }
  return (await response.json()) as UserProfileSummary;
}

export async function fetchJobExport(
  apiBaseUrl: string,
  accessToken: string,
  jobId: string,
  options: {
    variant?: ExportVariant;
    retentionDays?: number;
  } = {},
  fetchFn: typeof fetch = globalThis.fetch.bind(globalThis),
): Promise<JobExportResponse> {
  const variant = options.variant ?? "av1";
  const retentionDays = options.retentionDays ?? 7;
  const params = new URLSearchParams({
    variant,
    retention_days: String(retentionDays),
  });
  const response = await fetchFn(apiUrl(apiBaseUrl, `/v1/jobs/${encodeURIComponent(jobId)}/export?${params.toString()}`), {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
  if (!response.ok) {
    await throwDeliveryError(response, "Unable to fetch the delivery package.");
  }
  return (await response.json()) as JobExportResponse;
}

export async function fetchDeletionProof(
  apiBaseUrl: string,
  accessToken: string,
  proofId: string,
  fetchFn: typeof fetch = globalThis.fetch.bind(globalThis),
): Promise<DeletionProofResponse> {
  const response = await fetchFn(apiUrl(apiBaseUrl, `/v1/deletion-proofs/${encodeURIComponent(proofId)}`), {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
  if (!response.ok) {
    await throwDeliveryError(response, "Unable to fetch the deletion proof.");
  }
  return (await response.json()) as DeletionProofResponse;
}

export async function fetchTransformationManifest(
  apiBaseUrl: string,
  accessToken: string,
  jobId: string,
  fetchFn: typeof fetch = globalThis.fetch.bind(globalThis),
): Promise<TransformationManifestResponse> {
  const response = await fetchFn(apiUrl(apiBaseUrl, `/v1/manifests/${encodeURIComponent(jobId)}`), {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
  if (!response.ok) {
    await throwDeliveryError(response, "Unable to fetch the transformation manifest.");
  }
  return (await response.json()) as TransformationManifestResponse;
}
