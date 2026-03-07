-- Maps to: ENG-005, ENG-006, ENG-007, ENG-010, NFR-002

ALTER TABLE public.media_jobs
  ADD COLUMN IF NOT EXISTS effective_fidelity_tier TEXT NOT NULL DEFAULT 'Restore',
  ADD COLUMN IF NOT EXISTS effective_fidelity_profile JSONB NOT NULL DEFAULT '{}'::JSONB,
  ADD COLUMN IF NOT EXISTS reproducibility_mode TEXT NOT NULL DEFAULT 'perceptual_equivalence',
  ADD COLUMN IF NOT EXISTS quality_summary JSONB NOT NULL DEFAULT '{"e_hf":0.0,"s_ls_db":0.0,"t_tc":0.0,"thresholds_met":false}'::JSONB,
  ADD COLUMN IF NOT EXISTS reproducibility_summary JSONB,
  ADD COLUMN IF NOT EXISTS stage_timings JSONB NOT NULL DEFAULT '{"upload_ms":null,"era_detection_ms":null,"processing_ms":null,"encoding_ms":null,"download_ms":null,"total_ms":null}'::JSONB,
  ADD COLUMN IF NOT EXISTS manifest_available BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS manifest_uri TEXT,
  ADD COLUMN IF NOT EXISTS manifest_sha256 TEXT,
  ADD COLUMN IF NOT EXISTS manifest_generated_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS manifest_size_bytes INTEGER NOT NULL DEFAULT 0;

ALTER TABLE public.media_jobs
  DROP CONSTRAINT IF EXISTS media_jobs_reproducibility_mode_check;

ALTER TABLE public.media_jobs
  ADD CONSTRAINT media_jobs_reproducibility_mode_check
  CHECK (reproducibility_mode IN ('perceptual_equivalence', 'deterministic', 'bit_identical'));

ALTER TABLE public.job_segments
  ADD COLUMN IF NOT EXISTS quality_metrics JSONB,
  ADD COLUMN IF NOT EXISTS reproducibility_proof JSONB,
  ADD COLUMN IF NOT EXISTS uncertainty_callouts JSONB NOT NULL DEFAULT '[]'::JSONB;

CREATE TABLE IF NOT EXISTS public.job_manifests (
  id UUID PRIMARY KEY,
  job_id UUID NOT NULL UNIQUE REFERENCES public.media_jobs (id) ON DELETE CASCADE,
  external_job_id TEXT NOT NULL UNIQUE,
  owner_user_id UUID NOT NULL,
  external_user_id TEXT NOT NULL,
  manifest_uri TEXT NOT NULL,
  manifest_sha256 TEXT NOT NULL,
  payload JSONB NOT NULL,
  generated_at TIMESTAMPTZ NOT NULL,
  size_bytes INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_job_manifests_external_job
  ON public.job_manifests (external_job_id);

CREATE INDEX IF NOT EXISTS idx_job_manifests_external_user
  ON public.job_manifests (external_user_id, generated_at DESC);
