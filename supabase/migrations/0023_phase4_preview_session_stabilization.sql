-- Maps to: ENG-014, ENG-016

ALTER TABLE public.preview_sessions
  ADD COLUMN IF NOT EXISTS configured_at_snapshot TEXT,
  ADD COLUMN IF NOT EXISTS configuration_cache_fingerprint TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_preview_sessions_owner_upload_snapshot
  ON public.preview_sessions (external_user_id, external_upload_id, configured_at_snapshot)
  WHERE configured_at_snapshot IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_preview_sessions_owner_reuse
  ON public.preview_sessions (external_user_id, source_asset_checksum, configuration_cache_fingerprint, created_at DESC)
  WHERE deleted_at IS NULL AND configuration_cache_fingerprint IS NOT NULL;
