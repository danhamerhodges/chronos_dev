# ChronosRefine Phase 5 Packet 5K-E IAM Terraform And Audit Closeout Preflight Note

Status: Packet 5K-D1 hosted IAM repair is now codified in Terraform, the existing custom role and conditional bucket IAM member were imported into isolated local Terraform state, and the targeted IAM plan converges with no hosted changes. Lifecycle audit-log and compliance/two-engineer closeout preflight is complete, but `SEC-005` remains open because real lifecycle-deletion Cloud Audit Logs proof, compliance review, and two-engineer review are not yet available.

- Packet: `Packet 5K-E`
- Parent packet: `Packet 5K-D1`
- Requirement focus: `SEC-005` Transformation Manifest Retention
- Related security posture: `SEC-004` least privilege
- Branch: `codex/phase5-packet5ke-iam-terraform-audit-preflight`
- Source base before Packet 5K-E: `6dbf6d6b4399728ac010a115706ac57dd444e8d9`
- Cloud project: `chronos-dev-489301`
- Cloud Run service account: `19961431854-compute@developer.gserviceaccount.com`
- Target manifest bucket: `chronos-dev-kjlyuwiedsfcapduxdkn-raw`

This packet does not close `SEC-005`, does not advance Phase 5 tracker counts, and does not claim lifecycle audit-log, compliance, or two-engineer review completion.

## Terraform Codification

Packet 5K-E added opt-in Terraform ownership for the Packet 5K-D1 manual IAM repair:

- `infra/terraform/iam.tf`
  - `google_project_iam_custom_role.manifest_object_mutator`
  - `google_storage_bucket_iam_member.runtime_manifest_object_mutator`
- `infra/terraform/variables.tf`
  - `manage_manifest_object_mutator_iam`
  - `manifest_object_mutator_service_account`
  - `manifest_object_mutator_role_id`

The new Terraform block is disabled by default through `manage_manifest_object_mutator_iam = false`. Hosted operators must explicitly enable it and provide the manifest bucket plus runtime service account before Terraform manages the IAM repair.

The codified role remains limited to the two missing permissions proven in Packet 5K-D1:

- `storage.objects.delete`
- `storage.objects.update`

The codified bucket binding remains conditioned to manifest objects only:

```text
resource.name.startsWith("projects/_/buckets/chronos-dev-kjlyuwiedsfcapduxdkn-raw/objects/manifests/")
```

The existing `roles/storage.objectCreator` bucket grant remains separate and unchanged.

## Terraform Import And Plan Evidence

Packet 5K-E used isolated local Terraform state under `.tmp/packet5ke-iam-terraform-audit-preflight/`; no remote backend state was modified. Terraform `v1.15.4` was downloaded into `.tmp/terraform-1.15.4`, and the local zip checksum matched HashiCorp's published `terraform_1.15.4_SHA256SUMS` entry for `terraform_1.15.4_darwin_arm64.zip`.

Terraform validation:

```text
Success! The configuration is valid.
```

Imported custom role:

```text
Address: google_project_iam_custom_role.manifest_object_mutator[0]
Import ID: projects/chronos-dev-489301/roles/chronosManifestObjectMutator
Result: Import successful
```

Imported conditional bucket IAM member:

```text
Address: google_storage_bucket_iam_member.runtime_manifest_object_mutator[0]
Import ID: b/chronos-dev-kjlyuwiedsfcapduxdkn-raw projects/chronos-dev-489301/roles/chronosManifestObjectMutator serviceAccount:19961431854-compute@developer.gserviceaccount.com packet5kd1ManifestObjectsOnly
Result: Import successful
```

Isolated state list after import:

```text
google_project_iam_custom_role.manifest_object_mutator[0]
google_storage_bucket_iam_member.runtime_manifest_object_mutator[0]
```

Targeted IAM convergence plan:

```text
No changes. Your infrastructure matches the configuration.
```

The targeted plan intentionally covered only the two imported IAM resources. It did not apply changes and did not attempt full-root Terraform ownership of unrelated IAM, monitoring, alerting, or lifecycle resources.

## Live IAM And Bucket Posture

Live custom role readback:

- Name: `projects/chronos-dev-489301/roles/chronosManifestObjectMutator`
- Title: `Chronos Manifest Object Mutator`
- Stage: `GA`
- Permissions:
  - `storage.objects.delete`
  - `storage.objects.update`

Live bucket IAM readback for the runtime service account contains exactly:

- `roles/storage.objectCreator`
- `projects/chronos-dev-489301/roles/chronosManifestObjectMutator` with condition title `packet5kd1ManifestObjectsOnly`

Live bucket lifecycle readback still contains only the four finite-prefix Delete rules:

- `manifests/7d/`
- `manifests/90d/`
- `manifests/365d/`
- `manifests/1825d/`

No `manifests/0d/` or `manifests/indefinite/` lifecycle rule is present.

## Lifecycle Audit-Log Preflight

Packet 5K-E ran read-only Cloud Audit Logs and IAM audit-config queries for the manifest bucket.

Project audit config readback:

```text
gcloud projects get-iam-policy chronos-dev-489301 --format='json(auditConfigs)'
null
```

Recent bucket admin activity exists for the lifecycle apply and IAM repair:

- `2026-05-24T15:09:50.990773147Z` `storage.buckets.update`
- `2026-05-24T22:10:08.060193929Z` `storage.setIamPermissions`

Manifest object delete audit-log query for events since `2026-05-24T00:00:00Z` returned:

```json
[]
```

Manifest object activity audit-log query for events since `2026-05-24T00:00:00Z` returned:

```json
[]
```

Therefore Packet 5K-E does not have lifecycle-deletion audit-log proof. The current project IAM policy does not show Cloud Storage Data Access audit logging enabled, and the shortest applied lifecycle rule is `manifests/7d/`, so a real finite-prefix lifecycle deletion event cannot be proven from the current audit-log query results.

## Compliance And Two-Engineer Preflight

Canonical `SEC-005` still requires:

- `DoD-SEC-005-09`: Deletion events tested through Cloud Audit Logs
- `DoD-SEC-005-11`: Code review approved by 2+ engineers plus compliance review
- Verification method: automated tests plus manual compliance verification

Packet 5K-E found no repo-safe `SEC-005` compliance review note and no repo-safe two-engineer review note for final closeout. Those gates remain open.

## SEC-005 Status

Completed in this packet:

- D1 custom IAM repair codified in Terraform.
- Existing custom role imported into isolated local Terraform state.
- Existing conditional bucket IAM member imported into isolated local Terraform state.
- Targeted IAM plan proved no hosted changes are needed for those imported resources.
- Live IAM and lifecycle posture re-read after import/plan.
- Audit-log and compliance/two-engineer closeout preflight completed without premature closeout claims.

Still required before `SEC-005` closeout:

- Enable and verify Cloud Storage Data Access audit logging for lifecycle deletion evidence, if not already enabled through another approved control path.
- Capture a real finite-prefix lifecycle deletion event in Cloud Audit Logs.
- Record compliance review in repo-safe form.
- Record two-engineer review in repo-safe form.
- Reconcile `SEC-005` manual verification obligations before any tracker/count movement.
- Only then update Phase 5 tracker counts, implementation-plan status, or closeout language.

Recommended next loop: `Packet 5K-E1: Storage Data Access audit logging enable/import/plan/apply + finite-prefix lifecycle proof setup`, stopping before any project audit-config mutation or synthetic proof-object write without explicit approval.
