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
};

export type JobCostEstimateResponse = {
  configuration_fingerprint: string;
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
  launch_blocker: "none" | "overage_approval_required";
  estimator_version: string;
  generated_at: string;
};

export type OverageApprovalResponse = {
  user_id: string;
  approval_scope: string;
  approved_for_minutes: number;
  remaining_approved_overage_minutes: number;
  remaining_minutes: number;
  threshold_alerts: number[];
  overage_price_reference: string;
};

type ProblemPayload = {
  detail?: string;
  title?: string;
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
    // Fall back to raw text for non-JSON responses.
  }
  try {
    const text = (await response.text()).trim();
    return text || fallbackMessage;
  } catch {
    return fallbackMessage;
  }
}

export async function fetchJobEstimate(
  apiBaseUrl: string,
  accessToken: string,
  payload: Record<string, unknown>,
  fetchFn: typeof fetch = globalThis.fetch.bind(globalThis),
): Promise<JobCostEstimateResponse> {
  const response = await fetchFn(apiUrl(apiBaseUrl, "/v1/jobs/estimate"), {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await decodeProblem(response, "Unable to load the cost estimate."));
  }
  return (await response.json()) as JobCostEstimateResponse;
}

export async function approveSingleJobOverage(
  apiBaseUrl: string,
  accessToken: string,
  requestedMinutes: number,
  fetchFn: typeof fetch = globalThis.fetch.bind(globalThis),
): Promise<OverageApprovalResponse> {
  const response = await fetchFn(apiUrl(apiBaseUrl, "/v1/users/me/approve-overage"), {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      approval_scope: "single_job",
      requested_minutes: requestedMinutes,
      reason: "Approved from Packet 4E launch modal.",
    }),
  });
  if (!response.ok) {
    throw new Error(await decodeProblem(response, "Unable to approve the estimated overage."));
  }
  return (await response.json()) as OverageApprovalResponse;
}
