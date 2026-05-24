# ChronosRefine Phase 5 Packet 5K Hosted Execution Note

Date: 2026-05-24

Status: Blocked hosted execution note. This file records read-only Packet 5K evidence and blockers. It does not close `SEC-005`, does not advance Phase 5 tracker counts, and does not claim hosted lifecycle, compliance, or two-engineer review completion.

## Packet 5K Scope

- Packet: `Packet 5K`
- Requirement focus: `SEC-005` Transformation Manifest Retention
- Candidate branch: `codex/phase5-packet5k-sec005-hosted-closeout`
- Source base: `origin/main` at merge commit `e8f1b0d12a03ab526fbdb4f284f59c886e20ee20`
- Predecessor preflight: `docs/specs/chronosrefine_phase5_packet5j_hosted_preflight.md`
- Shared hosted environment: `chronos_dev`
- Cloud Run service: `chronos-phase1-app`
- Public base URL: `https://chronos-phase1-app-19961431854.us-central1.run.app`

## Summary

Packet 5K began the `SEC-005` hosted closeout execution loop from Packet 5J. The loop remained read-only because hosted readiness surfaced a runtime deployment blocker before any approval-gated actions could safely proceed.

The currently served Cloud Run revision is healthy, but it is not serving current `origin/main` or the Packet 5H/5J `SEC-005` code path. A newer Cloud Run revision was created after Packet 5J, but it failed startup before becoming ready. Therefore `SEC-005` hosted closeout cannot be claimed from the current hosted environment.

No Cloud Run deploy, traffic change, Supabase migration dry-run/apply, Terraform import/plan/apply/state operation, GCS lifecycle mutation, Cloud Audit Logs lifecycle-deletion query, seeded hosted manifest write, manual manifest deletion, tracker update, implementation-plan update, or coverage-matrix progress claim was performed.

## Read-Only Commands Run

Local validation:

```bash
python3 scripts/validate_test_traceability.py
uv run --extra dev pytest -q tests/security/test_manifest_retention.py tests/security/test_manifest_redaction.py tests/compliance/test_gdpr_manifest_retention.py tests/database/test_schema_migrations.py
```

Hosted read-only inspection:

```bash
curl -fsSL https://chronos-phase1-app-19961431854.us-central1.run.app/health
curl -fsSL https://chronos-phase1-app-19961431854.us-central1.run.app/v1/version
gcloud config list --format=json
gcloud auth list --format=json
gcloud run services describe chronos-phase1-app --project chronos-dev-489301 --region us-central1 --format=json
python3 scripts/ops/verify_cloud_run_runtime.py --service chronos-phase1-app --project chronos-dev-489301 --region us-central1
gcloud run revisions describe chronos-phase1-app-00079-46f --project chronos-dev-489301 --region us-central1 --format=json
gcloud run revisions describe chronos-phase1-app-00088-q4q --project chronos-dev-489301 --region us-central1 --format=json
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="chronos-phase1-app" AND resource.labels.revision_name="chronos-phase1-app-00088-q4q"' --project chronos-dev-489301 --limit=20 --format=json
gcloud storage buckets describe gs://chronos-dev-kjlyuwiedsfcapduxdkn-raw --format=json
```

## Evidence Summary

### Local SEC-005 Regression

- Traceability validation passed.
- Focused local tests passed: `31` tests.
- The local test set included:
  - `tests/security/test_manifest_retention.py`
  - `tests/security/test_manifest_redaction.py`
  - `tests/compliance/test_gdpr_manifest_retention.py`
  - `tests/database/test_schema_migrations.py`

Local validation confirms the merged code/test substrate remains intact. It does not prove hosted `SEC-005` closeout.

### Hosted Runtime

Public health endpoint:

```json
{"status":"ok"}
```

Public version endpoint:

```json
{"version":"0.2.0","build_sha":"ca092e73733d1c09a1e25a9ed7ea6ec20a1b7c43","build_time":"2026-05-09T02:53:09Z"}
```

Cloud Run service inspection showed:

- `latestCreatedRevisionName`: `chronos-phase1-app-00088-q4q`
- `latestReadyRevisionName`: `chronos-phase1-app-00079-46f`
- traffic: `100%` to `chronos-phase1-app-00079-46f`
- service `Ready`: `False`, caused by failed revision `chronos-phase1-app-00088-q4q`

Revision `chronos-phase1-app-00079-46f` is the current serving revision and reports build SHA `ca092e73733d1c09a1e25a9ed7ea6ec20a1b7c43`. That SHA is an ancestor of current `origin/main`, but it predates Packet 5H/5J `SEC-005` hosted-closeout work.

Current `origin/main` is `e8f1b0d12a03ab526fbdb4f284f59c886e20ee20`. The delta from served SHA to current `origin/main` includes Packet 5H `SEC-005` manifest retention substrate, Packet 5I `SEC-002` scaffolding, and Packet 5J hosted preflight.

### Failed Latest Created Revision

Revision `chronos-phase1-app-00088-q4q` failed startup before it could become ready.

Cloud Run status:

- revision: `chronos-phase1-app-00088-q4q`
- reason: `HealthCheckContainerError`
- startup failure: container exited before listening on port `8080`

The revision stderr traceback ended with:

```text
app.billing.pricebook.CommercialPricebookConfigurationError: COMMERCIAL_PRICEBOOK_JSON is required.
```

Revision `chronos-phase1-app-00088-q4q` also lacked literal values for `BUILD_SHA` and `BUILD_TIME` in its template, and the runtime verifier failed against the service template:

```text
FAIL: runtime verification failed for chronos-phase1-app @ chronos-phase1-app-00079-46f
- BUILD_TIME must be a non-empty literal env value
- BUILD_SHA must be a non-empty literal env value
- BUILD_SHA must look like a git commit SHA
```

The successful serving revision `chronos-phase1-app-00079-46f` still contains proper `BUILD_SHA`, `BUILD_TIME`, and commercial pricebook Secret Manager refs. The failure is therefore on the newer failed revision/template, not the current traffic-serving revision.

### GCS Bucket Readiness

Read-only bucket description for `gs://chronos-dev-kjlyuwiedsfcapduxdkn-raw` showed:

- location: `US-CENTRAL1`
- default storage class: `STANDARD`
- uniform bucket-level access: `true`
- soft delete retention: `604800` seconds
- no SEC-005 finite-prefix lifecycle rules were present in the bucket description output

No object listing, object reads, lifecycle-rule updates, Terraform operations, or manual cleanup were performed.

## Blockers

Packet 5K cannot close `SEC-005` until these blockers are resolved:

1. Current `origin/main` must be successfully deployed to the hosted validation service, or an explicitly chosen equivalent SHA must be recorded and justified.
2. Cloud Run revision `chronos-phase1-app-00088-q4q` startup failure must be resolved before using it or a successor revision for hosted proof.
3. Runtime build metadata must be present on the candidate hosted revision.
4. Migration `0027_phase5_sec005_manifest_retention.sql` still needs hosted dry-run/apply evidence before schema closeout can be claimed.
5. Hosted schema verification must prove `org_data_retention_settings`, `job_manifests` retention/redaction columns, RLS, grants, and check constraints.
6. GCS lifecycle rules for finite manifest prefixes must be imported/reviewed/planned/applied only after explicit operator approval.
7. Hosted Full + Redacted Museum manifest evidence is still missing.
8. Hosted expired-manifest and 0-day deleted-manifest not-found behavior evidence is still missing.
9. Cloud Audit Logs proof for at least one real lifecycle deletion event is still missing.
10. `SEC-005` compliance review and two-engineer review evidence is still missing.
11. The Phase 2 retention settings API/Web UI requirement remains explicitly deferred and must be reconciled before any global closeout claim.

## Required Approval Gates Before Continuing

The next execution loop must stop for explicit operator approval before:

- any Cloud Run deploy or traffic change
- any Supabase hosted migration dry-run or apply
- any Terraform import, plan, apply, state edit, or backend change
- any GCS lifecycle-rule mutation
- any elevated Cloud Audit Logs query for lifecycle-deletion proof
- any seeded hosted manifest job that writes real GCS objects
- any manual deletion or cleanup of hosted manifest objects
- any tracker, implementation-plan, or coverage-matrix change claiming `SEC-005` progress

## Recommended Next Loop

Proceed with `Packet 5K-A: hosted runtime/config recovery` before attempting SEC-005 closeout proof.

Minimum next-loop goals:

1. Deploy a candidate revision from current `origin/main` with valid `BUILD_SHA`, `BUILD_TIME`, and required commercial pricebook configuration.
2. Prove the candidate revision becomes ready and receives traffic only after health/version/runtime verification passes.
3. Capture runtime-before and runtime-after evidence.
4. Stop again before migration `0027`, Terraform lifecycle changes, hosted manifest writes, or lifecycle deletion proof.

## Packet Status

- Packet 5K status: `blocked-read-only`
- Global `SEC-005` status: open
- Phase 5 full-requirement count: remains `2/11`
