export type JobStatus = "queued" | "processing" | "completed" | "failed" | "partial" | "cancel_requested" | "cancelled";

export type JobProgressResponse = {
  job_id: string;
  segment_index: number;
  segment_count: number;
  percent_complete: number;
  eta_seconds: number;
  status: JobStatus;
  current_operation: string;
  updated_at: string;
};

export type JobDetailResponse = {
  job_id: string;
  media_uri: string;
  original_filename: string;
  mime_type: string;
  fidelity_tier: string;
  effective_fidelity_tier: string;
  processing_mode: string;
  reproducibility_mode: string;
  estimated_duration_seconds: number;
  status: JobStatus;
  progress_topic: string;
  result_uri?: string | null;
  manifest_available: boolean;
  failed_segments: number[];
  warnings: string[];
  created_at: string;
  updated_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  cancel_requested_at?: string | null;
  last_error?: string | null;
  progress: JobProgressResponse;
};

export type JobCancelResponse = {
  job_id: string;
  status: JobStatus;
  cancel_requested_at?: string | null;
};

export type UncertaintyCallout = {
  callout_id: string;
  code: string;
  severity: "warning" | "critical";
  title: string;
  message: string;
  scope: "segment" | "global";
  time_range_seconds: {
    start: number;
    end: number;
  };
  source: {
    segment_index?: number | null;
    metric_key?: string | null;
  };
};

export type JobUncertaintyCalloutsResponse = {
  job_id: string;
  status: JobStatus;
  callouts: UncertaintyCallout[];
};

type ProblemPayload = {
  detail?: string;
  title?: string;
};

function apiUrl(apiBaseUrl: string, path: string): string {
  return `${apiBaseUrl.replace(/\/$/, "")}${path}`;
}

async function decodeProblem(response: Response, fallbackMessage: string): Promise<string> {
  try {
    const payload = (await response.clone().json()) as ProblemPayload;
    if (payload.detail || payload.title) {
      return payload.detail || payload.title || fallbackMessage;
    }
  } catch {
    // Fall back to raw text for non-JSON responses.
  }
  try {
    const text = (await response.text()).trim();
    return text || fallbackMessage;
  } catch {
    return fallbackMessage;
  }
}

export async function startProcessing(
  apiBaseUrl: string,
  accessToken: string,
  payload: Record<string, unknown>,
  fetchFn: typeof fetch = globalThis.fetch.bind(globalThis),
): Promise<JobDetailResponse> {
  const response = await fetchFn(apiUrl(apiBaseUrl, "/v1/jobs"), {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await decodeProblem(response, "Unable to start processing."));
  }
  return (await response.json()) as JobDetailResponse;
}

export async function fetchJobDetail(
  apiBaseUrl: string,
  accessToken: string,
  jobId: string,
  fetchFn: typeof fetch = globalThis.fetch.bind(globalThis),
): Promise<JobDetailResponse> {
  const response = await fetchFn(apiUrl(apiBaseUrl, `/v1/jobs/${jobId}`), {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
  if (!response.ok) {
    throw new Error(await decodeProblem(response, "Unable to refresh processing status."));
  }
  return (await response.json()) as JobDetailResponse;
}

export async function fetchUncertaintyCallouts(
  apiBaseUrl: string,
  accessToken: string,
  jobId: string,
  fetchFn: typeof fetch = globalThis.fetch.bind(globalThis),
): Promise<JobUncertaintyCalloutsResponse> {
  const response = await fetchFn(apiUrl(apiBaseUrl, `/v1/jobs/${jobId}/uncertainty-callouts`), {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
  if (!response.ok) {
    throw new Error(await decodeProblem(response, "Unable to refresh uncertainty callouts."));
  }
  return (await response.json()) as JobUncertaintyCalloutsResponse;
}

export async function cancelProcessing(
  apiBaseUrl: string,
  accessToken: string,
  jobId: string,
  fetchFn: typeof fetch = globalThis.fetch.bind(globalThis),
): Promise<JobCancelResponse> {
  const response = await fetchFn(apiUrl(apiBaseUrl, `/v1/jobs/${jobId}`), {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
  if (!response.ok) {
    throw new Error(await decodeProblem(response, "Unable to cancel processing."));
  }
  return (await response.json()) as JobCancelResponse;
}

export function isActiveJobStatus(status: JobStatus | null | undefined): boolean {
  return status === "queued" || status === "processing" || status === "cancel_requested";
}

export function formatTimeRange(startSeconds: number, endSeconds: number): string {
  return `${Math.round(startSeconds)}s-${Math.round(endSeconds)}s`;
}
