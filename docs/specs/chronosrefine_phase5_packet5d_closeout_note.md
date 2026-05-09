# ChronosRefine Phase 5 Packet 5D Closeout Note

Status: Context-only closeout evidence note. This file does not alter canonical source-of-truth ordering in `AGENTS.md`.

## Packet 5D Scope

- Packet: `Packet 5D`
- Requirement focus: `NFR-006`
- Candidate branch: `codex/phase5-packet5d-impl`
- Hosted closeout date: `2026-05-09`
- Shared hosted environment: `chronos_dev`
- Cloud Run service: `chronos-phase1-app`
- Final serving revision: `chronos-phase1-app-00079-46f`

## Summary

Packet 5D is hosted-complete and closes global `NFR-006`. It finishes the remaining pricing-model acceptance criteria by moving hosted pricing authority to audited DB-backed commercial pricebook revisions, adding org-scoped billing account state, processing replay-safe Stripe webhooks on `/v1/webhooks/stripe`, exposing user billing summary and portal-session APIs, enforcing Museum quote/subscription precedence, and preserving immutable launch-time pricing snapshots for cost and margin reporting.

Packet 5D also keeps the Packet 5C contract intact: active commercial pricing can be changed through the hosted control plane without a code deploy, exactly one DB pricebook revision remains active, and current pricing/usage/overage surfaces stay coherent.

## Verification Commands

Local validation:

```bash
python3 scripts/validate_test_traceability.py
uv run --extra dev pytest -q tests/api/test_preview_sessions.py
uv run --extra dev pytest -q tests/api/test_billing_management.py
uv run --extra dev pytest -q tests/billing/test_stripe_webhooks.py
uv run --extra dev pytest -q tests/billing/test_museum_custom_pricing.py
uv run --extra dev pytest -q tests/database/test_schema_migrations.py
uv run --extra dev pytest -q tests/database/test_phase2_repository_backend.py
uv run --extra dev pytest -q tests/ops/test_cost_tracking.py
uv run --extra dev pytest -q tests/security/test_pii_redaction.py tests/ops/test_logging.py
git diff --check
```

Hosted validation:

```bash
python3 scripts/ops/verify_cloud_run_runtime.py --service chronos-phase1-app --project chronos-dev-489301 --region us-central1
curl -s https://chronos-phase1-app-19961431854.us-central1.run.app/health
curl -s https://chronos-phase1-app-19961431854.us-central1.run.app/v1/version
```

Hosted proof evidence was captured under `.tmp/packet5d-proof/` in the Packet 5D worktree. The secret-bearing token and webhook-signature helper artifacts are local proof artifacts only and are intentionally not copied into this note.

## Evidence Summary

### Final Runtime

- Final serving revision: `chronos-phase1-app-00079-46f`
- Final version endpoint:

```json
{"version":"0.2.0","build_sha":"ca092e73733d1c09a1e25a9ed7ea6ec20a1b7c43","build_time":"2026-05-09T02:53:09Z"}
```

- Runtime verification: `PASS: runtime verification passed for chronos-phase1-app @ chronos-phase1-app-00079-46f`
- Health check: `{"status":"ok"}`
- Cloud Run commercial config posture:
  - raw Stripe product/price IDs are not present in plain env on the final revision
  - raw `COMMERCIAL_PRICEBOOK_JSON` is not present in plain env on the final revision
  - commercial config values are supplied through Secret Manager refs

### Hosted Migration And RLS Proof

Hosted `0025` posture was verified by querying the deployed Supabase schema:

- `commercial_pricebook_revisions`, `billing_audit_events`, `processed_stripe_events`, `billing_accounts`, and `media_jobs` exist.
- RLS is enabled on `commercial_pricebook_revisions`, `billing_audit_events`, and `processed_stripe_events`.
- `anon` and `authenticated` have no direct grants on those three control-plane tables.
- Final pricebook invariant: `3` revisions, `1` active revision, active version `2026-05-09-packet5d-post-launch-margin`.

### DB-Backed Pricebook Control Plane

- First DB-backed pricebook bootstrap succeeded through the hosted admin API without a code deploy.
- A later audited pricebook activation changed effective hosted pricing without a code deploy.
- Exactly one DB revision was active before and after activation.
- Final standard estimate uses active DB pricebook version `2026-05-09-packet5d-post-launch-margin`, with `120` included minutes and `0.70` overage rate.
- `PUT /v1/ops/billing/pricebook` is protected by `ops:write`; `platform_admin` is allowed, while existing non-platform roles remain denied.

### Stripe Webhook Processing

- Canonical route: `POST /v1/webhooks/stripe`.
- Full DB-backed webhook proof covered:
  - first subscription event processed
  - duplicate subscription event returned duplicate no-op
  - invoice event persisted invoice/account state
  - failed event reclaimed once and then became duplicate-safe after success
  - Museum quote event persisted quote pricing
  - Museum recurring subscription event took precedence over quote pricing
- Final revision duplicate proof returned:

```json
{"event_id":"evt_packet5d_standard_sub_v1","event_type":"customer.subscription.updated","status":"duplicate","duplicate":true,"org_id":"org-packet5d-standard"}
```

### Billing Summary And Portal

- `GET /v1/users/me/billing` returned org-scoped billing state for the standard proof org:
  - `subscription_status = active`
  - `portal_available = true`
  - `recent_invoices` count = `2`
  - effective pricing version = `2026-05-09-packet5d-post-launch-margin`
- `POST /v1/users/me/billing/portal-session` returned a Stripe-hosted billing portal URL.
- Museum quote-only org resolved to quote override pricing.
- Museum recurring org resolved to recurring subscription override pricing, proving recurring subscription precedence over quote context.

### Launch Snapshot And Margin Reporting

- Packet 5A/5B preview launch behavior remained green:
  - bare launch without approval returned `409 /problems/preview_approval_required`
  - cross-user review remained denied
  - approved launch returned `202`
  - repeated launch reused the same `job_id`
- Hosted proof job: `ffadb230-4f63-56cf-b42e-57a5a7174fef`
- The job captured launch-time pricing snapshot version `2026-05-09-packet5d-hosted-alt`, `75` included minutes, and `0.55` overage rate.
- After a later pricebook activation moved live pricing to `2026-05-09-packet5d-post-launch-margin`, the persisted job snapshot remained unchanged.
- Cost ops margin reporting used the stored launch-time snapshot:

```json
{"revenue_total_usd":11.6,"cost_total_usd":4.0,"gross_margin_percent":65.52,"target_margin_percent":60.0,"below_target":false}
```

### Packet 5C Non-Regression

- `POST /v1/jobs/estimate` remains coherent under active DB-backed pricing.
- `GET /v1/users/me/usage` returned active DB pricing with `120` monthly limit minutes and `0.70` overage rate.
- `POST /v1/users/me/approve-overage` returned `single_job` approval for `10` minutes and the active overage price reference.

### Log Hygiene

Hosted logs for final revision `chronos-phase1-app-00079-46f` after fresh proof traffic showed:

- `whsec_` pattern count: `0`
- Stripe signature header marker count: `0`
- raw webhook object marker count: `0`
- raw customer payload marker count: `0`
- raw invoice payload marker count: `0`
- raw pricebook payload marker count: `0`
- raw product payload marker count: `0`
- commercial pricebook entry marker count: `0`

The only `STRIPE_WEBHOOK_SECRET` text in final logs was the Secret Manager env-var name in Cloud Run revision metadata, not a secret value.

## Implementation Corrections During Hosted Proof

- Hosted proof surfaced a Stripe SDK metadata compatibility issue on real signed webhook payloads. The webhook service now safely accepts mapping-like and StripeObject-like metadata instead of assuming `dict(metadata)` works for every Stripe SDK object.
- Hosted log hygiene surfaced raw Stripe product/price IDs in SDK INFO logs. The logging layer now redacts Stripe resource IDs and suppresses Stripe SDK INFO request/response logs.
- Hosted Cloud Run audit logs surfaced raw commercial config values from plain env. The final revision moves commercial pricebook JSON and Stripe product/price IDs to Secret Manager refs with secret-level runtime access only.

## Packet Status

- Packet 5D status: `hosted-complete`
- Global `NFR-006` status: complete
- Phase 5 full-requirement count: advanced to `2/11`
