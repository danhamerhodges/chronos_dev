import { createClient } from "@supabase/supabase-js";

type EnvRecord = Record<string, string | undefined>;

const viteEnv = (import.meta as unknown as { env?: EnvRecord }).env ?? {};
const nodeEnv =
  (globalThis as unknown as { process?: { env?: EnvRecord } }).process?.env ?? {};

const readEnv = (...keys: string[]): string => {
  for (const key of keys) {
    const value = viteEnv[key] ?? nodeEnv[key];
    if (value) return value;
  }
  return "";
};

const url = readEnv(
  "VITE_SUPABASE_URL_DEV",
  "VITE_SUPABASE_URL",
  "SUPABASE_URL_DEV",
  "SUPABASE_URL",
);
const anonKey = readEnv(
  "VITE_SUPABASE_ANON_KEY_DEV",
  "VITE_SUPABASE_ANON_KEY",
  "SUPABASE_ANON_KEY_DEV",
  "SUPABASE_ANON_KEY",
);

export const supabase = createClient(url, anonKey);
