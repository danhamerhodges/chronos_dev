export type UploadStatus = "pending" | "uploading" | "completed" | "failed";

export type UploadFileLike = Pick<File, "name" | "type" | "size" | "slice">;

export type UploadResponse = {
  upload_id: string;
  status: UploadStatus;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  checksum_sha256?: string | null;
  bucket_name: string;
  object_path: string;
  media_uri: string;
  resumable_session_url: string;
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
};

export type UploadResumeResponse = {
  upload_id: string;
  status: UploadStatus;
  resumable_session_url: string;
  next_byte_offset: number;
  upload_complete: boolean;
  session_regenerated: boolean;
  object_path: string;
  media_uri: string;
};

type ProblemPayload = {
  detail?: string;
  title?: string;
};

export type UploadProgress = {
  confirmedBytes: number;
  etaSeconds: number;
};

export type FetchFn = typeof fetch;

export type UploadProgressEventLike = {
  lengthComputable: boolean;
  loaded: number;
};

export type UploadRequestLike = {
  status: number;
  upload: {
    onprogress: ((event: UploadProgressEventLike) => void) | null;
  };
  onload: (() => void) | null;
  onerror: (() => void) | null;
  open: (method: string, url: string, async?: boolean) => void;
  setRequestHeader: (name: string, value: string) => void;
  getResponseHeader: (name: string) => string | null;
  send: (body: Blob) => void;
};

export type UploadTransportOptions = {
  fetchFn?: FetchFn;
  xhrFactory?: () => UploadRequestLike;
  now?: () => number;
};

export type UploadFlowDependencies = {
  getAccessToken: () => Promise<string>;
  createSession?: typeof createUploadSession;
  resumeSession?: typeof resumeUploadSession;
  uploadBytes?: typeof uploadRemainingBytes;
  finalizeSession?: typeof finalizeUpload;
  transportOptions?: UploadTransportOptions;
};

export type UploadFlowHandlers = {
  setUploadSession: (session: UploadResponse | null) => void;
  setStatus: (status: UploadStatus) => void;
  setProgress: (progress: number) => void;
  setEtaSeconds: (etaSeconds: number) => void;
  setCanResume: (canResume: boolean) => void;
  setError: (message: string) => void;
};

export type UploadFlowParams = {
  apiBaseUrl: string;
  file: UploadFileLike;
  resumeExisting: boolean;
  existingSession: UploadResponse | null;
  dependencies: UploadFlowDependencies;
  handlers: UploadFlowHandlers;
};

const SUPPORTED_FORMATS: Record<string, Set<string>> = {
  ".mp4": new Set(["video/mp4"]),
  ".avi": new Set(["video/x-msvideo", "video/avi"]),
  ".mov": new Set(["video/quicktime"]),
  ".mkv": new Set(["video/x-matroska"]),
  ".tif": new Set(["image/tiff"]),
  ".tiff": new Set(["image/tiff"]),
  ".png": new Set(["image/png"]),
  ".jpg": new Set(["image/jpeg"]),
  ".jpeg": new Set(["image/jpeg"]),
};

export class UploadInterruptedError extends Error {
  confirmedBytes: number;

  constructor(message: string, confirmedBytes: number) {
    super(message);
    this.name = "UploadInterruptedError";
    this.confirmedBytes = confirmedBytes;
  }
}

function defaultFetchFn(): FetchFn {
  return globalThis.fetch.bind(globalThis);
}

function defaultXhrFactory(): UploadRequestLike {
  return new XMLHttpRequest() as unknown as UploadRequestLike;
}

function uploadUrl(apiBaseUrl: string, path: string): string {
  return `${apiBaseUrl.replace(/\/$/, "")}${path}`;
}

function normalizeExtension(filename: string): string {
  const extensionIndex = filename.lastIndexOf(".");
  if (extensionIndex < 0) return "";
  return filename.slice(extensionIndex).toLowerCase();
}

function progressFromBytes(confirmedBytes: number, file: UploadFileLike): number {
  return progressPercentFromBytes(confirmedBytes, file.size);
}

function errorMessage(caught: unknown, fallback: string): string {
  return caught instanceof Error ? caught.message : fallback;
}

export function isSupportedUploadFormat(filename: string, mimeType: string): boolean {
  const extension = normalizeExtension(filename);
  const allowedMimeTypes = SUPPORTED_FORMATS[extension];
  if (!allowedMimeTypes) return false;
  return allowedMimeTypes.has(mimeType.toLowerCase());
}

export function estimateEtaSeconds(
  startedAt: number,
  loaded: number,
  total: number,
  now: () => number = Date.now,
): number {
  if (loaded <= 0 || total <= 0) return 0;
  const elapsedSeconds = Math.max((now() - startedAt) / 1000, 0.001);
  const bytesPerSecond = loaded / elapsedSeconds;
  if (bytesPerSecond <= 0) return 0;
  return Math.max(Math.round((total - loaded) / bytesPerSecond), 0);
}

export function parseCommittedRangeHeader(rangeHeader: string | null | undefined): number {
  if (!rangeHeader) return 0;
  const match = /^bytes=0-(\d+)$/.exec(rangeHeader.trim());
  if (!match) return 0;
  return Number.parseInt(match[1] ?? "0", 10) + 1;
}

export function buildContentRange(nextByteOffset: number, chunkSize: number, totalSize: number): string {
  if (chunkSize <= 0 || totalSize <= 0 || nextByteOffset >= totalSize) {
    return `bytes */${totalSize}`;
  }
  const lastByte = Math.min(nextByteOffset + chunkSize - 1, totalSize - 1);
  return `bytes ${nextByteOffset}-${lastByte}/${totalSize}`;
}

export function progressPercentFromBytes(confirmedBytes: number, totalBytes: number): number {
  if (totalBytes <= 0) return 0;
  return Math.min(Math.round((confirmedBytes / totalBytes) * 100), 100);
}

export function mergeUploadSessionWithResume(
  session: UploadResponse,
  resume: UploadResumeResponse,
): UploadResponse {
  return {
    ...session,
    status: resume.status,
    resumable_session_url: resume.resumable_session_url,
    object_path: resume.object_path,
    media_uri: resume.media_uri,
  };
}

async function decodeProblem(response: Response, fallbackMessage: string): Promise<string> {
  try {
    const payload = (await response.clone().json()) as ProblemPayload;
    if (payload.title || payload.detail) {
      return payload.detail || payload.title || fallbackMessage;
    }
  } catch {
    // Fall back to raw text for non-JSON error bodies.
  }
  try {
    const responseText = (await response.text()).trim();
    return responseText || fallbackMessage;
  } catch {
    return fallbackMessage;
  }
}

export async function createUploadSession(
  apiBaseUrl: string,
  accessToken: string,
  file: UploadFileLike,
  options: UploadTransportOptions = {},
): Promise<UploadResponse> {
  const fetchFn = options.fetchFn ?? defaultFetchFn();
  const response = await fetchFn(uploadUrl(apiBaseUrl, "/v1/upload"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({
      original_filename: file.name,
      mime_type: file.type,
      size_bytes: file.size,
    }),
  });
  if (!response.ok) {
    throw new Error(await decodeProblem(response, "Unable to create upload session."));
  }
  return (await response.json()) as UploadResponse;
}

export async function resumeUploadSession(
  apiBaseUrl: string,
  accessToken: string,
  uploadId: string,
  options: UploadTransportOptions = {},
): Promise<UploadResumeResponse> {
  const fetchFn = options.fetchFn ?? defaultFetchFn();
  const response = await fetchFn(uploadUrl(apiBaseUrl, `/v1/upload/${uploadId}/resume`), {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
  if (!response.ok) {
    throw new Error(await decodeProblem(response, "Unable to resume upload."));
  }
  return (await response.json()) as UploadResumeResponse;
}

export async function finalizeUpload(
  apiBaseUrl: string,
  accessToken: string,
  session: UploadResponse,
  file: UploadFileLike,
  options: UploadTransportOptions = {},
): Promise<UploadResponse> {
  const fetchFn = options.fetchFn ?? defaultFetchFn();
  const response = await fetchFn(uploadUrl(apiBaseUrl, `/v1/upload/${session.upload_id}`), {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({
      size_bytes: file.size,
    }),
  });
  if (!response.ok) {
    const message = await decodeProblem(response, "Unable to finalize upload.");
    if (response.status === 409) {
      throw new UploadInterruptedError(message, 0);
    }
    throw new Error(message);
  }
  return (await response.json()) as UploadResponse;
}

export async function uploadRemainingBytes(
  sessionUrl: string,
  file: UploadFileLike,
  nextByteOffset: number,
  onProgress: (progress: UploadProgress) => void,
  options: UploadTransportOptions = {},
): Promise<void> {
  if (nextByteOffset >= file.size) {
    return;
  }
  const uploadSlice = file.slice(nextByteOffset);
  const xhrFactory = options.xhrFactory ?? defaultXhrFactory;
  const now = options.now ?? Date.now;
  await new Promise<void>((resolve, reject) => {
    const request = xhrFactory();
    const startedAt = now();
    request.open("PUT", sessionUrl, true);
    request.setRequestHeader("Content-Type", file.type || "application/octet-stream");
    request.setRequestHeader("Content-Range", buildContentRange(nextByteOffset, uploadSlice.size, file.size));
    request.upload.onprogress = (event) => {
      if (!event.lengthComputable) return;
      const confirmedBytes = Math.min(nextByteOffset + event.loaded, file.size);
      onProgress({
        confirmedBytes,
        etaSeconds: estimateEtaSeconds(startedAt, event.loaded, uploadSlice.size, now),
      });
    };
    request.onload = () => {
      if (request.status >= 200 && request.status < 300) {
        onProgress({ confirmedBytes: file.size, etaSeconds: 0 });
        resolve();
        return;
      }
      if (request.status === 308) {
        const confirmedBytes = parseCommittedRangeHeader(request.getResponseHeader("Range"));
        reject(new UploadInterruptedError("Upload interrupted. Resume to continue.", confirmedBytes));
        return;
      }
      reject(new Error(`Upload failed with status ${request.status}.`));
    };
    request.onerror = () =>
      reject(new UploadInterruptedError("Upload interrupted. Resume to continue.", nextByteOffset));
    request.send(uploadSlice);
  });
}

export async function executeUploadFlow({
  apiBaseUrl,
  file,
  resumeExisting,
  existingSession,
  dependencies,
  handlers,
}: UploadFlowParams): Promise<void> {
  const createSession = dependencies.createSession ?? createUploadSession;
  const resumeSession = dependencies.resumeSession ?? resumeUploadSession;
  const uploadBytes = dependencies.uploadBytes ?? uploadRemainingBytes;
  const finalizeSession = dependencies.finalizeSession ?? finalizeUpload;
  const transportOptions = dependencies.transportOptions ?? {};

  handlers.setError("");
  let accessToken = "";
  let activeSession: UploadResponse | null = resumeExisting ? existingSession : null;
  try {
    accessToken = await dependencies.getAccessToken();
    const session =
      resumeExisting && existingSession
        ? existingSession
        : await createSession(apiBaseUrl, accessToken, file, transportOptions);
    activeSession = session;
    handlers.setUploadSession(session);

    const resumeState = await resumeSession(apiBaseUrl, accessToken, session.upload_id, transportOptions);
    activeSession = mergeUploadSessionWithResume(session, resumeState);
    handlers.setUploadSession(activeSession);
    handlers.setStatus(activeSession.status);
    handlers.setProgress(progressFromBytes(resumeState.next_byte_offset, file));
    handlers.setEtaSeconds(0);
    handlers.setCanResume(!resumeState.upload_complete);

    if (!resumeState.upload_complete) {
      await uploadBytes(
        activeSession.resumable_session_url,
        file,
        resumeState.next_byte_offset,
        ({ confirmedBytes, etaSeconds }) => {
          handlers.setProgress(progressFromBytes(confirmedBytes, file));
          handlers.setEtaSeconds(etaSeconds);
          handlers.setStatus("uploading");
        },
        transportOptions,
      );
    }

    const completed = await finalizeSession(apiBaseUrl, accessToken, activeSession, file, transportOptions);
    handlers.setUploadSession(completed);
    handlers.setStatus(completed.status);
    handlers.setProgress(100);
    handlers.setEtaSeconds(0);
    handlers.setCanResume(false);
  } catch (caught) {
    if (caught instanceof UploadInterruptedError && activeSession) {
      handlers.setProgress(progressFromBytes(caught.confirmedBytes, file));
      try {
        const token = accessToken || (await dependencies.getAccessToken());
        const resumeState = await resumeSession(apiBaseUrl, token, activeSession.upload_id, transportOptions);
        activeSession = mergeUploadSessionWithResume(activeSession, resumeState);
        handlers.setUploadSession(activeSession);
        handlers.setStatus(activeSession.status);
        handlers.setProgress(progressFromBytes(resumeState.next_byte_offset, file));
        handlers.setEtaSeconds(0);
        if (resumeState.upload_complete) {
          const completed = await finalizeSession(apiBaseUrl, token, activeSession, file, transportOptions);
          handlers.setUploadSession(completed);
          handlers.setStatus(completed.status);
          handlers.setProgress(100);
          handlers.setEtaSeconds(0);
          handlers.setCanResume(false);
          handlers.setError("");
          return;
        }
      } catch (resumeError) {
        console.error("Failed to resume upload after interruption.", resumeError);
        handlers.setStatus("uploading");
      }
      handlers.setCanResume(true);
    } else {
      handlers.setStatus("failed");
      handlers.setCanResume(false);
    }
    handlers.setError(errorMessage(caught, "Upload failed."));
  }
}
