-- Maps to: ENG-011, ENG-012, SEC-013

ALTER TABLE public.job_segments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.webhook_subscriptions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS job_segments_owner_select ON public.job_segments;
CREATE POLICY job_segments_owner_select
ON public.job_segments
FOR SELECT
USING (
  EXISTS (
    SELECT 1
    FROM public.media_jobs
    WHERE public.media_jobs.id = public.job_segments.job_id
      AND public.media_jobs.owner_user_id = auth.uid()
  )
);

DROP POLICY IF EXISTS job_segments_owner_insert ON public.job_segments;
CREATE POLICY job_segments_owner_insert
ON public.job_segments
FOR INSERT
WITH CHECK (
  auth.uid() = owner_user_id
  AND EXISTS (
    SELECT 1
    FROM public.media_jobs
    WHERE public.media_jobs.id = public.job_segments.job_id
      AND public.media_jobs.owner_user_id = auth.uid()
  )
);

DROP POLICY IF EXISTS job_segments_owner_update ON public.job_segments;
CREATE POLICY job_segments_owner_update
ON public.job_segments
FOR UPDATE
USING (
  EXISTS (
    SELECT 1
    FROM public.media_jobs
    WHERE public.media_jobs.id = public.job_segments.job_id
      AND public.media_jobs.owner_user_id = auth.uid()
  )
)
WITH CHECK (
  EXISTS (
    SELECT 1
    FROM public.media_jobs
    WHERE public.media_jobs.id = public.job_segments.job_id
      AND public.media_jobs.owner_user_id = auth.uid()
  )
);

-- webhook_subscriptions is admin-managed in Packet 3A.
-- No end-user RLS policies are created in this packet; service-role or direct DB access is required.
