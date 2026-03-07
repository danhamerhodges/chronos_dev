-- Maps to: ENG-008, ENG-009, OPS-003, NFR-002

ALTER TABLE public.media_jobs
  ADD COLUMN IF NOT EXISTS cache_summary JSONB NOT NULL DEFAULT '{"hits":0,"misses":0,"bypassed":0,"degraded":false,"hit_rate":0.0,"saved_gpu_seconds":0}'::JSONB,
  ADD COLUMN IF NOT EXISTS gpu_summary JSONB NOT NULL DEFAULT '{"gpu_type":null,"warm_start":null,"allocation_latency_ms":null,"gpu_runtime_seconds":0,"desired_warm_instances":0,"active_warm_instances":0,"busy_instances":0,"utilization_percent":0.0}'::JSONB,
  ADD COLUMN IF NOT EXISTS cost_summary JSONB NOT NULL DEFAULT '{"gpu_seconds":0,"storage_operations":0,"api_calls":0,"total_cost_usd":0.0}'::JSONB,
  ADD COLUMN IF NOT EXISTS slo_summary JSONB NOT NULL DEFAULT '{"target_total_ms":120000,"actual_total_ms":null,"p95_ratio":null,"compliant":null,"degraded":false,"error_budget_burn_percent":0.0,"museum_sla_applies":false}'::JSONB;

ALTER TABLE public.job_segments
  ADD COLUMN IF NOT EXISTS cache_status TEXT NOT NULL DEFAULT 'miss',
  ADD COLUMN IF NOT EXISTS cache_hit_latency_ms INTEGER,
  ADD COLUMN IF NOT EXISTS cache_namespace TEXT,
  ADD COLUMN IF NOT EXISTS cached_output_uri TEXT,
  ADD COLUMN IF NOT EXISTS gpu_type TEXT,
  ADD COLUMN IF NOT EXISTS allocation_latency_ms INTEGER;

ALTER TABLE public.job_segments
  DROP CONSTRAINT IF EXISTS job_segments_cache_status_check;

ALTER TABLE public.job_segments
  ADD CONSTRAINT job_segments_cache_status_check
  CHECK (cache_status IN ('hit', 'miss', 'bypass'));

CREATE TABLE IF NOT EXISTS public.gpu_worker_leases (
  id UUID PRIMARY KEY,
  worker_id TEXT NOT NULL UNIQUE,
  gpu_type TEXT NOT NULL,
  lease_state TEXT NOT NULL,
  is_warm BOOLEAN NOT NULL DEFAULT TRUE,
  current_job_id TEXT,
  queue_depth_snapshot INTEGER NOT NULL DEFAULT 0,
  metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
  allocated_at TIMESTAMPTZ,
  released_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT gpu_worker_leases_state_check CHECK (lease_state IN ('idle', 'busy', 'released'))
);

CREATE TABLE IF NOT EXISTS public.incident_events (
  id UUID PRIMARY KEY,
  incident_key TEXT NOT NULL UNIQUE,
  severity TEXT NOT NULL,
  incident_state TEXT NOT NULL,
  source_signal TEXT NOT NULL,
  runbook_key TEXT NOT NULL,
  issue_tracker_url TEXT,
  status_page_url TEXT,
  communication_status TEXT NOT NULL DEFAULT 'drafted',
  detection_delay_seconds INTEGER NOT NULL DEFAULT 0,
  resolution_time_seconds INTEGER,
  postmortem_due_at TIMESTAMPTZ,
  metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
  opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  acknowledged_at TIMESTAMPTZ,
  resolved_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT incident_events_severity_check CHECK (severity IN ('P0', 'P1', 'P2', 'P3')),
  CONSTRAINT incident_events_state_check CHECK (incident_state IN ('open', 'acknowledged', 'resolved'))
);

CREATE INDEX IF NOT EXISTS idx_gpu_worker_leases_state
  ON public.gpu_worker_leases (lease_state, gpu_type, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_incident_events_state
  ON public.incident_events (incident_state, severity, opened_at DESC);
