# ChronosRefine Phase 5 Packet 5K-A Runtime Recovery Note

Date: 2026-05-24

Status: Hosted runtime/config recovery complete. This file records Cloud Run recovery evidence only. It does not close `SEC-005`, does not advance Phase 5 tracker counts, and does not claim migration `0027`, GCS lifecycle, lifecycle-deletion audit-log, hosted manifest, compliance, or two-engineer review evidence.

## Packet 5K-A Scope

- Packet: `Packet 5K-A`
- Parent packet: `Packet 5K`
- Requirement focus: `SEC-005` Transformation Manifest Retention
- Candidate branch: `codex/phase5-packet5k-sec005-hosted-closeout`
- Recovery commit: `0ac7328585819191c00c61427a722764ec48bb3b`
- Shared hosted environment: `chronos_dev`
- Cloud Run service: `chronos-phase1-app`
- Public base URL: `https://chronos-phase1-app-19961431854.us-central1.run.app`

## Summary

Packet 5K-A recovered the hosted runtime/config blocker found during Packet 5K. The failed latest-created revision `chronos-phase1-app-00088-q4q` was superseded by a corrected deploy that preserved the current commercial runtime Secret Manager refs, stamped non-empty build metadata, and routed traffic only after Cloud Run created a ready revision.

The recovered hosted revision is `chronos-phase1-app-00089-bnh`, serving `100%` of traffic with build SHA `0ac7328585819191c00c61427a722764ec48bb3b`.

This recovery was limited to Cloud Run runtime/config and CI deploy-contract hardening. No Supabase migration, Terraform operation, GCS lifecycle mutation, lifecycle audit-log query, seeded hosted manifest write, manual object cleanup, tracker update, implementation-plan progress update, or coverage-matrix progress claim was performed.

## Code And Workflow Corrections

Packet 5K-A corrected the deploy contract so future staging deploys carry the runtime config required by the current application:

- `.github/workflows/deploy-staging.yml` now validates and deploys the required commercial Secret Manager refs:
  - `STRIPE_WEBHOOK_SECRET`
  - `COMMERCIAL_PRICEBOOK_JSON`
  - `STRIPE_PRODUCT_ID`
  - `STRIPE_PRICE_ID`
  - `STRIPE_HOBBYIST_PRICE_ID`
  - `STRIPE_PRO_PRICE_ID`
  - `STRIPE_MUSEUM_PRICE_ID`
  - `STRIPE_OVERAGE_PRODUCT_ID`
  - `STRIPE_OVERAGE_PRICE_ID`
- `.github/workflows/deploy-staging.yml` now sets:
  - `COMMERCIAL_PRICEBOOK_BOOTSTRAP_ENABLED=true`
  - `STRIPE_BILLING_PORTAL_RETURN_URL`
- `scripts/ops/verify_cloud_run_runtime.py` now verifies the commercial Secret Manager refs and non-empty billing portal return URL.
- `tests/ops/test_ci_cd_pipeline.py` now asserts the staging deploy workflow contains the commercial pricebook and tier-specific Stripe refs.

## Verification Commands

Local validation:

```bash
python3 scripts/validate_test_traceability.py
uv run --extra dev pytest -q tests/ops/test_ci_cd_pipeline.py
git diff --check
```

Secret readiness:

```bash
for secret in REDIS_URL SUPABASE_URL_DEV SUPABASE_ANON_KEY_DEV SUPABASE_SERVICE_ROLE_KEY STRIPE_SECRET_KEY STRIPE_WEBHOOK_SECRET COMMERCIAL_PRICEBOOK_JSON STRIPE_PRODUCT_ID STRIPE_PRICE_ID STRIPE_HOBBYIST_PRICE_ID STRIPE_PRO_PRICE_ID STRIPE_MUSEUM_PRICE_ID STRIPE_OVERAGE_PRODUCT_ID STRIPE_OVERAGE_PRICE_ID SUPABASE_DB_HOST SUPABASE_DB_PORT SUPABASE_DB_NAME SUPABASE_DB_USER SUPABASE_DB_PASSWORD JOB_WORKER_TRUSTED_TOKEN OUTPUT_DELIVERY_SIGNING_SECRET; do gcloud secrets describe "$secret" --project chronos-dev-489301 --format='value(name)' >/dev/null || exit 1; done
```

Hosted recovery and verification:

```bash
gcloud run deploy chronos-phase1-app --project chronos-dev-489301 --region us-central1 --source . --allow-unauthenticated --set-env-vars "ENVIRONMENT=staging,BUILD_SHA=0ac7328585819191c00c61427a722764ec48bb3b,BUILD_TIME=2026-05-24T01:17:50Z,JOB_DISPATCH_MODE=pubsub,JOB_PROGRESS_MODE=supabase,JOB_PUBSUB_TOPIC=projects/chronos-dev-489301/topics/chronos-async-jobs-smoke,SEGMENT_CACHE_MODE=redis,GCS_BUCKET_NAME=chronos-dev-kjlyuwiedsfcapduxdkn-raw,COMMERCIAL_PRICEBOOK_BOOTSTRAP_ENABLED=true,STRIPE_BILLING_PORTAL_RETURN_URL=https://chronos-phase1-app-wprbzt6h3q-uc.a.run.app/account/billing" --set-secrets "REDIS_URL=REDIS_URL:latest,SUPABASE_URL=SUPABASE_URL_DEV:latest,SUPABASE_ANON_KEY=SUPABASE_ANON_KEY_DEV:latest,SUPABASE_SERVICE_ROLE_KEY=SUPABASE_SERVICE_ROLE_KEY:latest,STRIPE_SECRET_KEY=STRIPE_SECRET_KEY:latest,STRIPE_WEBHOOK_SECRET=STRIPE_WEBHOOK_SECRET:latest,COMMERCIAL_PRICEBOOK_JSON=COMMERCIAL_PRICEBOOK_JSON:latest,STRIPE_PRODUCT_ID=STRIPE_PRODUCT_ID:latest,STRIPE_PRICE_ID=STRIPE_PRICE_ID:latest,STRIPE_HOBBYIST_PRICE_ID=STRIPE_HOBBYIST_PRICE_ID:latest,STRIPE_PRO_PRICE_ID=STRIPE_PRO_PRICE_ID:latest,STRIPE_MUSEUM_PRICE_ID=STRIPE_MUSEUM_PRICE_ID:latest,STRIPE_OVERAGE_PRODUCT_ID=STRIPE_OVERAGE_PRODUCT_ID:latest,STRIPE_OVERAGE_PRICE_ID=STRIPE_OVERAGE_PRICE_ID:latest,SUPABASE_DB_HOST=SUPABASE_DB_HOST:latest,SUPABASE_DB_PORT=SUPABASE_DB_PORT:latest,SUPABASE_DB_NAME=SUPABASE_DB_NAME:latest,SUPABASE_DB_USER=SUPABASE_DB_USER:latest,SUPABASE_DB_PASSWORD=SUPABASE_DB_PASSWORD:latest,JOB_WORKER_TRUSTED_TOKEN=JOB_WORKER_TRUSTED_TOKEN:latest,OUTPUT_DELIVERY_SIGNING_SECRET=OUTPUT_DELIVERY_SIGNING_SECRET:latest" --quiet
curl -fsSL https://chronos-phase1-app-19961431854.us-central1.run.app/health
curl -fsSL https://chronos-phase1-app-19961431854.us-central1.run.app/v1/version
python3 scripts/ops/verify_cloud_run_runtime.py --service chronos-phase1-app --project chronos-dev-489301 --region us-central1
gcloud run services describe chronos-phase1-app --project chronos-dev-489301 --region us-central1 --format=json
```

## Hosted Evidence

Deploy result:

```text
Service [chronos-phase1-app] revision [chronos-phase1-app-00089-bnh] has been deployed and is serving 100 percent of traffic.
Service URL: https://chronos-phase1-app-19961431854.us-central1.run.app
```

Public health endpoint:

```json
{"status":"ok"}
```

Public version endpoint:

```json
{"version":"0.2.0","build_sha":"0ac7328585819191c00c61427a722764ec48bb3b","build_time":"2026-05-24T01:17:50Z"}
```

Runtime verifier:

```text
PASS: runtime verification passed for chronos-phase1-app @ chronos-phase1-app-00089-bnh
```

Cloud Run service posture after recovery:

- `latestCreatedRevisionName`: `chronos-phase1-app-00089-bnh`
- `latestReadyRevisionName`: `chronos-phase1-app-00089-bnh`
- service `Ready`: `True`
- service `ConfigurationsReady`: `True`
- service `RoutesReady`: `True`
- traffic: `100%` to `chronos-phase1-app-00089-bnh`
- image digest: `us-central1-docker.pkg.dev/chronos-dev-489301/cloud-run-source-deploy/chronos-phase1-app@sha256:644bdf357752236349b6c233037851d586b6f46a7cc0a6180fbddd06cd61c7c6`

The recovered runtime keeps commercial config secret-managed. Secret-backed env refs include `COMMERCIAL_PRICEBOOK_JSON`, tier-specific Stripe price IDs, Stripe webhook secret, Supabase DB credentials, worker token, and output-delivery signing secret. Plain env values include only non-secret runtime settings such as build metadata, dispatch mode, bucket name, bootstrap flag, and billing portal return URL.

## Remaining SEC-005 Gates

`SEC-005` remains open after Packet 5K-A. The next SEC-005 closeout loop still requires explicit approval before:

- hosted Supabase migration `0027` dry-run/apply
- hosted schema verification for retention/redaction columns, RLS, grants, and check constraints
- Terraform import/plan/apply/state operations
- GCS lifecycle-rule mutation
- hosted Full + Redacted Museum manifest writes
- hosted expired-manifest and 0-day deleted-manifest not-found proof
- Cloud Audit Logs lifecycle-deletion proof
- compliance review and two-engineer review recording
- any tracker, implementation-plan, or coverage-matrix progress claim

## Recommended Next Loop

Proceed with `Packet 5K-B: SEC-005 migration and schema verification` only after explicit approval.

Minimum next-loop goals:

1. Capture runtime-before evidence from revision `chronos-phase1-app-00089-bnh`.
2. Dry-run and apply `0027_phase5_sec005_manifest_retention.sql` in `chronos_dev`.
3. Verify hosted schema, RLS, grants, and constraints.
4. Stop before Terraform/GCS lifecycle mutation or seeded manifest writes.

## Packet Status

- Packet 5K-A status: `hosted-runtime-recovered`
- Global `SEC-005` status: open
- Phase 5 full-requirement count: remains `2/11`
