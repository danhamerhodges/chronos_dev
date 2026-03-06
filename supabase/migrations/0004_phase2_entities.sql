-- Maps to: ENG-001, ENG-002, ENG-004, FR-002, NFR-007, SEC-009

ALTER TABLE public.user_profiles
  ADD COLUMN IF NOT EXISTS external_user_id TEXT UNIQUE,
  ADD COLUMN IF NOT EXISTS plan_tier TEXT NOT NULL DEFAULT 'hobbyist',
  ADD COLUMN IF NOT EXISTS org_id TEXT NOT NULL DEFAULT 'org-default',
  ADD COLUMN IF NOT EXISTS display_name TEXT,
  ADD COLUMN IF NOT EXISTS avatar_url TEXT,
  ADD COLUMN IF NOT EXISTS preferences JSONB NOT NULL DEFAULT '{}'::JSONB,
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE TABLE IF NOT EXISTS public.media_jobs (
  id UUID PRIMARY KEY,
  owner_user_id UUID NOT NULL,
  external_user_id TEXT NOT NULL,
  external_job_id TEXT NOT NULL UNIQUE,
  org_id TEXT NOT NULL,
  media_uri TEXT NOT NULL,
  original_filename TEXT NOT NULL DEFAULT '',
  mime_type TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'queued',
  era_profile JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.era_detections (
  id UUID PRIMARY KEY,
  job_id UUID NOT NULL,
  external_job_id TEXT NOT NULL,
  era_label TEXT NOT NULL,
  confidence NUMERIC(4, 3) NOT NULL,
  forensic_markers JSONB NOT NULL DEFAULT '{}'::JSONB,
  top_candidates JSONB NOT NULL DEFAULT '[]'::JSONB,
  manual_confirmation_required BOOLEAN NOT NULL DEFAULT FALSE,
  overridden_by_user BOOLEAN NOT NULL DEFAULT FALSE,
  override_reason TEXT,
  source TEXT NOT NULL,
  model_version TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  raw_response_gcs_uri TEXT,
  created_by UUID,
  external_created_by TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT era_detections_job_fk FOREIGN KEY (job_id) REFERENCES public.media_jobs (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS public.user_usage_monthly (
  id UUID PRIMARY KEY,
  owner_user_id UUID NOT NULL,
  external_user_id TEXT NOT NULL,
  billing_month DATE NOT NULL,
  plan_tier TEXT NOT NULL,
  used_minutes INTEGER NOT NULL DEFAULT 0,
  monthly_limit_minutes INTEGER NOT NULL DEFAULT 0,
  estimated_next_job_minutes INTEGER NOT NULL DEFAULT 0,
  approved_overage_minutes INTEGER NOT NULL DEFAULT 0,
  approval_scope TEXT,
  threshold_alerts INTEGER[] NOT NULL DEFAULT '{}'::INTEGER[],
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.org_log_settings (
  org_id TEXT PRIMARY KEY,
  retention_days INTEGER NOT NULL,
  redaction_mode TEXT NOT NULL,
  categories JSONB NOT NULL DEFAULT '[]'::JSONB,
  export_targets JSONB NOT NULL DEFAULT '[]'::JSONB,
  updated_by UUID,
  external_updated_by TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.log_deletion_requests (
  id UUID PRIMARY KEY,
  owner_user_id UUID NOT NULL,
  external_user_id TEXT NOT NULL,
  categories JSONB NOT NULL DEFAULT '[]'::JSONB,
  date_from DATE NOT NULL,
  date_to DATE NOT NULL,
  reason TEXT,
  status TEXT NOT NULL DEFAULT 'queued',
  deletion_proof_id UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.log_deletion_proofs (
  id UUID PRIMARY KEY,
  deletion_request_id UUID NOT NULL,
  owner_user_id UUID NOT NULL,
  external_user_id TEXT NOT NULL,
  deleted_entries INTEGER NOT NULL DEFAULT 0,
  deleted_categories JSONB NOT NULL DEFAULT '[]'::JSONB,
  generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT log_deletion_proofs_request_fk FOREIGN KEY (deletion_request_id) REFERENCES public.log_deletion_requests (id) ON DELETE CASCADE
);

ALTER TABLE public.media_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.era_detections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_usage_monthly ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.org_log_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.log_deletion_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.log_deletion_proofs ENABLE ROW LEVEL SECURITY;

CREATE POLICY media_jobs_owner_access
ON public.media_jobs
FOR ALL
USING (auth.uid() = owner_user_id)
WITH CHECK (auth.uid() = owner_user_id);

CREATE POLICY era_detections_owner_access
ON public.era_detections
FOR SELECT
USING (
  EXISTS (
    SELECT 1
    FROM public.media_jobs
    WHERE public.media_jobs.id = public.era_detections.job_id
      AND public.media_jobs.owner_user_id = auth.uid()
  )
);

CREATE POLICY usage_owner_access
ON public.user_usage_monthly
FOR ALL
USING (auth.uid() = owner_user_id)
WITH CHECK (auth.uid() = owner_user_id);

CREATE POLICY deletion_requests_owner_access
ON public.log_deletion_requests
FOR ALL
USING (auth.uid() = owner_user_id)
WITH CHECK (auth.uid() = owner_user_id);

CREATE POLICY deletion_proofs_owner_access
ON public.log_deletion_proofs
FOR SELECT
USING (auth.uid() = owner_user_id);
