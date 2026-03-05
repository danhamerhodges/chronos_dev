# ChronosRefine Security & Operations Requirements

**Purpose:** Security, compliance, monitoring, and operational requirements  
**Audience:** Security engineers, DevOps/SRE, compliance officers  
**Companion Documents:** ChronosRefine_Security_Implementation_Guide.md  
**Last Updated:** February 2026

---

**Change Note (February 2026):**  
This document has been updated to align with Engineering Requirements v6 and resolve 12 consistency/accuracy issues:

1. **Auth Provider Alignment:** Replaced Auth0/Firebase references with Supabase Auth (canonical provider per ENG-002 + SEC-013)
2. **Token Duration Normalization:** Aligned access token (~1 hour) and refresh token (rolling 7 days) durations across SEC-001 and SEC-013
3. **RBAC Model Separation:** Separated billing tiers (Hobbyist/Pro/Museum) from RBAC roles (user/archivist/admin) to prevent authorization logic confusion
4. **API Path Consistency:** Added `/v1` prefix to all API endpoints; settings endpoints marked `[Phase 2]`; added API Scope Note
5. **Metrics Path Normalization:** Changed `/metrics` to `/v1/metrics` (consistent with Engineering Requirements)
6. **Endpoint Count Fix:** Replaced hardcoded "23 endpoints" with dynamic reference to OpenAPI spec
7. **SEC-015 Numbering Repair:** Fixed AC-SEC-014-01 → AC-SEC-015-01, DoD-SEC-014-01 → DoD-SEC-015-01
8. **AWS KMS Removal:** Removed AWS KMS references (GCP-only infrastructure); SEC-007 now specifies Google Cloud KMS (CMEK for GCS)
9. **Password Validation Privacy:** Replaced Have I Been Pwned API with offline breach corpus or k-anonymity lookup (no plaintext passwords sent to third parties)
10. **Database Reference Fix:** Replaced Cloud SQL with Supabase Postgres in OPS-001
11. **Cryptography Fix:** Replaced "SHA-256 hash + timestamp" with "HMAC-SHA256 or Ed25519 signature + timestamp" in SEC-006 and SEC-010 (hash ≠ signature); added signature verification procedure documentation requirement

All changes preserve existing test coverage and DoD requirements while ensuring consistency with the Engineering Requirements document.

----

## Security & Compliance Overview

ChronosRefine handles sensitive archival materials for institutional clients and must meet stringent security and compliance requirements. This document defines security controls, compliance frameworks, and operational monitoring requirements.

**Compliance Frameworks:**
- GDPR (General Data Protection Regulation) - designed to support compliance
- SOC 2 Type II - audit readiness by GA+6 months
- Cultural Sensitivity - handling of culturally significant materials

**API Scope Note:**  
All API endpoints in this document follow the `/v1/` versioning scheme unless explicitly marked otherwise:
- `/health` is unversioned (infrastructure probe endpoint, not in OpenAPI spec)
- Settings/configuration endpoints marked `[Phase 2]` are deferred to Phase 2 implementation
- For the canonical list of Phase 1 endpoints, refer to ENG-002 in the Engineering Requirements document (22 endpoints in Phase 1)

---

## Security Requirements

### SEC-001: Authentication & Authorization

**Description:** System must implement secure authentication and authorization with OAuth 2.0, JWT tokens, and role-based access control (RBAC).

**Acceptance Criteria:**
- AC-SEC-001-01: Authentication via Supabase Auth (email/password, OAuth providers, magic links) issuing JWTs; OAuth 2.0 flows supported for configured providers
- AC-SEC-001-01a: Authorization MUST be enforced by (a) executing user-scoped DB operations with the end-user JWT so Postgres RLS is enforced, OR (b) if a service-role key is used, implementing equivalent authorization checks in the service layer and limiting service-role usage to strictly necessary system tasks
- AC-SEC-001-02: Access tokens (JWT) expire in ~1 hour; refresh tokens maintain a rolling session up to 7 days (configurable by tier/tenant)
- AC-SEC-001-03: Authorization uses (a) billing tier (Hobbyist/Pro/Museum) for entitlements and limits, and (b) RBAC roles (user/archivist/admin) for permissions; policies are enforced server-side
- AC-SEC-001-04: API key authentication for programmatic access (Museum Tier only)
- AC-SEC-001-05: Multi-factor authentication (MFA) support (optional for all tiers, required for Museum Admin)
- AC-SEC-001-06: Session management with secure cookie flags (HttpOnly, Secure, SameSite=Strict)
- AC-SEC-001-07: Password requirements: min 12 characters, complexity rules enforced
- AC-SEC-001-08: Account lockout after 5 failed login attempts (15-minute cooldown)
- AC-SEC-001-09: Audit logging for all authentication events (login, logout, failed attempts)
- AC-SEC-001-10: Token revocation support (immediate logout)

**Definition of Done:**
- DoD-SEC-001-01: Supabase Auth integration tested with **30+ test scenarios** (valid tokens, expired tokens, invalid signatures, token refresh, OAuth provider flows, magic links) achieving **>95% code coverage** (pytest-cov), **<200ms authentication latency** (p95, measured by k6)
- DoD-SEC-001-02: JWT token generation/validation tested with **20+ scenarios** (valid tokens, expired tokens, tampered signatures, missing claims) achieving **100% expiration enforcement** (~1-hour access, rolling 7-day session), **<50ms validation time** (p95)
- DoD-SEC-001-03: Authorization tested for **all 3 billing tiers** (Hobbyist, Pro, Museum) and **all 3 RBAC roles** (user, archivist, admin) with **50+ authorization scenarios** achieving **100% access control enforcement**, **100% RLS policy enforcement** (user-scoped DB operations), **zero unauthorized access** (penetration testing, 30+ attack vectors)
- DoD-SEC-001-04: API key authentication tested with **15+ scenarios** (valid keys, revoked keys, expired keys, rate limiting) achieving **100% Museum Tier enforcement**, **<100ms key validation** (p95)
- DoD-SEC-001-05: MFA tested with **25+ scenarios** (TOTP, SMS, backup codes, enrollment, recovery) achieving **100% Museum Admin enforcement**, **<3s MFA verification time** (p95), **>99.9% delivery rate** for SMS codes
- DoD-SEC-001-06: Session management tested with **20+ scenarios** (cookie flags, session expiry, concurrent sessions, session hijacking attempts) achieving **100% secure flag enforcement** (HttpOnly, Secure, SameSite=Strict), **zero session fixation vulnerabilities**
- DoD-SEC-001-07: Password requirements tested with **30+ test cases** (length, complexity, common passwords, dictionary attacks) achieving **100% policy enforcement** (min 12 chars, complexity rules), **zero weak password acceptance** (blocked via offline breach corpus or k-anonymity lookup where permitted; no plaintext passwords sent to third parties)
- DoD-SEC-001-08: Account lockout tested with **15+ scenarios** (5 failed attempts, cooldown period, legitimate user impact, distributed attacks) achieving **100% lockout enforcement**, **<1% false positive rate** (legitimate users locked), **15-minute cooldown verified**
- DoD-SEC-001-09: Audit logging tested with **all 8 authentication events** (login, logout, failed attempts, MFA enrollment, password reset, token refresh, account lockout, admin actions) achieving **100% event capture rate**, **<500ms log write latency** (p95), **zero log loss** (verified over 30-day period)
- DoD-SEC-001-10: Token revocation tested with **10+ scenarios** (immediate logout, revoked token rejection, revocation propagation) achieving **<5s revocation propagation time** (p95), **100% revoked token rejection rate**
- DoD-SEC-001-11: Code review approved by **2+ engineers** with **security checklist** (all 20 items passed: OWASP Top 10, authentication best practices, session security) and **external security review** (penetration testing by certified auditor), **zero critical/high vulnerabilities**, review completed within **48 hours**

**Verification Method:** Automated (pytest integration tests + security testing)

**Test Files:**
- `tests/security/test_authentication.py`
- `tests/security/test_authorization.py`
- `tests/security/test_rbac.py`
- `tests/security/test_mfa.py`
- `tests/security/test_session_management.py`

**Related Requirements:** ENG-002 (API Endpoint Implementation), SEC-002 (Data Encryption), SEC-004 (Access Control)

---

### SEC-002: Data Encryption

**Description:** System must encrypt all data at rest and in transit using industry-standard encryption algorithms.

**Acceptance Criteria:**
- AC-SEC-002-01: Encryption at rest: AES-256 (GCS default) for all stored data
- AC-SEC-002-02: Encryption in transit: TLS 1.3 for all API endpoints
- AC-SEC-002-03: TLS certificate management: auto-renewal via Let's Encrypt or managed certificates
- AC-SEC-002-04: Minimum TLS cipher suites: TLS_AES_128_GCM_SHA256, TLS_AES_256_GCM_SHA384, TLS_CHACHA20_POLY1305_SHA256
- AC-SEC-002-05: HSTS (HTTP Strict Transport Security) enabled with 1-year max-age
- AC-SEC-002-06: Certificate pinning for mobile apps (if applicable)
- AC-SEC-002-07: Customer-Managed Encryption Keys (CMEK) support for Museum Tier (GA+3 months)
- AC-SEC-002-08: Key rotation policy: automatic rotation every 90 days
- AC-SEC-002-09: Encryption key backup and recovery procedures documented
- AC-SEC-002-10: Encryption performance overhead <5% for upload/download operations

**Definition of Done:**
- DoD-SEC-002-01: AES-256 encryption verified for **all 3 GCS buckets** (uploads, outputs, backups) with **100% encryption coverage** (no unencrypted objects), **zero encryption failures** (monitored over 30-day period)
- DoD-SEC-002-02: TLS 1.3 verified for **all externally exposed HTTP endpoints** (per the current OpenAPI spec + `/health` probe endpoint) achieving **SSL Labs A+ rating** (score ≥95/100), **zero TLS 1.0/1.1 connections** (deprecated protocols blocked), **<50ms TLS handshake time** (p95)
- DoD-SEC-002-03: TLS certificate auto-renewal tested with **10+ scenarios** (renewal 30 days before expiry, renewal failures, certificate propagation) achieving **100% renewal success rate**, **<5 minutes propagation time**, **zero downtime** during renewal
- DoD-SEC-002-04: TLS cipher suites tested with **15+ scenarios** (allowed ciphers, deprecated ciphers, cipher negotiation) achieving **100% minimum cipher enforcement** (TLS_AES_128_GCM_SHA256, TLS_AES_256_GCM_SHA384, TLS_CHACHA20_POLY1305_SHA256), **zero weak cipher acceptance**
- DoD-SEC-002-05: HSTS tested with **8+ scenarios** (header presence, max-age value, subdomain inclusion, preload) achieving **100% HSTS enforcement** (1-year max-age = 31536000 seconds), **zero HTTP connections** after first visit
- DoD-SEC-002-06: Certificate pinning tested with **12+ scenarios** (valid pins, invalid pins, pin rotation, backup pins) achieving **100% pinning enforcement** (if mobile apps exist), **<1% false positive rate** (legitimate certificate rejection)
- DoD-SEC-002-07: CMEK support tested for **Museum Tier** with **20+ scenarios** (key creation, key usage, key rotation, key revocation, key recovery) achieving **100% CMEK enforcement** (GA+3 months), **<10% performance overhead** vs default encryption
- DoD-SEC-002-08: Key rotation tested with **automatic rotation every 90 days** achieving **100% rotation success rate**, **zero data loss** during rotation, **<5 minutes rotation time**, **automated monitoring** (alerts 7 days before rotation)
- DoD-SEC-002-09: Encryption key backup/recovery procedures documented with **100% procedure coverage** (backup frequency, storage location, recovery steps, RTO <4 hours), **recovery tested quarterly** with **100% success rate**
- DoD-SEC-002-10: Encryption performance overhead **<5%** verified with **load testing** (1,000+ upload/download operations) achieving **p95 overhead <3%**, **p99 overhead <5%**, measured by k6
- DoD-SEC-002-11: Code review approved by **2+ engineers** with **encryption security checklist** (all 15 items passed: key management, cipher selection, certificate validation) and **external security review** (cryptographic audit by certified auditor), **zero critical/high vulnerabilities**, review completed within **48 hours**

**Verification Method:** Automated (pytest integration tests + SSL Labs scan) + Manual (security audit)

**Test Files:**
- `tests/security/test_encryption_at_rest.py`
- `tests/security/test_encryption_in_transit.py`
- `tests/security/test_tls_configuration.py`
- `tests/security/test_cmek.py`

**Related Requirements:** SEC-001 (Authentication & Authorization), SEC-003 (Data Classification), SEC-007 (CMEK)

---

### SEC-003: Data Classification

**Description:** System must classify all data types and enforce appropriate handling policies for each classification level.

**Acceptance Criteria:**
- AC-SEC-003-01: Four data classification levels: Confidential, Internal, Compliance, Public
- AC-SEC-003-02: Source uploads classified as Confidential (AES-256 encryption, TLS 1.3, tier-specific retention)
- AC-SEC-003-03: Processed outputs classified as Confidential (AES-256 encryption, TLS 1.3, tier-specific retention)
- AC-SEC-003-04: Transformation Manifests classified as Internal (AES-256 encryption, tier-configurable retention)
- AC-SEC-003-05: Deletion Proofs classified as Compliance (AES-256 encryption, 7-year minimum retention)
- AC-SEC-003-06: Data classification labels applied to all GCS objects (metadata tags)
- AC-SEC-003-07: Data retention policies enforced per classification level
- AC-SEC-003-08: Data deletion policies enforced per classification level (GDPR Article 17)
- AC-SEC-003-09: Data access logging enforced for Confidential and Compliance data
- AC-SEC-003-10: Data classification audit trail maintained for compliance verification

**Definition of Done:**
- DoD-SEC-003-01: All 4 classification levels defined and documented with **100% policy coverage** (Confidential, Internal, Compliance, Public), **handling procedures documented** for each level (encryption, retention, access control, deletion)
- DoD-SEC-003-02: Source uploads classified as Confidential with **100% classification accuracy** (all uploads tagged), **AES-256 encryption verified**, **tier-specific retention enforced** (7d/90d/indefinite), tested with **50+ upload scenarios**
- DoD-SEC-003-03: Processed outputs classified as Confidential with **100% classification accuracy**, **AES-256 encryption verified**, **tier-specific retention enforced**, tested with **50+ processing scenarios**
- DoD-SEC-003-04: Transformation Manifests classified as Internal with **100% classification accuracy**, **tier-configurable retention verified** (5 retention options), tested with **30+ manifest scenarios**
- DoD-SEC-003-05: Deletion Proofs classified as Compliance with **100% classification accuracy**, **7-year minimum retention enforced** (2,555 days), **zero premature deletions** (monitored over 30-day period), tested with **20+ deletion scenarios**
- DoD-SEC-003-06: Data classification labels tested with **100% GCS metadata tag coverage** (all objects tagged), **<100ms tagging latency** (p95), **zero untagged objects** (automated monitoring)
- DoD-SEC-003-07: Data retention policies tested with **automatic deletion after retention period** achieving **100% deletion accuracy** (±1 day), **zero retention policy violations**, tested with **40+ retention scenarios** (all 4 classification levels × retention periods)
- DoD-SEC-003-08: Data deletion policies tested for **GDPR Article 17 compliance** with **<10 days deletion completion time** (p95), **100% deletion verification** (Cloud Audit Logs), tested with **25+ deletion request scenarios**
- DoD-SEC-003-09: Data access logging tested for **Confidential + Compliance data** with **100% access event capture rate**, **<500ms log write latency** (p95), **zero log loss** (verified over 30-day period), tested with **30+ access scenarios**
- DoD-SEC-003-10: Data classification audit trail tested with **100% audit event capture** (classification changes, retention policy updates, deletion events), **tamper-proof logging** (Cloud Audit Logs), **<1 hour audit report generation time**
- DoD-SEC-003-11: Code review approved by **2+ engineers** with **data classification checklist** (all 12 items passed: classification accuracy, retention enforcement, GDPR compliance) and **compliance review** (legal team approval), **zero critical issues**, review completed within **48 hours**

**Verification Method:** Automated (pytest integration tests) + Manual (compliance audit)

**Test Files:**
- `tests/security/test_data_classification.py`
- `tests/security/test_data_retention.py`
- `tests/security/test_data_deletion.py`
- `tests/compliance/test_gdpr_compliance.py`

**Related Requirements:** SEC-002 (Data Encryption), SEC-005 (Transformation Manifest Retention), SEC-010 (Deletion Proofs)

---

### SEC-004: Access Control

**Description:** System must implement principle of least privilege with IAM policies, API rate limiting, and multi-tenancy isolation.

**Acceptance Criteria:**
- AC-SEC-004-01: IAM policies managed via Terraform (infrastructure as code)
- AC-SEC-004-02: Principle of least privilege enforced (users/services granted minimum required permissions)
- AC-SEC-004-03: Quarterly IAM audits conducted (access review + permission cleanup)
- AC-SEC-004-04: API rate limiting: 100 req/min (Hobbyist), 1000 req/min (Pro/Museum)
- AC-SEC-004-05: Rate limiting enforced per user (not per IP to avoid shared IP issues)
- AC-SEC-004-06: Rate limit exceeded returns HTTP 429 with Retry-After header
- AC-SEC-004-07: Multi-tenancy isolation: strict project-level isolation in GCS (no cross-tenant access)
- AC-SEC-004-08: Service accounts for backend services (no user credentials in code)
- AC-SEC-004-09: Access control lists (ACLs) for GCS buckets (user-specific access)
- AC-SEC-004-10: Access logging for all GCS operations (Cloud Audit Logs)

**Definition of Done:**
- DoD-SEC-004-01: IAM policies managed via Terraform (all policies version-controlled)
- DoD-SEC-004-02: Principle of least privilege verified (IAM audit report)
- DoD-SEC-004-03: Quarterly IAM audits scheduled (access review + permission cleanup)
- DoD-SEC-004-04: API rate limiting tested (100 req/min Hobbyist, 1000 req/min Pro/Museum)
- DoD-SEC-004-05: Rate limiting per-user tested (not per-IP)
- DoD-SEC-004-06: HTTP 429 responses tested (Retry-After header verified)
- DoD-SEC-004-07: Multi-tenancy isolation tested (no cross-tenant access possible)
- DoD-SEC-004-08: Service accounts tested (no user credentials in code)
- DoD-SEC-004-09: GCS ACLs tested (user-specific access enforced)
- DoD-SEC-004-10: Access logging tested (Cloud Audit Logs enabled)
- DoD-SEC-004-11: Code review approved by 2+ engineers + security review

**Verification Method:** Automated (pytest integration tests + IAM audit) + Manual (quarterly IAM review)

**Test Files:**
- `tests/security/test_iam_policies.py`
- `tests/security/test_rate_limiting.py`
- `tests/security/test_multi_tenancy.py`
- `tests/security/test_access_logging.py`

**Related Requirements:** SEC-001 (Authentication & Authorization), SEC-003 (Data Classification), OPS-001 (Monitoring & Alerting)

---

### SEC-005: Transformation Manifest Retention

**Description:** System must implement tier-configurable retention policies for Transformation Manifests with optional PII redaction.

**Acceptance Criteria:**
- AC-SEC-005-01: Tier-specific default retention: Hobbyist (7 days), Pro (90 days), Museum (indefinite)
- AC-SEC-005-02: Museum Tier configurable retention: 0 days, 90 days, 1 year, 5 years, indefinite
- AC-SEC-005-03: Manifest Redaction Mode available for Museum Tier (generates Full + Redacted manifests)
- AC-SEC-005-04: Full Manifest contains all metadata (user IDs, file paths, timestamps)
- AC-SEC-005-05: Redacted Manifest contains only processing parameters (era profile, model versions, quality metrics)
- AC-SEC-005-06: Redacted Manifest retains reproducibility information (no PII)
- AC-SEC-005-07: Retention policy enforced via GCS Object Lifecycle Management
- AC-SEC-005-08: Expired manifests automatically deleted (no manual intervention)
- AC-SEC-005-09: Deletion events logged to Cloud Audit Logs
- AC-SEC-005-10: Configuration via Web UI (Settings > Data Retention) or API (PATCH /v1/orgs/{org_id}/settings/retention) [Phase 2]

**Definition of Done:**
- DoD-SEC-005-01: Tier-specific retention tested (7d/90d/indefinite)
- DoD-SEC-005-02: Museum Tier configurable retention tested (all 5 options)
- DoD-SEC-005-03: Manifest Redaction Mode tested (Full + Redacted manifests generated)
- DoD-SEC-005-04: Full Manifest tested (all metadata present)
- DoD-SEC-005-05: Redacted Manifest tested (only processing parameters, no PII)
- DoD-SEC-005-06: Reproducibility verified with Redacted Manifest
- DoD-SEC-005-07: GCS Object Lifecycle Management tested (automatic deletion)
- DoD-SEC-005-08: Expired manifests deletion tested (no manual intervention)
- DoD-SEC-005-09: Deletion events tested (Cloud Audit Logs)
- DoD-SEC-005-10: Configuration tested (Web UI + API)
- DoD-SEC-005-11: Code review approved by 2+ engineers + compliance review

**Verification Method:** Automated (pytest integration tests) + Manual (compliance verification)

**Test Files:**
- `tests/security/test_manifest_retention.py`
- `tests/security/test_manifest_redaction.py`
- `tests/compliance/test_gdpr_manifest_retention.py`

**Related Requirements:** SEC-003 (Data Classification), SEC-006 (GDPR Compliance), ENG-010 (Transformation Manifest Generation)

---

### SEC-006: GDPR Compliance

**Description:** System must be designed to support GDPR compliance obligations, particularly Article 17 (Right to Erasure) with signed Deletion Proofs.

**Acceptance Criteria:**
- AC-SEC-006-01: GDPR Article 17 (Right to Erasure) support via Deletion Proof feature
- AC-SEC-006-02: Data Processing Agreement (DPA) available for Museum Tier customers
- AC-SEC-006-03: User data deletion request via Web UI or API (POST /v1/user/delete_logs)
- AC-SEC-006-04: Deletion scope: all logs containing user ID, IP address, file paths permanently deleted
- AC-SEC-006-05: Aggregated/anonymized logs retained for analytics (no PII)
- AC-SEC-006-06: Deletion Proof generated and provided to user within 10 days
- AC-SEC-006-07: Deletion Proof contents: user ID, timestamp, log categories deleted, total entries, cryptographic signature
- AC-SEC-006-08: Deletion Proof cryptographic signature: HMAC-SHA256 with server-managed key + timestamp (or Ed25519 signature over canonical payload + timestamp for auditor-friendly verification)
- AC-SEC-006-08a: Signature verification procedure documented for auditors (verification steps + key distribution method)
- AC-SEC-006-09: Deletion events logged to Cloud Audit Logs (LogDelete event)
- AC-SEC-006-10: GDPR compliance documentation available for institutional auditors

**Definition of Done:**
- DoD-SEC-006-01: GDPR Article 17 support tested (Right to Erasure workflow)
- DoD-SEC-006-02: DPA template created for Museum Tier customers
- DoD-SEC-006-03: User data deletion tested (Web UI + API)
- DoD-SEC-006-04: Deletion scope tested (all PII logs deleted, aggregated logs retained)
- DoD-SEC-006-05: Aggregated logs tested (no PII present)
- DoD-SEC-006-06: Deletion Proof generation tested (within 10 days)
- DoD-SEC-006-07: Deletion Proof contents tested (all required fields present)
- DoD-SEC-006-08: Cryptographic signature tested (HMAC-SHA256 or Ed25519 signature + timestamp, signature verification procedure documented)
- DoD-SEC-006-09: Cloud Audit Logs tested (LogDelete event generated)
- DoD-SEC-006-10: GDPR compliance documentation created
- DoD-SEC-006-11: Code review approved by 2+ engineers + legal/compliance review

**Verification Method:** Automated (pytest integration tests) + Manual (legal/compliance review)

**Test Files:**
- `tests/compliance/test_gdpr_right_to_erasure.py`
- `tests/compliance/test_deletion_proof.py`
- `tests/compliance/test_gdpr_audit_trail.py`

**Related Requirements:** SEC-003 (Data Classification), SEC-005 (Transformation Manifest Retention), SEC-010 (Deletion Proofs)

---

### SEC-007: Customer-Managed Encryption Keys (CMEK)

**Description:** Museum Tier customers must be able to provide their own encryption keys managed via Google Cloud KMS.

**Acceptance Criteria:**
- AC-SEC-007-01: CMEK support for Museum Tier only (GA+3 months)
- AC-SEC-007-02: Customer-provided keys via Google Cloud KMS (CMEK for GCS and any other supported GCP services)
- AC-SEC-007-03: All source uploads, processed outputs, manifests encrypted with customer keys
- AC-SEC-007-04: Customer retains full control over encryption keys
- AC-SEC-007-05: Ability to revoke access to data by destroying keys
- AC-SEC-007-06: Configuration via Web UI (Settings > Security > Encryption Keys) or API (POST /v1/orgs/{org_id}/settings/cmek) [Phase 2]
- AC-SEC-007-07: KMS key URI format: `projects/PROJECT/locations/LOCATION/keyRings/RING/cryptoKeys/KEY`
- AC-SEC-007-08: Key rotation support (customer-initiated)
- AC-SEC-007-09: Performance overhead: 50-100ms latency for upload/download operations
- AC-SEC-007-10: Customer responsible for key lifecycle management and availability

**Definition of Done:**
- DoD-SEC-007-01: CMEK support implemented for Museum Tier (GA+3 months)
- DoD-SEC-007-02: Google Cloud KMS integration tested
- DoD-SEC-007-04: All data encrypted with customer keys verified
- DoD-SEC-007-05: Key revocation tested (data access denied after key destruction)
- DoD-SEC-007-06: Configuration tested (Web UI + API)
- DoD-SEC-007-07: KMS key URI format validated
- DoD-SEC-007-08: Key rotation tested (customer-initiated)
- DoD-SEC-007-09: Performance overhead measured (50-100ms verified)
- DoD-SEC-007-10: Customer key lifecycle documentation created
- DoD-SEC-007-11: Code review approved by 2+ engineers + security review

**Verification Method:** Automated (pytest integration tests) + Manual (security audit)

**Test Files:**
- `tests/security/test_cmek.py`
- `tests/security/test_cmek_gcp.py`
- `tests/security/test_key_rotation.py`

**Related Requirements:** SEC-002 (Data Encryption), SEC-008 (VPC Service Controls)

---

### SEC-008: VPC Service Controls

**Description:** Museum Tier customers must be able to deploy ChronosRefine within a VPC Service Perimeter with private networking.

**Acceptance Criteria:**
- AC-SEC-008-01: VPC Service Controls support for Museum Tier (GA+6 months)
- AC-SEC-008-02: Three deployment options: Public Endpoints (GA), VPC Service Controls (GA+6 months), Private Service Connect (GA+9 months)
- AC-SEC-008-03: VPC Service Controls: API endpoints restricted to customer's VPC perimeter
- AC-SEC-008-04: Private Service Connect: fully private connectivity via PSC endpoint
- AC-SEC-008-05: Customer must have GCP VPC Service Controls configured
- AC-SEC-008-06: Additional setup fee: $5,000 one-time
- AC-SEC-008-07: Minimum contract: 12 months
- AC-SEC-008-08: Configuration via dedicated account manager (architecture review + custom deployment plan)
- AC-SEC-008-09: Network isolation verified (no data exfiltration possible outside VPC)
- AC-SEC-008-10: Performance overhead <10% for private networking

**Definition of Done:**
- DoD-SEC-008-01: VPC Service Controls support implemented (GA+6 months)
- DoD-SEC-008-02: All 3 deployment options tested (Public, VPC, PSC)
- DoD-SEC-008-03: VPC Service Controls tested (API endpoints restricted to VPC)
- DoD-SEC-008-04: Private Service Connect tested (fully private connectivity)
- DoD-SEC-008-05: VPC Service Controls prerequisites documented
- DoD-SEC-008-06: Setup fee and minimum contract terms documented
- DoD-SEC-008-07: Configuration process documented (account manager + architecture review)
- DoD-SEC-008-08: Network isolation tested (no data exfiltration possible)
- DoD-SEC-008-09: Performance overhead measured (<10% verified)
- DoD-SEC-008-10: Deployment guide created for VPC Service Controls
- DoD-SEC-008-11: Code review approved by 2+ engineers + security review

**Verification Method:** Automated (integration tests) + Manual (architecture review + security audit)

**Test Files:**
- `tests/security/test_vpc_service_controls.py`
- `tests/security/test_private_service_connect.py`
- `tests/security/test_network_isolation.py`

**Related Requirements:** SEC-007 (CMEK), SEC-009 (Log Retention & PII Redaction)

---

### SEC-009: Log Retention & PII Redaction

**Description:** System must implement tier-specific log retention policies with optional PII redaction to balance operational needs with privacy requirements.

**Acceptance Criteria:**
- AC-SEC-009-01: Five log categories: Application Logs, Audit Logs, Processing Logs, Error Traces, Billing Logs
- AC-SEC-009-02: Tier-specific retention: Hobbyist (7d-1yr), Pro (30d-2yr), Museum (configurable 7d-7yr)
- AC-SEC-009-03: Three PII redaction modes: None (default), Standard Redaction (Pro+Museum), Strict Redaction (Museum only)
- AC-SEC-009-04: Standard Redaction patterns: emails, IPs, file paths with usernames, user IDs, API keys
- AC-SEC-009-05: Strict Redaction patterns: job IDs, all file paths, timestamps (retains date only), GCS bucket paths
- AC-SEC-009-06: Performance impact: Standard (<5% latency), Strict (10-15% latency)
- AC-SEC-009-07: Configuration via Web UI (Settings > Security > Logs & Privacy) or API (PATCH /v1/orgs/{org_id}/settings/logs) [Phase 2]
- AC-SEC-009-08: Log export for external SIEM (Cloud Logging, CloudWatch, Splunk, Syslog)
- AC-SEC-009-09: GDPR Article 17 support: user can request log deletion (POST /v1/user/delete_logs)
- AC-SEC-009-10: Deletion Proof generated for log deletion requests

**Definition of Done:**
- DoD-SEC-009-01: All 5 log categories implemented with tier-specific retention
- DoD-SEC-009-02: Tier-specific retention tested (Hobbyist/Pro/Museum)
- DoD-SEC-009-03: All 3 PII redaction modes tested (None/Standard/Strict)
- DoD-SEC-009-04: Standard Redaction patterns tested (5 patterns verified)
- DoD-SEC-009-05: Strict Redaction patterns tested (4 additional patterns verified)
- DoD-SEC-009-06: Performance impact measured (Standard <5%, Strict 10-15%)
- DoD-SEC-009-07: Configuration tested (Web UI + API)
- DoD-SEC-009-08: Log export tested (all 4 SIEM integrations)
- DoD-SEC-009-09: GDPR log deletion tested (POST /v1/user/delete_logs)
- DoD-SEC-009-10: Deletion Proof tested for log deletion
- DoD-SEC-009-11: Code review approved by 2+ engineers + compliance review

**Verification Method:** Automated (pytest integration tests) + Manual (compliance verification)

**Test Files:**
- `tests/security/test_log_retention.py`
- `tests/security/test_pii_redaction.py`
- `tests/security/test_log_export.py`
- `tests/compliance/test_gdpr_log_deletion.py`

**Related Requirements:** SEC-003 (Data Classification), SEC-006 (GDPR Compliance), OPS-001 (Monitoring & Alerting)

---

### SEC-010: Deletion Proofs

**Description:** System must generate cryptographically signed Deletion Proofs for GDPR Article 17 compliance and institutional audit requirements.

**Acceptance Criteria:**
- AC-SEC-010-01: Deletion Proof generated for all user data deletion requests
- AC-SEC-010-02: Deletion Proof contents: user ID, request timestamp, log categories deleted (with date ranges), total entries deleted
- AC-SEC-010-03: Cryptographic signature: HMAC-SHA256 with server-managed key + timestamp (or Ed25519 signature over canonical payload + timestamp for auditor-friendly verification)
- AC-SEC-010-03a: Signature verification procedure documented for auditors (verification steps + key distribution method)
- AC-SEC-010-04: Deletion Proof format: PDF with embedded signature
- AC-SEC-010-05: Deletion Proof delivery: emailed to user within 10 days
- AC-SEC-010-06: Deletion Proof retention: 7 years minimum (Compliance classification)
- AC-SEC-010-07: Deletion Proof verification instructions for institutional auditors
- AC-SEC-010-08: Deletion events logged to Cloud Audit Logs (LogDelete event)
- AC-SEC-010-09: Deletion Proof accessible via API (GET /v1/deletion-proofs/{id})
- AC-SEC-010-10: Deletion Proof tamper detection (signature verification)

**Definition of Done:**
- DoD-SEC-010-01: Deletion Proof generation tested (all required fields present)
- DoD-SEC-010-02: Deletion Proof contents tested (user ID, timestamp, log categories, total entries)
- DoD-SEC-010-03: Cryptographic signature tested (HMAC-SHA256 or Ed25519 signature + timestamp, signature verification procedure documented)
- DoD-SEC-010-04: Deletion Proof PDF format tested (embedded signature)
- DoD-SEC-010-05: Deletion Proof delivery tested (emailed within 10 days)
- DoD-SEC-010-06: Deletion Proof retention tested (7-year minimum)
- DoD-SEC-010-07: Verification instructions tested (institutional auditors can verify)
- DoD-SEC-010-08: Cloud Audit Logs tested (LogDelete event generated)
- DoD-SEC-010-09: API access tested (GET /deletion-proofs/{id})
- DoD-SEC-010-10: Tamper detection tested (signature verification)
- DoD-SEC-010-11: Code review approved by 2+ engineers + legal/compliance review

**Verification Method:** Automated (pytest integration tests) + Manual (legal/compliance review)

**Test Files:**
- `tests/compliance/test_deletion_proof.py`
- `tests/compliance/test_deletion_proof_signature.py`
- `tests/compliance/test_deletion_proof_verification.py`

**Related Requirements:** SEC-003 (Data Classification), SEC-006 (GDPR Compliance), SEC-009 (Log Retention & PII Redaction)

---

### SEC-011: Dataset Provenance

**Description:** System must document and maintain provenance information for Heritage Test Set and all training/evaluation datasets to meet institutional compliance requirements.

**Acceptance Criteria:**
- AC-SEC-011-01: Heritage Test Set provenance documented (2,000 items from 4 source categories)
- AC-SEC-011-02: Source categories: Public Domain Archives, Licensed Historical Footage, Synthetic Test Cases, User-Contributed Samples (with consent)
- AC-SEC-011-03: Licensing matrix documented (Training/Evaluation/Demos/Marketing permissions)
- AC-SEC-011-04: PII policy documented (faces, minors, consent, redaction capabilities)
- AC-SEC-011-05: Bias coverage documented (Monk Skin Tone Scale, gender, age, damage types)
- AC-SEC-011-06: Dataset versioning and change control (semantic versioning: v1.0.0, v1.1.0, etc.)
- AC-SEC-011-07: Institutional compliance support (private test sets, DPAs, audit rights)
- AC-SEC-011-08: Dataset provenance accessible via API (GET /v1/datasets/{id}/provenance)
- AC-SEC-011-09: Dataset provenance included in Transformation Manifest
- AC-SEC-011-10: Dataset provenance audit trail maintained for compliance verification

**Definition of Done:**
- DoD-SEC-011-01: Heritage Test Set provenance documented (all 2,000 items)
- DoD-SEC-011-02: Source categories documented (4 categories with item counts)
- DoD-SEC-011-03: Licensing matrix documented (all permissions defined)
- DoD-SEC-011-04: PII policy documented (faces, minors, consent, redaction)
- DoD-SEC-011-05: Bias coverage documented (Monk Skin Tone Scale, gender, age, damage types)
- DoD-SEC-011-06: Dataset versioning tested (semantic versioning enforced)
- DoD-SEC-011-07: Institutional compliance support documented (private test sets, DPAs, audit rights)
- DoD-SEC-011-08: API access tested (GET /v1/datasets/{id}/provenance)
- DoD-SEC-011-09: Transformation Manifest tested (dataset provenance included)
- DoD-SEC-011-10: Audit trail tested (dataset provenance changes tracked)
- DoD-SEC-011-11: Code review approved by 2+ engineers + legal/compliance review

**Verification Method:** Automated (pytest integration tests) + Manual (legal/compliance review)

**Test Files:**
- `tests/compliance/test_dataset_provenance.py`
- `tests/compliance/test_heritage_test_set.py`
- `tests/compliance/test_dataset_versioning.py`

**Related Requirements:** SEC-006 (GDPR Compliance), ENG-004 (Era Detection Model), ENG-010 (Transformation Manifest Generation)

---

### SEC-012: Data Residency

**Description:** Museum Tier customers must be able to configure data residency to meet regional compliance requirements (GDPR, etc.).

**Acceptance Criteria:**
- AC-SEC-012-01: Four supported GCS regions: us-central1 (GA), europe-west1 (GA Museum), asia-east1 (GA+3 Museum), australia-southeast1 (GA+6 Museum)
- AC-SEC-012-02: Data residency guarantee: source uploads, processing, outputs, logs, backups remain in selected region
- AC-SEC-012-03: Strict Residency Mode: API calls to Gemini/SynthID routed through regional endpoints (when available)
- AC-SEC-012-04: Configuration via Web UI (Settings > Data & Privacy > Data Residency) or API (PATCH /v1/orgs/{org_id}/settings/data_residency) [Phase 2]
- AC-SEC-012-05: Region change does not automatically migrate existing data (manual migration required)
- AC-SEC-012-06: Strict Residency Mode fallback: jobs queued until regional endpoints available (no automatic fallback to US)
- AC-SEC-012-07: Performance impact: Strict Residency Mode may increase latency by 10-20%
- AC-SEC-012-08: Regional endpoint availability tracked in dependency registry
- AC-SEC-012-09: Data residency configuration persists across all jobs
- AC-SEC-012-10: Data residency audit trail maintained for compliance verification

**Definition of Done:**
- DoD-SEC-012-01: All 4 GCS regions tested (us-central1, europe-west1, asia-east1, australia-southeast1)
- DoD-SEC-012-02: Data residency guarantee tested (all data remains in selected region)
- DoD-SEC-012-03: Strict Residency Mode tested (regional API routing verified)
- DoD-SEC-012-04: Configuration tested (Web UI + API)
- DoD-SEC-012-05: Region change tested (no automatic migration, manual migration required)
- DoD-SEC-012-06: Strict Residency Mode fallback tested (jobs queued, no US fallback)
- DoD-SEC-012-07: Performance impact measured (10-20% latency increase verified)
- DoD-SEC-012-08: Regional endpoint availability documented in dependency registry
- DoD-SEC-012-09: Data residency persistence tested (all jobs use selected region)
- DoD-SEC-012-10: Audit trail tested (data residency changes tracked)
- DoD-SEC-012-11: Code review approved by 2+ engineers + compliance review

**Verification Method:** Automated (pytest integration tests) + Manual (compliance verification)

**Test Files:**
- `tests/compliance/test_data_residency.py`
- `tests/compliance/test_strict_residency_mode.py`
- `tests/compliance/test_regional_endpoints.py`

**Related Requirements:** SEC-003 (Data Classification), SEC-006 (GDPR Compliance), SEC-007 (CMEK)

---

### SEC-013: Authentication Provider Selection (Supabase)

**Description:** System must use Supabase Auth as the primary authentication provider, supporting email/password, OAuth (Google, GitHub), and magic link authentication with secure session management and role-based access control (RBAC).

**Acceptance Criteria:**
- AC-SEC-013-01: Supabase Auth configured with email/password authentication (password strength requirements enforced)
- AC-SEC-013-02: OAuth providers integrated (Google OAuth 2.0, GitHub OAuth)
- AC-SEC-013-03: Magic link authentication supported (passwordless email login)
- AC-SEC-013-04: Multi-factor authentication (MFA) available for all users (TOTP-based)
- AC-SEC-013-05: Session management configured (access tokens ~1 hour expiration, refresh tokens maintain rolling session up to 7 days)
- AC-SEC-013-06: Role-based access control (RBAC) implemented (user, admin, archivist roles)
- AC-SEC-013-07: User profile management supported (email, display name, avatar)
- AC-SEC-013-08: Password reset flow implemented (secure token-based reset)
- AC-SEC-013-09: Email verification required for new accounts (confirmation link sent)
- AC-SEC-013-10: Account lockout policy enforced (5 failed login attempts, 15-minute lockout)
- AC-SEC-013-11: Supabase Auth client libraries integrated (JavaScript SDK for frontend)
- AC-SEC-013-12: Authentication state persisted across sessions (localStorage or secure cookies)

**Definition of Done:**
- DoD-SEC-013-01: Supabase Auth configured: email/password authentication enabled, password strength requirements enforced (minimum 12 characters, uppercase, lowercase, number, special character), password policy tested with 30+ scenarios
- DoD-SEC-013-02: OAuth providers integrated: Google OAuth 2.0 configured (client ID, client secret), GitHub OAuth configured, OAuth flow tested with 50+ scenarios (successful login, error handling, account linking)
- DoD-SEC-013-03: Magic link authentication tested: passwordless email login flow tested with 30+ scenarios (link generation, link expiration, link validation, error handling)
- DoD-SEC-013-04: Multi-factor authentication (MFA) implemented: TOTP-based MFA configured (QR code generation, backup codes), MFA tested with 40+ scenarios (enrollment, verification, recovery, disable)
- DoD-SEC-013-05: Session management tested: access tokens (JWT) issued with ~1 hour expiration, refresh tokens maintain rolling session up to 7 days (configurable by tier/tenant), refresh tokens tested (automatic refresh, manual refresh, revocation), session persistence tested (page reload, browser close, token expiration)
- DoD-SEC-013-06: Role-based access control (RBAC) implemented: 3 roles defined (user, admin, archivist), role permissions defined (user: own data, admin: all data, archivist: audit trail), RBAC tested with 50+ scenarios (role assignment, permission enforcement, role escalation prevention)
- DoD-SEC-013-07: User profile management tested: profile CRUD operations tested (create, read, update, delete), profile validation tested (email format, display name length, avatar upload), profile UI tested with 25+ scenarios
- DoD-SEC-013-08: Password reset flow tested: secure token-based reset implemented (token generation, token expiration, token validation), reset flow tested with 30+ scenarios (request reset, validate token, set new password, error handling)
- DoD-SEC-013-09: Email verification tested: confirmation link sent to new users, email verification flow tested with 25+ scenarios (link generation, link expiration, link validation, resend confirmation)
- DoD-SEC-013-10: Account lockout policy tested: 5 failed login attempts trigger 15-minute lockout, lockout policy tested with 20+ scenarios (lockout trigger, lockout duration, lockout reset, admin override)
- DoD-SEC-013-11: Supabase Auth client libraries integrated: JavaScript SDK installed (`@supabase/supabase-js`), auth client initialization tested (50+ scenarios), auth state management tested (login, logout, session refresh, error handling)
- DoD-SEC-013-12: Authentication state persistence tested: localStorage persistence tested (login state preserved across page reloads), secure cookie persistence tested (HttpOnly, Secure, SameSite flags), state synchronization tested (multiple tabs, session expiration)
- DoD-SEC-013-13: Security audit passed: password storage verified (bcrypt hashing), JWT token security verified (HMAC-SHA256 signing), OAuth security verified (CSRF protection, state parameter validation), MFA security verified (TOTP algorithm compliance)
- DoD-SEC-013-14: Code review approved by 2+ engineers with authentication security checklist (password policy, session management, RBAC implementation, OAuth security)

**Verification Method:** Automated (integration tests + security tests) + Manual (security audit + penetration testing)

**Test Files:**
- `tests/auth/test_supabase_auth.py`
- `tests/auth/test_email_password_auth.py`
- `tests/auth/test_oauth_integration.py`
- `tests/auth/test_magic_link_auth.py`
- `tests/auth/test_mfa.py`
- `tests/auth/test_session_management.py`
- `tests/auth/test_rbac.py`
- `tests/auth/test_password_reset.py`

**Related Requirements:** ENG-016 (Database Technology Selection), SEC-001 (Data Encryption at Rest), SEC-002 (Data Encryption in Transit), SEC-004 (Access Control)

**Implementation Guidance:**
- 📄 **Supabase Auth Setup:** `docs/specs/chronosrefine_implementation_plan.md#phase-1-foundation--core-infrastructure` (to be cross-referenced)
- 📄 **Authentication Flows:** `companion_docs/ChronosRefine_Auth_Flows.md` (to be created)
- 📄 **RBAC Policies:** `companion_docs/ChronosRefine_Security_Spec.md#rbac-policies` (to be created)
- 📄 **Session Management:** `companion_docs/ChronosRefine_Security_Spec.md#session-management` (to be created)

---

### SEC-014: Reserved for Future Use

---

### SEC-015: Third-Party Security Audit

**Description:** System must undergo a comprehensive third-party security audit by a qualified security firm before General Availability (GA) launch, covering application security, infrastructure security, data protection, and compliance with industry standards (OWASP Top 10, SOC 2 Type II readiness).

**Acceptance Criteria:**
- AC-SEC-015-01: Security audit firm selected (qualified firm with media/SaaS experience)
- AC-SEC-015-02: Audit scope defined (application security, infrastructure security, data protection, compliance)
- AC-SEC-015-03: Audit methodology documented (penetration testing, code review, configuration review, compliance assessment)
- AC-SEC-015-04: Audit conducted with full access to codebase, infrastructure, and documentation
- AC-SEC-015-05: Audit findings documented with severity ratings (critical, high, medium, low)
- AC-SEC-015-06: All critical and high-severity findings remediated before GA launch
- AC-SEC-015-07: Medium and low-severity findings tracked with remediation timeline
- AC-SEC-015-08: Audit report reviewed by engineering and security teams
- AC-SEC-015-09: Remediation verification conducted by audit firm (re-test critical/high findings)
- AC-SEC-015-10: Final audit report published (executive summary shared with stakeholders)
- AC-SEC-015-11: SOC 2 Type II readiness assessment included in audit scope
- AC-SEC-015-12: Audit findings integrated into security roadmap for continuous improvement

**Definition of Done:**
- DoD-SEC-015-01: Security audit firm selected: qualified firm with media/SaaS experience (minimum 5 years experience, CREST or OSCP certified auditors), firm contract signed, audit timeline agreed (4-6 weeks)
- DoD-SEC-015-02: Audit scope documented: application security (OWASP Top 10, authentication, authorization, input validation, session management), infrastructure security (GCP configuration, network security, access controls), data protection (encryption, data residency, PII handling), compliance (GDPR, CCPA, SOC 2 Type II readiness)
- DoD-SEC-015-03: Audit methodology documented: penetration testing (black-box, gray-box, white-box), code review (static analysis, manual review), configuration review (GCP, Supabase, third-party services), compliance assessment (policy review, control testing)
- DoD-SEC-015-04: Audit conducted: full access provided to codebase (GitHub repository), infrastructure (GCP project, Supabase project), documentation (PRD, security policies, runbooks), audit team on-site or remote access for 2-4 weeks
- DoD-SEC-015-05: Audit findings documented: formal audit report delivered with severity ratings (critical: immediate remediation required, high: remediation within 30 days, medium: remediation within 90 days, low: remediation within 180 days), findings categorized by OWASP Top 10, CWE, or custom taxonomy
- DoD-SEC-015-06: Critical and high-severity findings remediated: all critical findings fixed (0 critical findings remaining), all high-severity findings fixed (0 high-severity findings remaining), remediation verified by internal testing (100+ test scenarios)
- DoD-SEC-015-07: Medium and low-severity findings tracked: remediation timeline documented (medium: 90 days, low: 180 days), findings tracked in issue tracker (Jira, GitHub Issues), progress reviewed in monthly security meetings
- DoD-SEC-015-08: Audit report reviewed: engineering team review completed (all findings understood, remediation plan agreed), security team review completed (findings prioritized, risk assessment conducted), executive team briefing completed (audit summary, remediation status, GA readiness)
- DoD-SEC-015-09: Remediation verification conducted: audit firm re-tests all critical and high-severity findings (100% remediation verified), re-test report delivered (0 critical/high findings remaining), final sign-off obtained from audit firm
- DoD-SEC-015-10: Final audit report published: executive summary shared with stakeholders (board, investors, customers), full report archived (secure storage, access controls), audit certificate issued (if applicable)
- DoD-SEC-015-11: SOC 2 Type II readiness assessment completed: control environment assessed (policies, procedures, training), control effectiveness assessed (monitoring, logging, incident response), readiness report delivered (gaps identified, remediation plan documented)
- DoD-SEC-015-12: Security roadmap updated: audit findings integrated into security roadmap (prioritized by severity, risk, and business impact), continuous improvement process defined (quarterly security reviews, annual audits, bug bounty program)
- DoD-SEC-015-13: Code review approved by 2+ engineers + security team with audit remediation checklist (all critical/high findings fixed, medium/low findings tracked, verification testing complete)

**Verification Method:** Manual (third-party audit + remediation verification)

**Test Files:**
- `tests/security/test_audit_remediation.py` (automated tests for remediated findings)
- `docs/security/Third_Party_Security_Audit_Report.pdf` (audit report)
- `docs/security/Audit_Remediation_Plan.md` (remediation tracking)

**Related Requirements:** SEC-001 (Data Encryption at Rest), SEC-002 (Data Encryption in Transit), SEC-004 (Access Control), SEC-006 (GDPR Compliance), SEC-013 (Authentication Provider Selection)

**Implementation Guidance:**
- 📄 **Security Audit Process:** `docs/specs/chronosrefine_implementation_plan.md#phase-6-production-readiness--launch` (to be cross-referenced)
- 📄 **Audit Scope:** `docs/specs/chronosrefine_prd_v9.md#beta-exit-criteria-ga-readiness`
- 📄 **Security Policies:** `companion_docs/ChronosRefine_Security_Policies.md` (to be created)
- 📄 **SOC 2 Readiness:** `companion_docs/ChronosRefine_SOC2_Readiness.md` (to be created)

---

## Operations Requirements

### OPS-001: Monitoring & Alerting

**Description:** System must implement comprehensive monitoring and alerting with Cloud Monitoring, Prometheus metrics, and PagerDuty integration.

**Acceptance Criteria:**
- AC-OPS-001-01: Cloud Monitoring integration for all GCP services (Cloud Run, GCS, Supabase Postgres, Redis)
- AC-OPS-001-02: Prometheus metrics endpoint (/v1/metrics) for custom application metrics
- AC-OPS-001-03: Key metrics tracked: job success rate, GPU utilization, processing time, API latency, error rate, cache hit rate
- AC-OPS-001-04: Alerting rules configured for SLO violations (job success rate <99.5%, processing time >2x video duration)
- AC-OPS-001-05: PagerDuty integration for critical alerts (on-call rotation)
- AC-OPS-001-06: Slack integration for non-critical alerts (team notifications)
- AC-OPS-001-07: Monitoring dashboard with real-time metrics (Grafana or Cloud Monitoring)
- AC-OPS-001-08: Log aggregation via Cloud Logging (structured JSON logs)
- AC-OPS-001-09: Distributed tracing via Cloud Trace (request correlation IDs)
- AC-OPS-001-10: Monitoring data retention: 90 days (metrics), 30 days (logs)

**Definition of Done:**
- DoD-OPS-001-01: Cloud Monitoring integration tested for **all 4 GCP services** (Cloud Run, GCS, Supabase Postgres, Redis) with **100% service coverage**, **<2 minute metric ingestion latency** (p95), **>99.9% metric collection uptime** (measured over 30-day period)
- DoD-OPS-001-02: Prometheus metrics endpoint tested with **/v1/metrics accessible** achieving **<100ms scrape time** (p95), **20+ custom metrics exposed** (job_success_rate, gpu_utilization, processing_time, api_latency, error_rate, cache_hit_rate), **Prometheus-compatible format** (validated by promtool)
- DoD-OPS-001-03: Key metrics tested with **all 6 metrics tracked** (job success rate ≥99.5%, GPU utilization >80%, processing time <2x video duration, API latency p95 <500ms, error rate <0.1%, cache hit rate >45%) achieving **<1 minute metric freshness** (p95)
- DoD-OPS-001-04: Alerting rules tested for **SLO violations** with **30+ alert scenarios** (job success rate <99.5%, processing time >2x duration, API latency >1s, error rate >1%) achieving **<2 minute alert delivery time** (p95), **<1% false positive rate**
- DoD-OPS-001-05: PagerDuty integration tested with **20+ critical alert scenarios** achieving **<1 minute alert delivery time** (p95), **100% alert delivery success rate**, **on-call rotation verified** (3+ engineers), **escalation policy tested** (15-minute escalation)
- DoD-OPS-001-06: Slack integration tested with **15+ non-critical alert scenarios** achieving **<30 second alert delivery time** (p95), **>99.9% delivery success rate**, **alert formatting verified** (rich formatting, links to dashboards)
- DoD-OPS-001-07: Monitoring dashboard created with **real-time metrics** (Grafana or Cloud Monitoring) displaying **all 6 key metrics**, **<5 second dashboard load time**, **auto-refresh every 30 seconds**, **mobile-responsive design**, **>4.0/5.0 usability score** (n=5 engineers)
- DoD-OPS-001-08: Log aggregation tested with **structured JSON logs** in Cloud Logging achieving **100% log capture rate**, **<30 second log ingestion latency** (p95), **zero log loss** (verified over 30-day period), **all 8 log levels supported** (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- DoD-OPS-001-09: Distributed tracing tested with **correlation IDs tracked** for **100% of requests** achieving **<100ms trace ingestion latency** (p95), **>99.9% trace capture rate**, **end-to-end request tracing** (API → processing → storage), **<2 second trace query time** (p95)
- DoD-OPS-001-10: Monitoring data retention tested with **90-day metrics retention** and **30-day logs retention** achieving **100% retention policy enforcement** (±1 day), **automated data deletion** after retention period, **zero retention policy violations**
- DoD-OPS-001-11: Code review approved by **2+ engineers** with **monitoring checklist** (all 15 items passed: metric coverage, alert thresholds, dashboard usability, log structure, trace completeness), **zero critical issues**, review completed within **24 hours**

**Verification Method:** Automated (pytest integration tests) + Manual (dashboard verification)

**Test Files:**
- `tests/ops/test_monitoring.py`
- `tests/ops/test_alerting.py`
- `tests/ops/test_prometheus_metrics.py`
- `tests/ops/test_pagerduty_integration.py`

**Related Requirements:** OPS-002 (SLO Monitoring), OPS-003 (Incident Response), SEC-004 (Access Control)

---

### OPS-002: SLO Monitoring

**Description:** System must track and report on Service Level Objectives (SLOs) with automated SLO violation detection and reporting.

**Acceptance Criteria:**
- AC-OPS-002-01: Four SLOs defined: Job Success Rate (99.5%), GPU Pool Pre-warm Time (p99 <120s), Processing Time (p95 <2x video duration), Reproducibility Success Rate (95% first attempt, 99% after retry)
- AC-OPS-002-02: SLO tracking dashboard with real-time compliance status
- AC-OPS-002-03: SLO violation alerts triggered when SLO breached (PagerDuty + Slack)
- AC-OPS-002-04: SLO error budget tracking (monthly error budget consumption)
- AC-OPS-002-05: SLO reporting: weekly SLO compliance report (automated email)
- AC-OPS-002-06: SLO historical data retention: 12 months
- AC-OPS-002-07: SLO breach postmortems required for critical SLO violations
- AC-OPS-002-08: SLO targets reviewed quarterly (adjusted based on performance data)
- AC-OPS-002-09: SLO compliance included in Museum Tier SLA
- AC-OPS-002-10: SLO metrics exported to Prometheus (/metrics endpoint)

**Definition of Done:**
- DoD-OPS-002-01: All 4 SLOs defined and tracked
- DoD-OPS-002-02: SLO tracking dashboard created (real-time compliance status)
- DoD-OPS-002-03: SLO violation alerts tested (PagerDuty + Slack)
- DoD-OPS-002-04: Error budget tracking tested (monthly consumption calculated)
- DoD-OPS-002-05: SLO reporting tested (weekly automated email)
- DoD-OPS-002-06: SLO historical data retention tested (12 months)
- DoD-OPS-002-07: SLO breach postmortem process documented
- DoD-OPS-002-08: SLO targets review process documented (quarterly)
- DoD-OPS-002-09: SLO compliance included in Museum Tier SLA
- DoD-OPS-002-10: SLO metrics tested (Prometheus /metrics endpoint)
- DoD-OPS-002-11: Code review approved by 2+ engineers

**Verification Method:** Automated (pytest integration tests) + Manual (SLO dashboard verification)

**Test Files:**
- `tests/ops/test_slo_monitoring.py`
- `tests/ops/test_slo_violation_alerts.py`
- `tests/ops/test_error_budget.py`

**Related Requirements:** OPS-001 (Monitoring & Alerting), OPS-003 (Incident Response), ENG-007 (Reproducibility Proof)

---

### OPS-003: Incident Response

**Description:** System must implement incident response procedures with on-call rotation, runbooks, and postmortem processes.

**Acceptance Criteria:**
- AC-OPS-003-01: On-call rotation configured in PagerDuty (24/7 coverage)
- AC-OPS-003-02: Incident severity levels: P0 (Critical), P1 (High), P2 (Medium), P3 (Low)
- AC-OPS-003-03: Incident response runbooks for common incidents (GPU pool exhaustion, API outage, data loss)
- AC-OPS-003-04: Incident escalation procedures (P0: immediate escalation, P1: escalate after 1 hour)
- AC-OPS-003-05: Incident communication plan (status page updates, customer notifications)
- AC-OPS-003-06: Incident postmortem process (required for P0/P1 incidents within 5 business days)
- AC-OPS-003-07: Incident tracking via issue tracker (Jira, Linear, GitHub Issues)
- AC-OPS-003-08: Incident metrics tracked: MTTR (Mean Time To Resolution), MTTD (Mean Time To Detection), incident frequency
- AC-OPS-003-09: Incident response training for on-call engineers (quarterly)
- AC-OPS-003-10: Incident response playbook maintained and updated quarterly

**Definition of Done:**
- DoD-OPS-003-01: On-call rotation configured (PagerDuty 24/7 coverage)
- DoD-OPS-003-02: Incident severity levels defined (P0/P1/P2/P3)
- DoD-OPS-003-03: Incident response runbooks created (3+ common incidents)
- DoD-OPS-003-04: Incident escalation procedures documented
- DoD-OPS-003-05: Incident communication plan documented (status page + customer notifications)
- DoD-OPS-003-06: Incident postmortem process documented (P0/P1 within 5 days)
- DoD-OPS-003-07: Incident tracking configured (Jira/Linear/GitHub Issues)
- DoD-OPS-003-08: Incident metrics tracked (MTTR, MTTD, frequency)
- DoD-OPS-003-09: Incident response training scheduled (quarterly)
- DoD-OPS-003-10: Incident response playbook created and maintained
- DoD-OPS-003-11: Code review approved by 2+ engineers

**Verification Method:** Manual (incident response drills + tabletop exercises)

**Test Files:**
- N/A (manual verification via incident response drills)

**Related Requirements:** OPS-001 (Monitoring & Alerting), OPS-002 (SLO Monitoring), OPS-004 (Performance Monitoring)

---

### OPS-004: Performance Monitoring

**Description:** System must monitor performance metrics with automated performance regression detection and optimization recommendations.

**Acceptance Criteria:**
- AC-OPS-004-01: Performance metrics tracked: API latency (p50/p95/p99), processing time (p50/p95/p99), GPU utilization, cache hit rate, error rate
- AC-OPS-004-02: Performance baselines established for all metrics (updated monthly)
- AC-OPS-004-03: Performance regression detection: automated alerts when metrics degrade >10% from baseline
- AC-OPS-004-04: Performance profiling tools integrated (Cloud Profiler, py-spy)
- AC-OPS-004-05: Performance optimization recommendations generated quarterly
- AC-OPS-004-06: Load testing conducted monthly (simulated peak load)
- AC-OPS-004-07: Performance dashboard with real-time metrics (Grafana or Cloud Monitoring)
- AC-OPS-004-08: Performance data retention: 90 days (detailed), 12 months (aggregated)
- AC-OPS-004-09: Performance metrics exported to Prometheus (/metrics endpoint)
- AC-OPS-004-10: Performance SLOs tracked (processing time p95 <2x video duration)

**Definition of Done:**
- DoD-OPS-004-01: All performance metrics tracked (API latency, processing time, GPU utilization, cache hit rate, error rate)
- DoD-OPS-004-02: Performance baselines established (updated monthly)
- DoD-OPS-004-03: Performance regression detection tested (alerts triggered for >10% degradation)
- DoD-OPS-004-04: Performance profiling tools integrated (Cloud Profiler, py-spy)
- DoD-OPS-004-05: Performance optimization recommendations generated (quarterly)
- DoD-OPS-004-06: Load testing conducted (monthly simulated peak load)
- DoD-OPS-004-07: Performance dashboard created (Grafana or Cloud Monitoring)
- DoD-OPS-004-08: Performance data retention tested (90d detailed, 12m aggregated)
- DoD-OPS-004-09: Performance metrics tested (Prometheus /metrics endpoint)
- DoD-OPS-004-10: Performance SLOs tracked (processing time p95 <2x video duration)
- DoD-OPS-004-11: Code review approved by 2+ engineers

**Verification Method:** Automated (pytest integration tests + load testing) + Manual (performance dashboard verification)

**Test Files:**
- `tests/ops/test_performance_monitoring.py`
- `tests/ops/test_performance_regression.py`
- `tests/load/test_peak_load.py`

**Related Requirements:** OPS-001 (Monitoring & Alerting), OPS-002 (SLO Monitoring), ENG-008 (GPU Pool Management)

---

## References

- GDPR (General Data Protection Regulation): https://gdpr.eu/
- SOC 2 Type II: https://www.aicpa.org/interestareas/frc/assuranceadvisoryservices/aicpasoc2report.html
- Cloud Audit Logs: https://cloud.google.com/logging/docs/audit
- Cloud Monitoring: https://cloud.google.com/monitoring
- Prometheus: https://prometheus.io/
- PagerDuty: https://www.pagerduty.com/

---

**End of Security & Operations Requirements**
