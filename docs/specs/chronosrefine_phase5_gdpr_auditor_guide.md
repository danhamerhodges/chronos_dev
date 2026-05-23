# ChronosRefine Phase 5 GDPR Auditor Guide

**Status:** Repo-side verification guidance recorded; legal/compliance approval recorded
**Recorded On:** 2026-03-21
**Scope:** `SEC-006` AC-SEC-006-08a / AC-SEC-006-10 and related deletion-proof verification posture on `main`

## Purpose

This repo-safe guide documents the current technical verification posture for ChronosRefine deletion-proof evidence on `main`. It is intended to support auditor handoff preparation and internal review after the Phase 5 legal/compliance kickoff approval has been recorded. It is not a substitute for customer-specific legal advice or contract review.

## Current Technical Surfaces

1. `POST /v1/user/delete_logs` records a right-to-erasure log deletion request and returns a deletion request ID plus deletion proof ID.
2. `GET /v1/deletion-proofs/{proof_id}` returns owner-scoped deletion-proof metadata with a signed PDF download URL.
3. Output-delivery proof generation currently uses `HMAC-SHA256` over `deletion_proof_id:proof_sha256`.

## Current Proof Fields Exposed On `main`

The deletion-proof API response currently exposes:

- `deletion_proof_id`
- `job_id`
- `generated_at`
- `signature_algorithm`
- `signature`
- `proof_sha256`
- `pdf_download_url`
- `pdf_expires_at`
- `verification_summary`

The `verification_summary` currently includes:

- `status`
- `result_uri`
- `manifest_sha256`
- `original_checksum`

## Internal Verification Procedure

For the current `main` implementation, the repo-side verification procedure is:

1. Request the deletion proof through the owner-scoped route and confirm `Cache-Control: private, no-store`.
2. Confirm `signature_algorithm` is `HMAC-SHA256`.
3. Confirm `signature` and `proof_sha256` are non-empty.
4. Confirm `verification_summary.status` is `verified`.
5. For internal engineering or controlled auditor review with repository access, retrieve the stored `proof_payload`, recompute the payload SHA-256, and verify that the stored signature matches `HMAC-SHA256(deletion_proof_id:proof_sha256)` using the server-managed signing key.

## Current Limitations

1. The public API does not expose the full `proof_payload`, so independent third-party verification cannot be completed from the external API response alone.
2. External auditor verification therefore currently requires a controlled evidence bundle or operator-assisted validation procedure.
3. This guide records technical posture only; it does not grant legal approval or attest that the broader Phase 5 `SEC-006` implementation is complete.

## Current Repo Evidence

- `tests/compliance/test_gdpr_log_deletion.py`
- `tests/api/test_deletion_proof.py`
- `app/api/logs.py`
- `app/api/deletion_proofs.py`
- `app/services/output_delivery.py`

## Next Update Needed

When the auditor distribution path changes, update this guide or a linked external artifact reference with:

1. sanitized auditor-facing evidence package reference
2. approved external verification/distribution method for proof validation
3. any contractual or customer-specific caveats for Museum tier reviews
