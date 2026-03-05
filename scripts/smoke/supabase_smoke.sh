#!/usr/bin/env bash
set -euo pipefail

SUPABASE_URL_EFFECTIVE="${SUPABASE_URL:-${SUPABASE_URL_DEV:-}}"
SUPABASE_ANON_KEY_EFFECTIVE="${SUPABASE_ANON_KEY:-${SUPABASE_ANON_KEY_DEV:-}}"

if [[ -z "${SUPABASE_URL_EFFECTIVE}" || -z "${SUPABASE_ANON_KEY_EFFECTIVE}" ]]; then
  echo "SUPABASE_URL/SUPABASE_ANON_KEY or SUPABASE_URL_DEV/SUPABASE_ANON_KEY_DEV are required"
  exit 1
fi

export SUPABASE_URL="${SUPABASE_URL_EFFECTIVE}"
export SUPABASE_ANON_KEY="${SUPABASE_ANON_KEY_EFFECTIVE}"

python3 - <<'PY'
from app.db.client import SupabaseClient

client = SupabaseClient()
ok, detail = client.healthcheck()
print({"ok": ok, "detail": detail})
if not ok:
    raise SystemExit(1)
PY
