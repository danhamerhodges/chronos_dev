import React, { useState } from "react";

import { Button } from "./components/Button";
import { Card } from "./components/Card";
import { InputField } from "./components/InputField";
import { ProgressBar } from "./components/ProgressBar";
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

export function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadSession, setUploadSession] = useState<UploadResponse | null>(null);
  const [progress, setProgress] = useState(0);
  const [etaSeconds, setEtaSeconds] = useState(0);
  const [status, setStatus] = useState<UploadResponse["status"]>("pending");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [canResume, setCanResume] = useState(false);

  async function runUpload(resumeExisting: boolean): Promise<void> {
    if (!selectedFile) {
      setError("Choose a file before starting an upload.");
      return;
    }
    if (!isSupportedUploadFormat(selectedFile.name, selectedFile.type)) {
      setError("Supported formats are MP4, AVI, MOV, MKV, TIFF, PNG, and JPEG.");
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
          setError,
        },
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <main
      style={{
        minHeight: "100vh",
        background:
          "radial-gradient(circle at top left, rgba(22,119,179,0.18), transparent 32%), linear-gradient(180deg, #f5f8fb 0%, #e9f0f7 100%)",
        color: "var(--color-text-primary)",
        fontFamily: "var(--font-family-base)",
        padding: "var(--spacing-xl)",
      }}
    >
      <div style={{ maxWidth: 760, margin: "0 auto" }}>
        <Card title="Packet 4A Upload Shell">
          <p style={{ color: "var(--color-text-muted)", marginTop: 0 }}>
            Start a resumable upload, track browser-side progress, and finalize the object pointer for later job launch.
          </p>
          <div style={{ display: "grid", gap: "var(--spacing-md)" }}>
            <label>
              <div style={{ marginBottom: "var(--spacing-xs)" }}>Media file</div>
              <InputField
                type="file"
                accept=".mp4,.avi,.mov,.mkv,.tif,.tiff,.png,.jpg,.jpeg"
                onChange={(event) => {
                  const file = event.target.files?.[0] ?? null;
                  setSelectedFile(file);
                  setUploadSession(null);
                  setProgress(0);
                  setEtaSeconds(0);
                  setStatus("pending");
                  setError("");
                  setCanResume(false);
                }}
              />
            </label>
            <div style={{ display: "flex", gap: "var(--spacing-sm)", flexWrap: "wrap" }}>
              <Button onClick={() => void runUpload(false)} disabled={busy || !selectedFile}>
                {busy ? "Uploading..." : "Start Upload"}
              </Button>
              <Button variant="secondary" onClick={() => void runUpload(true)} disabled={busy || !selectedFile || !canResume}>
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
            {error ? (
              <div
                role="alert"
                style={{
                  borderRadius: "var(--radius-md)",
                  background: "#fff0f0",
                  color: "#8a1f1f",
                  padding: "var(--spacing-sm) var(--spacing-md)",
                }}
              >
                {error}
              </div>
            ) : null}
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
      </div>
    </main>
  );
}
