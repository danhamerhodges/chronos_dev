-- Maps to: ENG-014, ENG-016

CREATE TABLE IF NOT EXISTS public.preview_sessions (
  id UUID PRIMARY KEY,
  owner_user_id UUID NOT NULL,
  external_user_id TEXT NOT NULL,
  upload_session_id UUID NOT NULL REFERENCES public.upload_sessions (id) ON DELETE CASCADE,
  external_upload_id TEXT NOT NULL,
  external_preview_id TEXT NOT NULL UNIQUE,
  org_id TEXT NOT NULL DEFAULT 'org-default',
  status TEXT NOT NULL,
  configuration_fingerprint TEXT NOT NULL,
  source_asset_checksum TEXT NOT NULL,
  cache_key TEXT NOT NULL,
  job_payload_preview JSONB NOT NULL DEFAULT '{}'::JSONB,
  selection_mode TEXT NOT NULL,
  scene_diversity DOUBLE PRECISION NOT NULL DEFAULT 0,
  keyframe_count INTEGER NOT NULL DEFAULT 0,
  estimated_cost_summary JSONB NOT NULL DEFAULT '{}'::JSONB,
  estimated_processing_time_seconds INTEGER NOT NULL DEFAULT 0,
  keyframes JSONB NOT NULL DEFAULT '[]'::JSONB,
  preview_root_uri TEXT NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  deleted_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT preview_sessions_status_check CHECK (status IN ('ready', 'failed')),
  CONSTRAINT preview_sessions_selection_mode_check CHECK (selection_mode IN ('scene_aware', 'uniform_fallback'))
);

CREATE INDEX IF NOT EXISTS idx_preview_sessions_owner_created
  ON public.preview_sessions (external_user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_preview_sessions_owner_fingerprint
  ON public.preview_sessions (external_user_id, external_upload_id, configuration_fingerprint);

CREATE INDEX IF NOT EXISTS idx_preview_sessions_owner_cache_key
  ON public.preview_sessions (external_user_id, external_upload_id, cache_key, created_at DESC);
