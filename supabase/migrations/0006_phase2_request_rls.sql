-- Maps to: ENG-002, ENG-004, FR-002, NFR-007, SEC-013, SEC-009

DROP POLICY IF EXISTS user_profiles_owner_insert ON public.user_profiles;
CREATE POLICY user_profiles_owner_insert
ON public.user_profiles
FOR INSERT
WITH CHECK (auth.uid() = id);

DROP POLICY IF EXISTS user_profiles_owner_update ON public.user_profiles;
CREATE POLICY user_profiles_owner_update
ON public.user_profiles
FOR UPDATE
USING (auth.uid() = id)
WITH CHECK (auth.uid() = id);

DROP POLICY IF EXISTS era_detections_owner_insert ON public.era_detections;
CREATE POLICY era_detections_owner_insert
ON public.era_detections
FOR INSERT
WITH CHECK (
  EXISTS (
    SELECT 1
    FROM public.media_jobs
    WHERE public.media_jobs.id = public.era_detections.job_id
      AND public.media_jobs.owner_user_id = auth.uid()
  )
);

DROP POLICY IF EXISTS deletion_proofs_owner_insert ON public.log_deletion_proofs;
CREATE POLICY deletion_proofs_owner_insert
ON public.log_deletion_proofs
FOR INSERT
WITH CHECK (auth.uid() = owner_user_id);
