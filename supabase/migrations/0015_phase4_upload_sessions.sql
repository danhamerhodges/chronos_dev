-- Maps to: FR-001, ENG-016

CREATE TABLE IF NOT EXISTS public.upload_sessions (
  id UUID PRIMARY KEY,
  owner_user_id UUID NOT NULL,
  external_user_id TEXT NOT NULL,
  external_upload_id TEXT NOT NULL UNIQUE,
  org_id TEXT NOT NULL,
  original_filename TEXT NOT NULL,
  mime_type TEXT NOT NULL,
  size_bytes BIGINT NOT NULL,
  checksum_sha256 TEXT,
  bucket_name TEXT NOT NULL,
  object_path TEXT NOT NULL,
  media_uri TEXT NOT NULL,
  resumable_session_url TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT upload_sessions_status_check CHECK (status IN ('pending', 'uploading', 'completed', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_upload_sessions_owner_created
  ON public.upload_sessions (external_user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_upload_sessions_owner_status
  ON public.upload_sessions (external_user_id, status);

ALTER TABLE public.gcs_object_pointers
  ADD COLUMN IF NOT EXISTS external_user_id TEXT,
  ADD COLUMN IF NOT EXISTS external_upload_id TEXT,
  ADD COLUMN IF NOT EXISTS org_id TEXT NOT NULL DEFAULT 'org-default',
  ADD COLUMN IF NOT EXISTS original_filename TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS mime_type TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS size_bytes BIGINT NOT NULL DEFAULT 0;

CREATE UNIQUE INDEX IF NOT EXISTS idx_gcs_object_pointers_external_upload_id
  ON public.gcs_object_pointers (external_upload_id);
