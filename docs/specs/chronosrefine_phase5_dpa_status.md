# ChronosRefine Phase 5 DPA Status Note

**Status:** Approved external template path recorded
**Recorded On:** 2026-03-21
**Scope:** `SEC-006` AC-SEC-006-02 / DoD-SEC-006-02 for Museum tier customers

## Purpose

This repo-safe note records the current Data Processing Agreement (DPA) status for Museum tier customers without storing customer-specific legal language or privileged contract artifacts in git.

## Current Repo Truth

1. `SEC-006` requires a DPA to be available for Museum tier customers.
2. The product and pricing specs already position Museum as the institutional/compliance tier.
3. No git-managed DPA template is currently present on `main`.
4. Legal/compliance approval for the external template path is recorded in `docs/specs/chronosrefine_phase5_gdpr_legal_clearance.md`.

## Repo-Safe Status Record

- Museum tier DPA requirement: `required`
- Customer-facing template stored in git: `no`
- External legal-approved template reference: `approved external template path recorded in repo-safe form`
- Customer rollout posture: `Museum-tier DPA availability may be represented as approved, but delivery must continue through the legal-controlled artifact path rather than git-managed files`

## Operating Rule

When the DPA template changes, update the linked legal clearance note and this status note with:

1. approval date
2. reviewer role or team
3. sanitized external document or ticket reference
4. whether the approved template is generally available for all Museum tier customers or requires contract review per account
5. any required rollout caveats

## Gate Effect

This note satisfies the repo-local need to track DPA status for Phase 5 kickoff governance. The approved Museum-tier DPA template remains outside git-managed files, but the external template path is recorded and no longer blocks Packet 5A kickoff.
