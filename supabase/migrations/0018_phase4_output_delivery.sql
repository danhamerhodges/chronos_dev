-- Maps to: FR-005, ENG-015, ENG-016

CREATE TABLE IF NOT EXISTS public.job_deletion_proofs (
  id UUID PRIMARY KEY,
  job_id UUID NOT NULL REFERENCES public.media_jobs (id) ON DELETE CASCADE,
  external_job_id TEXT NOT NULL,
  owner_user_id UUID NOT NULL,
  external_user_id TEXT NOT NULL,
  external_deletion_proof_id TEXT NOT NULL UNIQUE,
  generated_at TIMESTAMPTZ NOT NULL,
  signature_algorithm TEXT NOT NULL,
  signature TEXT NOT NULL,
  proof_sha256 TEXT NOT NULL,
  verification_summary JSONB NOT NULL DEFAULT '{}'::JSONB,
  proof_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
  pdf_uri TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_job_deletion_proofs_external_job
  ON public.job_deletion_proofs (external_job_id);

CREATE INDEX IF NOT EXISTS idx_job_deletion_proofs_external_user
  ON public.job_deletion_proofs (external_user_id, generated_at DESC);

CREATE TABLE IF NOT EXISTS public.job_export_packages (
  id UUID PRIMARY KEY,
  job_id UUID NOT NULL REFERENCES public.media_jobs (id) ON DELETE CASCADE,
  external_job_id TEXT NOT NULL,
  owner_user_id UUID NOT NULL,
  external_user_id TEXT NOT NULL,
  variant TEXT NOT NULL,
  package_uri TEXT NOT NULL,
  file_name TEXT NOT NULL,
  size_bytes BIGINT NOT NULL DEFAULT 0,
  sha256 TEXT NOT NULL,
  package_contents JSONB NOT NULL DEFAULT '[]'::JSONB,
  artifact_metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
  encoding_metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
  external_deletion_proof_id TEXT NOT NULL,
  available_until TIMESTAMPTZ NOT NULL,
  generated_at TIMESTAMPTZ NOT NULL,
  deleted_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT job_export_packages_variant_check CHECK (variant IN ('av1', 'h264')),
  CONSTRAINT job_export_packages_job_variant_unique UNIQUE (job_id, variant),
  CONSTRAINT job_export_packages_deletion_proof_fk
    FOREIGN KEY (external_deletion_proof_id)
    REFERENCES public.job_deletion_proofs (external_deletion_proof_id)
    ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_job_export_packages_external_job
  ON public.job_export_packages (external_job_id, variant);

CREATE INDEX IF NOT EXISTS idx_job_export_packages_external_user
  ON public.job_export_packages (external_user_id, generated_at DESC);
