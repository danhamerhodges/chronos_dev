# ChronosRefine Phase 5 Packet 5M-A Auth Access Hardening Preflight Note

Status: Packet 5M-A adds local `SEC-001` and `SEC-004` auth/access hardening coverage and explicit security policy contracts. This packet does not close global `SEC-001` or `SEC-004`, does not record hosted IAM/audit proof, does not record penetration-test or security-review approval, and does not advance Phase 5 tracker counts.

- Packet: `Packet 5M-A`
- Requirement focus: `SEC-001` Authentication & Authorization; `SEC-004` Access Control
- Phase 5 status: remains `2/11` full requirements complete
- Global `SEC-001` status: remains open
- Global `SEC-004` status: remains open

## Implementation Scope

Packet 5M-A adds a local unit-testable substrate for the Phase 5 auth/access security suite:

1. RBAC permission lookup normalizes roles and permission names before evaluation and fails closed for unknown values.
2. Auth policy readbacks now declare SEC-001 session, host-only cookie, password, lockout, Museum API-key, MFA, token-revocation, and auth-audit-event contracts with explicit local-preflight metadata and fail-closed bounds for unsafe auth timing/lockout settings; runtime cookie issuance, auth callback behavior, and hosted enforcement remain deferred to hosted/integration evidence.
3. Canonical SEC-001 target files now exist for authentication, RBAC, MFA, and session-management coverage.
4. Canonical SEC-004 target files now exist for Terraform-managed IAM posture and Cloud Storage Data Access audit logging coverage.
5. Existing user-scoped Supabase profile lookup behavior remains intact: API-facing authenticated profile access passes the end-user bearer token into repository calls.

## Evidence Boundary

Packet 5M-A is local implementation/preflight evidence only.

- It does not implement hosted Museum API-key storage, key hashing, key rotation, key revocation persistence, or API-key request authentication.
- It does not implement hosted MFA enrollment, TOTP/SMS verification, backup-code recovery, supported MFA method selection, or Supabase MFA runtime enforcement.
- It does not run penetration testing, k6 authentication latency tests, IAM audit reports, provider-backed Terraform validate/plan evidence, or hosted Cloud Audit Logs readback.
- It does not mutate Terraform state, Supabase migrations, GCS objects, Cloud Logging, Cloud Run configuration, or IAM bindings.
- It does not close `SEC-001`, close `SEC-004`, or move Phase 5 beyond `2/11`.

## Remaining Gates Before SEC-001 Closeout

Global `SEC-001` remains open until a follow-up closeout packet records all of the following:

1. Supabase Auth integration evidence for email/password, OAuth, magic-link, token refresh, expired tokens, invalid signatures, and missing/tampered claims.
2. Hosted or integration evidence for Museum-only API-key authentication with valid, revoked, expired, and rate-limited keys.
3. Hosted or integration evidence for MFA enrollment/enforcement, including Museum tenant-admin enforcement and platform-admin enforcement.
4. Session-management evidence for secure cookie flags, browser auth callback compatibility, token revocation, concurrent-session behavior, and session-fixation resistance.
5. Auth audit-event persistence evidence for all required events.
6. Security review, penetration-test evidence, and two-engineer approval with zero critical/high vulnerabilities.

## Remaining Gates Before SEC-004 Closeout

Global `SEC-004` remains open until a follow-up closeout packet records all of the following:

1. Hosted IAM audit report proving least privilege for runtime, deploy, build, and manifest object mutation service accounts.
2. Quarterly IAM access-review schedule and cleanup process evidence.
3. Hosted Cloud Storage Data Access audit logging readback for GCS operations.
4. Hosted GCS tenant-isolation evidence for user/project-specific object access.
5. Full rate-limit evidence for Hobbyist `100/min`, Pro `1000/min`, and Museum `1000/min` with `429` + `Retry-After`.
6. Security review and two-engineer approval.

Recommended next loop after merge: `Packet 5M-B` hosted/API-key/MFA implementation or `Packet 5N` auth/access hosted evidence closeout, depending on whether runtime API-key and MFA support are complete.
