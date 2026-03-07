-- Maps to: ENG-010, SEC-013

ALTER TABLE public.job_manifests ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS job_manifests_owner_select ON public.job_manifests;
CREATE POLICY job_manifests_owner_select
ON public.job_manifests
FOR SELECT
USING (
  EXISTS (
    SELECT 1
    FROM public.media_jobs
    WHERE public.media_jobs.id = public.job_manifests.job_id
      AND public.media_jobs.owner_user_id = auth.uid()
  )
);
