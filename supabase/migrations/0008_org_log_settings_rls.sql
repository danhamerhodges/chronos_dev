-- Maps to: ENG-002, SEC-009, SEC-013

DROP POLICY IF EXISTS org_log_settings_same_org_read ON public.org_log_settings;
CREATE POLICY org_log_settings_same_org_read
ON public.org_log_settings
FOR SELECT
USING (
  EXISTS (
    SELECT 1
    FROM public.user_profiles
    WHERE public.user_profiles.id = auth.uid()
      AND public.user_profiles.org_id = public.org_log_settings.org_id
      AND public.user_profiles.role IN ('admin', 'analyst')
  )
);

DROP POLICY IF EXISTS org_log_settings_admin_insert ON public.org_log_settings;
CREATE POLICY org_log_settings_admin_insert
ON public.org_log_settings
FOR INSERT
WITH CHECK (
  EXISTS (
    SELECT 1
    FROM public.user_profiles
    WHERE public.user_profiles.id = auth.uid()
      AND public.user_profiles.org_id = public.org_log_settings.org_id
      AND public.user_profiles.role = 'admin'
  )
);

DROP POLICY IF EXISTS org_log_settings_admin_update ON public.org_log_settings;
CREATE POLICY org_log_settings_admin_update
ON public.org_log_settings
FOR UPDATE
USING (
  EXISTS (
    SELECT 1
    FROM public.user_profiles
    WHERE public.user_profiles.id = auth.uid()
      AND public.user_profiles.org_id = public.org_log_settings.org_id
      AND public.user_profiles.role = 'admin'
  )
)
WITH CHECK (
  EXISTS (
    SELECT 1
    FROM public.user_profiles
    WHERE public.user_profiles.id = auth.uid()
      AND public.user_profiles.org_id = public.org_log_settings.org_id
      AND public.user_profiles.role = 'admin'
  )
);
