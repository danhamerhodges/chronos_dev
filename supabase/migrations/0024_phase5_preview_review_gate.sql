-- Maps to: FR-006, ENG-016

ALTER TABLE public.preview_sessions
  ADD COLUMN IF NOT EXISTS review_status TEXT NOT NULL DEFAULT 'pending',
  ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS launch_status TEXT NOT NULL DEFAULT 'not_launched',
  ADD COLUMN IF NOT EXISTS launched_job_id UUID REFERENCES public.media_jobs (id),
  ADD COLUMN IF NOT EXISTS launched_external_job_id TEXT,
  ADD COLUMN IF NOT EXISTS launched_at TIMESTAMPTZ;

ALTER TABLE public.preview_sessions
  DROP CONSTRAINT IF EXISTS preview_sessions_review_status_check,
  ADD CONSTRAINT preview_sessions_review_status_check
    CHECK (review_status IN ('pending', 'approved', 'rejected'));

ALTER TABLE public.preview_sessions
  DROP CONSTRAINT IF EXISTS preview_sessions_launch_status_check,
  ADD CONSTRAINT preview_sessions_launch_status_check
    CHECK (launch_status IN ('not_launched', 'launch_pending', 'launched'));

CREATE INDEX IF NOT EXISTS idx_preview_sessions_owner_launch_status
  ON public.preview_sessions (external_user_id, launch_status, updated_at DESC);
