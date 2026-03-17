# ChronosRefine Requirements Coverage Matrix

**Version:** 11.5 (FINAL PRODUCTION)  
**Last Updated:** March 2026  
**Purpose:** Map all 59 requirements to implementation phases to ensure 100% coverage and identify dependencies

**Repo Note:** For phases not yet implemented on `main`, listed test files are canonical target mappings rather than checked-in evidence. Completed-phase rows should align to the repo.

**Change Note (v11.0 - February 2026):** Applied 7-patch regression fix pack:
1. Added Canonical Requirement ID Map section (prevents future drift)
2. Fixed DS-001 through DS-006 in Phase 4 (6 requirements corrected)
3. Verified DS-007 placement in Phase 1 (correct)
4. Replaced ENG-008 through ENG-012 in Phase 3 (5 requirements corrected)
5. Fixed ENG-013/ENG-014/ENG-015 placements and names (3 requirements corrected)
6. Repaired Critical Path section (ENG-016 instead of ENG-003 for database)
7. Fixed Risk Assessment Summary math (derived from matrix, not hand-edited)

**Change Note (v11.1 - February 2026):** Applied 4-patch dependency/accuracy fix pack:
1. **FIX #1 (CRITICAL):** Moved ENG-002 from Phase 4 to Phase 2 (fixes ENG-011 backward dependency)
2. **FIX #2 (CRITICAL):** Changed ENG-013 dependencies from "FR-006, ENG-002" to "FR-004, ENG-002" (fixes backward dependency)
3. **FIX #3 (IMPORTANT):** Added ENG-014 to FR-006 dependencies (clarifies preview generation implementation relationship)
4. **FIX #4 (CRITICAL):** Corrected Risk Assessment Summary (23 High, not 21; 24 Medium, not 26)

**Change Note (v11.2 - February 2026):** Applied 4-patch dependency completeness fix pack:
1. **FIX #1 (IMPORTANT):** Updated ENG-002 dependencies to include SEC-013, ENG-016 (API needs auth + database)
2. **FIX #2 (IMPORTANT):** Updated FR-001 dependencies to include SEC-013 (upload needs auth)
3. **FIX #3 (CRITICAL):** Corrected Risk Assessment Summary to 28 Medium (47%), 8 Low (14%) - matches actual matrix
4. **FIX #4 (OPTIONAL):** Added FR-001 to FR-006 dependencies (explicit clarity for preview generation)

**Change Note (v11.3 - February 2026):** Applied 2-patch sequencing optimization pack:
1. **IMPROVEMENT #1 (CRITICAL):** Changed FR-001 dependencies from "SEC-013, ENG-002, ENG-003" to "SEC-013, ENG-002, ENG-016" (upload doesn't need full processing pipeline - accelerates early progress)
2. **IMPROVEMENT #2 (IMPORTANT):** Changed ENG-014 dependencies from "FR-001" to "FR-001, ENG-002" (preview generation exposed via API)

**Change Note (v11.4 - February 2026):** Applied 3-patch clarity improvement pack:
1. **CLARITY #1 (IMPORTANT):** Added FR-001 scope clarification note (upload/validation only, no segmentation/transforms)
2. **CLARITY #2 (IMPORTANT):** Added ENG-002 scaffolding note (authenticated + DB-backed endpoints required for DoD)
3. **CLARITY #3 (CONSISTENCY):** Normalized phase names across Coverage Summary, section headers, and phase goals

**Change Note (v11.5 - March 2026):** Applied Phase 3 closeout + Phase 4 kickoff reconciliation pack:
1. **STATUS #1 (CRITICAL):** Reconciled Phase 2 and Phase 3 progress rows with merged-state git history on `main`
2. **STATUS #2 (IMPORTANT):** Marked Phase 3 as kickoff-complete with `SEC-007` deferred per canon
3. **PHASE 4 #1 (IMPORTANT):** Added explicit Packet 4A kickoff note centered on `FR-001`
4. **TRACEABILITY #1 (IMPORTANT):** Aligned drifted Phase 4/5 test-file mappings with the higher-priority requirement specs

---

## Matrix Overview

This matrix maps each requirement to its implementation phase, identifies dependencies, specifies test files, and assesses risk level. Use this matrix to:
- Track implementation progress (% requirements complete per phase)
- Identify dependency chains (build order)
- Prioritize high-risk requirements
- Ensure no requirements are orphaned

---

## Canonical Requirement ID Map (Source of Truth)

This Coverage Matrix MUST match the canonical requirement IDs and titles in these documents:
- **Functional Requirements** (FR-xxx): `docs/specs/chronosrefine_functional_requirements.md`
- **Engineering Requirements** (ENG-xxx): `docs/specs/chronosrefine_engineering_requirements.md`
- **Security & Operations Requirements** (SEC-xxx / OPS-xxx): `docs/specs/chronosrefine_security_operations_requirements.md`
- **Nonfunctional Requirements** (NFR-xxx): `docs/specs/chronosrefine_nonfunctional_requirements.md`
- **Design Requirements** (DS-xxx): `docs/specs/chronosrefine_design_requirements.md`

If an ID/title conflicts with the above, this matrix must be updated immediately.

---

## Coverage Summary

| Phase | Requirements | Percentage |
|---|---|---|
| **Phase 1: Foundation & Core Infrastructure** | 6 requirements | 10% |
| **Phase 2: API Foundation & Data Layer** | 6 requirements | 10% |
| **Phase 3: Core Processing Pipeline & AI Integration** | 12 requirements | 25% |
| **Phase 4: User-Facing Features & Application Logic** | 14 requirements | 24% |
| **Phase 5: Advanced Features & UX Refinement** | 11 requirements | 19% |
| **Phase 6: Production Readiness & Launch** | 10 requirements | 17% |
| **TOTAL** | **59 requirements** | **100%** |

---

## Phase 1: Foundation & Core Infrastructure (6 requirements, 10%)

| Req ID | Requirement Name | Dependencies | Test Files | Verification | Risk |
|---|---|---|---|---|---|
| **ENG-016** | Database Technology Selection (Supabase) | None | `tests/database/test_supabase_connection.py`, `tests/database/test_schema_migrations.py` | Automated | Medium |
| **SEC-013** | Authentication Provider Selection (Supabase) | ENG-016 | `tests/auth/test_supabase_auth.py`, `tests/auth/test_oauth_integration.py`, `tests/auth/test_email_password_auth.py` | Automated | Medium |
| **DS-007** | Design System Implementation | None | `tests/design_system/test_tokens.spec.ts`, `tests/visual_regression/test_all_components.spec.ts` | Automated + Manual | Low |
| **NFR-012** | Payment Provider Selection | SEC-013 | `tests/billing/test_stripe_integration.py`, `tests/billing/test_subscription_lifecycle.py` | Automated | Medium |
| **OPS-001** | Monitoring & Alerting | None | `tests/ops/test_monitoring.py` | Automated | Low |
| **OPS-002** | SLO Monitoring | OPS-001 | `tests/ops/test_logging.py` | Automated | Low |

**Phase Goal:** Establish CI/CD, monitoring, infrastructure foundation, database, authentication, design system, and payment integration

---

## Phase 2: API Foundation & Data Layer (6 requirements, 10%)

| Req ID | Requirement Name | Dependencies | Test Files | Verification | Risk |
|---|---|---|---|---|---|
| **ENG-001** | JSON Schema Validation | None | `tests/api/test_schema_validation.py` | Automated | Medium |
| **ENG-002** | API Endpoint Implementation | ENG-001, SEC-013, ENG-016 | `tests/api/test_endpoints.py` | Automated | Medium |
| **ENG-004** | Era Detection Model | ENG-001 | `tests/ml/test_era_detection_service.py`, `tests/ml/test_gemini_integration.py` | Automated | High |
| **FR-002** | Era Detection | ENG-001, ENG-004 | `tests/api/test_era_detection.py`, `tests/integration/test_era_detection_e2e.py` | Automated | High |
| **SEC-009** | Log Retention & PII Redaction | SEC-013, OPS-001, OPS-002, ENG-016 | `tests/security/test_log_retention.py`, `tests/security/test_pii_redaction.py`, `tests/compliance/test_gdpr_log_deletion.py` | Automated + Manual | High |
| **NFR-007** | Cost Control Requirements | ENG-001, NFR-012 | `tests/billing/test_cost_control.py`, `tests/billing/test_budget_alerts.py` | Manual | Medium |

**Phase Goal:** Implement REST API foundation, schema validation, era detection, and compliance

**Note:** ENG-002 moved from Phase 4 to Phase 2 to resolve backward dependency (ENG-011 in Phase 3 depends on ENG-002).

---

## Phase 3: Core Processing Pipeline & AI Integration (12 requirements, 25%)

| Req ID | Requirement Name | Dependencies | Test Files | Verification | Risk |
|---|---|---|---|---|---|
| **ENG-003** | Video Processing Pipeline | ENG-001, ENG-016 | `tests/processing/test_pipeline.py`, `tests/processing/test_segment_processing.py` | Automated | High |
| **ENG-005** | Fidelity Tier Implementation | ENG-001, FR-002 | `tests/processing/test_fidelity_tiers.py`, `tests/ml/test_codeformer.py` | Automated | High |
| **ENG-006** | Quality Metrics Calculation | ENG-003, ENG-005 | `tests/quality/test_metrics_calculation.py`, `tests/quality/test_e_hf_s_ls_t_tc.py` | Automated | High |
| **ENG-007** | Reproducibility Proof | ENG-003, ENG-006 | `tests/processing/test_av1_fgs.py`, `tests/processing/test_reproducibility.py` | Automated | High |
| **ENG-008** | GPU Pool Management | ENG-003, OPS-003 | `tests/infrastructure/test_gpu_pool.py`, `tests/infrastructure/test_autoscaler.py` | Automated + Load | High |
| **ENG-009** | Deduplication Cache | ENG-003 | `tests/infrastructure/test_cache_dedup.py`, `tests/integration/test_partial_results.py` | Automated | Medium |
| **ENG-010** | Transformation Manifest Generation | ENG-003, ENG-006, ENG-007 | `tests/processing/test_manifest_generation.py`, `tests/api/test_transformation_manifest.py` | Automated | High |
| **ENG-011** | Async Processing | ENG-002, ENG-003 | `tests/api/test_async_processing.py`, `tests/api/test_progress_updates.py` | Automated + Load | High |
| **ENG-012** | Error Recovery | ENG-003, ENG-011 | `tests/processing/test_error_recovery.py`, `tests/integration/test_partial_results.py` | Automated | High |
| **NFR-002** | Processing Time SLO | ENG-003, ENG-007 | `tests/load/test_processing_performance.py` | Automated | High |
| **SEC-007** | Customer-Managed Encryption Keys (CMEK) | ENG-005, ENG-006 | Deferred; no repo-local automated test on `main` | Manual | Medium |
| **OPS-003** | Incident Response | ENG-008 | `tests/ops/test_incident_response.py`, `infra/runbooks/incident-response.md` | Automated + Manual | High |

**Phase Goal:** Build and validate core AI/ML processing pipeline

**High-Risk Requirements:** ENG-003, ENG-005, ENG-006, ENG-007, ENG-008, ENG-010, ENG-011, ENG-012, NFR-002, OPS-003 (10 high-risk requirements - requires extra attention)

---

## Phase 4: User-Facing Features & Application Logic (14 requirements, 24%)

| Req ID | Requirement Name | Dependencies | Test Files | Verification | Risk |
|---|---|---|---|---|---|
| **FR-001** | Video Upload and Validation | SEC-013, ENG-002, ENG-016 | `tests/api/test_upload.py` | Automated | Medium |
| **FR-003** | Fidelity Tier Selection | FR-002, ENG-001 | `tests/api/test_fidelity_configuration.py`, `tests/processing/test_tier_parameters.py`, `tests/ui/test_tier_selection.spec.ts` | Automated | Low |
| **FR-004** | Processing and Restoration | FR-001, FR-003, ENG-007 | `tests/processing/test_restoration_pipeline.py`, `tests/processing/test_uncertainty_callouts.py`, `tests/processing/test_retry_logic.py` | Automated | High |
| **FR-005** | Output Delivery | FR-004, ENG-007 | `tests/api/test_output_delivery.py`, `tests/api/test_transformation_manifest.py`, `tests/api/test_deletion_proof.py`, `tests/integration/test_export_workflow.py` | Automated | Medium |
| **ENG-013** | Cost Estimation | FR-004, ENG-002 | `tests/api/test_cost_estimation.py`, `tests/api/test_cost_breakdown.py`, `tests/integration/test_cost_reconciliation.py` | Automated | Medium |
| **ENG-014** | Preview Generation | FR-001, ENG-002 | `tests/processing/test_preview_generation.py`, `tests/processing/test_scene_detection.py`, `tests/load/test_preview_performance.py` | Automated | Medium |
| **ENG-015** | Output Encoding | FR-004 | `tests/processing/test_output_encoding.py`, `tests/processing/test_av1_encoding.py`, `tests/processing/test_metadata_preservation.py`, `tests/processing/test_encoding_performance.py` | Automated | High |
| **DS-001** | Fidelity Configuration UX | FR-002, FR-003 | `tests/ui/test_fidelity_tier_selector.spec.ts`, `tests/ui/test_era_override_modal.spec.ts`, `tests/accessibility/test_fidelity_config_a11y.spec.ts` | UI Validation | Medium |
| **DS-002** | Keyboard Navigation | DS-001 | `tests/accessibility/test_keyboard_navigation.spec.ts`, `tests/accessibility/test_focus_indicators.spec.ts`, `tests/accessibility/test_keyboard_shortcuts.spec.ts` | UI Validation | Medium |
| **DS-003** | Screen Reader Support | DS-001, DS-002 | `tests/accessibility/test_screen_reader_support.spec.ts`, `tests/accessibility/test_aria_labels.spec.ts`, `tests/accessibility/test_aria_live_regions.spec.ts` | UI Validation | Medium |
| **DS-004** | Color Contrast | DS-007 | `tests/accessibility/test_color_contrast.spec.ts`, `tests/accessibility/test_button_contrast.spec.ts`, `tests/accessibility/test_focus_contrast.spec.ts` | UI Validation | Medium |
| **DS-005** | Focus Indicators | DS-002, DS-003 | `tests/accessibility/test_focus_management.spec.ts`, `tests/accessibility/test_modal_focus.spec.ts`, `tests/accessibility/test_form_focus.spec.ts` | UI Validation | Medium |
| **DS-006** | Error Messages Accessibility | DS-003 | `tests/accessibility/test_error_messages.spec.ts`, `tests/accessibility/test_error_announcements.spec.ts`, `tests/accessibility/test_uncertainty_callouts_a11y.spec.ts` | UI Validation | Medium |
| **NFR-003** | Cost Optimization | ENG-002 | `tests/ops/test_cost_optimization.py`, `tests/ops/test_gpu_utilization.py`, `tests/ops/test_cost_tracking.py` | Automated | Medium |

**Phase Goal:** Build user interface and API layer

**High-Risk Requirements:** FR-004, ENG-015 (2 high-risk requirements)

**Note:** FR-001 covers upload, format/size validation, checksum, and metadata persistence only; no segmentation/transforms (ENG-003) required.

**Note:** ENG-002 includes authenticated + DB-backed endpoints; routing/scaffolding may begin earlier but does not satisfy ENG-002 DoD.

**Note:** ENG-013 dependencies changed from "FR-006, ENG-002" to "FR-004, ENG-002" to resolve backward dependency (FR-006 is in Phase 5).

---

## Phase 5: Advanced Features & UX Refinement (11 requirements, 19%)

| Req ID | Requirement Name | Dependencies | Test Files | Verification | Risk |
|---|---|---|---|---|---|
| **FR-006** | Preview Generation | FR-001, FR-002, ENG-007, ENG-014 | `tests/processing/test_preview_generation.py`, `tests/processing/test_scene_detection.py`, `tests/ui/test_preview_modal.spec.ts`, `tests/load/test_preview_performance.py` | Automated | Medium |
| **SEC-001** | Authentication & Authorization | FR-005, ENG-010 | `tests/security/test_deletion_proof.py` | Automated | High |
| **SEC-002** | Data Encryption | FR-002, ENG-007 | `tests/quality/test_uncertainty.py` | Automated | Medium |
| **SEC-003** | Data Classification | ENG-010, SEC-008 | `tests/security/test_manifest_redaction.py` | Automated | Medium |
| **SEC-004** | Access Control | ENG-016 | `tests/security/test_encryption.py` | Automated | High |
| **SEC-005** | Transformation Manifest Retention | SEC-013 | `tests/security/test_access_control.py` | Automated | Medium |
| **SEC-006** | GDPR Compliance | OPS-002, SEC-005 | `tests/security/test_audit_logging.py` | Automated | Low |
| **NFR-004** | Reliability & Availability | FR-003, SEC-013 | `tests/api/test_feature_gating.py` | Automated | Medium |
| **NFR-005** | Museum SLA & Disaster Recovery | FR-004, OPS-001 | `tests/ops/test_cost_control.py` | Automated | Medium |
| **NFR-006** | Pricing Model | DS-001, DS-002, DS-003, DS-004, DS-005, DS-006 | User testing | Manual | Low |
| **NFR-009** | Internationalization (i18n) | OPS-003 | `tests/ops/test_autoscaling.py` | Automated | High |

**Phase Goal:** Implement advanced features and tier-specific functionality

**High-Risk Requirements:** SEC-001, SEC-004, NFR-009 (3 high-risk requirements)

**Note:** FR-006 now explicitly depends on ENG-014 (Preview Generation implementation) to clarify the implementation relationship between the functional requirement (FR-006) and the technical implementation (ENG-014).

---

## Phase 6: Production Readiness & Launch (10 requirements, 17%)

| Req ID | Requirement Name | Dependencies | Test Files | Verification | Risk |
|---|---|---|---|---|---|
| **FR-007** | Human Preference Score (HPS) Validation | FR-002, ENG-003, ENG-005, ENG-007 | `tests/hps/test_evaluation_platform.py`, `tests/hps/test_statistical_analysis.py` | Manual + Automated | High |
| **NFR-001** | Cost Estimate Display | FR-007 | HPS protocol | Manual | High |
| **SEC-015** | Third-Party Security Audit | All SEC requirements | `tests/security/test_audit_remediation.py`, audit report | Manual | High |
| **NFR-008** | Usability | SEC-001, SEC-008, SEC-015 | Compliance audit | Manual | High |
| **NFR-010** | Documentation | All requirements | Documentation review | Manual | Low |
| **SEC-008** | VPC Service Controls (Post-GA roadmap) | ENG-016, OPS-002 | `tests/security/test_vpc_controls.py`, `tests/security/test_network_isolation.py` | Manual | High |
| **SEC-010** | Deletion Proofs | All requirements | Security scan | Automated | Medium |
| **SEC-011** | Dataset Provenance | OPS-001, SEC-006 | Runbook review | Manual | Medium |
| **SEC-012** | Data Residency | ENG-016, OPS-003 | DR drill | Manual | High |
| **OPS-004** | Performance Monitoring | OPS-001, OPS-002 | Runbook review | Manual | Low |

**Phase Goal:** Validate production readiness through HPS validation, security audit, compliance verification, and operational readiness

**High-Risk Requirements:** FR-007, NFR-001, SEC-015, NFR-008, SEC-009, SEC-012 (6 high-risk requirements - GA blockers)

---

## Dependency Graph (Critical Path)

The following requirements form the critical path and must be completed in order:

1. **ENG-016** (Database Technology Selection – Supabase) → persistence foundation
2. **SEC-013** (Authentication Provider Selection – Supabase Auth) → secure user identity
3. **ENG-001** (JSON Schema Validation) → valid job definitions
4. **ENG-002** (API Endpoint Implementation) → user/API entrypoint
5. **ENG-003** (Video Processing Pipeline) → segment execution backbone
6. **ENG-007** (Reproducibility Proof) → determinism/auditability baseline
7. **FR-004** (Processing and Restoration) → end-to-end job orchestration
8. **ENG-010** (Transformation Manifest Generation) → audit trail needed for SEC features
9. **NFR-001** (HPS Gate) → GA launch gate

**Critical Path Duration:** Phases 1-6 (estimated 16-20 weeks)

---

## Risk Assessment Summary (Derived)

Risk counts MUST be derived from the matrix rows (do not hand-edit).
After updating the matrix, recalculate:

**Actual Counts (from matrix above):**
- **High:** 23 requirements (39%)
- **Medium:** 28 requirements (47%)
- **Low:** 8 requirements (14%)
- **Total:** 59 requirements (100%)

**High-Risk Requirements Requiring Special Attention:**

### Phase 2 (2 High)
- ENG-004 (Era Detection Model) - Core AI functionality
- FR-002 (Era Detection) - Core AI functionality

### Phase 3 (10 High)
- ENG-003 (Video Processing Pipeline) - Core processing
- ENG-005 (Fidelity Tier Implementation) - Complex algorithms
- ENG-006 (Quality Metrics Calculation) - Complex algorithms
- ENG-007 (Reproducibility Proof) - Determinism critical
- ENG-008 (GPU Pool Management) - Cost and performance critical
- ENG-010 (Transformation Manifest Generation) - Reproducibility critical
- ENG-011 (Async Processing) - User experience critical
- ENG-012 (Error Recovery) - Reliability critical
- NFR-002 (Processing Time SLO) - User experience critical
- OPS-003 (Incident Response) - Cost and performance critical

### Phase 4 (2 High)
- FR-004 (Job Orchestration) - Critical path
- ENG-015 (Output Encoding) - Output quality critical

### Phase 5 (3 High)
- SEC-001 (Authentication & Authorization) - Security critical
- SEC-004 (Access Control) - Security critical
- NFR-009 (Internationalization) - Launch readiness

### Phase 6 (6 High)
- FR-007 (HPS Validation) - GA gate
- NFR-001 (Cost Estimate Display) - Launch blocker
- SEC-015 (Third-Party Security Audit) - Security validation
- NFR-008 (Usability) - Legal and launch requirement
- SEC-009 (Log Retention & PII Redaction) - Security validation
- SEC-012 (Data Residency) - Business continuity

---

## Current Progress Snapshot (2026-03-15)

Source evidence:
- `README.md` (Phase 1 baseline scope)
- `docs/phase1_readiness_report.md` (Phase 1 exit-gate report)
- `git log --oneline --decorate -n 8` and `git ls-remote --heads origin main`
- PR merge history on `main` (`709687a` for Phase 2, `a5b0f6c` for Phase 3, `5ac15cd` docs follow-up)
- Current test coverage + traceability headers under `tests/`
- `python3 scripts/ops/verify_cloud_run_runtime.py --service chronos-phase1-app --project chronos-dev-489301 --region us-central1`
- `curl https://chronos-phase1-app-19961431854.us-central1.run.app/v1/version`
- Packet 4A live-smoke evidence (`memory-live-smoke.json`, `supabase-live-smoke.json`, `staging-latency.json`) summarized in `docs/specs/chronosrefine_phase4_closeout_note.md`

| Phase | Requirements | Status | Notes |
|---|---:|---|---|
| Phase 1: Foundation & Core Infrastructure | 6/6 | ✅ Complete (baseline scope) | Baseline scaffolding and validation confirmed in `docs/phase1_readiness_report.md` |
| Phase 2: API Foundation & Data Layer | 6/6 | ✅ Complete (merged via PR #1) | `main` includes merge commit `709687a`; this is the canonical baseline for later phases |
| Phase 3: Core Processing Pipeline & AI Integration | 11/12 | ✅ Complete for Phase 4 kickoff | PR #2 merged to `main`; `SEC-007` remains deferred to its canonical `GA+3 months` milestone |
| Phase 4: User-Facing Features & Application Logic | 9/14 on `main`; 13/14 on candidate branch | 🚧 In Progress (Packets 4A, 4B, 4C, 4D, 4E, and 4F merged on `main`; Packet 4G is complete on the candidate branch) | `FR-001`, `FR-003` + `DS-001`, `FR-004` + the Packet 4C portion of `DS-006`, `FR-005` + `ENG-015`, `ENG-013` + the launch-decision slice of `NFR-003`, and `ENG-014` preview-generation substrate are complete on `main`; Packet 4G closes the Phase 4 accessibility requirements on the candidate branch, `NFR-003` remains the only open Phase 4 requirement, and Packet 4H remains next |
| Phase 5: Advanced Features & UX Refinement | 0/11 | ⏸️ Not Started | Dependent on Phase 4 completion |
| Phase 6: Production Readiness & Launch | 0/10 | ⏸️ Not Started | Dependent on Phase 5 completion |

### Phase 1 Progress: Foundation & Core Infrastructure

**Requirements:** 6 of 6 complete (baseline scope)  
**Status:** Complete (Phase 1 baseline)  
**Completion Date:** 2026-03-02 (readiness report)

| Req ID | Status | Notes |
|---|---|---|
| ENG-016 | ✅ Complete | Supabase baseline schema, migrations, and client scaffolding in place |
| SEC-013 | ✅ Complete | Supabase auth baseline and RBAC/session scaffolding in place |
| DS-007 | ✅ Complete | Design tokens, component primitives, and Storybook baseline in place |
| NFR-012 | ✅ Complete | Stripe Product/Price configuration and webhook scaffolding in place |
| OPS-001 | ✅ Complete | `/v1/metrics`, structured logging, and monitoring placeholders in place |
| OPS-002 | ✅ Complete | SLO baseline definitions and error-budget scaffolding in place |

### Phase 2 Progress: API Foundation & Data Layer

**Requirements:** 6 of 6 complete (merged to `main`)  
**Status:** Complete (merged via PR #1)  
**Completion Date:** Target TBD / Actual 2026-03-06 (`main` at `709687a`)

| Req ID | Status | Notes |
|---|---|---|
| ENG-001 | ✅ Complete | JSON Schema validation merged to `main` in PR #1 |
| ENG-002 | ✅ Complete | Approved Phase 2 API subset merged; canonical ENG-002 endpoint scope remains broader in Engineering Requirements |
| ENG-004 | ✅ Complete | Era-detection service, provider fallback, and persistence merged to `main` |
| FR-002 | ✅ Complete | `/v1/detect-era` contract, manual override, and integration coverage merged |
| SEC-009 | ✅ Complete | Log retention, PII redaction, and log-deletion flows merged to `main` |
| NFR-007 | ✅ Complete | Billing limits, overage approval, and usage controls merged to `main` |

### Phase 3 Progress: Core Processing Pipeline & AI Integration

**Requirements:** 11 of 12 complete on `main` (92%; `SEC-007` deferred per canon)  
**Status:** Complete for Phase 4 kickoff (Packets 3A, 3A.1, 3A.2, 3B, and 3C merged via PR #2; only the deferred `SEC-007` milestone remains outside current delivery scope)  
**Completion Date:** Target TBD / Actual 2026-03-07 (`a5b0f6c` merge on `main`; docs follow-up `5ac15cd`)

| Req ID | Status | Notes |
|---|---|---|
| ENG-003 | ✅ Complete | Job/segment pipeline, deterministic segmentation, persisted output pointers, and processing tests merged to `main` |
| ENG-005 | ✅ Complete | Reference-first fidelity profile enforcement, persistence, and validation merged to `main` |
| ENG-006 | ✅ Complete | Deterministic reference metric calculation, sampling metadata, and threshold reporting merged to `main` |
| ENG-007 | ✅ Complete | Perceptual-equivalence + deterministic reproducibility proofs, rerun handling, and rollup reporting merged to `main` |
| ENG-008 | ✅ Complete | GPU warm-pool reconciliation, allocation latency tracking, autoscaling signals, and runtime ops hooks merged to `main` |
| ENG-009 | ✅ Complete | Redis-compatible per-user segment dedup cache with degraded mode, invalidation namespace, and cache reporting merged to `main` |
| ENG-010 | ✅ Complete | Manifest generation, persistence, retrieval API, and schema-backed payload contract merged to `main` |
| ENG-011 | ✅ Complete | `/v1/jobs` API, Pub/Sub-capable dispatch boundary, trusted worker ingress, progress contract, cancellation, and webhook delivery tests merged to `main` |
| ENG-012 | ✅ Complete | Retry/backoff, segment isolation, partial-results handling, and worker-contract coverage merged to `main` |
| NFR-002 | ✅ Complete | End-to-end SLO accounting, five-stage timing plus queue/allocation tracking, alert hooks, and runtime summaries merged to `main` |
| SEC-007 | ⏸️ Deferred | Canonically tracked as `GA+3 months` |
| OPS-003 | ✅ Complete | Incident persistence, severity mapping, alert routing hooks, and runbook references merged to `main` |

### Phase 4 Current Status: User-Facing Features & Application Logic

**Requirements:** 9 of 14 complete on `main`; 13 of 14 complete on the candidate branch  
**Status:** Packets 4A and 4B are merged to `main` as of 2026-03-13 (`fc81b2a`); `Packet 4C = FR-004 + DS-006 (processing launch, progress, uncertainty callouts, and accessible runtime errors)` merged to `main` on 2026-03-14 in `8e8798c`; `Packet 4D = FR-005 + ENG-015 (output delivery, deterministic export packaging, and export-flow accessibility slices)` merged to `main` on 2026-03-14 in `f0667c8`; `Packet 4E = ENG-013 + the launch-time slice of NFR-003 (cost estimation, single-job overage approval, and launch-time cost controls)` merged to `main` on 2026-03-14 in `3303c65`; `Packet 4F = ENG-014 (draft preview-session substrate, owner-scoped `/v1/previews` create/reread, deterministic keyframe selection, cache reuse, and expiry-aware rereads)` merged to `main` on 2026-03-15 in `aea4809`; `Packet 4G = DS-002 + DS-003 + DS-004 + DS-005 (Phase 4 accessibility closeout across upload, detection, configuration, launch, progress, and export)` is complete on the candidate branch `codex/packet4g-accessibility-closeout`, with automated evidence plus manual browser/screen-reader closeout recorded in `docs/specs/chronosrefine_phase4_closeout_note.md`  
**Completed Packets:** `Packet 4A = FR-001 (Video Upload and Validation)` on `main`; `Packet 4B = FR-003 + DS-001 (Fidelity Tier Selection + Configuration UX)` on `main`; `Packet 4C = FR-004 + DS-006 (Processing Launch, Progress, and Accessible Runtime Errors)` on `main`; `Packet 4D = FR-005 + ENG-015 (Output Delivery + Output Encoding)` on `main`; `Packet 4E = ENG-013 + launch-time NFR-003 cost controls` on `main`; `Packet 4F = ENG-014 (Preview Generation Substrate)` on `main`

| Area | Current Phase 4 note |
|---|---|
| Packet 4A scope on `main` | Signed GCS upload URL generation, resumable upload handling, format/size validation, authenticated metadata persistence, and a thin upload UI shell |
| Packet 4B scope on `main` | Upload-scoped era detection, persona/tier/grain configuration, launch-ready `job_payload_preview`, explicit hobbyist early-photo entitlement gating, and rendered `DS-001` verification |
| Packet 4C scope on `main` | Launch processing from saved Packet 4B configuration, poll job progress, cancel processing, expose uncertainty callouts via `GET /v1/jobs/{job_id}/uncertainty-callouts`, and surface DS-006-compliant launch/cancel/refresh error states |
| Packet 4D scope on `main` | Materialize deterministic AV1 + H.264 export packages at job finalization, expose owner-scoped `GET /v1/jobs/{job_id}/export` and `GET /v1/deletion-proofs/{proof_id}`, and extend the Packet 4C terminal UI with delivery/download actions plus export-path accessibility slices |
| Packet 4E scope on `main` | Adds `POST /v1/jobs/estimate`, persists per-job cost-estimate and reconciliation summaries, resolves launch-time pricing from configured Stripe metadata, and extends the existing launch CTA into a cost-review modal with single-job overage approval and accessible modal/error states |
| Packet 4F scope on `main` | Adds owner-scoped `POST /v1/previews` and `GET /v1/previews/{preview_id}`, persists draft preview sessions separate from `media_jobs`, reuses the latest saved Packet 4B configuration snapshot, emits deterministic scene-aware keyframes with uniform fallback, signs preview artifacts on reread, and keeps all Phase 5 preview-review UX out of scope |
| Packet 4G scope on candidate branch | Adds app-level skip navigation and `main` landmarking, Help-documented safe shortcuts for existing Phase 4 actions, shared focus/contrast primitives, screen-reader/error-association cleanup, and DS-002 through DS-005 rendered coverage across upload, detection, configuration, launch review, processing/progress, and export/delivery |
| Explicit Exclusions after Packet 4G | `FR-006` preview-review UX and preview-specific accessibility remain Phase 5 work; `NFR-003` remains in progress because Packet 4E only delivered the launch-time cost-control slice |
| Dependencies Satisfied | `SEC-013`, `ENG-002`, `ENG-016`; Phase 3 kickoff dependency is satisfied with `SEC-007` deferred per canon |
| Packet 4A test mapping | `tests/api/test_upload.py`, `tests/integration/test_resumable_upload.py`, `tests/load/test_upload_performance.py` |
| Packet 4B test mapping | `tests/api/test_fidelity_configuration.py`, `tests/processing/test_tier_parameters.py`, `tests/integration/test_configuration_job_handoff.py`, `tests/ui/test_tier_selection.spec.ts`, `tests/ui/test_fidelity_tier_selector.spec.ts`, `tests/ui/test_era_override_modal.spec.ts`, `tests/accessibility/test_fidelity_config_a11y.spec.ts` |
| Packet 4C test mapping | `tests/api/test_uncertainty_callouts.py`, `tests/integration/test_processing_launch_flow.py`, `tests/api/test_progress_updates.py`, `tests/api/test_async_processing.py`, `tests/integration/test_job_lifecycle.py`, `tests/ui/test_processing_flow.spec.ts`, `tests/accessibility/test_error_messages.spec.ts`, `tests/accessibility/test_error_announcements.spec.ts`, `tests/accessibility/test_uncertainty_callouts_a11y.spec.ts` |
| Packet 4D test mapping | `tests/api/test_output_delivery.py`, `tests/api/test_transformation_manifest.py`, `tests/api/test_deletion_proof.py`, `tests/integration/test_export_workflow.py`, `tests/processing/test_output_encoding.py`, `tests/processing/test_av1_encoding.py`, `tests/processing/test_metadata_preservation.py`, `tests/processing/test_encoding_performance.py`, `tests/ui/test_output_delivery.spec.ts`, `tests/accessibility/test_focus_management.spec.ts`, `tests/accessibility/test_keyboard_navigation.spec.ts`, `tests/accessibility/test_screen_reader_support.spec.ts`, `tests/accessibility/test_color_contrast.spec.ts` |
| Packet 4E test mapping | `tests/api/test_cost_estimation.py`, `tests/api/test_cost_breakdown.py`, `tests/integration/test_cost_reconciliation.py`, `tests/ops/test_cost_optimization.py`, `tests/billing/test_usage_alerts.py`, `tests/billing/test_overage_approval.py`, `tests/ui/test_cost_estimate_modal.spec.ts`, `tests/accessibility/test_cost_estimate_modal_a11y.spec.ts` |
| Packet 4G test mapping | `tests/accessibility/test_keyboard_navigation.spec.ts`, `tests/accessibility/test_keyboard_shortcuts.spec.ts`, `tests/accessibility/test_screen_reader_support.spec.ts`, `tests/accessibility/test_aria_labels.spec.ts`, `tests/accessibility/test_aria_live_regions.spec.ts`, `tests/accessibility/test_color_contrast.spec.ts`, `tests/accessibility/test_button_contrast.spec.ts`, `tests/accessibility/test_focus_contrast.spec.ts`, `tests/accessibility/test_focus_management.spec.ts`, `tests/accessibility/test_modal_focus.spec.ts`, `tests/accessibility/test_form_focus.spec.ts`, `./node_modules/.bin/pnpm -C web test` |
| Packet 4A closure evidence | Live memory + GCS smoke passed, live Supabase + GCS smoke passed, staging latency probe passed on revision `chronos-phase1-app-00036-blf` (`build_sha=9a5791c4023794af8d6cc96d7dd2561aafdb93bc`) |
| Packet 4B merge evidence | Shared fidelity resolver accepts all grain presets across all tiers, hobbyist early-photo saves return `403 Plan Upgrade Required` with no persistence, rendered `DS-001` jsdom tests pass, and `job_payload_preview` is accepted by `/v1/jobs` in integration coverage; merged to `main` in `fc81b2a568fb7059989963bedeb7a22df8e63008` |
| Packet 4C merge evidence | `GET /v1/jobs/{job_id}/uncertainty-callouts` derives global low-confidence/manual-confirmation warnings plus deterministic segment callouts, Packet 4B `job_payload_preview` launches unchanged through `/v1/jobs`, and rendered DS-006 tests cover launch failures, cancel failures, non-blocking refresh failures, and terminal callout summaries; merged to `main` in `8e8798c394c36faf3e34e65b1c373f851e486f52` |
| Packet 4D merge evidence | Completed and partial jobs materialize deterministic AV1 + H.264 export packages with manifest, uncertainty-callout, quality-report, and deletion-proof artifacts; owner-scoped export/proof APIs are covered by automated tests, Packet 4D terminal delivery actions plus export-path accessibility tests pass, and the packet merged to `main` in `f0667c8ab052324fdecd25292e6912933cf871a2` |
| Packet 4E merge evidence | Launch review now runs through `POST /v1/jobs/estimate`, pricing metadata is resolved from configured Stripe price IDs with a short-lived cache, `POST /v1/jobs` persists `cost_estimate_summary` and terminal reconciliation data, launch-time overage approval remains single-job only, and rendered Packet 4E modal tests cover retry, approval, and focus/live-region behavior; merged to `main` in `3303c6584005e374e2d21ce8f028338ec3950177` |
| Packet 4F merge evidence | `POST /v1/previews` consumes the latest saved Packet 4B `job_payload_preview` by `upload_id`, draft preview sessions are persisted separately from `media_jobs`, rereads stay owner-scoped through `preview_id`, deterministic scene-aware selection emits 10 keyframes with 320x180 thumbnails plus uniform fallback coverage, and preview performance/cache/expiry paths are covered by automated tests; merged to `main` in `aea4809b7cbb111e4273ece0a4fb566e96c63e7b` |
| Packet 4G candidate evidence | Skip-link/main-landmark shell updates, Help-documented safe shortcuts for upload/save/launch/export actions, shared focus and contrast primitives, and rendered DS-002 through DS-005 suites pass on `codex/packet4g-accessibility-closeout`; `docs/specs/chronosrefine_phase4_closeout_note.md` records the automated evidence plus the completed Chrome, Firefox, Safari/WebKit, keyboard-only, and screen-reader matrix |
| Context Note | `docs/specs/chronosrefine_phase4_closeout_note.md` records Packet 4A evidence on `main` plus Packet 4G candidate-branch completion evidence; Packet 4H is next after Packet 4G |

## Progress Tracking Template

Use this template for future phase updates:

```markdown
## Phase X Progress: [Phase Name]

**Requirements:** X of Y complete (Z%)
**Status:** [Not Started | In Progress | Complete]
**Completion Date:** [Target] / [Actual]

| Req ID | Status | Assignee | Notes |
|---|---|---|---|
| REQ-XXX | ✅ Complete | Engineer Name | Merged PR #123 |
| REQ-YYY | 🔄 In Progress | Engineer Name | Blocked by dependency |
| REQ-ZZZ | ⏸️ Blocked | Engineer Name | Waiting for API keys |
```

---

## Related Documents

- **Implementation Plan**: `docs/specs/chronosrefine_implementation_plan.md`
- **Functional Requirements**: `docs/specs/chronosrefine_functional_requirements.md`
- **Engineering Requirements**: `docs/specs/chronosrefine_engineering_requirements.md`
- **Security & Operations Requirements**: `docs/specs/chronosrefine_security_operations_requirements.md`
- **Nonfunctional Requirements**: `docs/specs/chronosrefine_nonfunctional_requirements.md`
- **Design Requirements**: `docs/specs/chronosrefine_design_requirements.md`
- **Repository Note**: Historical companion-doc names from earlier planning are not present on `main`. Use the canonical documents above plus `docs/api/openapi.yaml` for the checked-in API contract.

---

**End of Coverage Matrix**
