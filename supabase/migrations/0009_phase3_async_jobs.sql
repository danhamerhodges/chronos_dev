-- Maps to: ENG-003, ENG-011, ENG-012

ALTER TABLE public.media_jobs
  ADD COLUMN IF NOT EXISTS plan_tier TEXT NOT NULL DEFAULT 'hobbyist',
  ADD COLUMN IF NOT EXISTS source_asset_checksum TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS fidelity_tier TEXT NOT NULL DEFAULT 'Restore',
  ADD COLUMN IF NOT EXISTS processing_mode TEXT NOT NULL DEFAULT 'balanced',
  ADD COLUMN IF NOT EXISTS config JSONB NOT NULL DEFAULT '{}'::JSONB,
  ADD COLUMN IF NOT EXISTS estimated_duration_seconds INTEGER NOT NULL DEFAULT 60,
  ADD COLUMN IF NOT EXISTS segment_duration_seconds INTEGER NOT NULL DEFAULT 10,
  ADD COLUMN IF NOT EXISTS segment_count INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS completed_segment_count INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS failed_segment_count INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS progress_percent NUMERIC(5, 2) NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS eta_seconds INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS current_operation TEXT NOT NULL DEFAULT 'Queued for processing',
  ADD COLUMN IF NOT EXISTS progress_topic TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS result_uri TEXT,
  ADD COLUMN IF NOT EXISTS failed_segments JSONB NOT NULL DEFAULT '[]'::JSONB,
  ADD COLUMN IF NOT EXISTS warnings JSONB NOT NULL DEFAULT '[]'::JSONB,
  ADD COLUMN IF NOT EXISTS last_error TEXT,
  ADD COLUMN IF NOT EXISTS queued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS cancel_requested_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

ALTER TABLE public.media_jobs
  DROP CONSTRAINT IF EXISTS media_jobs_status_check;

ALTER TABLE public.media_jobs
  ADD CONSTRAINT media_jobs_status_check
  CHECK (status IN ('queued', 'processing', 'completed', 'failed', 'partial', 'cancel_requested', 'cancelled'));

CREATE TABLE IF NOT EXISTS public.job_segments (
  id UUID PRIMARY KEY,
  job_id UUID NOT NULL REFERENCES public.media_jobs (id) ON DELETE CASCADE,
  external_job_id TEXT NOT NULL,
  owner_user_id UUID NOT NULL,
  external_user_id TEXT NOT NULL,
  segment_index INTEGER NOT NULL,
  segment_start_seconds INTEGER NOT NULL,
  segment_end_seconds INTEGER NOT NULL,
  segment_duration_seconds INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',
  attempt_count INTEGER NOT NULL DEFAULT 0,
  idempotency_key TEXT NOT NULL,
  last_error_classification TEXT,
  retry_backoffs_seconds JSONB NOT NULL DEFAULT '[]'::JSONB,
  output_uri TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT job_segments_unique_job_index UNIQUE (job_id, segment_index),
  CONSTRAINT job_segments_status_check CHECK (status IN ('queued', 'processing', 'completed', 'failed', 'cancelled'))
);

CREATE TABLE IF NOT EXISTS public.webhook_subscriptions (
  id UUID PRIMARY KEY,
  owner_user_id UUID NOT NULL,
  external_user_id TEXT NOT NULL,
  webhook_url TEXT NOT NULL,
  event_types TEXT[] NOT NULL DEFAULT '{}'::TEXT[],
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_webhook_subscriptions_owner_url
  ON public.webhook_subscriptions (external_user_id, webhook_url);

CREATE INDEX IF NOT EXISTS idx_media_jobs_owner_created
  ON public.media_jobs (external_user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_media_jobs_progress_topic
  ON public.media_jobs (progress_topic);

CREATE INDEX IF NOT EXISTS idx_job_segments_job_segment
  ON public.job_segments (external_job_id, segment_index);

CREATE INDEX IF NOT EXISTS idx_job_segments_owner_status
  ON public.job_segments (external_user_id, status);
