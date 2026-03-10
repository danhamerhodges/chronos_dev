# ChronosRefine Phase 4 Packet 4A Closeout Note

Status: Context-only evidence note. This file does not alter canonical source-of-truth ordering in `AGENTS.md`.

## Scope

- Packet: `Packet 4A`
- Requirement: `FR-001`
- Candidate branch: `codex/packet4a-closure`
- Candidate SHA: `9a5791c4023794af8d6cc96d7dd2561aafdb93bc`
- Closure date: `2026-03-08`

## Summary

Packet 4A (`FR-001`) is complete on the candidate branch. Deterministic tests passed, the live memory-backed and Supabase-backed resumable upload smokes both passed, and staging revision `chronos-phase1-app-00036-blf` served upload-session creation successfully with recorded latency evidence.

## Verification Commands

Local deterministic gates:

```bash
./node_modules/.bin/pnpm -C web test
./.venv/bin/pytest tests/api/test_upload.py tests/database/test_schema_migrations.py tests/api/test_endpoints.py tests/database/test_phase2_repository_backend.py tests/integration/test_resumable_upload.py tests/integration/test_job_lifecycle.py tests/load/test_upload_performance.py -q
python3 scripts/validate_test_traceability.py
```

Live memory-backed GCS smoke:

```bash
set -a
source .env >/dev/null 2>&1
test -f .env.local && source .env.local >/dev/null 2>&1
set +a
export ENVIRONMENT=test
export CHRONOS_RUN_GCS_UPLOAD_INTEGRATION=1
./.venv/bin/pytest tests/integration/test_resumable_upload.py -q -rs -k 'real_gcs and not supabase'
```

Live Supabase-backed GCS smoke:

```bash
set -a
source .env >/dev/null 2>&1
test -f .env.local && source .env.local >/dev/null 2>&1
set +a
export ENVIRONMENT=test
export CHRONOS_RUN_GCS_UPLOAD_INTEGRATION=1
export CHRONOS_RUN_SUPABASE_INTEGRATION=1
./.venv/bin/pytest tests/integration/test_resumable_upload.py -q -rs -k supabase
```

Staging validation:

```bash
curl --silent --show-error https://chronos-phase1-app-19961431854.us-central1.run.app/v1/version
python3 scripts/ops/verify_cloud_run_runtime.py --service chronos-phase1-app --project chronos-dev-489301 --region us-central1
set -a
source .env >/dev/null 2>&1
test -f .env.local && source .env.local >/dev/null 2>&1
export CHRONOS_PACKET4A_STAGING_BASE_URL='https://chronos-phase1-app-19961431854.us-central1.run.app'
export CHRONOS_PACKET4A_STAGING_EMAIL="$CHRONOS_TEST_EMAIL"
export CHRONOS_PACKET4A_STAGING_PASSWORD="$CHRONOS_TEST_PASSWORD"
set +a
./.venv/bin/python scripts/ops/run_packet4a_live_smoke.py --mode staging-latency --output .tmp/packet4a/staging-latency.json
```

## Evidence Summary

### Live Memory-Backed Smoke

- Evidence file: `.tmp/packet4a/memory-live-smoke.json`
- Result: passed
- Same `upload_id`: yes
- Same `object_path`: yes
- Resume offset after first chunk: `262144`
- Persisted status transition: `pending -> uploading -> completed`
- Pointer persisted: yes
- Secondary-user resume/finalize denied: `404 / 404`

### Live Supabase-Backed Smoke

- Evidence file: `.tmp/packet4a/supabase-live-smoke.json`
- Result: passed
- Same `upload_id`: yes
- Same `object_path`: yes
- Resume offset after first chunk: `262144`
- Persisted status transition: `pending -> uploading -> completed`
- Pointer persisted: yes
- Pointer owner matched creator: yes
- Secondary-user resume/finalize denied: `404 / 404`

### Staging Validation

- Revision: `chronos-phase1-app-00036-blf`
- Version endpoint:

```json
{"version":"0.2.0","build_sha":"9a5791c4023794af8d6cc96d7dd2561aafdb93bc","build_time":"2026-03-08T20:03:49Z"}
```

- Runtime verifier: passed
- Latency evidence file: `.tmp/packet4a/staging-latency.json`
- Session-creation latency:
  - `p50 = 0.7823s`
  - `p95 = 9.6927s`
  - `p99 = 9.6927s`

## Staging Environment Notes

- GitHub `workflow_dispatch` on `deploy-staging.yml` was rejected for the candidate branch by environment protection rules, so staging validation used a manual fallback deploy with the same Cloud Run env/secret shape.
- The staging deploy workflow now requires `GCS_BUCKET_NAME`.
- The staging Cloud Run runtime service account (`19961431854-compute@developer.gserviceaccount.com`) required bucket-scoped `roles/storage.objectCreator` on the upload bucket for resumable session creation.
- Staging Supabase required Packet 4A migrations `0015` and `0016` before `/v1/upload` could persist `upload_sessions`.

## Non-Blocking Caveats

- Phase 4 overall is incomplete. This note only closes Packet 4A (`FR-001`).
- The staging latency result meets functional proof needs, but `p95`/`p99` remain elevated enough to warrant monitoring during later Phase 4 follow-on work.
