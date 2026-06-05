-- Maps to: SEC-005, SEC-001, SEC-013

ALTER TABLE public.org_data_retention_settings ENABLE ROW LEVEL SECURITY;

GRANT SELECT, INSERT, UPDATE ON TABLE public.org_data_retention_settings TO authenticated;

DROP POLICY IF EXISTS org_data_retention_settings_same_org_admin_read ON public.org_data_retention_settings;
CREATE POLICY org_data_retention_settings_same_org_admin_read
ON public.org_data_retention_settings
FOR SELECT
TO authenticated
USING (
  plan_tier = 'museum'
  AND EXISTS (
    SELECT 1
    FROM public.user_profiles
    WHERE public.user_profiles.id = auth.uid()
      AND public.user_profiles.org_id = public.org_data_retention_settings.org_id
      AND public.user_profiles.plan_tier = 'museum'
      AND public.user_profiles.role IN ('admin', 'platform_admin')
  )
);

DROP POLICY IF EXISTS org_data_retention_settings_same_org_admin_insert ON public.org_data_retention_settings;
CREATE POLICY org_data_retention_settings_same_org_admin_insert
ON public.org_data_retention_settings
FOR INSERT
TO authenticated
WITH CHECK (
  plan_tier = 'museum'
  AND EXISTS (
    SELECT 1
    FROM public.user_profiles
    WHERE public.user_profiles.id = auth.uid()
      AND public.user_profiles.org_id = public.org_data_retention_settings.org_id
      AND public.user_profiles.plan_tier = 'museum'
      AND public.user_profiles.role IN ('admin', 'platform_admin')
  )
);

DROP POLICY IF EXISTS org_data_retention_settings_same_org_admin_update ON public.org_data_retention_settings;
CREATE POLICY org_data_retention_settings_same_org_admin_update
ON public.org_data_retention_settings
FOR UPDATE
TO authenticated
USING (
  plan_tier = 'museum'
  AND EXISTS (
    SELECT 1
    FROM public.user_profiles
    WHERE public.user_profiles.id = auth.uid()
      AND public.user_profiles.org_id = public.org_data_retention_settings.org_id
      AND public.user_profiles.plan_tier = 'museum'
      AND public.user_profiles.role IN ('admin', 'platform_admin')
  )
)
WITH CHECK (
  plan_tier = 'museum'
  AND EXISTS (
    SELECT 1
    FROM public.user_profiles
    WHERE public.user_profiles.id = auth.uid()
      AND public.user_profiles.org_id = public.org_data_retention_settings.org_id
      AND public.user_profiles.plan_tier = 'museum'
      AND public.user_profiles.role IN ('admin', 'platform_admin')
  )
);
