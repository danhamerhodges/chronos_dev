# ChronosRefine Phase 5 Packet 5K-B Migration And Schema Note

Status: Blocked on dependency migration scope. This file records hosted migration/schema verification evidence only. It does not close `SEC-005`, does not advance Phase 5 tracker counts, and does not claim GCS lifecycle, hosted manifest, lifecycle audit-log, compliance, or two-engineer review evidence.

## Packet Scope

- Packet: `Packet 5K-B`
- Parent packet: `Packet 5K`
- Requirement focus: `SEC-005` Transformation Manifest Retention
- Branch: `codex/phase5-packet5kb-migration-schema-verification`
- Source base: `e332bdd2a1b29ec34d2881cff77e477b115a449e`
- Cloud Run service: `chronos-phase1-app`
- Hosted DB: `chronos_dev`

## Summary

Packet 5K-B confirmed the hosted runtime is ready for schema work, but stopped before applying any hosted migration because the Supabase dry-run surfaced an unapproved dependency boundary.

`supabase db push --dry-run` reported two pending migrations:

- `0026_phase5_sec003_data_classification.sql`
- `0027_phase5_sec005_manifest_retention.sql`

Hosted schema-before verification confirmed both surfaces are absent. A rollback-only dry-run of `0027` alone failed because `job_manifests.retention_expires_at` does not exist. A rollback-only dry-run of `0026` followed by `0027` succeeded and rolled back. Therefore `0027` cannot be safely applied through the canonical Supabase migration flow without also applying dependency migration `0026`.

## Evidence

- `/health`: `{"status":"ok"}`
- `/v1/version`: `{"version":"0.2.0","build_sha":"e332bdd2a1b29ec34d2881cff77e477b115a449e","build_time":"2026-05-24T02:15:07Z"}`
- Runtime verifier: `PASS: runtime verification passed for chronos-phase1-app @ chronos-phase1-app-00093-xwr`
- Local traceability validator: `Traceability validation passed.`
- Local SEC-005 regressions: `31 passed`
- Supabase CLI dry-run: would push `0026_phase5_sec003_data_classification.sql` and `0027_phase5_sec005_manifest_retention.sql`
- Hosted schema-before: `public.org_data_retention_settings` absent; `job_manifests` SEC-005 retention/redaction columns absent; SEC-003 classification columns absent
- `0027` rollback-only dry-run: failed with `ERROR: column "retention_expires_at" does not exist`
- `0026` + `0027` rollback-only dry-run: `exit_status=0`, ended with `ROLLBACK`
- Schema-after-dry-run matched schema-before; no hosted schema mutation was applied.

## Remaining Gates

`SEC-005` remains open after Packet 5K-B. The next migration/schema loop needs explicit approval to include dependency migration `0026` with target migration `0027`, or an alternate approved migration-history repair plan.

Stop gates still in force:

- no Terraform/GCS lifecycle mutation
- no hosted manifest writes
- no lifecycle-deletion audit-log claim
- no compliance or two-engineer review claim
- no tracker, implementation-plan, or coverage-matrix progress movement
