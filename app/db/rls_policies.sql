-- ENG-016 baseline RLS policy sketch.
-- Canonical policies are versioned under supabase/migrations/0002_rls_policies.sql.

-- Example policy pattern:
-- CREATE POLICY "users_can_select_own_rows" ON public.user_profiles
-- FOR SELECT USING (auth.uid() = user_id);
