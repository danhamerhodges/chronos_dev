/**
 * Maps to:
 * - FR-001
 * - AC-FR-001-03
 * - AC-FR-001-04
 */

import { describe, expect, it, vi } from "vitest";

import {
  UploadInterruptedError,
  executeUploadFlow,
  type UploadFlowHandlers,
  type UploadResponse,
  type UploadStatus,
} from "../../web/src/lib/uploadHelpers";

type FlowState = {
  session: UploadResponse | null;
  status: UploadStatus;
  progress: number;
  etaSeconds: number;
  canResume: boolean;
  error: string;
};

function makeFile(content = "0123456789"): File {
  return new File([content], "archive.mov", { type: "video/quicktime" });
}

function baseSession(overrides: Partial<UploadResponse> = {}): UploadResponse {
  return {
    upload_id: "upload-1",
    status: "pending",
    original_filename: "archive.mov",
    mime_type: "video/quicktime",
    size_bytes: 10,
    checksum_sha256: null,
    bucket_name: "chronos-dev",
    object_path: "uploads/user-1/upload-1/archive.mov",
    media_uri: "gs://chronos-dev/uploads/user-1/upload-1/archive.mov",
    resumable_session_url: "https://example.invalid/resumable/original",
    created_at: "2026-03-08T00:00:00+00:00",
    updated_at: "2026-03-08T00:00:00+00:00",
    completed_at: null,
    ...overrides,
  };
}

function buildHandlers(state: FlowState): UploadFlowHandlers {
  return {
    setUploadSession: (session) => {
      state.session = session;
    },
    setStatus: (status) => {
      state.status = status;
    },
    setProgress: (progress) => {
      state.progress = progress;
    },
    setEtaSeconds: (etaSeconds) => {
      state.etaSeconds = etaSeconds;
    },
    setCanResume: (canResume) => {
      state.canResume = canResume;
    },
    setError: (error) => {
      state.error = error;
    },
  };
}

describe("upload flow orchestration", () => {
  it("re-probes the upload after interruption and preserves the resumed session url", async () => {
    const file = makeFile();
    const state: FlowState = {
      session: null,
      status: "pending",
      progress: 0,
      etaSeconds: 0,
      canResume: false,
      error: "",
    };

    const createSession = vi.fn(async () => baseSession());
    const resumeSession = vi
      .fn()
      .mockResolvedValueOnce({
        upload_id: "upload-1",
        status: "uploading",
        resumable_session_url: "https://example.invalid/resumable/regenerated",
        next_byte_offset: 0,
        upload_complete: false,
        session_regenerated: true,
        object_path: "uploads/user-1/upload-1/archive.mov",
        media_uri: "gs://chronos-dev/uploads/user-1/upload-1/archive.mov",
      })
      .mockResolvedValueOnce({
        upload_id: "upload-1",
        status: "uploading",
        resumable_session_url: "https://example.invalid/resumable/regenerated",
        next_byte_offset: 5,
        upload_complete: false,
        session_regenerated: false,
        object_path: "uploads/user-1/upload-1/archive.mov",
        media_uri: "gs://chronos-dev/uploads/user-1/upload-1/archive.mov",
      });
    const uploadBytes = vi.fn(async (sessionUrl: string) => {
      expect(sessionUrl).toBe("https://example.invalid/resumable/regenerated");
      throw new UploadInterruptedError("Upload interrupted. Resume to continue.", 5);
    });
    const finalizeSession = vi.fn();

    await executeUploadFlow({
      apiBaseUrl: "https://api.example.test",
      file,
      resumeExisting: false,
      existingSession: null,
      dependencies: {
        getAccessToken: async () => "access-token",
        createSession,
        resumeSession,
        uploadBytes,
        finalizeSession,
      },
      handlers: buildHandlers(state),
    });

    expect(createSession).toHaveBeenCalledTimes(1);
    expect(resumeSession).toHaveBeenCalledTimes(2);
    expect(uploadBytes).toHaveBeenCalledTimes(1);
    expect(finalizeSession).not.toHaveBeenCalled();
    expect(state.session?.resumable_session_url).toBe("https://example.invalid/resumable/regenerated");
    expect(state.status).toBe("uploading");
    expect(state.progress).toBe(50);
    expect(state.canResume).toBe(true);
    expect(state.error).toContain("Upload interrupted");
  });

  it("finalizes the same upload id on a manual resume when the backend reports completion", async () => {
    const file = makeFile();
    const state: FlowState = {
      session: baseSession({ status: "uploading" }),
      status: "uploading",
      progress: 50,
      etaSeconds: 0,
      canResume: true,
      error: "",
    };
    const finalizeResult = baseSession({ status: "completed", completed_at: "2026-03-08T00:10:00+00:00" });
    const createSession = vi.fn();
    const resumeSession = vi.fn().mockResolvedValue({
      upload_id: "upload-1",
      status: "uploading",
      resumable_session_url: "https://example.invalid/resumable/regenerated",
      next_byte_offset: 10,
      upload_complete: true,
      session_regenerated: false,
      object_path: "uploads/user-1/upload-1/archive.mov",
      media_uri: "gs://chronos-dev/uploads/user-1/upload-1/archive.mov",
    });
    const uploadBytes = vi.fn();
    const finalizeSession = vi.fn(async () => finalizeResult);

    await executeUploadFlow({
      apiBaseUrl: "https://api.example.test",
      file,
      resumeExisting: true,
      existingSession: state.session,
      dependencies: {
        getAccessToken: async () => "access-token",
        createSession,
        resumeSession,
        uploadBytes,
        finalizeSession,
      },
      handlers: buildHandlers(state),
    });

    expect(createSession).not.toHaveBeenCalled();
    expect(resumeSession).toHaveBeenCalledTimes(1);
    expect(uploadBytes).not.toHaveBeenCalled();
    expect(finalizeSession).toHaveBeenCalledTimes(1);
    expect(finalizeSession.mock.calls[0]?.[2]).toMatchObject({ upload_id: "upload-1" });
    expect(state.session?.upload_id).toBe("upload-1");
    expect(state.status).toBe("completed");
    expect(state.progress).toBe(100);
    expect(state.canResume).toBe(false);
    expect(state.error).toBe("");
  });

  it("logs resume probe failures instead of swallowing them silently", async () => {
    const file = makeFile();
    const state: FlowState = {
      session: null,
      status: "pending",
      progress: 0,
      etaSeconds: 0,
      canResume: false,
      error: "",
    };

    const createSession = vi.fn(async () => baseSession());
    const resumeSession = vi
      .fn()
      .mockResolvedValueOnce({
        upload_id: "upload-1",
        status: "uploading",
        resumable_session_url: "https://example.invalid/resumable/regenerated",
        next_byte_offset: 0,
        upload_complete: false,
        session_regenerated: true,
        object_path: "uploads/user-1/upload-1/archive.mov",
        media_uri: "gs://chronos-dev/uploads/user-1/upload-1/archive.mov",
      })
      .mockRejectedValueOnce(new Error("resume probe failed"));
    const uploadBytes = vi.fn(async () => {
      throw new UploadInterruptedError("Upload interrupted. Resume to continue.", 5);
    });
    const finalizeSession = vi.fn();
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);

    await executeUploadFlow({
      apiBaseUrl: "https://api.example.test",
      file,
      resumeExisting: false,
      existingSession: null,
      dependencies: {
        getAccessToken: async () => "access-token",
        createSession,
        resumeSession,
        uploadBytes,
        finalizeSession,
      },
      handlers: buildHandlers(state),
    });

    expect(consoleError).toHaveBeenCalledWith(
      "Failed to resume upload after interruption.",
      expect.objectContaining({ message: "resume probe failed" }),
    );
    expect(state.status).toBe("uploading");
    expect(state.canResume).toBe(true);
    consoleError.mockRestore();
  });
});
