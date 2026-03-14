-- Maps to: ENG-013, NFR-003

ALTER TABLE public.media_jobs
  ADD COLUMN IF NOT EXISTS cost_estimate_summary JSONB,
  ADD COLUMN IF NOT EXISTS cost_reconciliation_summary JSONB;
