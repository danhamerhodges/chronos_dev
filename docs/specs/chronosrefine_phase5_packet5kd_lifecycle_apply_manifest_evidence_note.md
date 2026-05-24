# ChronosRefine Phase 5 Packet 5K-D GCS Lifecycle Apply And Hosted Manifest Evidence Note

Status: GCS finite-prefix lifecycle apply is complete and verified. Hosted manifest evidence remains blocked by bucket IAM for the Cloud Run service account. This file records Packet 5K-D evidence only; it does not close `SEC-005`, does not advance Phase 5 tracker counts, and does not claim lifecycle audit-log, compliance, or two-engineer review completion.

- Packet: `Packet 5K-D`
- Parent packet: `Packet 5K-C`
- Requirement focus: `SEC-005` Transformation Manifest Retention
- Branch: `codex/phase5-packet5kd-lifecycle-apply-manifest-evidence`
- Source base before apply: `dc2e37e22e03e47df357a01b059b295ccdc79cc2`
- Cloud Run service: `chronos-phase1-app`
- Cloud Run revision: `chronos-phase1-app-00097-7xf`
- Hosted build: `{"version":"0.2.0","build_sha":"dc2e37e22e03e47df357a01b059b295ccdc79cc2","build_time":"2026-05-24T14:34:15Z"}`
- Cloud Run service account: `19961431854-compute@developer.gserviceaccount.com`
- Target manifest bucket: `chronos-dev-kjlyuwiedsfcapduxdkn-raw`

Packet 5K-D re-ran the Packet 5K-C lifecycle preflight from a fresh isolated Terraform state, applied the saved lifecycle-only mutation after approval, and verified the live bucket. The packet then attempted hosted manifest evidence using two synthetic Museum jobs through the deployed internal worker path. The worker could upload full manifest objects but failed on GCS metadata patching with `403 Forbidden`, so hosted Full + Redacted manifest persistence and 0-day deletion evidence remain incomplete.

## Lifecycle Apply Evidence

- Terraform toolchain: scoped temporary Terraform `v1.6.6`; `hashicorp/google v7.22.0`
- Terraform state: isolated under `.tmp/packet5kd-lifecycle-apply/manifest-retention.tfstate`
- Fresh pre-apply bucket export: `.tmp/packet5kd-lifecycle-apply/bucket-before-apply.json`
- Terraform import artifact: `.tmp/packet5kd-lifecycle-apply/terraform-import.txt`
- Fresh targeted plan artifact: `.tmp/packet5kd-lifecycle-apply/terraform-plan-targeted.txt`
- Machine-readable plan artifact: `.tmp/packet5kd-lifecycle-apply/manifest-retention-targeted-plan.json`
- Plan guard result: `.tmp/packet5kd-lifecycle-apply/plan-guard-result.txt` returned `true`
- Planned resource action: exactly one resource, `google_storage_bucket.manifest_retention[0]`, action `update`
- Planned operation count: `Plan: 0 to add, 1 to change, 0 to destroy.`
- Planned lifecycle change: add Delete rules for `manifests/7d/`, `manifests/90d/`, `manifests/365d/`, and `manifests/1825d/`
- Planned exclusion check: no `manifests/0d/` or `manifests/indefinite/` lifecycle rule appears in the saved targeted plan
- Terraform apply artifact: `.tmp/packet5kd-lifecycle-apply/terraform-apply.txt`
- Apply result: `Apply complete! Resources: 0 added, 1 changed, 0 destroyed.`
- Post-apply bucket export: `.tmp/packet5kd-lifecycle-apply/bucket-after-apply.json`
- Post-apply bucket guard result: `.tmp/packet5kd-lifecycle-apply/post-apply-bucket-guard-result.txt` returned `true`

The live bucket now has exactly these lifecycle rules:

- Delete after `7` days for `manifests/7d/`
- Delete after `90` days for `manifests/90d/`
- Delete after `365` days for `manifests/365d/`
- Delete after `1825` days for `manifests/1825d/`

The live bucket still has no lifecycle rule for `manifests/0d/` or `manifests/indefinite/`.

## Hosted Manifest Evidence Attempt

Packet 5K-D used the deployed hosted runtime instead of test-only endpoints. Staging correctly exposes no `/v1/testing/*` helper surface, so the probe seeded synthetic Supabase jobs and invoked:

```text
POST /internal/workers/jobs/run
```

Synthetic probe jobs:

- `packet5kd-museum-redacted-90d-20260524151743`
- `packet5kd-museum-redacted-0d-20260524151743`

Probe artifact:

- `.tmp/packet5kd-lifecycle-apply/hosted-manifest-probe-result.json`

Observed hosted result:

- Both worker invocations returned terminal `failed`.
- Both job rows recorded `last_error="Manifest generation failed: "`.
- No `job_manifests` row was persisted for either synthetic job.
- No hosted Full + Redacted manifest pair was persisted.
- No hosted 0-day deleted-manifest row was recorded.
- The probe assertions `has_90d_redacted_job` and `has_0d_deleted_job` are both `false`.

Cloud Run log artifact:

- `.tmp/packet5kd-lifecycle-apply/hosted-manifest-probe-cloudrun-logs.json`

Cloud Run logs show the decisive failure mode:

- Full manifest upload to `manifests/90d/.../*.json`: `HTTP/1.1 200 OK`
- Metadata patch on the same `90d` object: `HTTP/1.1 403 Forbidden`
- Full manifest upload to `manifests/0d/.../*.json`: `HTTP/1.1 200 OK`
- Metadata patch on the same `0d` object: `HTTP/1.1 403 Forbidden`

Bucket IAM artifact:

- `.tmp/packet5kd-lifecycle-apply/bucket-iam-policy-after-hosted-probe.json`

Bucket IAM currently grants the Cloud Run service account only:

```text
roles/storage.objectCreator
```

That role is sufficient for hosted object upload but insufficient for the existing runtime's required metadata patch step. It is also insufficient for the 0-day delete path. Therefore hosted manifest redaction and 0-day deletion evidence cannot pass until the Cloud Run service account receives narrowly scoped object metadata update and delete capability for the manifest bucket.

## Probe Artifact Cleanup

The failed hosted probe created two full manifest objects before metadata patching failed. Their metadata was captured before cleanup:

- `.tmp/packet5kd-lifecycle-apply/orphan-90d-object-metadata.json`
- `.tmp/packet5kd-lifecycle-apply/orphan-0d-object-metadata.json`

Both synthetic orphan objects were then manually deleted after approval. Post-cleanup describe checks returned `404`:

- `.tmp/packet5kd-lifecycle-apply/orphan-90d-object-after-cleanup.err`
- `.tmp/packet5kd-lifecycle-apply/orphan-0d-object-after-cleanup.err`

The synthetic failed Supabase job rows remain as hosted evidence anchors. They did not produce retained manifest rows.

## SEC-005 Status

`SEC-005` remains open after Packet 5K-D.

Completed in this packet:

- GCS lifecycle rules applied for finite manifest prefixes.
- Post-apply bucket lifecycle verification captured.
- Hosted worker manifest attempt captured.
- Hosted IAM blocker identified precisely.
- Synthetic orphan GCS objects cleaned up after capture.

Still required before `SEC-005` closeout:

- Repair hosted manifest bucket IAM for the Cloud Run service account using least privilege.
- Re-run hosted Museum Full + Redacted manifest evidence.
- Re-run hosted 0-day deleted-manifest not-found evidence.
- Capture hosted expired-manifest behavior evidence.
- Capture Cloud Audit Logs lifecycle-deletion proof for a real lifecycle deletion event.
- Record compliance review and two-engineer review.
- Only then update tracker counts, implementation-plan status, or coverage-matrix closeout language.

Recommended next loop: `Packet 5K-D1: hosted GCS object metadata/delete IAM repair + manifest proof rerun`, with approval required before any IAM mutation.
