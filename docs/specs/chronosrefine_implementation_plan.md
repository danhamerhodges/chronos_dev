# ChronosRefine Implementation Plan

**Version:** 10.4  
**Last Updated:** March 2026  
**Status:** Handoff-Ready  
**Audience:** Development Team, Product Manager, Engineering Manager

**Change Note (v10.4 - March 2026):** Reconciled merged-state Phase 2/3 status notes, corrected Phase 4 scope drift, removed stale companion-doc references from Phase 4 gating, and approved Packet 4A as `FR-001`.

---

## 10. Implementation Plan

This implementation plan is organized into a logical execution sequence designed to build foundational components first, mitigate risks early, and deliver incremental value at each phase. This approach provides the development team with a clear roadmap for building ChronosRefine with minimal risk and an optimal chance of success.

**Status Note:** The per-phase checklists below remain gate artifacts. Current merged-state progress and kickoff readiness are tracked in `docs/specs/ChronosRefine Requirements Coverage Matrix.md`.
**Repo Note:** Test-file references for future phases are target mappings and may not yet exist on `main` until the corresponding packet is implemented.

### Phase 1: Foundation & Core Infrastructure

**Objective:** Establish the development environment, CI/CD pipeline, core infrastructure, database, authentication, design system, and payment integration.

**Requirements Implemented:** **ENG-016**, **SEC-013**, **DS-007**, **NFR-012**, **OPS-001**, **OPS-002** (6 requirements)  
**Coverage Matrix:** See `docs/specs/ChronosRefine Requirements Coverage Matrix.md`

**Entry Criteria:**
- [ ] Project charter approved and budget allocated
- [ ] Development team assembled and onboarded
- [ ] GCP project created with billing enabled → **See:** `docs/specs/chronosrefine_prd_v9.md#infrastructure-requirements`
- [ ] Git repository provisioned
- [ ] Supabase account created → **Req:** **ENG-016**, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-016-database-technology-selection-supabase`
- [ ] Stripe account created → **Req:** **NFR-012**, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-012-payment-provider-selection`

**Deliverables:**
-   Initialized project structure in a Git repository → **Test:** `tests/infrastructure/test_project_structure.py`
-   Automated CI/CD pipeline for testing and deployment → **Req:** **OPS-001**, **Test:** `tests/ops/test_ci_cd_pipeline.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#ops-001-monitoring--alerting`
-   Configured logging, monitoring, and alerting → **Req:** **OPS-001**, **OPS-002**, **Test:** `tests/ops/test_monitoring.py`, `tests/ops/test_logging.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#ops-001-monitoring--alerting`, `docs/specs/chronosrefine_security_operations_requirements.md#ops-002-slo-monitoring`
-   Secure GCP project setup with IAM policies defined in Terraform
-   Supabase database and authentication configured → **Req:** **ENG-016**, **SEC-013**, **Test:** `tests/database/test_supabase_connection.py`, `tests/auth/test_supabase_auth.py`, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-016-database-technology-selection-supabase`, `docs/specs/chronosrefine_security_operations_requirements.md#sec-013-authentication-provider-selection-supabase`
-   Design system implemented with component library → **Req:** **DS-007**, **Test:** `tests/design_system/test_tokens.spec.ts`, **See:** `docs/specs/chronosrefine_design_requirements.md#ds-007-design-system-implementation`
-   Stripe payment integration configured → **Req:** **NFR-012**, **Test:** `tests/billing/test_stripe_integration.py`, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-012-payment-provider-selection`

**Exit Criteria:**
- [ ] Git repository contains project scaffold with README and contributing guidelines
- [ ] CI/CD pipeline successfully deploys to staging environment on merge to main → **Req:** **OPS-001**, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#ops-001-monitoring--alerting`
- [ ] All tests pass in CI pipeline (minimum: linting, unit tests)
- [ ] Cloud Monitoring dashboards created for key infrastructure metrics → **Req:** **OPS-001**, **Test:** `tests/ops/test_monitoring.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#ops-001-monitoring--alerting`
- [ ] IAM policies applied via Terraform with no manual console changes
- [ ] Security scan passes with zero critical vulnerabilities
- [ ] Team can deploy a "Hello World" service end-to-end in < 10 minutes
- [ ] Supabase database schema applied with migration scripts → **Req:** **ENG-016**, **Test:** `tests/database/test_schema_migrations.py`, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-016-database-technology-selection-supabase`
- [ ] Supabase Auth configured with email/password and OAuth → **Req:** **SEC-013**, **Test:** `tests/auth/test_email_password_auth.py`, `tests/auth/test_oauth_integration.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-013-authentication-provider-selection-supabase`
- [ ] Design system tokens and component library implemented → **Req:** **DS-007**, **Test:** `tests/design_system/test_component_library.spec.ts`, **See:** `docs/specs/chronosrefine_design_requirements.md#ds-007-design-system-implementation`
- [ ] Stripe subscription plans created (Pro: $29/month, Museum: $500/month) → **Req:** **NFR-012**, **Test:** `tests/billing/test_subscription_lifecycle.py`, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-012-payment-provider-selection`
- [ ] Stripe webhook integration tested → **Req:** **NFR-012**, **Test:** `tests/billing/test_stripe_webhooks.py`, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-012-payment-provider-selection`

**Phase-Specific Risks:**
- **Risk**: Team unfamiliarity with GCP infrastructure
  - **Mitigation**: Conduct GCP training workshop; pair programming for Terraform development
- **Risk**: CI/CD pipeline complexity delays feature work
  - **Mitigation**: Start with minimal pipeline; iterate based on team feedback

**Rationale:** A solid foundation is critical before any feature development can begin. Automating the development and deployment workflow early will ensure consistency and quality throughout the project.

### Phase 2: API Foundation & Data Layer

**Objective:** Implement API foundations, schema validation, era detection, and core data-layer controls.

**Requirements Implemented:** **ENG-001**, **ENG-002**, **ENG-004**, **FR-002**, **SEC-009**, **NFR-007** (6 requirements)  
**Coverage Matrix:** See `docs/specs/ChronosRefine Requirements Coverage Matrix.md`

**Implementation Note:** The merged Phase 2 delivery closes an approved `ENG-002` API subset for the backend closeout packet. The canonical `ENG-002` endpoint catalog in Engineering Requirements remains broader and should not be redefined by this status snapshot.

**Entry Criteria:**
- [ ] Phase 1 complete: Infrastructure operational → **See:** `docs/specs/chronosrefine_implementation_plan.md#phase-1-foundation--core-infrastructure`
- [ ] Database technology selected (Supabase PostgreSQL) → **Req:** **ENG-016** (completed in Phase 1), **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-016-database-technology-selection-supabase`
- [ ] JSON Schema v2020-12 specification finalized → **Req:** **ENG-001**, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-001-json-schema-validation`

**Deliverables:**
-   Finalized JSON Schema for Era Profiles → **Req:** **ENG-001**, **Test:** `tests/api/test_schema_validation.py`, **See:** `docs/specs/chronosrefine_prd_v9.md#era-profile-schema`
-   Phase 2 API foundation subset (`/v1/detect-era`, `/v1/eras`, `/v1/users/me`, `/v1/users/me/usage`, `/v1/users/me/approve-overage`, `/v1/orgs/{org_id}/settings/logs`, `/v1/user/delete_logs`, `/v1/health`, `/v1/version`) → **Req:** **ENG-002**, **Test:** `tests/api/test_endpoints.py`, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-002-api-endpoint-implementation`
-   Era-detection model service, persistence, and fallback contract → **Req:** **ENG-004**, **FR-002**, **Test:** `tests/ml/test_era_detection_service.py`, `tests/ml/test_gemini_integration.py`, `tests/api/test_era_detection.py`, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-004-era-detection-model`, `docs/specs/chronosrefine_functional_requirements.md#fr-002-era-detection`
-   Validation logic that enforces all schema rules → **Req:** **ENG-001**, **Test:** `tests/api/test_schema_validation.py`, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-001-json-schema-validation`
-   PII redaction, log retention, and GDPR log-deletion flows configured → **Req:** **SEC-009**, **Test:** `tests/security/test_log_retention.py`, `tests/security/test_pii_redaction.py`, `tests/compliance/test_gdpr_log_deletion.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-009-log-retention--pii-redaction`

**Exit Criteria:**
- [ ] JSON Schema validates all 6 era profiles with 100% pass rate → **Req:** **ENG-001**, **Test:** `tests/api/test_schema_validation.py`, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-001-json-schema-validation`
- [ ] Phase 2 API subset documented in OpenAPI and covered by contract tests → **Req:** **ENG-002**, **Test:** `tests/api/test_endpoints.py`, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-002-api-endpoint-implementation`
- [ ] Era-detection model fallback and manual-confirmation contract validated → **Req:** **ENG-004**, **FR-002**, **Test:** `tests/ml/test_era_detection_service.py`, `tests/api/test_era_detection.py`, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-004-era-detection-model`, `docs/specs/chronosrefine_functional_requirements.md#fr-002-era-detection`
- [ ] Schema validation correctly rejects invalid profiles (tested with 50+ negative test cases) → **Req:** **ENG-001**, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-001-json-schema-validation`
- [ ] All three validation rules (A, B, C) enforced programmatically → **Req:** **ENG-001**, **See:** `docs/specs/chronosrefine_prd_v9.md#validation-rules`
- [ ] Performance: Schema validation completes in <100ms for 95th percentile → **Req:** **ENG-001**, **Test:** `tests/load/test_schema_validation_performance.py`, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-001-json-schema-validation`
- [ ] PII redaction and log retention tested with Phase 2 API/config surfaces → **Req:** **SEC-009**, **Test:** `tests/security/test_log_retention.py`, `tests/security/test_pii_redaction.py`, `tests/compliance/test_gdpr_log_deletion.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-009-log-retention--pii-redaction`
- [ ] Cost-control hard-stop, overage approval, and usage alerts validated against Stripe-configured pricing → **Req:** **NFR-007**, **Test:** `tests/billing/test_cost_control.py`, `tests/billing/test_overage_approval.py`, `tests/billing/test_usage_alerts.py`, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-007-cost-control-requirements`

**Phase-Specific Risks:**
- **Risk**: Schema changes during development require migration complexity
  - **Mitigation**: Use database migration tool (Alembic/Flyway); version all schema changes
- **Risk**: Validation logic becomes bottleneck
  - **Mitigation**: Cache validated schemas; benchmark validation performance early

**Rationale:** The data layer is a core dependency for all subsequent features. A well-defined schema and data access layer will prevent data-related bugs and simplify future development.

### Phase 3: Core Processing Pipeline & AI Integration

**Objective:** Build the canonical Phase 3 processing substrate, quality controls, and scaling/runtime systems without reclassifying already-delivered Phase 2 era-detection work.

**Requirements Implemented:** **ENG-003**, **ENG-005**, **ENG-006**, **ENG-007**, **ENG-008**, **ENG-009**, **ENG-010**, **ENG-011**, **ENG-012**, **NFR-002**, **SEC-007**, **OPS-003** (12 requirements)  
**Coverage Matrix:** See `docs/specs/ChronosRefine Requirements Coverage Matrix.md`

**Implementation Status Note:** Packets 3A, 3A.1, 3A.2, 3B, and 3C are merged to `main` via PR #2 (`a5b0f6c`). The docs-only follow-up on `main` is `5ac15cd`. Current staging/runtime evidence remains context-only and is tracked in `docs/specs/chronosrefine_phase3_closeout_note.md`. **SEC-007** remains a deferred Museum-tier milestone tracked for `GA+3 months`.

**Entry Criteria:**
- [ ] Phase 2 merged to `main` and progress docs reconciled → **See:** `docs/specs/ChronosRefine Requirements Coverage Matrix.md#phase-2-progress-api-foundation--data-layer`
- [ ] Persistence boundary hardened for user-request paths (end-user JWT + RLS by default; privileged access explicit) → **Req:** **ENG-002**, **SEC-001**, **SEC-013**, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-002-api-endpoint-implementation`, `docs/specs/chronosrefine_security_operations_requirements.md#sec-001-authentication--authorization`
- [x] Runtime prerequisites identified for processing execution (GCS, Redis/degraded-cache path, worker runtime, GPU capacity planning) → **Req:** **ENG-003**, **ENG-008**, **ENG-009**, **OPS-003**
- [ ] Processing/infrastructure test scaffolding created for new Phase 3 suites → **See:** `docs/specs/chronosrefine_test_templates.md`

**Deliverables:**
-   Core job and segment processing pipeline with explicit job state transitions → **Req:** **ENG-003**
-   Dispatcher + worker execution boundary aligned to canonical Pub/Sub / Cloud Run Jobs topology, with explicit trusted-background mutation and publish paths → **Req:** **ENG-011**, **ENG-012**
-   Fidelity-tier execution parameters persisted and enforced throughout processing → **Req:** **ENG-005**
-   Quality metrics implementation for `E_HF`, `S_LS`, and `T_TC` with threshold handling → **Req:** **ENG-006**
-   Reproducibility proof modes and audit evidence generation → **Req:** **ENG-007**
-   GPU pool management, autoscaling hooks, and incident-ready operational controls → **Req:** **ENG-008**, **OPS-003**
-   Deduplication cache with degraded-mode behavior when cache infrastructure is unavailable → **Req:** **ENG-009**
-   Transformation manifest generation, storage, and retrieval contract → **Req:** **ENG-010**
-   Async processing substrate with progress delivery, retry behavior, and failure isolation → **Req:** **ENG-011**, **ENG-012**
-   End-to-end processing time instrumentation, alerting, and SLO reporting → **Req:** **NFR-002**
-   Deferred CMEK milestone tracked explicitly for Museum tier rollout timing → **Req:** **SEC-007** (`GA+3 months`)

**Exit Criteria:**
- [ ] Processing jobs execute through a canonical job/segment pipeline with persistent status and recovery checkpoints → **Req:** **ENG-003**, **ENG-011**, **ENG-012**
- [ ] Dispatcher and worker entrypoint contracts are explicit, testable in unit-only mode, and preserve the user-request JWT boundary while keeping background writes/publish actions privileged → **Req:** **ENG-011**, **ENG-012**, **SEC-013**
- [ ] Fidelity tier parameters and quality thresholds are enforced using the canonical metric definitions in Engineering + Functional Requirements → **Req:** **ENG-005**, **ENG-006**
- [ ] Reproducibility proof artifacts are captured alongside manifest data and remain traceable for audits → **Req:** **ENG-007**, **ENG-010**
- [x] GPU pool readiness, autoscaling behavior, and incident hooks are validated in local/runtime test coverage, with env-gated live validation path retained for deployed environments → **Req:** **ENG-008**, **OPS-003**
- [x] Deduplication cache behavior is validated for hit, miss, invalidation, and degraded-mode scenarios → **Req:** **ENG-009**
- [x] End-to-end processing time is measured against the canonical `p95 <2x video duration` SLO with alerting hooks in place → **Req:** **NFR-002**
- [ ] `SEC-007` is tracked as a deferred Museum-tier milestone and is not used as an unconditional Phase 3 completion blocker before `GA+3 months` → **Req:** **SEC-007**

**Phase-Specific Risks:**
- **Risk**: Phase 3 execution drifts back toward already-delivered Phase 2 era-detection work
  - **Mitigation**: Keep packet scope anchored to the canonical Phase 3 requirement IDs and titles
- **Risk**: Async orchestration, cache, and GPU concerns are introduced without a clear trust boundary
  - **Mitigation**: Require explicit privileged-access decisions and keep JWT/RLS as the default for user-request paths
- **Risk**: Test-mode dispatch helpers are mistaken for production runtime infrastructure
  - **Mitigation**: Keep the dispatcher interface explicit, document the cloud binding as a follow-on, and restrict trusted worker execution behind an explicit background token
- **Risk**: `SEC-007` is treated as an immediate blocker despite its canonical rollout timing
  - **Mitigation**: Track CMEK as a deferred milestone criterion aligned to `GA+3 months`

**Rationale:** This phase should be repacketed from canonical requirement semantics, not from older narrative bullets. The goal is to land the missing processing substrate and operational controls that Phase 2 did not implement.

### Phase 4: User-Facing Features & Application Logic

**Objective:** Build the user-facing upload, configuration, launch, delivery, accessibility, preview-substrate, and cost-optimization features on top of the authenticated Phase 2/3 backend. Authentication/provider selection itself remains completed Phase 1 scope.

**Requirements Implemented:** **FR-001**, **FR-003**, **FR-004**, **FR-005**, **ENG-013**, **ENG-014**, **ENG-015**, **DS-001**, **DS-002**, **DS-003**, **DS-004**, **DS-005**, **DS-006**, **NFR-003** (14 requirements)  
**Coverage Matrix:** See `docs/specs/ChronosRefine Requirements Coverage Matrix.md`

**Current Status Note:** Packets 4A (`FR-001`) and 4B (`FR-003` + `DS-001`) are merged on `main`, with Packet 4B landing in merge commit `fc81b2a568fb7059989963bedeb7a22df8e63008`. Packet 4C remains the next feature packet on `main`. Follow-on packets must still follow the canonical Phase 4 requirement IDs above and the higher-priority requirement specs, not older PRD-style Phase 4 prose. `FR-006` remains a Phase 5 functional requirement; Phase 4 includes only `ENG-014` as the technical preview-generation substrate.

**Entry Criteria:**
- [x] Phase 3 is complete for kickoff on `main`; `SEC-007` remains deferred per canon and does not block Phase 4 kickoff → **See:** `docs/specs/chronosrefine_implementation_plan.md#phase-3-core-processing-pipeline--ai-integration`
- [x] Design system baseline is already in place from Phase 1 → **Req:** **DS-007**, **See:** `docs/specs/chronosrefine_design_requirements.md#ds-007-design-system-implementation`
- [x] Authentication/provider selection is already completed in Phase 1 and is a dependency, not new Phase 4 scope → **Req:** **SEC-013**, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-013-authentication-provider-selection-supabase`

**Deliverables:**
-   Authenticated upload + validation API and UI surfaces, including signed GCS URL generation, resumable upload handling, format/size validation, and metadata persistence → **Req:** **FR-001**, **Test:** `tests/api/test_upload.py`, `tests/integration/test_resumable_upload.py`, `tests/load/test_upload_performance.py`, **See:** `docs/specs/chronosrefine_functional_requirements.md#fr-001-video-upload-and-validation`
-   Fidelity selection and configuration UX using existing Phase 1 design-system primitives → **Req:** **FR-003**, **DS-001**, **Test:** `tests/api/test_fidelity_configuration.py`, `tests/processing/test_tier_parameters.py`, `tests/ui/test_tier_selection.spec.ts`, `tests/ui/test_fidelity_tier_selector.spec.ts`, **See:** `docs/specs/chronosrefine_functional_requirements.md#fr-003-fidelity-tier-selection`, `docs/specs/chronosrefine_design_requirements.md#ds-001-fidelity-configuration-ux`
-   Job launch, progress, and restoration-control flows that extend the Phase 3 job substrate rather than replacing it → **Req:** **FR-004**, **Test:** `tests/processing/test_restoration_pipeline.py`, `tests/processing/test_uncertainty_callouts.py`, `tests/processing/test_retry_logic.py`, **See:** `docs/specs/chronosrefine_functional_requirements.md#fr-004-processing-and-restoration`
-   Output delivery surfaces for encoded artifacts, manifest access, deletion-proof availability, and download-expiry handling → **Req:** **FR-005**, **ENG-015**, **Test:** `tests/api/test_output_delivery.py`, `tests/api/test_transformation_manifest.py`, `tests/api/test_deletion_proof.py`, `tests/integration/test_export_workflow.py`, `tests/processing/test_output_encoding.py`, **See:** `docs/specs/chronosrefine_functional_requirements.md#fr-005-output-delivery`, `docs/specs/chronosrefine_engineering_requirements.md#eng-015-output-encoding`
-   Cost estimation and cost-optimization signals exposed at launch decision points without hardcoded pricing → **Req:** **ENG-013**, **NFR-003**, **Test:** `tests/api/test_cost_estimation.py`, `tests/api/test_cost_breakdown.py`, `tests/integration/test_cost_reconciliation.py`, `tests/ops/test_cost_optimization.py`, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-013-cost-estimation`, `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-003-cost-optimization`
-   Preview artifact generation backend for downstream Phase 5 `FR-006` review flows → **Req:** **ENG-014**, **Test:** `tests/processing/test_preview_generation.py`, `tests/processing/test_scene_detection.py`, `tests/load/test_preview_performance.py`, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-014-preview-generation`
-   Accessibility implementation across `DS-002` through `DS-006` for upload, configuration, progress, and export flows → **Req:** **DS-002**, **DS-003**, **DS-004**, **DS-005**, **DS-006**, **Test:** `tests/accessibility/test_keyboard_navigation.spec.ts`, `tests/accessibility/test_screen_reader_support.spec.ts`, `tests/accessibility/test_color_contrast.spec.ts`, `tests/accessibility/test_focus_management.spec.ts`, `tests/accessibility/test_error_messages.spec.ts`, **See:** `docs/specs/chronosrefine_design_requirements.md#ds-002-keyboard-navigation`, `docs/specs/chronosrefine_design_requirements.md#ds-003-screen-reader-support`, `docs/specs/chronosrefine_design_requirements.md#ds-004-color-contrast`, `docs/specs/chronosrefine_design_requirements.md#ds-005-focus-indicators`, `docs/specs/chronosrefine_design_requirements.md#ds-006-error-messages-accessibility`

**Exit Criteria:**
- [ ] Upload endpoints are documented in OpenAPI and covered by canonical upload tests → **Req:** **FR-001**, **ENG-002**, **Test:** `tests/api/test_upload.py`, `tests/integration/test_resumable_upload.py`, **See:** `docs/specs/chronosrefine_functional_requirements.md#fr-001-video-upload-and-validation`, `docs/specs/chronosrefine_engineering_requirements.md#eng-002-api-endpoint-implementation`, `docs/api/openapi.yaml`
- [ ] Resumable uploads are validated for files >10GB with simulated network interruptions → **Req:** **FR-001**, **Test:** `tests/integration/test_resumable_upload.py`, **See:** `docs/specs/chronosrefine_functional_requirements.md#fr-001-video-upload-and-validation`
- [x] Fidelity tier selection and era-override UX persist canonical configuration and meet `DS-001` requirements on `main` → **Req:** **FR-003**, **DS-001**, **Test:** `tests/api/test_fidelity_configuration.py`, `tests/processing/test_tier_parameters.py`, `tests/integration/test_configuration_job_handoff.py`, `tests/ui/test_tier_selection.spec.ts`, `tests/ui/test_fidelity_tier_selector.spec.ts`, `tests/ui/test_era_override_modal.spec.ts`, `tests/accessibility/test_fidelity_config_a11y.spec.ts`, **See:** `docs/specs/chronosrefine_functional_requirements.md#fr-003-fidelity-tier-selection`, `docs/specs/chronosrefine_design_requirements.md#ds-001-fidelity-configuration-ux`
- [ ] Job launch, progress, and results flows operate on top of the Phase 3 job APIs with authenticated access and accessible error states → **Req:** **FR-004**, **DS-006**, **Test:** `tests/processing/test_restoration_pipeline.py`, `tests/processing/test_uncertainty_callouts.py`, `tests/accessibility/test_error_messages.spec.ts`, **See:** `docs/specs/chronosrefine_functional_requirements.md#fr-004-processing-and-restoration`, `docs/specs/chronosrefine_design_requirements.md#ds-006-error-messages-accessibility`
- [ ] Output delivery surfaces expose encoded artifacts, manifest retrieval, deletion-proof availability, and link-expiry handling → **Req:** **FR-005**, **ENG-015**, **Test:** `tests/api/test_output_delivery.py`, `tests/api/test_transformation_manifest.py`, `tests/api/test_deletion_proof.py`, `tests/integration/test_export_workflow.py`, `tests/processing/test_output_encoding.py`, **See:** `docs/specs/chronosrefine_functional_requirements.md#fr-005-output-delivery`, `docs/specs/chronosrefine_engineering_requirements.md#eng-015-output-encoding`
- [ ] Preview artifact generation backend meets `ENG-014` latency and storage expectations for downstream Phase 5 `FR-006` UI work → **Req:** **ENG-014**, **Test:** `tests/processing/test_preview_generation.py`, `tests/processing/test_scene_detection.py`, `tests/load/test_preview_performance.py`, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-014-preview-generation`
- [ ] Accessibility audit passes WCAG 2.1 AA for `DS-002` through `DS-006` → **Req:** **DS-002**, **DS-003**, **DS-004**, **DS-005**, **DS-006**, **Test:** `tests/accessibility/test_keyboard_navigation.spec.ts`, `tests/accessibility/test_screen_reader_support.spec.ts`, `tests/accessibility/test_color_contrast.spec.ts`, `tests/accessibility/test_focus_management.spec.ts`, `tests/accessibility/test_error_messages.spec.ts`, **See:** `docs/specs/chronosrefine_design_requirements.md#ds-002-keyboard-navigation`, `docs/specs/chronosrefine_design_requirements.md#ds-003-screen-reader-support`, `docs/specs/chronosrefine_design_requirements.md#ds-004-color-contrast`, `docs/specs/chronosrefine_design_requirements.md#ds-005-focus-indicators`, `docs/specs/chronosrefine_design_requirements.md#ds-006-error-messages-accessibility`
- [ ] Cost-estimate accuracy and Phase 4 cost-optimization guardrails align with `ENG-013` + `NFR-003` with no hardcoded pricing or entitlements → **Req:** **ENG-013**, **NFR-003**, **Test:** `tests/api/test_cost_estimation.py`, `tests/api/test_cost_breakdown.py`, `tests/integration/test_cost_reconciliation.py`, `tests/ops/test_cost_optimization.py`, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-013-cost-estimation`, `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-003-cost-optimization`
- [ ] Cross-browser coverage is complete for upload, configuration, launch, and export flows → **Req:** **DS-001**, **DS-002**, **DS-003**, **DS-004**, **DS-005**, **DS-006**, **See:** `docs/specs/chronosrefine_design_requirements.md#ds-001-fidelity-configuration-ux`

**Approved Kickoff Packet: Packet 4A (2026-03-07; closed 2026-03-08)**

**Requirement Focus:** `FR-001`

**Reason for kickoff choice:** `FR-001` is the smallest dependency-unlocking Phase 4 packet. `SEC-013`, `ENG-002`, and `ENG-016` are already satisfied, and the packet extends the existing Phase 2/3 substrate without reopening auth, persistence, or runtime-ops design decisions.

**In Scope:**
- Signed GCS upload URL generation and authenticated upload-session creation
- Resumable upload handling, checksum/format/size validation, and persisted upload metadata
- Thin upload UI shell using existing `DS-007` primitives
- OpenAPI/API contract updates for upload initiation and validation responses

**Out of Scope:**
- Fidelity selection (`FR-003`, `DS-001`)
- Job launch/progress UX (`FR-004`)
- Output delivery (`FR-005`, `ENG-015`)
- Phase 5 preview-review UX (`FR-006`)
- Phase 4 follow-on work (`ENG-013`, `ENG-014`, `NFR-003`) except where non-functional guardrails already constrain upload design

**Dependencies Confirmed:**
- `SEC-013`, `ENG-002`, and `ENG-016` are already delivered
- Phase 3 kickoff dependency is satisfied; `SEC-007` remains deferred per canon and does not block Packet 4A

**Likely Extension Surfaces:**
- `app/api`
- `app/db`
- `app/services`
- `supabase/migrations`
- `docs/api/openapi.yaml`
- `web/src`

**Mapped Tests:**
- `tests/api/test_upload.py`
- `tests/integration/test_resumable_upload.py`
- `tests/load/test_upload_performance.py`

**Packet 4A Closure Evidence:**
- [x] Upload API contract and OpenAPI coverage landed for `POST /v1/upload`, `POST /v1/upload/{upload_id}/resume`, and `PATCH /v1/upload/{upload_id}` → **Req:** **FR-001**, **ENG-002**, **See:** `docs/api/openapi.yaml`
- [x] Deterministic upload tests and traceability validation passed and are now reflected on `main` → **Req:** **FR-001**, **See:** `tests/api/test_upload.py`, `tests/integration/test_resumable_upload.py`, `tests/load/test_upload_performance.py`, `python3 scripts/validate_test_traceability.py`
- [x] Live memory-backed resumable smoke passed with same-`upload_id`, same-`object_path`, persisted `pending -> uploading -> completed`, and denied secondary access → **Req:** **FR-001**, **See:** `docs/specs/chronosrefine_phase4_closeout_note.md`
- [x] Live Supabase-backed resumable smoke passed with the same persisted-state and owner-boundary evidence → **Req:** **FR-001**, **SEC-013**, **See:** `docs/specs/chronosrefine_phase4_closeout_note.md`
- [x] Staging revision `chronos-phase1-app-00036-blf` (`build_sha=9a5791c4023794af8d6cc96d7dd2561aafdb93bc`) served upload-session creation successfully and produced recorded latency evidence (`p50=0.7823s`, `p95=9.6927s`, `p99=9.6927s`) → **Req:** **FR-001**, **See:** `docs/specs/chronosrefine_phase4_closeout_note.md`

**Latest Completed Packet: Packet 4B (merged on `main` 2026-03-13 via `fc81b2a`)**

**Requirement Focus:** `FR-003`, `DS-001`

**Reason for packet choice:** `FR-003` unlocks `FR-004`, and `DS-001` is its direct user-facing pair. The packet extends Packet 4A's upload session into a launch-ready configuration flow without changing `/v1/jobs` semantics ahead of Packet 4C.

**In Scope:**
- Upload-scoped era detection without `media_jobs` side effects
- Persona, fidelity-tier, and grain-preset configuration persisted on `upload_sessions`
- Explicit hobbyist early-photography entitlement gating with `403 Plan Upgrade Required`
- Launch-ready `job_payload_preview` generation that is accepted by the existing `/v1/jobs` path
- Rendered `DS-001` verification for the tier selector, era override modal, confirmation flow, and upgrade-required error path

**Out of Scope:**
- `/v1/jobs` launch/progress UX (`FR-004`)
- Output delivery (`FR-005`, `ENG-015`)
- Phase 4 cost-estimation/productized cost controls (`ENG-013`, `NFR-003`)
- Preview-generation follow-on work (`ENG-014`) and Phase 5 `FR-006` review UX

**Dependencies Confirmed:**
- `FR-002` and `ENG-001` are already complete on `main`
- Packet 4A upload/session substrate is already merged on `main`
- Phase 3 processing/job substrate remains the downstream handoff target for Packet 4C

**Mapped Tests:**
- `tests/api/test_fidelity_configuration.py`
- `tests/processing/test_tier_parameters.py`
- `tests/integration/test_configuration_job_handoff.py`
- `tests/ui/test_tier_selection.spec.ts`
- `tests/ui/test_fidelity_tier_selector.spec.ts`
- `tests/ui/test_era_override_modal.spec.ts`
- `tests/accessibility/test_fidelity_config_a11y.spec.ts`

**Packet 4B Merge Evidence:**
- [x] Shared fidelity resolver accepts all three grain presets across all three tiers while preserving canonical tier defaults → **Req:** **FR-003**, **ENG-005**, **See:** `tests/processing/test_tier_parameters.py`, `tests/processing/test_fidelity_tiers.py`
- [x] Hobbyist `daguerreotype` / `albumen` configuration saves return `403 Plan Upgrade Required` and do not persist `launch_config`, `configured_at`, or user-preference updates → **Req:** **FR-003**, **See:** `tests/api/test_fidelity_configuration.py`
- [x] Returned `job_payload_preview` is accepted by the existing `/v1/jobs` path in integration coverage → **Req:** **FR-003** (Packet 4C `/v1/jobs` handoff), **See:** `tests/integration/test_configuration_job_handoff.py`
- [x] Rendered `DS-001` jsdom tests pass for tier selection, era override, confirmation flow, and the upgrade-required error path → **Req:** **DS-001**, **See:** `tests/ui/test_tier_selection.spec.ts`, `tests/ui/test_fidelity_tier_selector.spec.ts`, `tests/ui/test_era_override_modal.spec.ts`, `tests/accessibility/test_fidelity_config_a11y.spec.ts`

**Guardrails to Preserve:**
- End-user JWT / RLS-safe request path by default
- No service-role use in user-request paths without equivalent enforcement
- Existing degraded-mode/runtime-ops behavior remains intact
- Live/integration validation stays env-gated; unit-only mode remains secret-independent

**Phase-Specific Risks:**
- **Risk**: Phase 4 scope creeps backward into completed Phase 1 auth work or forward into Phase 5 `FR-006` UX
  - **Mitigation**: Keep planning and packeting anchored to the canonical Phase 4 requirement IDs and the approved Packet 4A scope boundary
- **Risk**: User-facing surfaces bypass the established JWT/RLS boundary or break degraded-mode/runtime safeguards
  - **Mitigation**: Extend the existing Phase 2/3 APIs and ops behavior rather than replacing them; require explicit privileged-path justification
- **Risk**: Accessibility work is treated as polish instead of delivery scope
  - **Mitigation**: Keep `DS-002` through `DS-006` in the primary Phase 4 deliverable set with mapped tests and exit criteria

**Rationale:** With the authenticated backend and Phase 3 processing substrate already merged, this phase focuses on the user-facing application layer that unlocks upload, configuration, orchestration, delivery, accessibility, and downstream preview readiness without re-planning completed infrastructure.

### Phase 5: Advanced Features & UX Refinement

**Objective:** Implement security/compliance hardening, reliability controls, pricing model controls, and internationalization readiness for advanced tiers.

**Requirements Implemented:** **FR-006**, **SEC-001**, **SEC-002**, **SEC-003**, **SEC-004**, **SEC-005**, **SEC-006**, **NFR-004**, **NFR-005**, **NFR-006**, **NFR-009** (11 requirements)  
**Coverage Matrix:** See `docs/specs/ChronosRefine Requirements Coverage Matrix.md`

**Entry Criteria:**
- [ ] Phase 4 complete: User-facing features operational → **See:** `docs/specs/chronosrefine_implementation_plan.md#phase-4-user-facing-features--application-logic`
- [ ] Pricing tiers finalized with feature allocation → **Req:** **NFR-006**, **NFR-012**, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-006-pricing-model`, `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-012-payment-provider-selection`, `docs/specs/chronosrefine_prd_v9.md#pricing--business-model`
- [ ] Legal review complete for GDPR and data-handling controls → **Req:** **SEC-006**, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-006-gdpr-compliance`

**Deliverables:**
-   Preview generation system hardened for production usage → **Req:** **FR-006**, **Test:** `tests/processing/test_preview_generation.py`, `tests/processing/test_scene_detection.py`, `tests/ui/test_preview_modal.spec.ts`, `tests/load/test_preview_performance.py`, **See:** `docs/specs/chronosrefine_functional_requirements.md#fr-006-preview-generation`
-   Authentication and authorization controls hardened for tiered access → **Req:** **SEC-001**, **SEC-004**, **Test:** `tests/security/test_access_control.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-001-authentication--authorization`, `docs/specs/chronosrefine_security_operations_requirements.md#sec-004-access-control`
-   Data encryption and key-management controls validated → **Req:** **SEC-002**, **Test:** `tests/security/test_encryption.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-002-data-encryption`
-   Data classification and retention controls implemented for manifests/audit artifacts → **Req:** **SEC-003**, **SEC-005**, **Test:** `tests/security/test_data_classification.py`, `tests/security/test_manifest_retention.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-003-data-classification`, `docs/specs/chronosrefine_security_operations_requirements.md#sec-005-transformation-manifest-retention`
-   GDPR support implemented (export/deletion/consent workflows) → **Req:** **SEC-006**, **Test:** `tests/compliance/test_gdpr_compliance.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-006-gdpr-compliance`
-   Reliability/availability controls and Museum-tier DR posture validated → **Req:** **NFR-004**, **NFR-005**, **Test:** `tests/ops/test_availability_slo.py`, `tests/ops/test_disaster_recovery.py`, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-004-reliability--availability`, `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-005-museum-sla--disaster-recovery`
-   Pricing model and entitlement enforcement finalized (no hardcoded pricing) → **Req:** **NFR-006**, **NFR-012**, **Test:** `tests/billing/test_feature_gating.py`, `tests/billing/test_subscription_lifecycle.py`, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-006-pricing-model`, `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-012-payment-provider-selection`
-   UTF-8 metadata support and i18n framework foundations implemented → **Req:** **NFR-009**, **Test:** `tests/i18n/test_utf8_encoding.py`, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-009-internationalization-i18n`

**Exit Criteria:**
- [ ] Preview generation remains <6s p95 under expected load → **Req:** **FR-006**, **Test:** `tests/load/test_preview_performance.py`, **See:** `docs/specs/chronosrefine_functional_requirements.md#fr-006-preview-generation`
- [ ] Authentication/authorization and access control pass security validation suite → **Req:** **SEC-001**, **SEC-004**, **Test:** `tests/security/test_access_control.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-001-authentication--authorization`, `docs/specs/chronosrefine_security_operations_requirements.md#sec-004-access-control`
- [ ] Encryption controls pass at-rest and in-transit verification → **Req:** **SEC-002**, **Test:** `tests/security/test_encryption.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-002-data-encryption`
- [ ] Data classification and manifest retention policies pass automated checks → **Req:** **SEC-003**, **SEC-005**, **Test:** `tests/security/test_data_classification.py`, `tests/security/test_manifest_retention.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-003-data-classification`, `docs/specs/chronosrefine_security_operations_requirements.md#sec-005-transformation-manifest-retention`
- [ ] GDPR workflows validated (export/deletion/consent) → **Req:** **SEC-006**, **Test:** `tests/compliance/test_gdpr_compliance.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-006-gdpr-compliance`
- [ ] Reliability/SLA/DR requirements validated for Museum tier → **Req:** **NFR-004**, **NFR-005**, **Test:** `tests/ops/test_availability_slo.py`, `tests/ops/test_disaster_recovery.py`, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-004-reliability--availability`, `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-005-museum-sla--disaster-recovery`
- [ ] Pricing model and feature gating validate against Stripe-configured pricing only → **Req:** **NFR-006**, **NFR-012**, **Test:** `tests/billing/test_feature_gating.py`, `tests/billing/test_subscription_lifecycle.py`, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-006-pricing-model`, `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-012-payment-provider-selection`
- [ ] UTF-8 handling and localization framework pass baseline coverage → **Req:** **NFR-009**, **Test:** `tests/i18n/test_utf8_encoding.py`, `tests/i18n/test_localization.py`, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-009-internationalization-i18n`

**Phase-Specific Risks:**
- **Risk**: Security/compliance controls add latency and operational overhead
  - **Mitigation**: Track p95 latency budgets per control and tune enforcement paths before Phase 6
- **Risk**: Pricing and entitlement drift from Stripe configuration
  - **Mitigation**: Enforce Product/Price-ID-only billing configuration and add reconciliation checks in CI

**Rationale:** This phase converts a functional product into a launch-ready system by hardening security, compliance, reliability, and pricing/i18n controls before production readiness gates.

### Phase 6: Production Readiness & Launch

**Objective:** Prepare the application for production launch through rigorous testing, security hardening, and documentation.

**Requirements Implemented:** **FR-007**, **NFR-001**, **SEC-015**, **NFR-008**, **NFR-010**, **SEC-009**, **SEC-010**, **SEC-011**, **SEC-012**, **OPS-004** (10 requirements)  
**Coverage Matrix:** See `docs/specs/ChronosRefine Requirements Coverage Matrix.md`

**Entry Criteria:**
- [ ] Phase 5 complete: All features implemented → **See:** `docs/specs/chronosrefine_implementation_plan.md#phase-5-advanced-features--ux-refinement`
- [ ] HPS protocol executed with results documented → **Req:** **FR-007**, **See:** `docs/specs/chronosrefine_functional_requirements.md#fr-007-human-preference-score-hps-validation`, `docs/specs/chronosrefine_prd_v9.md#beta-exit-criteria-ga-readiness`
- [ ] Third-party security auditor engaged → **Req:** **SEC-015**, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-015-third-party-security-audit`

**Deliverables:**
-   Repository note: launch-artifact directories such as `docs/user_guide/`, `docs/operations/`, `docs/compliance/`, `docs/security/`, and `docs/hps/` are not yet present on `main`; until they exist, rely on the canonical spec references below and treat launch evidence packages as planned artifacts.
-   Completed third-party security audit with remediation verification → **Req:** **SEC-015**, **Test:** `tests/security/test_audit_remediation.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-015-third-party-security-audit`, launch audit evidence package (planned artifact)
-   Successful load testing that meets all SLOs → **Req:** **NFR-002**, **Test:** `tests/load/test_production_load.py`, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-002-processing-time-slo`, `docs/specs/chronosrefine_prd_v9.md#performance-slos`
-   Log retention and PII-redaction controls validated and documented → **Req:** **SEC-009**, **Test:** `tests/security/test_log_retention_redaction.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-009-log-retention--pii-redaction`
-   Deletion proof generation and verification finalized for launch readiness → **Req:** **SEC-010**, **Test:** `tests/compliance/test_deletion_proof.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-010-deletion-proofs`
-   Dataset provenance chain and evidence model validated → **Req:** **SEC-011**, **Test:** `tests/compliance/test_dataset_provenance.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-011-dataset-provenance`
-   Data residency controls and validation reports finalized → **Req:** **SEC-012**, **Test:** `tests/ops/test_data_residency.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-012-data-residency`
-   Usability and end-user readiness checks finalized → **Req:** **NFR-008**, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-008-usability`
-   Comprehensive internal and user-facing documentation finalized → **Req:** **NFR-010**, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-010-documentation`, `docs/api/`, launch user/ops documentation package (planned artifact)
-   Performance monitoring dashboards, baselines, and runbooks finalized → **Req:** **OPS-004**, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#ops-004-performance-monitoring`, launch operations runbook package (planned artifact)
-   HPS validation platform and results → **Req:** **FR-007**, **Test:** `tests/hps/test_evaluation_platform.py`, `tests/hps/test_statistical_analysis.py`, **See:** `docs/specs/chronosrefine_functional_requirements.md#fr-007-human-preference-score-hps-validation`, launch HPS validation report (planned artifact)
-   Compliance documentation package (usability/legal/security readiness) → **Req:** **NFR-008**, **SEC-015**, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-008-usability`, launch compliance evidence package (planned artifact)

**Exit Criteria:**
- [ ] **HPS Gate**: ≥75% in EACH media category (Daguerreotype, Albumen, 16mm, Super 8, Kodachrome, VHS) → **Req:** **FR-007**, **NFR-001**, **Test:** `tests/hps/test_statistical_analysis.py`, **See:** `docs/specs/chronosrefine_functional_requirements.md#fr-007-human-preference-score-hps-validation`, `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-001-cost-estimate-display`, `docs/specs/chronosrefine_prd_v9.md#beta-exit-criteria-ga-readiness`
- [ ] Security audit complete with zero critical vulnerabilities → **Req:** **SEC-015**, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-015-third-party-security-audit`, launch audit evidence package (planned artifact)
- [ ] Log retention and PII redaction controls validated in production-like environment → **Req:** **SEC-009**, **Test:** `tests/security/test_log_retention_redaction.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-009-log-retention--pii-redaction`
- [ ] Deletion proofs generated/verified for required launch scenarios → **Req:** **SEC-010**, **Test:** `tests/compliance/test_deletion_proof.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-010-deletion-proofs`
- [ ] Dataset provenance evidence chain validated for audit samples → **Req:** **SEC-011**, **Test:** `tests/compliance/test_dataset_provenance.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-011-dataset-provenance`
- [ ] Data residency controls validated for supported launch regions → **Req:** **SEC-012**, **Test:** `tests/ops/test_data_residency.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-012-data-residency`
- [ ] Load testing validates 1000 concurrent users with <5% error rate → **Req:** **NFR-002**, **Test:** `tests/load/test_production_load.py`, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-002-processing-time-slo`
- [ ] All SLOs met in staging environment for 7 consecutive days → **Req:** **NFR-002**, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-002-processing-time-slo`, `docs/specs/chronosrefine_prd_v9.md#performance-slos`
- [ ] Usability acceptance checks pass for launch personas → **Req:** **NFR-008**, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-008-usability`
- [ ] User documentation complete with video tutorials for each persona → **Req:** **NFR-010**, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-010-documentation`, launch user-guide package (planned artifact)
- [ ] Performance monitoring runbook and regression detection procedures documented → **Req:** **OPS-004**, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#ops-004-performance-monitoring`, launch operations runbook package (planned artifact)
- [ ] Monitoring-driven rollback decision procedure tested in staging → **Req:** **OPS-004**, **Test:** `tests/ops/test_rollback.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#ops-004-performance-monitoring`
- [ ] Legal review complete for Terms of Service and Privacy Policy → **Req:** **NFR-008**, **SEC-006**, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-008-usability`, `docs/specs/chronosrefine_security_operations_requirements.md#sec-006-gdpr-compliance`
- [ ] SOC 2 Type II readiness assessment complete → **Req:** **NFR-008**, **SEC-015**, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-008-usability`, `docs/specs/chronosrefine_security_operations_requirements.md#sec-015-third-party-security-audit`, launch compliance evidence package (planned artifact)

**Phase-Specific Risks:**
- **Risk**: HPS fails to meet 75% threshold in one or more categories
  - **Mitigation**: Category-specific launch strategy; block GA for failing categories only
- **Risk**: Production load exceeds capacity planning estimates
  - **Mitigation**: Phased rollout with invite-only beta; monitor autoscaling behavior closely

**Rationale:** This final phase ensures that the product is stable, secure, and ready for public launch. It is the final quality gate before making ChronosRefine available to the public.

### 10.0 Beta → GA Release Gates

**Post-GA roadmap note:** `SEC-008` (VPC Service Controls) remains a post-GA roadmap requirement per canonical security requirements (`GA+6 months` / `GA+9 months`) and is intentionally excluded from the Phase 1-6 implementation packets.

This section defines the formal entry and exit criteria for the Beta and GA (General Availability) phases, along with canary deployment rules and operational readiness requirements. These gates ensure that ChronosRefine launches with high quality and minimal risk.

#### Beta Entry Criteria

The following conditions must be met before opening Beta to external users:

- [ ] **All Phase 1-5 deliverables complete**: Infrastructure, data layer, AI pipeline, user features, and advanced features fully implemented
- [ ] **Core functionality validated**: End-to-end processing pipeline successfully processes all 6 media types (Daguerreotype, Albumen, 16mm, Super 8, Kodachrome, VHS)
- [ ] **Internal dogfooding complete**: Product team has processed 50+ real-world items with documented results
- [ ] **Beta infrastructure provisioned**: Separate beta environment with monitoring, alerting, and cost tracking
- [ ] **Beta user cohort recruited**: Minimum 50 beta users across all personas (20 hobbyists, 20 documentary filmmakers, 10 institutional archivists)
- [ ] **Feedback collection mechanism**: In-app survey, feedback forum, and weekly beta user interviews scheduled
- [ ] **Known issues documented**: Public beta known issues list published; critical blockers resolved
- [ ] **Beta Terms of Service**: Legal review complete; beta users acknowledge experimental status

#### Beta Exit Criteria (GA Readiness)

The following conditions must be met before promoting to General Availability:

**Quality Gates:**

- [ ] **HPS ≥75% in EACH media category**: Human Preference Score meets threshold in all 6 categories individually (not averaged)
  - Daguerreotype: ≥75%
  - Albumen: ≥75%
  - 16mm: ≥75%
  - Super 8: ≥75%
  - Kodachrome: ≥75%
  - VHS: ≥75%
- [ ] **Anti-Plastic metrics validated**: E_HF, S_LS, and T_TC metrics meet targets across all modes (Conserve, Restore, Enhance) on Heritage Test Set
- [ ] **Era classification accuracy**: >90% on Heritage Test Set with <10% low-confidence rate
- [ ] **Export completion rate**: >85% of started jobs result in successful download

**Performance Gates:**

- [ ] **Job success rate**: >99.5% over 7 consecutive days in beta environment
- [ ] **Processing time SLO**: p95 processing time <2x realtime for 4K video
- [ ] **GPU pre-warm latency**: p99 <120s for cold start
- [ ] **Load testing passed**: 1000 concurrent users with <5% error rate
- [ ] **Soak testing passed**: 24-hour continuous operation with no memory leaks or degradation

**User Satisfaction Gates:**

- [ ] **Net Promoter Score (NPS)**: >40 from beta users
- [ ] **Beta user retention**: >60% of beta users active in final month
- [ ] **Critical bug resolution**: Zero P0 bugs; <5 P1 bugs in backlog
- [ ] **Preview abandonment rate**: <15% (users who generate preview but cancel job)

**Operational Readiness:**

- [ ] **Security audit complete**: Third-party penetration testing with zero critical vulnerabilities
- [ ] **Compliance validation**: GDPR support mechanisms validated; SOC 2 pre-audit controls in place
- [ ] **Monitoring dashboards**: All SLO dashboards operational with alerting configured
- [ ] **Runbooks documented**: Incident response procedures for top 10 failure scenarios
- [ ] **On-call rotation**: 24/7 on-call schedule established with escalation paths
- [ ] **Cost model validated**: Actual beta costs within 15% of projections; pricing model adjusted if needed

**Documentation & Legal:**

- [ ] **User documentation**: Complete guides for all personas with video tutorials
- [ ] **API documentation**: OpenAPI/Swagger spec published with examples
- [ ] **Terms of Service**: Legal review complete and published
- [ ] **Privacy Policy**: Legal review complete and published
- [ ] **Data Processing Agreement (DPA)**: Template ready for Museum Tier customers

#### Canary Deployment Rules

To minimize risk during GA launch, the following canary deployment strategy will be used:

**Canary Stages:**

| Stage | User Cohort | Duration | Success Criteria | Rollback Triggers |
|---|---|---|---|---|
| **Canary 1** | 5% of traffic (beta users only) | 24 hours | Error rate <1%, p95 latency <2x baseline | Error rate >2%, any P0 bugs |
| **Canary 2** | 25% of traffic (beta + new signups) | 48 hours | Error rate <1%, NPS >35 | Error rate >2%, NPS <30 |
| **Canary 3** | 50% of traffic | 72 hours | All SLOs met, cost within budget | Any SLO violation for >1 hour |
| **Full GA** | 100% of traffic | Ongoing | All SLOs met, NPS >40 | Error rate >5%, multiple SLO violations |

**Rollback Triggers:**

Automatic rollback to previous version if any of the following conditions are met:

- **Error rate >5%** for >15 minutes
- **P0 bug reported** affecting >10% of users
- **Security vulnerability** discovered with CVSS score >7.0
- **Data loss incident** affecting any user data
- **Cost overrun >50%** of budget for >6 hours

**Rollback Procedure:**

1. **Immediate**: Stop new job submissions; allow in-flight jobs to complete
2. **Within 5 minutes**: Route all traffic to previous stable version
3. **Within 15 minutes**: Verify rollback success; communicate status to users
4. **Within 1 hour**: Root cause analysis initiated; incident postmortem scheduled

#### Operational Readiness Checklist

The following operational capabilities must be in place before GA launch:

**Monitoring & Alerting:**

- [ ] **SLO dashboards**: Job success rate, processing time, GPU pre-warm latency, error rate
- [ ] **Cost dashboards**: GPU spend, storage costs, API costs (Gemini, SynthID) with budget alerts
- [ ] **User behavior dashboards**: Preview abandonment, export completion, tier distribution
- [ ] **PagerDuty integration**: Alerts configured for all SLO violations with on-call escalation
- [ ] **Slack integration**: Non-critical alerts posted to #chronosrefine-ops channel

**Incident Response:**

- [ ] **Runbooks**: Documented procedures for:
  - GPU pool exhaustion
  - Gemini API rate limit exceeded
  - GCS upload failures
  - Job processing timeouts
  - Cost spike investigation
  - User data deletion requests
  - Security incident response
  - Rollback execution
- [ ] **On-call rotation**: 24/7 coverage with primary and secondary on-call engineers
- [ ] **Escalation paths**: Clear escalation to engineering manager, product manager, and executive team
- [ ] **Incident postmortem template**: Standardized format for documenting and learning from incidents

**Capacity Planning:**

- [ ] **Autoscaling validated**: GPU pool scales from 0 to 100 instances within 5 minutes
- [ ] **Quota limits confirmed**: GCP quotas sufficient for 5x expected peak load
- [ ] **Cost projections**: Monthly cost model validated against beta actuals; pricing adjusted if needed
- [ ] **Storage lifecycle policies**: Automatic deletion of expired assets (7d/90d) tested and operational

**User Support:**

- [ ] **Support email**: support@chronosrefine.com monitored with 24-hour response SLA
- [ ] **Community forum**: Discourse or similar platform operational with moderators
- [ ] **FAQ published**: Top 20 user questions answered with examples
- [ ] **Status page**: Public status page (status.chronosrefine.com) with uptime history

## 10.1 Test Strategy & Quality Assurance

A comprehensive test strategy ensures that ChronosRefine meets all quality, performance, and security requirements before launch. This section defines the test pyramid, coverage targets, and specialized testing approaches for each quality dimension.

### Test Pyramid

The test pyramid defines the distribution of testing effort across different levels of the system, optimizing for fast feedback and comprehensive coverage.

| Test Level | Percentage of Total Tests | Target Coverage | Tools | Execution Frequency |
|---|---|---|---|---|
| **Unit Tests** | 70% | >85% code coverage | pytest (Python), Jest (JavaScript) | Every commit (CI) |
| **Integration Tests** | 20% | >70% of critical paths | pytest with fixtures, Postman/Newman | Every merge to main |
| **End-to-End Tests** | 10% | All happy paths + critical errors | Playwright, Cypress | Nightly + pre-release |

### Test Data Requirements

#### Heritage Test Set

A curated dataset of 2,000 historical media items stratified across multiple dimensions to ensure representative coverage.

| Dimension | Distribution |
|---|---|
| **Era** | 333 items per era (Daguerreotype, Albumen, 16mm, Super 8, Kodachrome, VHS) |
| **Damage Severity** | 33% light, 33% moderate, 33% severe |
| **Content Type** | 40% portraits, 30% landscapes, 20% documents, 10% mixed |
| **Resolution** | Proportional to era capabilities (VHS: 720p, Kodachrome: 4K, etc.) |

**Provenance:** All test items must have documented provenance and usage rights. Items sourced from public domain archives (Library of Congress, Internet Archive) and synthetic generation.

#### Synthetic Test Cases

Generated edge cases for boundary testing and adversarial scenarios.

-   **Extreme Damage**: Synthetically degraded media with 90%+ noise
-   **Edge Artifacts**: Media with intentional edge cases (pure black frames, extreme motion blur)
-   **Ambiguous Eras**: Media that blends characteristics of multiple eras
-   **Invalid Inputs**: Malformed files, corrupted headers, unsupported codecs

#### Regression Suite

Known-good outputs from previous versions to detect quality regressions.

-   **Golden Set**: 100 reference outputs with frozen quality metrics (E_HF, S_LS, LPIPS)
-   **Version Tracking**: Each release freezes a new golden set for future regression testing

### Performance Testing

#### Load Testing

Validate system behavior under expected production load.

| Scenario | Concurrent Users | Job Mix | Duration | Success Criteria |
|---|---|---|---|---|
| **Normal Load** | 100 | 60% Enhance, 30% Restore, 10% Conserve | 1 hour | <2% error rate, p95 latency <10s |
| **Peak Load** | 500 | Same distribution | 30 minutes | <5% error rate, p95 latency <15s |
| **Spike Test** | 0→1000 in 5 min | Same distribution | 15 minutes | Autoscaler responds within 2 min |

**Tools:** Locust, k6, or Artillery for load generation; Cloud Monitoring for metrics collection.

#### Stress Testing

Identify breaking points and failure modes.

-   **Objective**: Determine maximum concurrent jobs before system degradation
-   **Method**: Gradually increase load until error rate exceeds 10% or latency exceeds 60s
-   **Expected Outcome**: Graceful degradation with clear error messages; no data loss

#### Soak Testing

Detect memory leaks and resource exhaustion over extended periods.

-   **Duration**: 24 hours continuous operation
-   **Load**: 50 concurrent users with realistic job distribution
-   **Monitoring**: Memory usage, connection pool exhaustion, disk space growth
-   **Success Criteria**: No memory leaks (heap growth <5% over 24h); no connection pool exhaustion

### Security Testing

#### Penetration Testing

-   **Frequency**: Annual third-party audit + quarterly internal scans
-   **Scope**: Web application, API endpoints, infrastructure (GCP IAM, network policies)
-   **Tools**: Burp Suite, OWASP ZAP, Metasploit
-   **Deliverable**: Penetration testing report with severity ratings and remediation timeline

#### Vulnerability Scanning

-   **Frequency**: Weekly automated scans
-   **Tools**: Snyk, Dependabot, Trivy (container scanning)
-   **Policy**: Critical vulnerabilities must be patched within 7 days; high within 30 days

#### Compliance Validation

-   **GDPR**: Validate Article 17 (Right to Erasure) with end-to-end deletion proof generation
-   **SOC 2 Type II**: Audit controls for access management, change management, and monitoring
-   **Testing**: Quarterly compliance control testing; annual SOC 2 audit

### Specialized Testing

#### Quality Metrics Validation

Ensure E_HF, S_LS, and LPIPS metrics are calculated correctly.

-   **Method**: Compare against reference implementations (MATLAB, Python scipy)
-   **Test Set**: 100 synthetic videos with known ground-truth metric values
-   **Tolerance**: <1% deviation from reference implementation

#### Era Classification Accuracy

-   **Test Set**: Heritage Test Set (2,000 items)
-   **Target**: >90% accuracy; <10% low-confidence rate (confidence <0.70)
-   **Confusion Matrix**: Track misclassification patterns to identify model weaknesses

#### Watermark Robustness

-   **Test**: Apply SynthID watermark; re-encode with AV1, H.264, H.265 at various bitrates
-   **Detection**: Verify watermark detection rate >98% after re-encoding
-   **Fallback**: Validate manifest metadata fallback for non-supported formats

### Test Automation & CI/CD Integration

-   **Unit Tests**: Run on every commit; block merge if tests fail
-   **Integration Tests**: Run on merge to main; deploy to staging only if passing
-   **E2E Tests**: Run nightly; alert on-call engineer if failures detected
-   **Performance Tests**: Run weekly; track trends in Cloud Monitoring dashboards

### Test Coverage Reporting

-   **Tool**: Codecov or Coveralls for coverage tracking
-   **Visibility**: Coverage reports posted to pull requests; block merge if coverage drops >2%
-   **Target**: Maintain >85% overall coverage; >95% for critical paths (schema validation, job orchestration)
