-- Maps to: NFR-006, NFR-012, ENG-016, SEC-013

ALTER TABLE public.billing_accounts
  ADD COLUMN IF NOT EXISTS org_id TEXT,
  ADD COLUMN IF NOT EXISTS stripe_subscription_id TEXT,
  ADD COLUMN IF NOT EXISTS subscription_status TEXT,
  ADD COLUMN IF NOT EXISTS subscription_price_id TEXT,
  ADD COLUMN IF NOT EXISTS subscription_price_usd NUMERIC,
  ADD COLUMN IF NOT EXISTS included_minutes_monthly INTEGER,
  ADD COLUMN IF NOT EXISTS overage_price_id TEXT,
  ADD COLUMN IF NOT EXISTS overage_rate_usd_per_minute NUMERIC,
  ADD COLUMN IF NOT EXISTS museum_quote_id TEXT,
  ADD COLUMN IF NOT EXISTS museum_quote_status TEXT,
  ADD COLUMN IF NOT EXISTS museum_quote_pricing JSONB NOT NULL DEFAULT '{}'::JSONB,
  ADD COLUMN IF NOT EXISTS recent_invoices JSONB NOT NULL DEFAULT '[]'::JSONB,
  ADD COLUMN IF NOT EXISTS last_synced_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

UPDATE public.billing_accounts
SET org_id = public.user_profiles.org_id
FROM public.user_profiles
WHERE public.billing_accounts.owner_user_id = public.user_profiles.id
  AND public.billing_accounts.org_id IS NULL;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM public.billing_accounts
    WHERE org_id IS NULL
  ) THEN
    RAISE EXCEPTION 'billing_accounts org_id backfill has unresolved rows';
  END IF;

  IF EXISTS (
    SELECT 1
    FROM public.billing_accounts
    GROUP BY org_id
    HAVING COUNT(*) > 1
  ) THEN
    RAISE EXCEPTION 'billing_accounts org_id backfill would violate one account per org';
  END IF;
END $$;

ALTER TABLE public.billing_accounts
  ALTER COLUMN org_id SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_billing_accounts_org_id
  ON public.billing_accounts (org_id);

ALTER TABLE public.media_jobs
  ADD COLUMN IF NOT EXISTS billing_pricing_snapshot JSONB NOT NULL DEFAULT '{}'::JSONB;

CREATE TABLE IF NOT EXISTS public.commercial_pricebook_revisions (
  id UUID PRIMARY KEY,
  version TEXT NOT NULL UNIQUE,
  payload JSONB NOT NULL,
  applied_by_user_id TEXT NOT NULL,
  applied_by_org_id TEXT NOT NULL,
  source TEXT NOT NULL,
  change_summary TEXT NOT NULL DEFAULT '',
  activated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  active BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_commercial_pricebook_revisions_single_active
  ON public.commercial_pricebook_revisions (active)
  WHERE active = true;

CREATE TABLE IF NOT EXISTS public.billing_audit_events (
  id UUID PRIMARY KEY,
  org_id TEXT NOT NULL,
  source TEXT NOT NULL,
  event_type TEXT NOT NULL,
  actor_user_id TEXT,
  stripe_event_id TEXT,
  before_summary JSONB NOT NULL DEFAULT '{}'::JSONB,
  after_summary JSONB NOT NULL DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.processed_stripe_events (
  stripe_event_id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL,
  org_id TEXT,
  processing_status TEXT NOT NULL DEFAULT 'claimed',
  summary_metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  processed_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT processed_stripe_events_processing_status_check
    CHECK (processing_status IN ('claimed', 'processed', 'failed'))
);

DROP POLICY IF EXISTS billing_accounts_owner_read ON public.billing_accounts;
DROP POLICY IF EXISTS billing_accounts_org_read ON public.billing_accounts;

CREATE POLICY billing_accounts_org_read
ON public.billing_accounts
FOR SELECT
USING (
  EXISTS (
    SELECT 1
    FROM public.user_profiles
    WHERE public.user_profiles.id = auth.uid()
      AND public.user_profiles.org_id = public.billing_accounts.org_id
  )
);

ALTER TABLE public.commercial_pricebook_revisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.billing_audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.processed_stripe_events ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.commercial_pricebook_revisions FROM anon, authenticated;
REVOKE ALL ON public.billing_audit_events FROM anon, authenticated;
REVOKE ALL ON public.processed_stripe_events FROM anon, authenticated;
