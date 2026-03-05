-- Maps to: ENG-016

CREATE INDEX IF NOT EXISTS idx_user_profiles_email ON public.user_profiles (email);
CREATE INDEX IF NOT EXISTS idx_billing_accounts_owner_user_id ON public.billing_accounts (owner_user_id);
CREATE INDEX IF NOT EXISTS idx_gcs_object_pointers_owner_user_id ON public.gcs_object_pointers (owner_user_id);
