# ChronosRefine Phase 5 Packet 5C Closeout Note

Status: Context-only closeout evidence note. This file does not alter canonical source-of-truth ordering in `AGENTS.md`.

## Packet 5C Scope

- Packet: `Packet 5C`
- Requirement focus: `NFR-006`
- Candidate branch: `codex/phase5-packet5c-impl`
- Hosted closeout date: `2026-04-08`
- Shared hosted environment: `chronos_dev`
- Cloud Run service: `chronos-phase1-app`
- Final serving revision: `chronos-phase1-app-00069-wgr`

## Summary

Packet 5C is hosted-complete as the first `NFR-006` slice for current merged pricing-model surfaces. The packet adds the runtime commercial pricebook, replaces the remaining hardcoded current-surface pricing and entitlement lookups, exposes effective configured pricing through usage and estimate responses, and records the required config-only hosted proof in `chronos_dev`.

Packet 5C does **not** claim global `NFR-006` closeout. Deferred acceptance criteria `AC-NFR-006-05`, `AC-NFR-006-06`, `AC-NFR-006-09`, and `AC-NFR-006-10` remain open, so `NFR-006` stays partial and the Phase 5 full-requirement count remains unchanged.

## Verification Commands

Local validation:

```bash
python3 scripts/validate_test_traceability.py
./.venv/bin/python -m pytest tests/billing/test_feature_gating.py tests/billing/test_usage_alerts.py tests/api/test_cost_estimation.py tests/api/test_cost_breakdown.py tests/api/test_fidelity_configuration.py tests/api/test_output_delivery.py tests/processing/test_output_encoding.py tests/api/test_endpoints.py tests/api/test_async_processing.py tests/integration/test_configuration_job_handoff.py tests/integration/test_processing_launch_flow.py tests/api/test_preview_sessions.py -q
node web/node_modules/vitest/vitest.mjs run --config web/vitest.config.ts tests/ui/test_cost_estimate_modal.spec.ts tests/ui/test_preview_modal.spec.ts tests/ui/test_processing_flow.spec.ts tests/ui/test_output_delivery.spec.ts tests/accessibility/test_preview_review_modal_a11y.spec.ts tests/accessibility/test_cost_estimate_modal_a11y.spec.ts
.agents/skills/spec-consistency-audit/scripts/audit_specs.sh /tmp/chronos_phase5_packet5c_impl
python3 scripts/ops/verify_cloud_run_runtime.py --service chronos-phase1-app --project chronos-dev-489301 --region us-central1
```

Hosted closeout probes:

```bash
./.venv/bin/python /tmp/packet5c_hosted_closeout.py --repo-root /tmp/chronos_phase5_packet5c_impl --base-url https://chronos-phase1-app-19961431854.us-central1.run.app --pricebook-path /tmp/packet5c_pricebook_baseline.json
gcloud run services update chronos-phase1-app --project chronos-dev-489301 --region us-central1 --env-vars-file /tmp/packet5c_env_alt.yaml
./.venv/bin/python /tmp/packet5c_hosted_closeout.py --repo-root /tmp/chronos_phase5_packet5c_impl --base-url https://chronos-phase1-app-19961431854.us-central1.run.app --pricebook-path /tmp/packet5c_pricebook_alt.json
gcloud run services update chronos-phase1-app --project chronos-dev-489301 --region us-central1 --env-vars-file /tmp/packet5c_env_baseline.yaml
./.venv/bin/python /tmp/packet5b_hosted_closeout.py --repo-root /tmp/chronos_phase5_packet5c_impl --base-url https://chronos-phase1-app-19961431854.us-central1.run.app --mode basic
gcloud run services update chronos-phase1-app --project chronos-dev-489301 --region us-central1 --update-env-vars JOB_PUBSUB_TOPIC=projects/chronos-dev-489301/topics/chronos-async-jobs-smoke-missing
./.venv/bin/python /tmp/packet5b_hosted_closeout.py --repo-root /tmp/chronos_phase5_packet5c_impl --base-url https://chronos-phase1-app-19961431854.us-central1.run.app --mode publish-fail --artifact /tmp/packet5c_publish_fail_artifact.json
gcloud run services update chronos-phase1-app --project chronos-dev-489301 --region us-central1 --update-env-vars JOB_PUBSUB_TOPIC=projects/chronos-dev-489301/topics/chronos-async-jobs-smoke
./.venv/bin/python /tmp/packet5b_hosted_closeout.py --repo-root /tmp/chronos_phase5_packet5c_impl --base-url https://chronos-phase1-app-19961431854.us-central1.run.app --mode retry-existing --artifact /tmp/packet5c_publish_fail_artifact.json --min-age-seconds 305
./.venv/bin/python /tmp/packet5b_hosted_closeout.py --repo-root /tmp/chronos_phase5_packet5c_impl --base-url https://chronos-phase1-app-19961431854.us-central1.run.app --mode preview-latency --samples 6
curl -s https://chronos-phase1-app-19961431854.us-central1.run.app/v1/version
curl -s https://chronos-phase1-app-19961431854.us-central1.run.app/v1/metrics
```

## Evidence Summary

### Local Validation

- `python3 scripts/validate_test_traceability.py`
  - Result: passed
- `.agents/skills/spec-consistency-audit/scripts/audit_specs.sh /tmp/chronos_phase5_packet5c_impl`
  - Result: passed
- Packet 5C billing/configuration/backend suites
  - Result: passed
- Targeted Packet 5C web and accessibility suites
  - Result: passed
- `python3 scripts/ops/verify_cloud_run_runtime.py --service chronos-phase1-app --project chronos-dev-489301 --region us-central1`
  - Result: passed on the deployed Packet 5C serving revision

### Hosted Packet 5C Baseline Proof

- First 5C code serving revision: `chronos-phase1-app-00065-rst`
- Final serving revision after runtime-signal proof and topic restore: `chronos-phase1-app-00069-wgr`
- Version endpoint on the 5C build:

```json
{"version":"0.2.0","build_sha":"5c9cf8d316d3e17c31f3050809cd6b5764819b11","build_time":"2026-04-08T23:22:47Z"}
```

- Baseline `COMMERCIAL_PRICEBOOK_JSON` version: `2026-04-08-staging-baseline`
- Hosted baseline proof:
  - hobbyist usage effective pricing returned `subscription_price_id = price_1TK4j2LHlGnsBfENVm7hGvG2`, `included_minutes_monthly = 30`, `overage_enabled = false`
  - hobbyist estimate returned the same baseline effective pricing block
  - hobbyist unsupported fidelity save returned `403`
  - hobbyist early-photo/current resolution-cap gate returned `403`
  - pro usage effective pricing returned `subscription_price_id = price_1TK4j2LHlGnsBfENxFAzZ4h4`, `included_minutes_monthly = 60`, `overage_rate_usd_per_minute = 0.5`
  - pro estimate returned the same effective pricing block and `launch_blocker = overage_approval_required`
  - overage approval returned `overage_price_reference = price_1TK4j3LHlGnsBfENNyRSRvag`
  - bare generic `/v1/jobs` launch without approved-preview provenance returned `/problems/preview_approval_required`
  - preview launch before approval returned `/problems/preview_approval_required`
  - approved repeated generic launch returned the same `job_id` (`833d4a14-a1cf-5c19-97fd-7720d93e6336`)
  - cross-user preview review and generic launch remained denied (`404`)

### Config-Only Alternate Pricebook Proof

- Config-only alternate revision: `chronos-phase1-app-00066-kxg`
- Baseline restore revision: `chronos-phase1-app-00067-plk`
- Alternate revision used the same build SHA (`5c9cf8d316d3e17c31f3050809cd6b5764819b11`) as the baseline Packet 5C code, proving the pricing change occurred without a code deploy.
- Alternate `COMMERCIAL_PRICEBOOK_JSON` version: `2026-04-08-staging-alt`
- Hosted alternate proof:
  - hobbyist usage and estimate both moved to `included_minutes_monthly = 35`
  - pro usage and estimate both moved to `included_minutes_monthly = 75`
  - pro overage rate moved to `0.55`
  - pricing references, launch blocking, and overage approval remained coherent under the alternate configuration
- After restoring the approved staging baseline, the service returned to the baseline env contract while preserving the same 5C code build.

### Packet 5A / 5B Non-Regression On The 5C Revision

- Packet 5B basic smoke against the 5C build returned:
  - preview create pending = `true`
  - bare `/v1/jobs` launch = `409 /problems/preview_approval_required`
  - malformed `launch_context` = `422`
  - estimate with and without `launch_context` = `200`
  - approved repeated generic launch reused the same `job_id`
  - stale anti-replay returned `/problems/preview_stale`
  - cross-user preview review, preview launch, and generic launch remained denied (`404`)
  - Packet 5A preview-route launch after approval remained green

### Runtime Signal Evidence

- Temporary publish-failure revision: `chronos-phase1-app-00068-d8x`
- Publish-failure proof:
  - injected bad Pub/Sub topic returned `/problems/launch_dispatch_failed`
  - preview entered `launch_pending`
  - bound `job_id` was `81a3ed77-5bae-583c-b961-9c1aa2097936`
- Retry-after-stale proof on the restored topic:
  - retry reused the same `job_id`
  - preview finalized to `launch_status = launched`
  - `preview_launch_pending_stale_metric_delta = 1.0`
  - `preview_launch_pending_count = 0.0`
  - `preview_launch_pending_oldest_age_seconds = 0.0`
- Packet 5B basic smoke on the 5C build also recorded `preview_approval_required_jobs_launch_metric_delta = 1.0`

### Hosted Preview Latency

- Smoke sample size: `6`
- `p50 = 0.9261s`
- `p95 = 1.0161s`
- `p99 = 1.0161s`
- `mean = 0.9365s`
- `max = 1.0161s`
- Result: within the canonical `<6s p95` guardrail

## Implementation Correction During Hosted Proof

- Hosted proof surfaced one narrow implementation bug on the real-auth path: authenticated requests could overwrite an existing staged `plan_tier` back to hobbyist when reading the persisted user profile.
- The packet was corrected by preserving an existing user profile on the end-user JWT path and inserting default hobbyist state only for first-time profiles.
- Fix commit: `5c9cf8d316d3e17c31f3050809cd6b5764819b11`

## Consumer Rollout Note

- Packet 5C does not change the Packet 5B public launch migration path.
- Legacy bare `/v1/jobs` clients still must:
  1. save or fetch the configuration again,
  2. generate and approve the current preview,
  3. relaunch with the refreshed payload carrying `launch_context.source = approved_preview`.
- Packet 5C adds configuration-driven pricing and entitlement resolution on top of that path; it does not add new Stripe subscription lifecycle behavior.

## Packet Status

- Packet 5C status: `hosted-complete slice`
- Global `NFR-006` status: still partial
- Phase 5 full-requirement count: unchanged at `1/11`
