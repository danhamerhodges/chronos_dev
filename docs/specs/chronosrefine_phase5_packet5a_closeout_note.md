# ChronosRefine Phase 5 Packet 5A Closeout Note

Status: Context-only closeout evidence note. This file does not alter canonical source-of-truth ordering in `AGENTS.md`.

## Packet 5A Scope

- Packet: `Packet 5A`
- Requirement focus: `FR-006`
- Candidate branch: `codex/phase5-packet5a-impl`
- Hosted closeout date: `2026-04-06`
- Shared hosted environment: `chronos_dev`
- Cloud Run service: `chronos-phase1-app`
- Final serving revision: `chronos-phase1-app-00053-l9b`

## Summary

Packet 5A is hosted-complete for the first `FR-006` slice. The packet adds the preview-review gate on top of the merged Packet 4F preview substrate, gates preview-launch and first-party UI only, preserves generic `POST /v1/jobs` behavior and OpenAPI, and records the required local, migration, and hosted closeout evidence in `chronos_dev`.

Packet 5A does not claim global `FR-006` closeout. Generic `/v1/jobs` preview-approval enforcement remains deferred, and canonical `NFR-008` ownership remains Phase 6 work per `docs/specs/chronosrefine_nonfunctional_requirements.md`.

## Verification Commands

Local validation:

```bash
python3 scripts/validate_test_traceability.py
./.venv/bin/python -m pytest tests/api/test_preview_sessions.py tests/api/test_endpoints.py tests/database/test_schema_migrations.py tests/integration/test_preview_pipeline.py tests/load/test_preview_performance.py -q
./.venv/bin/python -m pytest tests/processing/test_preview_generation.py tests/processing/test_scene_detection.py tests/api/test_cost_estimation.py tests/api/test_async_processing.py tests/integration/test_processing_launch_flow.py -q
npm --prefix web test -- ../tests/ui/test_cost_estimate_modal.spec.ts ../tests/ui/test_preview_modal.spec.ts ../tests/accessibility/test_preview_review_modal_a11y.spec.ts
.agents/skills/spec-consistency-audit/scripts/audit_specs.sh /tmp/chronos_phase5_packet5a_impl
```

Hosted unblock and rollout:

```bash
gcloud run services describe chronos-phase1-app --project=chronos-dev-489301 --region=us-central1 --format=json
gcloud secrets add-iam-policy-binding STRIPE_SECRET_KEY --project=chronos-dev-489301 --member=serviceAccount:19961431854-compute@developer.gserviceaccount.com --role=roles/secretmanager.secretAccessor
gcloud run services update chronos-phase1-app --project=chronos-dev-489301 --region=us-central1 --update-secrets=STRIPE_SECRET_KEY=STRIPE_SECRET_KEY:1
gcloud run deploy chronos-phase1-app --project=chronos-dev-489301 --region=us-central1 --source=. --allow-unauthenticated ...
```

Hosted closeout probes:

```bash
./.venv/bin/python /tmp/packet5a_hosted_closeout.py --mode basic
./.venv/bin/python /tmp/packet5a_hosted_closeout.py --mode publish-fail
./.venv/bin/python /tmp/packet5a_hosted_closeout.py --mode publish-retry-existing --preview-id <preview_id> --configuration-fingerprint <fingerprint>
psql "<chronos_dev direct db url>" -Atc "select count(*) from public.preview_sessions where launch_status = 'launch_pending' and updated_at < now() - interval '5 minutes';"
```

## Evidence Summary

### Local Validation

- `python3 scripts/validate_test_traceability.py`
  - Result: passed
- `.agents/skills/spec-consistency-audit/scripts/audit_specs.sh /tmp/chronos_phase5_packet5a_impl`
  - Result: passed
- Backend/local packet suites
  - Result: passed
- Targeted UI/accessibility packet suites
  - Result: passed

### Migration State In `chronos_dev`

- Applied migration chain confirmed in `supabase_migrations.schema_migrations`
- Highest applied versions:
  - `0024 phase5_preview_review_gate`
  - `0023 phase4_preview_session_stabilization`
  - `0022 phase4_preview_sessions_rls`
  - `0021 phase4_preview_sessions`
  - `0020 phase4_cost_estimation`
  - `0019 phase4_output_delivery_rls`
  - `0018 phase4_output_delivery`
  - `0017 phase4_upload_configuration`

### Secret / IAM Evidence

- Runtime service account verified as `19961431854-compute@developer.gserviceaccount.com`
- Secret-level IAM grant added only on `STRIPE_SECRET_KEY`
- Bound secret version: `STRIPE_SECRET_KEY:1`
- No plain environment-variable fallback used for Stripe secret handling

### Hosted Packet 5A Smoke

- Final serving revision: `chronos-phase1-app-00053-l9b`
- Version endpoint:

```json
{"version":"0.2.0","build_sha":"2b0d44b18df61797b0729aee8113b429febea3ed-dirty-launchfix","build_time":"2026-04-06T01:12:00Z"}
```

- Basic hosted proof:
  - preview create returned `review_status = pending`
  - launch before approval returned `/problems/preview_approval_required`
  - review persisted `approved`
  - repeated preview launch returned the same `job_id` (`161655f3-4deb-50e7-aa41-2abdfc2113be`)
  - cross-user review and launch remained denied (`404 / 404`)
  - stale anti-replay returned `/problems/preview_stale`
  - regenerated preview after config change returned `review_status = pending`
- Generic `/v1/jobs` non-regression:
  - OpenAPI still reports `202`
  - preview-gate problem types are absent from `/v1/jobs`
  - direct generic job launch still succeeded with queued job `4284cc86-e2e9-4310-b241-c1f25ba25c29`
- Publish-failure retry proof:
  - injected publish failure returned `/problems/launch_dispatch_failed`
  - preview entered `launch_pending`
  - bound job id was `170bd9b8-a8d9-5a61-a89a-8756693a098d`
  - retry reused the same job id and advanced the preview to `launched`
- Historical orphan cleanup:
  - one pre-fix `launch_pending` preview from revision `chronos-phase1-app-00049-6bw` was retried successfully
  - final stale `launch_pending` count older than five minutes: `0`

### Hosted Preview Latency

- Smoke sample size: `6`
- Samples (seconds): `1.6512`, `1.7209`, `1.7522`, `1.7856`, `1.8466`, `1.9511`
- `p95 = 1.8466s`
- `mean = 1.7846s`
- `max = 1.9511s`
- Result: within the canonical `<6s p95` Packet 5A guardrail

## Environment Notes

- The staging unblock started as a Secret Manager / IAM problem for `STRIPE_SECRET_KEY` and was resolved with a least-privilege secret-level grant.
- Hosted closeout then surfaced two implementation bugs that were fixed on the candidate branch before final closeout:
  - Stripe pricing metadata resolution expected `.get()` on Stripe SDK objects
  - preview-launch job creation forwarded a string `fidelity_tier` into an enum-only fidelity-profile path
- The final serving revision keeps the same shared staging/pre-prod environment model:
  - `chronos_dev` is the shared hosted environment
  - `ENVIRONMENT=staging`

## Non-Blocking Follow-Up

- `scripts/ops/verify_cloud_run_runtime.py` still fails on the serving revision because `BUILD_SHA` includes a non-canonical suffix (`-dirty-launchfix`) instead of a bare git SHA.
- This does not block Packet 5A hosted closeout, but it should be cleaned up in a follow-up change so runtime verification passes on future staged revisions.

## Packet Status

- Packet 5A status: `hosted-complete`
- Global `FR-006` status: still open
- Phase 5 full-requirement count: unchanged until a later packet closes `FR-006` globally
