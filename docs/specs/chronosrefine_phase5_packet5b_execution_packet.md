# ChronosRefine Phase 5 Packet 5B Execution Packet

Status: Candidate execution packet for `FR-006` global closeout. This file records the decision-complete Packet 5B implementation contract on the candidate branch and does not change canonical source-of-truth ordering in `AGENTS.md`.

**Packet:** Packet 5B  
**Requirement Focus:** `FR-006`  
**Status:** In implementation on candidate branch  
**Baseline:** `origin/main` after PR #25 (`3782373a64f3cb3ec2ab2d43c7246d7d124e602a`)  
**Predecessor Packet:** `docs/specs/chronosrefine_phase5_packet5a_closeout_note.md`

## 1) Decision Summary

Packet 5B closes the remaining global `FR-006` gap by making public `POST /v1/jobs` honor the same approved-preview launch policy Packet 5A already enforces on preview launch and the first-party UI.

This packet intentionally changes the public generic launch contract:

- bare `/v1/jobs` launch payloads without preview provenance are no longer accepted
- refreshed saved launch payloads now carry `launch_context`
- repeated approved generic launches return `202` with the same existing `job_id`
- generic launch delegates to Packet 5A preview-launch semantics instead of creating a second approval or idempotency path

Packet 5B must remain narrow:

- no pricing enforcement work
- no GDPR delivery work
- no Phase 6 launch-readiness work
- no weakening of Packet 5A hosted proof or staging runtime hygiene

## 2) Public Contract

### 2.1 Job launch provenance

`JobCreateRequest` now carries optional wire-level provenance:

```json
{
  "launch_context": {
    "source": "approved_preview",
    "upload_id": "upload-123",
    "configuration_fingerprint": "<64-char sha256>"
  }
}
```

Rules:

- `launch_context` is optional in schema so omission can return policy `409`, not schema `422`
- `launch_context.source` is fixed to `approved_preview`
- `UploadConfigurationResponse.job_payload_preview` must include `launch_context` after Packet 5B so refreshed saved-config payloads are the canonical approved-launch handoff
- `launch_context` is transport metadata only and is excluded from the fingerprint hash

### 2.2 Legacy payload compatibility

Pre-5B saved payloads without `launch_context` are intentionally no longer valid for public `/v1/jobs`.

- result: `409 /problems/preview_approval_required`
- no server-side inference fallback from `media_uri`, `configured_at`, or other payload fields
- migration path: save or fetch configuration again, generate and approve the current preview, then relaunch with the refreshed payload

### 2.3 `/v1/jobs/estimate`

`/v1/jobs/estimate` formally accepts the same launch_context-capable request shape as `/v1/jobs`.

- provenance metadata is ignored for billing calculations
- preview approval is not enforced on estimate requests
- malformed request bodies or invalid `launch_context` still return `422`

## 3) Backend Contract

### 3.1 Enforcement path

Public `/v1/jobs` must:

1. require end-user JWT auth as today
2. resolve `launch_context.upload_id` on the owner-scoped upload path only
3. verify the latest saved configuration fingerprint matches both:
   - the request payload fingerprint computed without `launch_context`
   - `launch_context.configuration_fingerprint`
4. derive the current preview identity from `upload_id + configured_at`
5. require that preview to exist and be approved
6. delegate final launch to the existing Packet 5A preview-launch path

The lower-level `JobService.create_job` remains unchanged as the internal job creator and must not absorb preview policy.

### 3.2 Repeated launch and recovery

- repeated approved `/v1/jobs` calls for the same upload/fingerprint return `202 Accepted`
- response includes the same existing `job_id`
- no second job is created
- injected publish failure leaves the preview in `launch_pending`
- retry through `/v1/jobs` must reuse the same `job_id` and eventually dispatch successfully

### 3.3 Error precedence

- malformed request body or invalid `launch_context` field type/format/source -> `422`
- missing `launch_context` -> `409 /problems/preview_approval_required`
- no current approved preview -> `409 /problems/preview_approval_required`
- fingerprint or saved-config mismatch -> `409 /problems/preview_stale`
- expired preview -> `410 /problems/preview_expired`
- cross-user upload or preview resolution -> `404`

### 3.4 Auth boundary

All `/v1/jobs` preview-gate enforcement remains owner-scoped on the end-user JWT path.

- no service-role shortcut for user-request launch resolution
- preview lookup, upload lookup, and launch delegation must all preserve owner scoping

### 3.5 Schema/index checkpoint

Before closing Packet 5B, confirm the current upload/preview indexes are sufficient for the new `/v1/jobs` lookup path:

- owner-scoped upload lookup
- latest saved configuration lookup
- derived preview lookup by owner/upload/configured snapshot

Current candidate finding: existing indexes appear sufficient. If implementation exposes a concrete lookup gap, allow one narrow additive index-only migration and document it in closeout evidence.

## 4) Non-Regression Boundary

Packet 5B must preserve:

- Packet 5A preview-review and preview-launch behavior
- billing and overage behavior once preview gating passes
- current first-party UI behavior
- staging runtime verifier cleanliness
- current traceability and targeted web/a11y green state

Explicit non-regression:

- Packet 5A preview routes remain green
- `/v1/jobs/estimate` billing behavior remains unchanged
- generic launch now breaks bare public payloads intentionally, and this must be documented as the public API migration

## 5) Tests and Hosted Proof

Automated coverage must prove:

- missing `launch_context` blocks `/v1/jobs` with `409 /problems/preview_approval_required`
- malformed `launch_context` yields `422`
- pre-5B saved payload without `launch_context` is blocked
- refreshed saved payload with approved preview succeeds through `/v1/jobs`
- repeated `/v1/jobs` launch returns the same `job_id`
- stale anti-replay blocks generic launch after config resave
- cross-user generic launch denial holds
- publish-failure retry through `/v1/jobs` reuses the same `job_id` and clears `launch_pending`
- Packet 5A preview-launch route remains green
- `/v1/jobs/estimate` accepts the shared request shape and preserves billing/overage behavior

Hosted `chronos_dev` closeout must prove:

- preview create returns `pending`
- generic `/v1/jobs` without approved-preview provenance returns `409 /problems/preview_approval_required`
- pre-5B saved payload without `launch_context` returns `409 /problems/preview_approval_required`
- refreshed saved payload with approved preview succeeds through `/v1/jobs`
- repeated generic launch returns the same `job_id`
- stale anti-replay blocks generic launch
- cross-user denial works
- injected publish failure leaves `launch_pending`, retry reuses the same `job_id`, and dispatch eventually succeeds
- no `launch_pending` previews older than five minutes remain after recovery
- staging runtime evidence shows:
  - preview approval required failures for generic `/v1/jobs`
  - `preview_launch_pending_stale` signal when applicable
- hosted preview latency remains under the canonical `<6s p95` guardrail

## 6) Tracker Advancement Rule

Do not mark global `FR-006` complete and do not advance the Phase 5 full-requirement count until:

- Packet 5B local validation passes
- hosted `chronos_dev` proof passes
- Packet 5B closeout evidence is recorded

At that point:

- Packet 5B becomes the packet that closes global `FR-006`
- Phase 5 completed-requirement count advances to `1/11`
