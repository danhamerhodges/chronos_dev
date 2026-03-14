-- Maps to: FR-005, SEC-013

ALTER TABLE public.job_deletion_proofs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.job_export_packages ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS job_deletion_proofs_owner_select ON public.job_deletion_proofs;
CREATE POLICY job_deletion_proofs_owner_select
ON public.job_deletion_proofs
FOR SELECT
USING (
  EXISTS (
    SELECT 1
    FROM public.media_jobs
    WHERE public.media_jobs.id = public.job_deletion_proofs.job_id
      AND public.media_jobs.owner_user_id = auth.uid()
  )
);

DROP POLICY IF EXISTS job_export_packages_owner_select ON public.job_export_packages;
CREATE POLICY job_export_packages_owner_select
ON public.job_export_packages
FOR SELECT
USING (
  EXISTS (
    SELECT 1
    FROM public.media_jobs
    WHERE public.media_jobs.id = public.job_export_packages.job_id
      AND public.media_jobs.owner_user_id = auth.uid()
  )
);
