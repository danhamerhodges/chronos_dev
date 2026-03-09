/**
 * Maps to:
 * - FR-001
 * - AC-FR-001-03
 * - AC-FR-001-04
 */

import { describe, expect, it } from "vitest";

import {
  UploadInterruptedError,
  buildContentRange,
  createUploadSession,
  finalizeUpload,
  isSupportedUploadFormat,
  mergeUploadSessionWithResume,
  parseCommittedRangeHeader,
  progressPercentFromBytes,
  type UploadRequestLike,
  type UploadResponse,
  type UploadResumeResponse,
  uploadRemainingBytes,
} from "../../web/src/lib/uploadHelpers";

class FakeUploadRequest implements UploadRequestLike {
  status = 0;
  upload = {
    onprogress: null as ((event: { lengthComputable: boolean; loaded: number }) => void) | null,
  };
  onload: (() => void) | null = null;
  onerror: (() => void) | null = null;
  headers = new Map<string, string>();
  responseHeaders = new Map<string, string>();
  body: Blob | null = null;
  method = "";
  url = "";
  onSend: ((request: FakeUploadRequest, body: Blob) => void) | null = null;

  open(method: string, url: string): void {
    this.method = method;
    this.url = url;
  }

  setRequestHeader(name: string, value: string): void {
    this.headers.set(name, value);
  }

  getResponseHeader(name: string): string | null {
    return this.responseHeaders.get(name) ?? null;
  }

  send(body: Blob): void {
    this.body = body;
    this.onSend?.(this, body);
  }
}

function makeFile(
  content = "0123456789",
  name = "archive.mov",
  type = "video/quicktime",
): File {
  return new File([content], name, { type });
}

describe("upload helpers", () => {
  it("parses committed range headers into the next byte offset", () => {
    expect(parseCommittedRangeHeader(undefined)).toBe(0);
    expect(parseCommittedRangeHeader("bytes=0-524287")).toBe(524288);
  });

  it("builds content-range headers for resumed uploads", () => {
    expect(buildContentRange(5, 5, 10)).toBe("bytes 5-9/10");
    expect(buildContentRange(10, 0, 10)).toBe("bytes */10");
  });

  it("matches client-side format validation to backend extension and mime requirements", () => {
    expect(isSupportedUploadFormat("ARCHIVE.MOV", "video/quicktime")).toBe(true);
    expect(isSupportedUploadFormat("archive.mov", "video/mp4")).toBe(false);
  });

  it("merges regenerated session metadata without changing upload identity", () => {
    const session: UploadResponse = {
      upload_id: "upload-1",
      status: "pending",
      original_filename: "archive.mov",
      mime_type: "video/quicktime",
      size_bytes: 1024,
      checksum_sha256: null,
      bucket_name: "chronos-dev",
      object_path: "uploads/user-1/upload-1/archive.mov",
      media_uri: "gs://chronos-dev/uploads/user-1/upload-1/archive.mov",
      resumable_session_url: "https://example.invalid/resumable/original",
      created_at: "2026-03-08T00:00:00+00:00",
      updated_at: "2026-03-08T00:00:00+00:00",
      completed_at: null,
    };
    const resume: UploadResumeResponse = {
      upload_id: "upload-1",
      status: "uploading",
      resumable_session_url: "https://example.invalid/resumable/regenerated",
      next_byte_offset: 512,
      upload_complete: false,
      session_regenerated: true,
      object_path: "uploads/user-1/upload-1/archive.mov",
      media_uri: "gs://chronos-dev/uploads/user-1/upload-1/archive.mov",
    };

    const merged = mergeUploadSessionWithResume(session, resume);

    expect(merged.upload_id).toBe("upload-1");
    expect(merged.status).toBe("uploading");
    expect(merged.resumable_session_url).toBe("https://example.invalid/resumable/regenerated");
  });

  it("preserves confirmed progress when a resume probe returns a known byte offset", () => {
    expect(progressPercentFromBytes(512, 1024)).toBe(50);
    expect(progressPercentFromBytes(1024, 1024)).toBe(100);
  });

  it("uploads the remaining bytes and reports success progress", async () => {
    const request = new FakeUploadRequest();
    const progress: Array<{ confirmedBytes: number; etaSeconds: number }> = [];

    request.onSend = (xhr, body) => {
      xhr.upload.onprogress?.({ lengthComputable: true, loaded: body.size });
      xhr.status = 200;
      xhr.onload?.();
    };

    await expect(
      uploadRemainingBytes(
        "https://example.invalid/resumable/upload",
        makeFile(),
        5,
        (nextProgress) => progress.push(nextProgress),
        { xhrFactory: () => request, now: () => 1_000 },
      ),
    ).resolves.toBeUndefined();

    expect(request.method).toBe("PUT");
    expect(request.headers.get("Content-Range")).toBe("bytes 5-9/10");
    expect(progress.at(-1)?.confirmedBytes).toBe(10);
  });

  it("turns a 308 response into a retryable interruption with the committed range", async () => {
    const request = new FakeUploadRequest();

    request.onSend = (xhr) => {
      xhr.status = 308;
      xhr.responseHeaders.set("Range", "bytes=0-4");
      xhr.onload?.();
    };

    await expect(
      uploadRemainingBytes(
        "https://example.invalid/resumable/upload",
        makeFile(),
        0,
        () => undefined,
        { xhrFactory: () => request },
      ),
    ).rejects.toMatchObject({
      name: "UploadInterruptedError",
      confirmedBytes: 5,
    });
  });

  it("preserves the last confirmed offset on network interruption", async () => {
    const request = new FakeUploadRequest();

    request.onSend = (xhr) => {
      xhr.onerror?.();
    };

    await expect(
      uploadRemainingBytes(
        "https://example.invalid/resumable/upload",
        makeFile(),
        5,
        () => undefined,
        { xhrFactory: () => request },
      ),
    ).rejects.toMatchObject({
      name: "UploadInterruptedError",
      confirmedBytes: 5,
    });
  });

  it("treats finalize 409 responses as retryable upload interruptions", async () => {
    const session: UploadResponse = {
      upload_id: "upload-1",
      status: "uploading",
      original_filename: "archive.mov",
      mime_type: "video/quicktime",
      size_bytes: 10,
      checksum_sha256: null,
      bucket_name: "chronos-dev",
      object_path: "uploads/user-1/upload-1/archive.mov",
      media_uri: "gs://chronos-dev/uploads/user-1/upload-1/archive.mov",
      resumable_session_url: "https://example.invalid/resumable/upload",
      created_at: "2026-03-08T00:00:00+00:00",
      updated_at: "2026-03-08T00:00:00+00:00",
      completed_at: null,
    };

    const fetchFn = async () =>
      new Response(JSON.stringify({ title: "Upload Finalization Failed" }), {
        status: 409,
        headers: { "Content-Type": "application/json" },
      });

    await expect(
      finalizeUpload("", "access-token", session, makeFile(), { fetchFn }),
    ).rejects.toBeInstanceOf(UploadInterruptedError);
  });

  it("falls back to plain-text error bodies when problem-details JSON is unavailable", async () => {
    const fetchFn = async () =>
      new Response("upstream exploded", {
        status: 500,
        headers: { "Content-Type": "text/plain" },
      });

    await expect(
      createUploadSession("", "access-token", makeFile(), { fetchFn }),
    ).rejects.toThrow("upstream exploded");
  });
});
