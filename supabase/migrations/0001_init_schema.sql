-- Maps to: ENG-016

CREATE TABLE IF NOT EXISTS public.user_profiles (
  id UUID PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  role TEXT NOT NULL DEFAULT 'member',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.billing_accounts (
  id UUID PRIMARY KEY,
  owner_user_id UUID NOT NULL,
  stripe_customer_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.gcs_object_pointers (
  id UUID PRIMARY KEY,
  owner_user_id UUID NOT NULL,
  bucket_name TEXT NOT NULL,
  object_path TEXT NOT NULL,
  checksum_sha256 TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
