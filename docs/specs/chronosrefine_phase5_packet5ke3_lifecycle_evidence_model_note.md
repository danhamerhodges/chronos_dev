# ChronosRefine Phase 5 Packet 5K-E3 Lifecycle Evidence Model Repair Note

Status: Packet 5K-E3 records the final finite-prefix lifecycle observation for the Packet 5K-E1 proof object and repairs the `SEC-005` lifecycle deletion evidence model. The seeded object is no longer retrievable, but Cloud Audit Logs did not emit `storage.objects.delete` for the GCS Object Lifecycle Management action. This packet accepts a compensating evidence model for lifecycle-managed deletion only. It does not close `SEC-005`, does not advance Phase 5 tracker counts, and does not claim compliance review or two-engineer review completion.

- Packet: `Packet 5K-E3`
- Parent packets: `Packet 5K-E1`, `Packet 5K-E2`
- Requirement focus: `SEC-005` Transformation Manifest Retention
- Related security posture: `SEC-004` least privilege and auditability
- Branch: `codex/phase5-packet5ke3-lifecycle-evidence`
- Source base before Packet 5K-E3: `9964a1628f8a18dd14f86b7965707d2c99b67031`
- Cloud project: `chronos-dev-489301`
- Target manifest bucket: `chronos-dev-kjlyuwiedsfcapduxdkn-raw`
- Proof object: `gs://chronos-dev-kjlyuwiedsfcapduxdkn-raw/manifests/7d/packet5ke1-lifecycle-proof-20260525T020609Z.json`

## Platform Logging Limitation

Packet 5K-E3 verified the original closeout proof shape against Google Cloud documentation and live evidence. Google Cloud's Cloud Storage audit-log restrictions state that Cloud Audit Logs does not track Object Lifecycle Management changes:

- Cloud Audit Logs with Cloud Storage: `https://cloud.google.com/storage/docs/audit-logging`
- Object Lifecycle Management: `https://cloud.google.com/storage/docs/lifecycle`
- Cloud Storage usage logs: `https://cloud.google.com/storage/docs/access-logs`

Google's lifecycle documentation also identifies Cloud Storage usage logs and Pub/Sub notifications as the supported options for tracking lifecycle actions. Usage logs can identify lifecycle actions through the `GCS Lifecycle Management` user-agent value, while Pub/Sub notifications can report object events without identifying the actor. Packet 5K-E3 does not enable either surface; it records the platform limitation and the compensating evidence accepted for this hosted closeout path.

## Lifecycle Evidence Observed

Packet 5K-E1 created the repo-safe finite-prefix proof object:

```text
gs://chronos-dev-kjlyuwiedsfcapduxdkn-raw/manifests/7d/packet5ke1-lifecycle-proof-20260525T020609Z.json
```

Creation evidence:

- Created: `2026-05-25T02:07:57Z`
- Generation: `1779674877479453`
- Size: `361`
- Prefix: `manifests/7d/`
- Retention class tested: finite 7-day lifecycle prefix

Lifecycle configuration readback confirmed the finite-prefix delete rules remain present:

```text
manifests/7d/    Delete at age 7 days
manifests/90d/   Delete at age 90 days
manifests/365d/  Delete at age 365 days
manifests/1825d/ Delete at age 1825 days
```

The `manifests/0d/` and `manifests/indefinite/` prefixes remain excluded from GCS lifecycle rules.

Observed object read timeline:

```text
2026-06-01T13:03:28.631840912Z storage.objects.get status={}
2026-06-02T13:12:36.814108544Z storage.objects.get status={code: 5, message: No such object}
2026-06-03T13:01:23.567713735Z storage.objects.get status={code: 5, message: No such object}
```

The object was present after becoming lifecycle-eligible and was no longer retrievable by the next hosted audit window. This demonstrates lifecycle-driven disappearance for the finite `manifests/7d/` prefix, but does not produce a Cloud Audit Logs delete method entry.

## Cloud Audit Logs Readback

Storage Data Access audit logging remains enabled for Cloud Storage:

```json
{
  "auditConfigs": [
    {
      "auditLogConfigs": [
        {
          "logType": "DATA_WRITE"
        },
        {
          "logType": "DATA_READ"
        }
      ],
      "service": "storage.googleapis.com"
    }
  ]
}
```

Cloud Audit Logs captured the proof object's create/read activity:

```text
2026-05-25T02:07:57.458911465Z storage.objects.create
2026-05-25T02:08:22.069770622Z storage.objects.get
2026-05-25T02:36:06.850757067Z storage.objects.get
2026-06-01T13:03:28.631840912Z storage.objects.get
2026-06-02T13:12:36.814108544Z storage.objects.get status=No such object
2026-06-03T13:01:23.567713735Z storage.objects.get status=No such object
```

The exact delete query required by the original closeout model returned no events:

```text
logName="projects/chronos-dev-489301/logs/cloudaudit.googleapis.com%2Fdata_access"
protoPayload.serviceName="storage.googleapis.com"
protoPayload.methodName="storage.objects.delete"
protoPayload.resourceName="projects/_/buckets/chronos-dev-kjlyuwiedsfcapduxdkn-raw/objects/manifests/7d/packet5ke1-lifecycle-proof-20260525T020609Z.json"
timestamp>="2026-05-25T02:07:57Z"
```

Result:

```json
[]
```

A delayed-log follow-up using the same exact delete query after `2026-06-01T13:03:28Z` also returned:

```json
[]
```

A bucket-scoped `storage.objects.delete` query after `2026-06-01T13:03:28Z` likewise returned:

```json
[]
```

## Approved Compensating Evidence Model

For GCS Object Lifecycle Management deletions, `SEC-005` lifecycle deletion evidence may be satisfied by all of the following, without requiring a non-emitted Cloud Audit Logs delete event:

1. Lifecycle rule readback for the exact finite prefix under test.
2. Proof object creation evidence with bucket, prefix, timestamp, and generation.
3. Cloud Audit Logs create/read evidence showing Data Access logging is enabled and object access is observable.
4. Successful proof-object read after creation and before lifecycle disappearance.
5. Post-threshold proof-object read returning `No such object`.
6. Explicit readback that exact and delayed `storage.objects.delete` Cloud Audit Logs queries return no events.
7. Official Google Cloud documentation citation showing Object Lifecycle Management changes are outside Cloud Audit Logs tracking.

Cloud Audit Logs remain required for emitted user/API-driven object operations. This compensating model applies only to lifecycle-managed deletion performed by GCS Object Lifecycle Management.

## SEC-005 Status

Completed in this packet:

- Recorded lifecycle-managed disappearance for the seeded `manifests/7d/` proof object.
- Recorded Cloud Audit Logs create/read evidence and post-deletion `No such object` evidence.
- Recorded that exact and delayed Cloud Audit Logs delete queries remain empty.
- Repaired the evidence model to use Google-supported lifecycle proof instead of a non-emitted audit event.
- Preserved `SEC-005` open status and Phase 5 tracker counts.

Still required before `SEC-005` closeout:

- Record compliance review approval for the compensating evidence model.
- Record two-engineer review approval in repo-safe form.
- Confirm manual verification obligations are satisfied under the revised evidence model.
- Only then update Phase 5 tracker counts, implementation-plan status, or closeout language.

Recommended next loop: `Packet 5K-E4` compliance and two-engineer closeout preflight for the revised `SEC-005` lifecycle evidence model.
