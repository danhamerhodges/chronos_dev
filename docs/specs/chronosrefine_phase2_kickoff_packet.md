# ChronosRefine Phase 2 Kickoff Packet

**Date:** 2026-03-05  
**Phase:** Phase 2 - API Foundation & Data Layer  
**Status:** Ready for implementation handoff  
**Source of truth:** `docs/specs/*` canonical ordering in `AGENTS.md`

---

## 1) Objective

Deliver the Phase 2 requirement set that unlocks API and data-layer execution:

- **ENG-001** JSON Schema Validation
- **ENG-002** API Endpoint Implementation
- **ENG-004** Era Detection Model
- **FR-002** Era Detection
- **SEC-009** Log Retention & PII Redaction
- **NFR-007** Cost Control Requirements

Phase 2 is complete when these six requirements have passing mapped tests and phase exit criteria evidence.

---

## 2) Dependency and Phase Gate Check

Confirmed against coverage matrix + implementation plan:

- Phase 1 prerequisites are the baseline requirements: `ENG-016`, `SEC-013`, `DS-007`, `NFR-012`, `OPS-001`, `OPS-002`.
- Phase 2 dependencies from matrix:
  - `ENG-002` depends on `ENG-001`, `SEC-013`, `ENG-016`.
  - `FR-002` depends on `ENG-001`, `ENG-004`.
  - `SEC-009` depends on `SEC-013`, `OPS-001`, `OPS-002`, `ENG-016`.
  - `NFR-007` depends on `ENG-001`, `NFR-012`.

---

## 3) Deliverable Contract (Phase 2)

### 3.1 Core Implementation Outcomes

1. Schema validation layer for job payloads and era-profile contracts (`ENG-001`).
2. Authenticated, DB-backed API foundation with OpenAPI-aligned endpoints (`ENG-002`).
3. Era-detection model integration and confidence workflow path (`ENG-004`, `FR-002`).
4. Log-retention, PII-redaction, and GDPR deletion controls implemented at API and policy level (`SEC-009`).
5. Cost-control enforcement and reporting hooks for billing and operations (`NFR-007`).

### 3.2 Out of Scope (Phase 2)

- Full media processing pipeline and GPU orchestration (`ENG-003`, Phase 3).
- User-facing end-to-end upload/preview/restore workflows (`FR-001`, `FR-004`, Phase 4+).
- Beta/GA gate audits and launch operations (Phase 6).

---

## 4) Workstreams

### Workstream A - Schema and Validation (`ENG-001`)

- Define/lock schema contracts and enum validation.
- Return structured validation failures.
- Enforce pre-submission validation path.

### Workstream B - API Foundation (`ENG-002`)

- Build authenticated endpoint scaffolding with RLS-safe request handling.
- Add RFC7807-compatible error responses.
- Add versioned health/status API coverage and OpenAPI parity.

### Workstream C - Era Detection (`ENG-004`, `FR-002`)

- Implement model interface and deterministic fallback behavior.
- Add confidence threshold handling and manual override integration contract.
- Add telemetry for accuracy/latency and model outputs.

### Workstream D - Security + Cost Controls (`SEC-008`, `NFR-007`)

- Implement/validate log-retention, redaction, and deletion-policy expectations.
- Add cost-control/budget guardrails and policy checks.
- Ensure compatibility with Stripe-configured pricing model from Phase 1.

---

## 5) Test Mapping (Canonical)

| Requirement | Primary Tests |
|---|---|
| ENG-001 | `tests/api/test_schema_validation.py` |
| ENG-002 | `tests/api/test_endpoints.py` |
| ENG-004 | `tests/ml/test_era_detection.py`, `tests/ml/test_gemini_integration.py` |
| FR-002 | `tests/api/test_era_detection.py`, `tests/integration/test_era_detection_e2e.py` |
| SEC-009 | `tests/security/test_log_retention.py`, `tests/security/test_pii_redaction.py`, `tests/compliance/test_gdpr_log_deletion.py` |
| NFR-007 | `tests/billing/test_cost_control.py`, `tests/billing/test_budget_alerts.py` |

Phase 2 implementation must also preserve:

- `python3 scripts/validate_test_traceability.py`
- Existing Phase 1 regression suites in CI baseline

---

## 6) Verification Commands

### 6.1 Planning/Documentation Verification

```bash
rg -n "^## Phase [1-6]:" "docs/specs/ChronosRefine Requirements Coverage Matrix.md"
rg -n "^### Phase [1-6]:|\\*\\*Requirements Implemented:\\*\\*" docs/specs/chronosrefine_implementation_plan.md
python3 scripts/validate_test_traceability.py
./scripts/validate_codex_setup.sh
```

### 6.2 Implementation Verification Target (Post-Phase 2 Build)

```bash
pytest tests/api tests/ml tests/security tests/billing -q
pytest -q
```

---

## 7) Risks and Mitigations

1. **Schema/API drift risk** (`ENG-001`, `ENG-002`)  
   Mitigation: lock schema + OpenAPI updates in same changeset and gate with tests.

2. **Auth and deletion-path misconfiguration risk** (`ENG-002`, `SEC-009`)  
   Mitigation: enforce end-user JWT path for user-scoped operations; explicitly test cross-user denial cases.

3. **Model confidence and fallback ambiguity** (`ENG-004`, `FR-002`)  
   Mitigation: codify confidence thresholds and fallback path with deterministic test fixtures.

4. **Cost-control semantics mismatch** (`NFR-007`, `NFR-012`)  
   Mitigation: keep billing logic configuration-driven from Stripe Product/Price IDs; add reconciliation assertions.

---

## 8) Environment Contract for Phase 2 Work

Baseline variable mapping (current repo):

- `DATABASE_URL = N/A`
- `SUPABASE_URL = SUPABASE_URL_DEV`
- `SUPABASE_ANON_KEY = SUPABASE_ANON_KEY_DEV`

Required for unit-only developer loop:

- `ENVIRONMENT=test`
- `SUPABASE_URL`
- `TEST_AUTH_OVERRIDE` (per test-template contract)

Phase 2 note:

- `SUPABASE_URL` may continue to resolve from `SUPABASE_URL_DEV` via config fallback in the current baseline.
- `SUPABASE_ANON_KEY` may continue to resolve from `SUPABASE_ANON_KEY_DEV` via config fallback in the current baseline.

---

## 9) Exit Definition for This Packet

This kickoff packet is complete when:

1. Requirement IDs and titles match canonical specs (no drift in matrix/plan references).
2. Phase 2 scope and dependencies are explicit and test-mapped.
3. Verification command set is documented and runnable in CI/local context.
