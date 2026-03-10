-- Maps to: FR-001, ENG-016, SEC-013

ALTER TABLE public.upload_sessions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS upload_sessions_owner_access ON public.upload_sessions;
CREATE POLICY upload_sessions_owner_access
ON public.upload_sessions
FOR ALL
USING (auth.uid() = owner_user_id)
WITH CHECK (auth.uid() = owner_user_id);

DROP POLICY IF EXISTS gcs_pointers_owner_read ON public.gcs_object_pointers;
DROP POLICY IF EXISTS gcs_pointers_owner_access ON public.gcs_object_pointers;
CREATE POLICY gcs_pointers_owner_access
ON public.gcs_object_pointers
FOR ALL
USING (auth.uid() = owner_user_id)
WITH CHECK (auth.uid() = owner_user_id);
