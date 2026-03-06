-- Maps to: ENG-002, ENG-004, NFR-007, SEC-009

CREATE INDEX IF NOT EXISTS idx_media_jobs_owner_created_at
ON public.media_jobs (owner_user_id, created_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_media_jobs_external_job_id
ON public.media_jobs (external_job_id);

CREATE INDEX IF NOT EXISTS idx_era_detections_job_created_at
ON public.era_detections (job_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_era_detections_external_job_id_created_at
ON public.era_detections (external_job_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_usage_monthly_owner_billing_month
ON public.user_usage_monthly (owner_user_id, billing_month DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_usage_monthly_external_user_billing_month
ON public.user_usage_monthly (external_user_id, billing_month);

CREATE INDEX IF NOT EXISTS idx_log_deletion_requests_owner_created_at
ON public.log_deletion_requests (owner_user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_log_deletion_requests_status
ON public.log_deletion_requests (status);
