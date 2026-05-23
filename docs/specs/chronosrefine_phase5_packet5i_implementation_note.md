# Phase 5 Packet 5I: SEC-002 Encryption Controls Implementation Note

Date: 2026-05-12

## Scope

Packet 5I adds local SEC-002 encryption-control verification scaffolding only. It records the canon-derived
contracts for AES-256 GCS bucket encryption, TLS 1.3 cipher enforcement, HSTS configuration, and certificate
renewal evidence boundaries.

This packet does not mutate hosted infrastructure, does not add runtime application behavior, and does not
claim global `SEC-002` closeout.

## Local Evidence Added

- `tests/security/test_encryption_at_rest.py` verifies the required uploads, outputs, and backups bucket
  roles use the AES-256 default-encryption contract and that Packet 5I encryption checks are disabled by
  default. CMEK-backed buckets are still AES-256 encrypted at rest; Packet 5I defers CMEK key-management
  behavior rather than treating CMEK as non-compliant.
- `tests/security/test_encryption_in_transit.py` verifies the canonical TLS 1.3 cipher-suite contract and
  documents that SSL Labs A+ scan, TLS 1.0/1.1 rejection evidence, and TLS handshake p95 evidence remain
  hosted gates. Packet 5I does not emulate live protocol negotiation because cipher negotiation is enforced
  by the edge or certificate-terminating platform in hosted environments. Deprecated protocol evidence must
  cover TLS 1.0 and TLS 1.1 individually.
- `tests/security/test_tls_configuration.py` verifies the HSTS one-year max-age contract and keeps
  certificate auto-renewal scenarios outside local-only closeout. `includeSubDomains` and `preload` are part
  of the Packet 5I HSTS contract.
- Packet 5I does not claim certificate-renewal closeout.
- `infra/terraform/variables.tf` adds `manage_sec002_encryption_checks`, disabled by default, so future
  Terraform inspection resources can be introduced without breaking unauthenticated local/CI plans.

## CMEK Forward Reference

The SEC-002 matrix row intentionally retains `tests/security/test_cmek.py` because it is listed in the
canonical SEC-002 test-file list. `tests/security/test_cmek.py` is intentionally not created in Packet 5I:
full CMEK implementation and key-rotation coverage remain reserved for `SEC-007`.

Until `SEC-007` starts, Packet 5I asserts the CMEK deferral state in `tests/security/test_encryption_at_rest.py`.

## Open Hosted And Review Gates

`SEC-002` remains open until all canon-required hosted and external evidence is captured. SEC-002 remains open
until these gates pass:

- SSL Labs A+ scan with score >=95/100 against the staged externally exposed endpoints.
- Runtime evidence that TLS 1.0/1.1 connections are rejected.
- TLS handshake p95 evidence below 50ms.
- Certificate auto-renewal scenarios and zero-downtime propagation evidence.
- AES-256 coverage evidence for all stored objects in the uploads, outputs, and backups buckets.
- Encryption performance overhead evidence from load testing.
- Two-engineer encryption checklist review.
- External cryptographic audit by a certified auditor with zero critical/high vulnerabilities.

No Phase 5 tracker counts move in Packet 5I.
