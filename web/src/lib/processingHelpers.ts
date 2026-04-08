export type JobStatus = "queued" | "processing" | "completed" | "failed" | "partial" | "cancel_requested" | "cancelled";

export type UsageSnapshotResponse = {
  user_id: string;
  plan_tier: string;
  used_minutes: number;
  monthly_limit_minutes: number;
  remaining_minutes: number;
  estimated_next_job_minutes: number;
  approved_overage_minutes: number;
  remaining_approved_overage_minutes: number;
  threshold_alerts: number[];
  overage_approval_scope?: string | null;
  hard_stop: boolean;
  price_reference: string;
  overage_price_reference: string;
  reconciliation_source: string;
  reconciliation_status: string;
  effective_pricing?: EffectivePricingResponse | null;
};

export type EffectivePricingResponse = {
  pricebook_version: string;
  subscription_price_id: string;
  subscription_price_usd: number;
  included_minutes_monthly: number;
  overage_enabled: boolean;
  overage_price_id: string;
  overage_rate_usd_per_minute: number;
  entitlement_source: string;
};

export type CostEstimateSummaryResponse = {
  estimated_usage_minutes: number;
  operational_cost_breakdown_usd: {
    gpu_time: number;
    storage: number;
    api_calls: number;
    total: number;
  };
  billing_breakdown_usd: {
    included_usage: number;
    overage_minutes: number;
    overage_rate_usd_per_minute: number;
    estimated_charge_total_usd: number;
  };
  confidence_interval_usd: {
    low: number;
    high: number;
  };
  usage_snapshot: UsageSnapshotResponse;
  effective_pricing?: EffectivePricingResponse | null;
  launch_blocker: "none" | "overage_approval_required";
  estimator_version: string;
  generated_at: string;
};

export type CostReconciliationSummaryResponse = {
  estimated_total_cost_usd: number;
  actual_total_cost_usd: number;
  delta_usd: number;
  delta_percent: number;
  estimated_charge_total_usd: number;
  actual_charge_total_usd: number;
  actual_usage_minutes: number;
  outlier_threshold_percent: number;
  outlier_flagged: boolean;
  estimator_version: string;
  reconciled_at?: string | null;
};

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
  cost_estimate_summary?: CostEstimateSummaryResponse | null;
  cost_reconciliation_summary?: CostReconciliationSummaryResponse | null;
  failed_segments: number[];
  warnings: string[];
  created_at: string;
  updated_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  cancel_requested_at?: string | null;
  last_error?: string | null;
  deletion_proof_id?: string | null;
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
