# ChronosRefine Phase 5 Packet 5K-B1 Dependency Migration And Schema Note

Status: Hosted dependency migration and schema verification complete. This file records `0026` + `0027` migration evidence only. It does not close `SEC-003` or `SEC-005`, does not advance Phase 5 tracker counts, and does not claim GCS lifecycle, hosted manifest, lifecycle audit-log, compliance, or two-engineer review evidence.

- Packet: `Packet 5K-B1`
- Parent packet: `Packet 5K-B`
- Requirement focus: `SEC-005` Transformation Manifest Retention
- Dependency included by approval: `SEC-003` migration `0026_phase5_sec003_data_classification.sql`
- Branch: `codex/phase5-packet5kb1-dependency-migration-schema`
- Source base before hosted apply: `0d40379f93246157b62d05707d4952cced77092b`
- Cloud Run service: `chronos-phase1-app`
- Hosted DB: `chronos_dev`

Packet 5K-B1 applied the approved dependency migration pair to the hosted `chronos_dev` database through Supabase CLI after a scoped dry-run confirmed exactly two pending migrations:

- `0026_phase5_sec003_data_classification.sql`
- `0027_phase5_sec005_manifest_retention.sql`

Post-apply dry-run reported `Remote database is up to date.` Hosted schema verification confirmed the `SEC-003` classification columns and audit table are present, and the `SEC-005` retention/redaction schema, RLS posture, direct grants, and check constraints match the expected migration contract.

- Runtime-before `/health`: `{"status":"ok"}`
- Runtime-before `/v1/version`: `{"version":"0.2.0","build_sha":"0d40379f93246157b62d05707d4952cced77092b","build_time":"2026-05-24T02:53:44Z"}`
- Runtime verifier before apply: `PASS: runtime verification passed for chronos-phase1-app @ chronos-phase1-app-00094-q5c`
- Local precheck: `45 passed`
- Supabase dry-run before apply: exactly `0026_phase5_sec003_data_classification.sql` then `0027_phase5_sec005_manifest_retention.sql`
- Supabase apply: `Applying migration 0026_phase5_sec003_data_classification.sql...`; `Applying migration 0027_phase5_sec005_manifest_retention.sql...`; `Finished supabase db push.`
- Hosted schema-after: migration history contains `0026` / `phase5_sec003_data_classification` and `0027` / `phase5_sec005_manifest_retention`; `public.data_classification_audit_events` exists with RLS enabled and no direct `anon` / `authenticated` grants; SEC-003 classification and retention columns exist on `gcs_object_pointers`, `job_manifests`, `job_export_packages`, and `job_deletion_proofs`; `public.org_data_retention_settings` exists with RLS enabled and no direct `anon` / `authenticated` grants; `job_manifests` contains all SEC-005 redaction and retention columns.
- Hosted constraints-after: `job_manifests_retention_class_check` allows only `0d`, `7d`, `90d`, `365d`, `1825d`, `indefinite`, and `v0-backfill`; `job_manifests_retention_delete_status_check` allows only `pending`, `deleted`, `failed`, or null.
- Supabase dry-run after apply: `Remote database is up to date.`
- Local postcheck: `45 passed`
- Runtime verifier after apply: `PASS: runtime verification passed for chronos-phase1-app @ chronos-phase1-app-00094-q5c`

`SEC-003` and `SEC-005` remain open after Packet 5K-B1. The next `SEC-005` hosted closeout loop still requires explicit approval before:

- Terraform import/plan/apply/state operations
- GCS lifecycle-rule mutation
- hosted Full + Redacted Museum manifest writes
- hosted expired-manifest and 0-day deleted-manifest not-found proof
- Cloud Audit Logs lifecycle-deletion proof
- compliance review and two-engineer review recording
- any tracker, implementation-plan, or coverage-matrix progress claim

Recommended next loop: `Packet 5K-C: GCS lifecycle preflight/import/plan`, stopping before apply unless lifecycle mutation is explicitly approved.
