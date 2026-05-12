-- Maps to: SEC-005

CREATE TABLE IF NOT EXISTS public.org_data_retention_settings (
  org_id TEXT PRIMARY KEY,
  plan_tier TEXT NOT NULL DEFAULT 'museum',
  manifest_retention_days INTEGER,
  manifest_redaction_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  updated_by TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT org_data_retention_settings_museum_only_check
    CHECK (plan_tier = 'museum'),
  CONSTRAINT org_data_retention_settings_manifest_retention_days_check
    CHECK (
      manifest_retention_days IS NULL
      OR manifest_retention_days IN (0, 90, 365, 1825)
    )
);

ALTER TABLE public.org_data_retention_settings ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.org_data_retention_settings FROM anon;
REVOKE ALL ON TABLE public.org_data_retention_settings FROM authenticated;

ALTER TABLE public.job_manifests
  ADD COLUMN IF NOT EXISTS redacted_payload JSONB,
  ADD COLUMN IF NOT EXISTS redacted_manifest_uri TEXT,
  ADD COLUMN IF NOT EXISTS redacted_manifest_sha256 TEXT,
  ADD COLUMN IF NOT EXISTS redacted_size_bytes INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS manifest_redaction_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS retention_class TEXT NOT NULL DEFAULT 'v0-backfill',
  ADD COLUMN IF NOT EXISTS retention_policy_source TEXT NOT NULL DEFAULT 'v0-backfill',
  ADD COLUMN IF NOT EXISTS retention_deleted_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS retention_delete_status TEXT,
  ADD COLUMN IF NOT EXISTS retention_delete_attempted_at TIMESTAMPTZ;

ALTER TABLE public.job_manifests
  DROP CONSTRAINT IF EXISTS job_manifests_retention_class_check,
  ADD CONSTRAINT job_manifests_retention_class_check
  CHECK (retention_class IN ('0d', '7d', '90d', '365d', '1825d', 'indefinite', 'v0-backfill'));

ALTER TABLE public.job_manifests
  DROP CONSTRAINT IF EXISTS job_manifests_retention_delete_status_check,
  ADD CONSTRAINT job_manifests_retention_delete_status_check
  CHECK (retention_delete_status IS NULL OR retention_delete_status IN ('pending', 'deleted', 'failed'));

CREATE INDEX IF NOT EXISTS idx_job_manifests_retention_expiry
  ON public.job_manifests (retention_expires_at)
  WHERE retention_deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_job_manifests_retention_class
  ON public.job_manifests (retention_class, generated_at DESC);
