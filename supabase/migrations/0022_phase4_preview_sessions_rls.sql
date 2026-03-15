-- Maps to: ENG-014, SEC-013

ALTER TABLE public.preview_sessions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS preview_sessions_owner_access ON public.preview_sessions;
CREATE POLICY preview_sessions_owner_access
ON public.preview_sessions
FOR ALL
USING (auth.uid() = owner_user_id)
WITH CHECK (auth.uid() = owner_user_id);
