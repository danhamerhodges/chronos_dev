# Chronos Environment Variables

## Canonical Environment Model
- `local` is the default contributor environment.
- `chronos_dev` is the only shared hosted environment and is treated operationally as staging / pre-prod.
- `production` is deferred and not implemented yet.
- Local Supabase is optional and not required for the default local path.

See [chronos_environment_strategy_runbook.md](./chronos_environment_strategy_runbook.md) for the governing environment rules.

## Variable Classes

### `local-required`
These are the only values required for the default no-external unit/test path:
- `ENVIRONMENT=test`
- `TEST_AUTH_OVERRIDE=true`
- `SUPABASE_URL=http://localhost:54321`

`SUPABASE_URL` is a placeholder for code paths that expect a non-empty URL. Unit-only mode does not require a running local Supabase instance.

### `remote-required (chronos_dev)`
These are required for the shared hosted deployment and runtime contract.

GitHub environment inputs used by the deploy workflow:
- `GCP_PROJECT_ID`
- `GCP_REGION`
- `CLOUD_RUN_SERVICE`
- `GCP_WIF_PROVIDER`
- `GCP_DEPLOY_SERVICE_ACCOUNT`
- `GCS_BUCKET_NAME`

Cloud Run runtime secret refs:
- `REDIS_URL -> REDIS_URL`
- `SUPABASE_URL -> SUPABASE_URL_DEV`
- `SUPABASE_ANON_KEY -> SUPABASE_ANON_KEY_DEV`
- `SUPABASE_SERVICE_ROLE_KEY -> SUPABASE_SERVICE_ROLE_KEY`
- `STRIPE_SECRET_KEY -> STRIPE_SECRET_KEY:1` (pinned staging binding validated during Packet 5A hosted closeout; rotate deliberately)
- `SUPABASE_DB_HOST -> SUPABASE_DB_HOST`
- `SUPABASE_DB_PORT -> SUPABASE_DB_PORT`
- `SUPABASE_DB_NAME -> SUPABASE_DB_NAME`
- `SUPABASE_DB_USER -> SUPABASE_DB_USER`
- `SUPABASE_DB_PASSWORD -> SUPABASE_DB_PASSWORD`
- `JOB_WORKER_TRUSTED_TOKEN -> JOB_WORKER_TRUSTED_TOKEN`
- `OUTPUT_DELIVERY_SIGNING_SECRET -> OUTPUT_DELIVERY_SIGNING_SECRET`

Cloud Run runtime literal envs:
- `ENVIRONMENT=staging`
- `BUILD_SHA` (bare 40-character git commit SHA; for direct source deploys use `bash scripts/ops/emit_build_metadata.sh`)
- `BUILD_TIME` (UTC ISO-8601 timestamp; for direct source deploys use `bash scripts/ops/emit_build_metadata.sh`)
- `JOB_DISPATCH_MODE=pubsub`
- `JOB_PROGRESS_MODE=supabase`
- `JOB_PUBSUB_TOPIC`
- `SEGMENT_CACHE_MODE=redis`
- `GCS_BUCKET_NAME`

### `future-prod-only`
These should remain dormant until a real production environment exists:
- `ENVIRONMENT=production`
- `STRIPE_HOBBYIST_PRICE_ID`
- `STRIPE_PRO_PRICE_ID`
- `STRIPE_MUSEUM_PRICE_ID`
- `STRIPE_PRO_OVERAGE_PRICE_ID`
- `STRIPE_MUSEUM_OVERAGE_PRICE_ID`

### `optional`
These are supported by the current runtime but are not required for the default local path:
- local app settings: `APP_ENV`, `APP_HOST`, `APP_PORT`, `CORS_ORIGINS`
- auth and rate limits: `AUTH_SESSION_TTL_MINUTES`, `AUTH_MAX_FAILED_ATTEMPTS`, `AUTH_LOCKOUT_MINUTES`, `HOBBYIST_RATE_LIMIT_PER_MINUTE`, `PRO_RATE_LIMIT_PER_MINUTE`, `MUSEUM_RATE_LIMIT_PER_MINUTE`
- metrics and logging: `METRICS_ENABLED`, `METRICS_NAMESPACE`, `LOG_LEVEL`, `LOG_REDACTION_MODE`
- billing integration: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRODUCT_ID`, `STRIPE_PRICE_ID`, `STRIPE_SUBSCRIPTION_PRODUCT_ID`, `STRIPE_SUBSCRIPTION_PRICE_ID`, `STRIPE_OVERAGE_PRODUCT_ID`, `STRIPE_OVERAGE_PRICE_ID`, `STRIPE_BILLING_PORTAL_RETURN_URL`, `COMMERCIAL_PRICEBOOK_JSON`, `HOBBYIST_MONTHLY_LIMIT_MINUTES`, `PRO_MONTHLY_LIMIT_MINUTES`, `MUSEUM_MONTHLY_LIMIT_MINUTES`
- GCP and Gemini integration: `GOOGLE_CLOUD_PROJECT`, `VERTEX_AI_LOCATION`, `GCP_ACCESS_TOKEN`, `ENABLE_REAL_GEMINI`, `GEMINI_MODEL`, `GEMINI_PROMPT_VERSION`, `GEMINI_RAW_RESPONSE_PREFIX`
- async and cache tuning: `SEGMENT_CACHE_NAMESPACE`, `SEGMENT_CACHE_TTL_SECONDS`, `JOB_CLOUD_RUN_NAME`, `GPU_*`
- ops and alerting: `RUNTIME_OPS_*`, `ALERT_ROUTING_MODE`, `PAGERDUTY_INTEGRATION_KEY`, `PAGERDUTY_SERVICE_ID`, `SLACK_ALERT_WEBHOOK_URL`, `SLO_DEGRADATION_THRESHOLD_PERCENT`, `MONTHLY_ERROR_BUDGET_PERCENT`, `MUSEUM_PROCESSING_SLA_ENABLED`
- explicit integration and hosted smoke toggles: `CHRONOS_RUN_*`, `CHRONOS_PACKET*`, `CHRONOS_ASYNC_SMOKE*`, `CHRONOS_REALTIME_DIAG*`, `CHRONOS_TEST_*`

### `stale/drifted`
These should not appear in active docs or hosted verification for the current model:
- stage-suffixed Supabase secret aliases previously accepted by hosted verification
- `AUTH_REQUIRE_EMAIL_VERIFICATION`
- `AUTH_OAUTH_GOOGLE_ENABLED`
- `AUTH_OAUTH_GITHUB_ENABLED`
- `AUTH_MAGIC_LINK_ENABLED`
- `PAGERDUTY_ROUTING_KEY`
- `SLO_AVAILABILITY_TARGET`
- `SLO_P95_LATENCY_MS_TARGET`
- `SLO_ERROR_RATE_TARGET`
- `SLO_INGEST_SUCCESS_TARGET`

### `compatibility-only`
These names are still accepted by the current code path, but they are retained only to avoid disruptive renames in this pass:
- `SUPABASE_URL_DEV`
- `SUPABASE_ANON_KEY_DEV`
- `VITE_SUPABASE_URL_DEV`
- `VITE_SUPABASE_ANON_KEY_DEV`

Preferred guidance:
- use `SUPABASE_URL` and `SUPABASE_ANON_KEY` as the runtime env names when documenting application behavior
- treat `*_DEV` names as compatibility-only names tied to current secret inventory and frontend fallback logic

## Non-Goals For This Pass
- Do not rename `chronos_dev`.
- Do not rename `SUPABASE_*_DEV` or `VITE_SUPABASE_*_DEV`.
- Do not change `app/config.py` or frontend fallback order unless a concrete bug is proven.
- Do not make local Supabase a baseline requirement.
