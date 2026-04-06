import type { JobCostEstimateResponse } from "./costEstimateHelpers";
import type { JobDetailResponse } from "./processingHelpers";

export type PreviewReviewStatus = "pending" | "approved" | "rejected";
export type PreviewLaunchStatus = "not_launched" | "launch_pending" | "launched";

export type PreviewKeyframeResponse = {
  index: number;
  timestamp_seconds: number;
  scene_number: number;
  confidence_score: number;
  thumbnail_url: string;
  frame_url: string;
};

export type PreviewSessionResponse = {
  preview_id: string;
  upload_id: string;
  status: "ready";
  configuration_fingerprint: string;
  review_status: PreviewReviewStatus;
  reviewed_at?: string | null;
  launch_status: PreviewLaunchStatus;
  launched_job_id?: string | null;
  launched_at?: string | null;
  stale: boolean;
  expires_at: string;
  selection_mode: "scene_aware" | "uniform_fallback";
  scene_diversity: number;
  keyframe_count: number;
  estimated_cost_summary: JobCostEstimateResponse;
  estimated_processing_time_seconds: number;
  keyframes: PreviewKeyframeResponse[];
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

export async function createPreview(
  apiBaseUrl: string,
  accessToken: string,
  uploadId: string,
  fetchFn: typeof fetch = globalThis.fetch.bind(globalThis),
): Promise<PreviewSessionResponse> {
  const response = await fetchFn(apiUrl(apiBaseUrl, "/v1/previews"), {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ upload_id: uploadId }),
  });
  if (!response.ok) {
    throw new Error(await decodeProblem(response, "Unable to create the preview."));
  }
  return (await response.json()) as PreviewSessionResponse;
}

export async function reviewPreview(
  apiBaseUrl: string,
  accessToken: string,
  previewId: string,
  reviewStatus: Exclude<PreviewReviewStatus, "pending">,
  fetchFn: typeof fetch = globalThis.fetch.bind(globalThis),
): Promise<PreviewSessionResponse> {
  const response = await fetchFn(apiUrl(apiBaseUrl, `/v1/previews/${previewId}/review`), {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ review_status: reviewStatus }),
  });
  if (!response.ok) {
    throw new Error(await decodeProblem(response, "Unable to update the preview review state."));
  }
  return (await response.json()) as PreviewSessionResponse;
}

export async function launchApprovedPreview(
  apiBaseUrl: string,
  accessToken: string,
  previewId: string,
  configurationFingerprint: string,
  fetchFn: typeof fetch = globalThis.fetch.bind(globalThis),
): Promise<JobDetailResponse> {
  const response = await fetchFn(apiUrl(apiBaseUrl, `/v1/previews/${previewId}/launch`), {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ configuration_fingerprint: configurationFingerprint }),
  });
  if (!response.ok) {
    throw new Error(await decodeProblem(response, "Unable to start processing from the approved preview."));
  }
  return (await response.json()) as JobDetailResponse;
}
