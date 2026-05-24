# ChronosRefine Phase 5 Packet 5K-C GCS Lifecycle Preflight Note

Status: GCS lifecycle preflight complete; Terraform import and plan are blocked by the local Terraform core version. This file records read-only runtime, bucket, Terraform config, and state-posture evidence only. It does not close `SEC-005`, does not advance Phase 5 tracker counts, and does not claim lifecycle apply, hosted manifest, lifecycle audit-log, compliance, or two-engineer review evidence.

- Packet: `Packet 5K-C`
- Parent packet: `Packet 5K-B1`
- Requirement focus: `SEC-005` Transformation Manifest Retention
- Branch: `codex/phase5-packet5kc-gcs-lifecycle-preflight`
- Source base before preflight: `32bd9f46ddea3d0d9b1bdee00612cf1b953ec428`
- Cloud Run service: `chronos-phase1-app`
- Target manifest bucket: `chronos-dev-kjlyuwiedsfcapduxdkn-raw`

Packet 5K-C identified the hosted manifest bucket from the active Cloud Run runtime config and exported the bucket posture before Terraform ownership. The target bucket currently has no lifecycle rules in the read-only bucket description output. Terraform config already defines the expected finite-prefix lifecycle rules and excludes `manifests/0d/` and `manifests/indefinite/`, but import and plan were not executed because the local Terraform binary is below the repository constraint.

- `/health`: `{"status":"ok"}`
- `/v1/version`: `{"version":"0.2.0","build_sha":"32bd9f46ddea3d0d9b1bdee00612cf1b953ec428","build_time":"2026-05-24T03:37:13Z"}`
- Runtime verifier: `PASS: runtime verification passed for chronos-phase1-app @ chronos-phase1-app-00095-9xh`
- Cloud Run traffic: `100%` to `chronos-phase1-app-00095-9xh`
- Cloud Run manifest bucket env: `GCS_BUCKET_NAME=chronos-dev-kjlyuwiedsfcapduxdkn-raw`
- Bucket export: `gs://chronos-dev-kjlyuwiedsfcapduxdkn-raw/`, location `US-CENTRAL1`, location type `region`, default storage class `STANDARD`, uniform bucket-level access `true`, soft delete retention `604800` seconds
- Bucket lifecycle posture: no `lifecycle` field or SEC-005 finite-prefix lifecycle rules were present in the bucket description output
- Terraform lifecycle resource: `google_storage_bucket.manifest_retention[0]`, guarded by `manage_manifest_lifecycle_rules`
- Terraform lifecycle safeguards: `force_destroy = false`, `prevent_destroy = true`, and non-empty bucket-name precondition
- Terraform finite-prefix rules: `manifests/7d/`, `manifests/90d/`, `manifests/365d/`, and `manifests/1825d/`
- Terraform exclusion check: no `manifests/0d/` or `manifests/indefinite/` lifecycle rule is configured
- Terraform state posture: no backend is declared in `infra/terraform/*.tf`; local Terraform state files are ignored by `.gitignore`; no import or state mutation was performed
- Terraform toolchain blocker: repo requires `required_version = ">= 1.6.0"`, but `/opt/homebrew/bin/terraform` is `Terraform v1.5.7`
- Terraform init result: `terraform -chdir=infra/terraform init -backend=false -input=false` failed with `Unsupported Terraform Core version`

The next import/plan attempt must use a compatible Terraform binary without weakening the repository version constraint. After that toolchain gate is resolved, run import before plan so Terraform does not attempt to create or replace the existing bucket:

```bash
terraform -chdir=infra/terraform init -input=false
terraform -chdir=infra/terraform import \
  -var='project_id=chronos-dev-489301' \
  -var='manage_manifest_lifecycle_rules=true' \
  -var='manifest_lifecycle_bucket_name=chronos-dev-kjlyuwiedsfcapduxdkn-raw' \
  -var='manifest_lifecycle_bucket_location=US-CENTRAL1' \
  'google_storage_bucket.manifest_retention[0]' \
  chronos-dev-kjlyuwiedsfcapduxdkn-raw
terraform -chdir=infra/terraform plan \
  -var='project_id=chronos-dev-489301' \
  -var='manage_manifest_lifecycle_rules=true' \
  -var='manifest_lifecycle_bucket_name=chronos-dev-kjlyuwiedsfcapduxdkn-raw' \
  -var='manifest_lifecycle_bucket_location=US-CENTRAL1'
```

Stop after plan review. Do not run Terraform apply, mutate lifecycle rules, write hosted manifests, query lifecycle deletion audit logs, or move `SEC-005` tracker status without a separate approval gate.

`SEC-005` remains open after Packet 5K-C. Because no import or plan was actually performed under this packet, the next `SEC-005` hosted closeout loop should reconfirm operator approval before:

- installing or switching to a Terraform `>= 1.6.0` binary if the host remains on `1.5.7`
- Terraform import, plan, apply, or state operations
- GCS lifecycle-rule mutation
- hosted Full + Redacted Museum manifest writes
- hosted expired-manifest and 0-day deleted-manifest not-found proof
- Cloud Audit Logs lifecycle-deletion proof
- compliance review and two-engineer review recording
- any tracker, implementation-plan, or coverage-matrix progress claim

Recommended next loop: `Packet 5K-C1: Terraform toolchain recovery + lifecycle import/plan`, stopping before lifecycle apply unless lifecycle mutation is explicitly approved.
