-- Maps to: ENG-016, SEC-013

ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.billing_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.gcs_object_pointers ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_profiles_owner_read
ON public.user_profiles
FOR SELECT
USING (auth.uid() = id);

CREATE POLICY billing_accounts_owner_read
ON public.billing_accounts
FOR SELECT
USING (auth.uid() = owner_user_id);

CREATE POLICY gcs_pointers_owner_read
ON public.gcs_object_pointers
FOR SELECT
USING (auth.uid() = owner_user_id);
