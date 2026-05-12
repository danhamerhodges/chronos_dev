-- Maps to: SEC-003

ALTER TABLE public.gcs_object_pointers
  ADD COLUMN IF NOT EXISTS classification_label TEXT NOT NULL DEFAULT 'Confidential',
  ADD COLUMN IF NOT EXISTS retention_days INTEGER,
  ADD COLUMN IF NOT EXISTS retention_expires_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS classification_policy_version TEXT NOT NULL DEFAULT 'v0-backfill';

ALTER TABLE public.job_manifests
  ADD COLUMN IF NOT EXISTS classification_label TEXT NOT NULL DEFAULT 'Internal',
  ADD COLUMN IF NOT EXISTS retention_days INTEGER,
  ADD COLUMN IF NOT EXISTS retention_expires_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS classification_policy_version TEXT NOT NULL DEFAULT 'v0-backfill';

ALTER TABLE public.job_export_packages
  ADD COLUMN IF NOT EXISTS classification_label TEXT NOT NULL DEFAULT 'Confidential',
  ADD COLUMN IF NOT EXISTS retention_days INTEGER,
  ADD COLUMN IF NOT EXISTS retention_expires_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS classification_policy_version TEXT NOT NULL DEFAULT 'v0-backfill';

ALTER TABLE public.job_deletion_proofs
  ADD COLUMN IF NOT EXISTS classification_label TEXT NOT NULL DEFAULT 'Compliance',
  ADD COLUMN IF NOT EXISTS retention_days INTEGER,
  ADD COLUMN IF NOT EXISTS retention_expires_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS classification_policy_version TEXT NOT NULL DEFAULT 'v0-backfill';

ALTER TABLE public.gcs_object_pointers
  DROP CONSTRAINT IF EXISTS gcs_object_pointers_classification_label_check,
  ADD CONSTRAINT gcs_object_pointers_classification_label_check
  CHECK (classification_label IN ('Confidential', 'Internal', 'Compliance', 'Public'));

ALTER TABLE public.job_manifests
  DROP CONSTRAINT IF EXISTS job_manifests_classification_label_check,
  ADD CONSTRAINT job_manifests_classification_label_check
  CHECK (classification_label IN ('Confidential', 'Internal', 'Compliance', 'Public'));

ALTER TABLE public.job_export_packages
  DROP CONSTRAINT IF EXISTS job_export_packages_classification_label_check,
  ADD CONSTRAINT job_export_packages_classification_label_check
  CHECK (classification_label IN ('Confidential', 'Internal', 'Compliance', 'Public'));

ALTER TABLE public.job_deletion_proofs
  DROP CONSTRAINT IF EXISTS job_deletion_proofs_classification_label_check,
  ADD CONSTRAINT job_deletion_proofs_classification_label_check
  CHECK (classification_label IN ('Confidential', 'Internal', 'Compliance', 'Public'));

CREATE TABLE IF NOT EXISTS public.data_classification_audit_events (
  id UUID PRIMARY KEY,
  artifact_type TEXT NOT NULL,
  classification_label TEXT NOT NULL,
  object_uri TEXT NOT NULL,
  object_hash TEXT NOT NULL,
  retention_days INTEGER,
  retention_expires_at TIMESTAMPTZ,
  policy_version TEXT NOT NULL,
  event_type TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT data_classification_audit_artifact_type_check
    CHECK (artifact_type IN (
      'source_upload',
      'processed_output',
      'transformation_manifest',
      'export_package',
      'deletion_proof'
    )),
  CONSTRAINT data_classification_audit_label_check
    CHECK (classification_label IN ('Confidential', 'Internal', 'Compliance', 'Public')),
  CONSTRAINT data_classification_audit_event_type_check
    CHECK (event_type IN (
      'classification_assigned',
      'gcs_metadata_patched',
      'gcs_metadata_patch_skipped',
      'gcs_metadata_patch_failed'
    ))
);

CREATE INDEX IF NOT EXISTS idx_data_classification_audit_object_hash
  ON public.data_classification_audit_events (object_hash, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_data_classification_audit_type_label
  ON public.data_classification_audit_events (artifact_type, classification_label, created_at DESC);

ALTER TABLE public.data_classification_audit_events ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.data_classification_audit_events FROM anon, authenticated;
