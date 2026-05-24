# ChronosRefine Phase 5 Packet 5J Hosted Closeout Preflight

Status: Context-only hosted closeout preflight note. This file does not alter canonical source-of-truth ordering in `AGENTS.md`, does not close `SEC-005`, and does not advance Phase 5 tracker counts.

## Packet 5J Scope

- Packet: `Packet 5J`
- Requirement focus: `SEC-005` Transformation Manifest Retention
- Candidate branch: `codex/phase5-packet5j-sec005-hosted-preflight`
- Source base: `origin/main` at merge commit `8eea2190e1799a7816fcefaebf42ec1b2753ca5f`
- Predecessor evidence: `docs/specs/chronosrefine_phase5_packet5h_implementation_note.md`
- Target hosted environment: `chronos_dev`
- Target Cloud Run service: `chronos-phase1-app`

## Summary

Packet 5J binds the hosted closeout boundary for `SEC-005` after Packet 5H landed the local transformation-manifest retention substrate.

The goal of this preflight is to make the next hosted execution loop safe and reviewable before any remote mutation occurs. The preflight captures the required read set, evidence paths, approval gates, rollback posture, and validation commands for applying migration `0027`, deploying the completed runtime, enabling GCS lifecycle rules, and collecting hosted proof for redacted manifests plus lifecycle deletion audit logs.

This packet is planning and governance only. It does not run migrations, deploy services, mutate Terraform-managed resources, alter GCS bucket lifecycle rules, query production data, or claim hosted evidence.

## Requirement And Dependency Check

Canonical requirement:

- `SEC-005`: Transformation Manifest Retention
- Canonical definition: `docs/specs/chronosrefine_security_operations_requirements.md#sec-005-transformation-manifest-retention`
- Phase: Phase 5, Advanced Features & UX Refinement
- Coverage Matrix dependency: `SEC-013`
- Matrix test files:
  - `tests/security/test_manifest_retention.py`
  - `tests/security/test_manifest_redaction.py`
  - `tests/compliance/test_gdpr_manifest_retention.py`

Dependency posture:

- `SEC-013` is satisfied as a Phase 1 foundation requirement and may be relied on for authenticated hosted access.
- `ENG-010` transformation-manifest generation is a related requirement and must remain intact; Packet 5J must not change manifest schema semantics beyond hosted verification of Packet 5H behavior.
- `SEC-003` data-classification substrate exists as partial Phase 5 evidence from Packet 5G; Packet 5J may rely on its merged classification labels but must not close global `SEC-003`.
- `SEC-006` GDPR workflows depend on retention behavior but remain explicitly out of scope for Packet 5J.

Current Phase 5 status:

- Phase 5 remains `2/11` full requirements complete.
- Complete: `FR-006`, `NFR-006`.
- `SEC-005` remains open until hosted proof, compliance review, and two-engineer review evidence are recorded.

## In Scope

Packet 5J preflight covers the next hosted execution boundary for:

1. Deploying the current `origin/main` runtime to the shared hosted validation service after explicit approval.
2. Applying and verifying migration `0027_phase5_sec005_manifest_retention.sql` after explicit approval.
3. Importing or reviewing the target GCS bucket before Terraform manages lifecycle rules.
4. Enabling `manage_manifest_lifecycle_rules` only after bucket-owner approval and lifecycle-rule review.
5. Verifying finite manifest lifecycle rules for:
   - `manifests/7d/`
   - `manifests/90d/`
   - `manifests/365d/`
   - `manifests/1825d/`
6. Capturing hosted Full + Redacted Museum manifest evidence.
7. Capturing hosted expired/0-day retention behavior evidence.
8. Capturing Cloud Audit Logs evidence for at least one real lifecycle deletion event.
9. Recording compliance and two-engineer review status without claiming it prematurely.

## Out Of Scope

Packet 5J must not include:

- tracker movement or Phase 5 count changes
- global `SEC-005` closeout before hosted evidence is recorded
- global `SEC-003` closeout
- `SEC-006` erasure request orchestration, right-to-access workflows, consent workflows, or full GDPR closeout
- Phase 2 retention settings API or Web UI (`PATCH /v1/orgs/{org_id}/settings/retention`)
- `SEC-002` encryption hosted proof or cryptographic audit work
- `SEC-008` VPC Service Controls
- product-surface or UI changes
- new dependencies
- destructive cleanup of existing manifests or buckets

## Stop Gates

The following actions require explicit operator approval in the execution loop:

1. Any Cloud Run deploy or traffic change.
2. Any Supabase hosted migration dry run or apply.
3. Any Terraform import, plan, apply, state edit, or backend change.
4. Any GCS lifecycle-rule mutation.
5. Any Cloud Audit Logs query that requires elevated project access.
6. Any seeded hosted manifest job that writes real GCS objects.
7. Any manual deletion or cleanup of hosted manifest objects.
8. Any tracker, implementation-plan, or coverage-matrix change claiming `SEC-005` progress.

If any stop gate cannot be approved or evidenced, the execution loop must close as blocked with the missing approval or artifact named.

## Hosted Evidence Checklist

The execution loop may only claim `SEC-005` hosted closeout after all required evidence exists.

### Runtime And Migration

- [ ] Runtime version endpoint captured before deploy.
- [ ] Candidate deploy SHA and revision recorded.
- [ ] Migration `0027` dry-run evidence captured.
- [ ] Migration `0027` applied to `chronos_dev`.
- [ ] Hosted schema verification confirms:
  - `public.org_data_retention_settings` exists.
  - `public.org_data_retention_settings` has RLS enabled.
  - `anon` and `authenticated` do not have direct table grants.
  - `public.job_manifests` contains Packet 5H retention and redaction columns.
  - `job_manifests_retention_class_check` allows only `0d`, `7d`, `90d`, `365d`, `1825d`, `indefinite`, and `v0-backfill`.
  - `job_manifests_retention_delete_status_check` allows only `pending`, `deleted`, `failed`, or null.

### Manifest Retention And Redaction

- [ ] Hobbyist hosted manifest resolves to `7d`.
- [ ] Pro hosted manifest resolves to `90d`.
- [ ] Museum default hosted manifest resolves to `indefinite`.
- [ ] Museum configured hosted manifests cover `0d`, `90d`, `365d`, `1825d`, and `indefinite`.
- [ ] Museum redaction-enabled run writes Full and Redacted manifests with a shared basename.
- [ ] Redacted manifest excludes PII-bearing fields and operational environment details.
- [ ] Redacted manifest retains reproducibility information.
- [ ] Owner-scoped manifest retrieval continues to deny cross-user reads.
- [ ] Expired manifests and 0-day deleted manifests return the existing not-found behavior.

### GCS Lifecycle And Audit Logs

- [ ] Target manifest bucket identified and recorded.
- [ ] Existing lifecycle rules exported before Terraform ownership.
- [ ] Terraform import or state posture recorded before `google_storage_bucket.manifest_retention` management.
- [ ] Terraform plan shows only expected finite-prefix lifecycle rules.
- [ ] Lifecycle rules exclude `manifests/0d/` and `manifests/indefinite/`.
- [ ] Lifecycle rules are applied only after operator approval.
- [ ] At least one real lifecycle deletion event appears in Cloud Audit Logs.
- [ ] Audit-log evidence links deletion to the expected manifest prefix and bucket.

### Reviews

- [ ] Compliance review result recorded.
- [ ] Two-engineer review result recorded.
- [ ] Residual risks and follow-up items recorded.

## Evidence Paths

Recommended repo-local proof directory for execution artifacts:

```text
.tmp/packet5j-sec005-hosted-closeout/
```

Recommended artifact names:

- `runtime-before.json`
- `runtime-after.json`
- `version-before.json`
- `version-after.json`
- `migration-0027-dry-run.txt`
- `migration-0027-apply.txt`
- `schema-verification.json`
- `bucket-before-lifecycle.json`
- `terraform-import.txt`
- `terraform-plan.txt`
- `terraform-apply.txt`
- `manifest-retention-proof.json`
- `manifest-redaction-proof.json`
- `manifest-access-control-proof.json`
- `lifecycle-audit-log-proof.json`
- `compliance-review-note.md`
- `two-engineer-review-note.md`

Do not commit secret-bearing tokens, raw customer data, signed URLs, private bucket object contents, privileged legal communications, or hosted credentials. Summaries copied into `docs/specs/*` must be repo-safe and sanitized.

## Validation Commands

Documentation/preflight validation:

```bash
git diff --check -- docs/specs/chronosrefine_phase5_packet5j_hosted_preflight.md
python3 scripts/validate_test_traceability.py
bash .agents/skills/spec-consistency-audit/scripts/audit_specs.sh /private/tmp/chronos_phase5_packet5j_sec005_hosted_preflight
rg -n "SEC-005|Packet 5J|0027|manifest lifecycle|Cloud Audit Logs" docs/specs/chronosrefine_phase5_packet5j_hosted_preflight.md docs/specs/chronosrefine_phase5_packet5h_implementation_note.md docs/specs/chronosrefine_security_operations_requirements.md "docs/specs/ChronosRefine Requirements Coverage Matrix.md" docs/specs/chronosrefine_implementation_plan.md
```

Local implementation non-regression commands to rerun before any hosted execution:

```bash
python3 scripts/validate_test_traceability.py
uv run --extra dev pytest -q tests/security/test_manifest_retention.py tests/security/test_manifest_redaction.py tests/compliance/test_gdpr_manifest_retention.py tests/database/test_schema_migrations.py
```

Hosted execution commands are intentionally not included as directly runnable commands in this preflight note. The execution loop must derive exact commands after operator approval, target environment confirmation, and credential availability checks.

## Reviewer Checklist

- [ ] Packet targets only `SEC-005`.
- [ ] Packet does not claim `SEC-005` completion or Phase 5 count movement.
- [ ] Hosted proof cannot be claimed from local tests alone.
- [ ] `SEC-006`, `SEC-002`, `SEC-003`, and Phase 2 retention settings remain out of scope.
- [ ] GCS lifecycle changes are treated as authoritative bucket mutations and require explicit approval.
- [ ] Migration `0027` and Terraform lifecycle actions are approval-gated.
- [ ] Evidence paths are repo-safe and exclude secrets/customer data.
- [ ] Rollback and residual risks are named.

## Rollback And Risk Notes

Migration `0027` is additive for retention settings and manifest metadata, but hosted rollback should still be deploy/config-first unless an approved database rollback plan exists. Do not drop hosted columns or tables without a separate rollback packet and explicit approval.

GCS bucket lifecycle configuration is authoritative when managed through `google_storage_bucket`. The execution loop must export and review existing lifecycle rules before import/apply to avoid overwriting unrelated bucket policies.

If lifecycle deletion behavior cannot be observed within the execution window, close the hosted loop as partially complete and record the missing Cloud Audit Logs proof rather than advancing `SEC-005`.

If redacted-manifest proof reveals PII leakage, stop immediately, preserve sanitized evidence, and route the fix through a new implementation packet before any closeout claim.
