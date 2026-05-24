# ChronosRefine Phase 5 Packet 5K-D1 IAM Repair And Hosted Manifest Proof Note

Status: Hosted GCS object metadata/delete IAM repair is complete, and the hosted manifest proof rerun now passes for Museum redacted `90d` and `0d` retention behavior. This file records Packet 5K-D1 evidence only; it does not close `SEC-005`, does not advance Phase 5 tracker counts, and does not claim lifecycle audit-log, compliance, or two-engineer review completion.

- Packet: `Packet 5K-D1`
- Parent packet: `Packet 5K-D`
- Requirement focus: `SEC-005` Transformation Manifest Retention
- Related security posture: `SEC-004` least privilege
- Branch: `codex/phase5-packet5kd1-iam-manifest-proof`
- Source base before IAM repair: `7c5f7f6fdff0cf1af695bf237ba764b52d22421d`
- Cloud Run service: `chronos-phase1-app`
- Cloud Run revision: `chronos-phase1-app-00098-jnd`
- Hosted build: `{"version":"0.2.0","build_sha":"7c5f7f6fdff0cf1af695bf237ba764b52d22421d","build_time":"2026-05-24T21:31:10Z"}`
- Cloud Run service account: `19961431854-compute@developer.gserviceaccount.com`
- Target manifest bucket: `chronos-dev-kjlyuwiedsfcapduxdkn-raw`

Packet 5K-D1 repaired the exact hosted blocker found in Packet 5K-D. The runtime already had `storage.objects.create` through `roles/storage.objectCreator`, but manifest finalization also requires object metadata patching and `0d` delete. Packet 5K-D1 added only the missing object mutation permissions, then reran the hosted worker proof.

Infrastructure handles in this note are staging validation identifiers intentionally recorded for SEC-004/SEC-005 auditability. They are not credentials, signed URLs, raw object contents, or customer data. Artifact paths under `.tmp/packet5kd1-iam-manifest-proof/` are ephemeral local operator proof files; the durable repo-safe evidence is the sanitized summary recorded in this note.

## IAM Repair Evidence

Pre-repair artifacts:

- Runtime snapshot: `.tmp/packet5kd1-iam-manifest-proof/run-before-iam.json`
- Hosted version: `.tmp/packet5kd1-iam-manifest-proof/version-before.json`
- Bucket IAM before repair: `.tmp/packet5kd1-iam-manifest-proof/bucket-iam-before.json`
- Bucket lifecycle before repair: `.tmp/packet5kd1-iam-manifest-proof/bucket-before-iam.json`
- Lifecycle guard before repair: `.tmp/packet5kd1-iam-manifest-proof/bucket-lifecycle-before-iam-guard.txt` returned `true`
- IAM repair plan: `.tmp/packet5kd1-iam-manifest-proof/iam-repair-plan.json`

Applied IAM delta:

- Created custom role `projects/chronos-dev-489301/roles/chronosManifestObjectMutator`
- Custom role permissions:
  - `storage.objects.update`
  - `storage.objects.delete`
- Preserved existing bucket-level `roles/storage.objectCreator` grant for the Cloud Run service account
- Added bucket-level custom-role binding for the Cloud Run service account with condition:

```text
resource.name.startsWith("projects/_/buckets/chronos-dev-kjlyuwiedsfcapduxdkn-raw/objects/manifests/")
```

Post-repair artifacts:

- Custom role verification: `.tmp/packet5kd1-iam-manifest-proof/custom-role-after.json`
- Bucket IAM after repair: `.tmp/packet5kd1-iam-manifest-proof/bucket-iam-after.json`
- Bucket lifecycle after repair: `.tmp/packet5kd1-iam-manifest-proof/bucket-after-iam.json`
- Lifecycle guard after repair: `.tmp/packet5kd1-iam-manifest-proof/bucket-lifecycle-after-iam-guard.txt` returned `true`

Post-repair bucket IAM for the Cloud Run service account contains exactly:

- `roles/storage.objectCreator`
- `projects/chronos-dev-489301/roles/chronosManifestObjectMutator` with the `manifests/` object-prefix condition

The GCS lifecycle configuration remained unchanged and still contains only the four finite-prefix Delete rules for `manifests/7d/`, `manifests/90d/`, `manifests/365d/`, and `manifests/1825d/`.

## Hosted Manifest Proof Rerun

Packet 5K-D1 reran the hosted internal worker proof after IAM repair using synthetic Museum jobs:

- `packet5kd-museum-redacted-90d-20260524221339`
- `packet5kd-museum-redacted-0d-20260524221339`

Proof artifacts:

- Hosted probe result: `.tmp/packet5kd1-iam-manifest-proof/hosted-manifest-probe-result.json`
- Hosted assertion guard: `.tmp/packet5kd1-iam-manifest-proof/hosted-manifest-assertions-guard.txt` returned `true`
- Cloud Run log proof: `.tmp/packet5kd1-iam-manifest-proof/hosted-manifest-probe-cloudrun-logs.json`
- Hosted version after proof: `.tmp/packet5kd1-iam-manifest-proof/version-after.json`

Observed hosted result:

- Both worker invocations returned terminal `completed`.
- Both job rows have `last_error=null`.
- The `90d` Museum redaction-enabled job produced Full and Redacted manifests with the same basename.
- The `90d` Full and Redacted manifests both have `metageneration=2` and classification custom fields:
  - `artifact_type=transformation_manifest`
  - `classification_label=Internal`
  - `classification_policy_version=sec-003-v1`
  - `retention_days=90`
  - `retention_expires_at=2026-08-22T22:14:06.547496+00:00`
- The redacted payload excludes `user_id`, environment details, segment output URIs, and result URI.
- The redacted payload retains `source_manifest_sha256`.
- The `0d` Museum redaction-enabled job recorded `retention_delete_status=deleted` and `retention_deleted_at=2026-05-24 22:14:46.110242+00:00`.

Cloud Run logs for the successful rerun show:

- Full `90d` manifest upload: `HTTP/1.1 200 OK`
- Full `90d` metadata patch: `HTTP/1.1 200 OK`
- Redacted `90d` manifest upload: `HTTP/1.1 200 OK`
- Redacted `90d` metadata patch: `HTTP/1.1 200 OK`
- Full `0d` manifest upload: `HTTP/1.1 200 OK`
- Full `0d` metadata patch: `HTTP/1.1 200 OK`
- Redacted `0d` manifest upload: `HTTP/1.1 200 OK`
- Redacted `0d` metadata patch: `HTTP/1.1 200 OK`
- Full `0d` object delete: `HTTP/1.1 204 No Content`
- Redacted `0d` object delete: `HTTP/1.1 204 No Content`

Object-level artifacts:

- `90d` full object metadata: `.tmp/packet5kd1-iam-manifest-proof/object-90d-full.json`
- `90d` redacted object metadata: `.tmp/packet5kd1-iam-manifest-proof/object-90d-redacted.json`
- `0d` full object post-delete check: `.tmp/packet5kd1-iam-manifest-proof/object-0d-full-after-delete.err` returned `404`
- `0d` redacted object post-delete check: `.tmp/packet5kd1-iam-manifest-proof/object-0d-redacted-after-delete.err` returned `404`

The `90d` synthetic proof objects remain in the manifest bucket as hosted evidence and are covered by the `manifests/90d/` lifecycle rule. The `0d` synthetic proof objects were deleted by the hosted runtime.

## SEC-005 Status

`SEC-005` remains open after Packet 5K-D1.

Completed in this packet:

- Hosted IAM repair for manifest metadata patch and `0d` delete.
- Least-privilege custom role and conditional bucket binding recorded.
- Hosted Museum Full + Redacted `90d` proof passed.
- Hosted Museum `0d` delete proof passed.
- GCS lifecycle rules remained unchanged after IAM repair.

Still required before `SEC-005` closeout:

- Capture hosted expired-manifest behavior evidence beyond immediate `0d` deletion.
- Capture Cloud Audit Logs lifecycle-deletion proof for a real finite-prefix lifecycle deletion event.
- Record compliance review.
- Record two-engineer review.
- Decide whether to codify/import the custom IAM role and bucket binding into Terraform instead of leaving them as a manual hosted repair.
- Only then update tracker counts, implementation-plan status, or coverage-matrix closeout language.

Recommended next loop: `Packet 5K-E: lifecycle audit-log proof + compliance/two-engineer closeout preflight`, with a separate IaC follow-up if the team wants Terraform ownership of the D1 IAM repair before final closeout.
