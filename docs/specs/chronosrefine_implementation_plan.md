# ChronosRefine Implementation Plan

**Version:** 10.3  
**Last Updated:** February 2026  
**Status:** Handoff-Ready  
**Audience:** Development Team, Product Manager, Engineering Manager

---

## 10. Implementation Plan

This implementation plan is organized into a logical execution sequence designed to build foundational components first, mitigate risks early, and deliver incremental value at each phase. This approach provides the development team with a clear roadmap for building ChronosRefine with minimal risk and an optimal chance of success.

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
-   Secure GCP project setup with IAM policies defined in Terraform → **See:** `companion_docs/ChronosRefine_Infrastructure_Spec.md` (to be created)
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
- [ ] Design system tokens and component library implemented → **Req:** **DS-007**, **Test:** `tests/design_system/test_component_library.spec.ts`, **See:** `docs/specs/chronosrefine_design_requirements.md#ds-007-design-system-implementation`, `chronosrefine_companion_docs/ChronosRefine_Design_System_Specification.md`
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

**Entry Criteria:**
- [ ] Phase 1 complete: Infrastructure operational → **See:** `docs/specs/chronosrefine_implementation_plan.md#phase-1-foundation--core-infrastructure`
- [ ] Database technology selected (Supabase PostgreSQL) → **Req:** **ENG-016** (completed in Phase 1), **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-016-database-technology-selection-supabase`
- [ ] JSON Schema v2020-12 specification finalized → **Req:** **ENG-001**, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-001-json-schema-validation`

**Deliverables:**
-   Finalized JSON Schema for Era Profiles → **Req:** **ENG-001**, **Test:** `tests/api/test_schema_validation.py`, **See:** `docs/specs/chronosrefine_prd_v9.md#era-profile-schema`
-   Phase 2 API foundation subset (`/v1/detect-era`, `/v1/eras`, `/v1/users/me`, `/v1/users/me/usage`, `/v1/users/me/approve-overage`, `/v1/orgs/{org_id}/settings/logs`, `/v1/user/delete_logs`, `/v1/health`, `/v1/version`) → **Req:** **ENG-002**, **Test:** `tests/api/test_endpoints.py`, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-002-api-endpoint-implementation`
-   Era-detection model service, persistence, and fallback contract → **Req:** **ENG-004**, **FR-002**, **Test:** `tests/ml/test_era_detection.py`, `tests/ml/test_gemini_integration.py`, `tests/api/test_era_detection.py`, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-004-era-detection-model`, `docs/specs/chronosrefine_functional_requirements.md#fr-002-era-detection`
-   Validation logic that enforces all schema rules → **Req:** **ENG-001**, **Test:** `tests/api/test_schema_validation.py`, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-001-json-schema-validation`
-   PII redaction, log retention, and GDPR log-deletion flows configured → **Req:** **SEC-009**, **Test:** `tests/security/test_log_retention.py`, `tests/security/test_pii_redaction.py`, `tests/compliance/test_gdpr_log_deletion.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-009-log-retention--pii-redaction`

**Exit Criteria:**
- [ ] JSON Schema validates all 6 era profiles with 100% pass rate → **Req:** **ENG-001**, **Test:** `tests/api/test_schema_validation.py`, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-001-json-schema-validation`
- [ ] Phase 2 API subset documented in OpenAPI and covered by contract tests → **Req:** **ENG-002**, **Test:** `tests/api/test_endpoints.py`, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-002-api-endpoint-implementation`
- [ ] Era-detection model fallback and manual-confirmation contract validated → **Req:** **ENG-004**, **FR-002**, **Test:** `tests/ml/test_era_detection.py`, `tests/api/test_era_detection.py`, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-004-era-detection-model`, `docs/specs/chronosrefine_functional_requirements.md#fr-002-era-detection`
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

**Objective:** Build the core video processing pipeline and integrate the primary AI/ML models.

**Requirements Implemented:** **ENG-003**, **ENG-005**, **ENG-006**, **ENG-007**, **ENG-008**, **ENG-009**, **ENG-010**, **ENG-011**, **ENG-012**, **NFR-002**, **SEC-007**, **OPS-003** (12 requirements)  
**Coverage Matrix:** See `docs/specs/ChronosRefine Requirements Coverage Matrix.md`

**Entry Criteria:**
- [ ] Phase 2 complete: Data layer operational with >95% test coverage → **See:** `docs/specs/chronosrefine_implementation_plan.md#phase-2-api-foundation--data-layer`
- [ ] GPU access configured (Vertex AI L4 instances) → **Req:** **OPS-003**, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#ops-003-incident-response`, `docs/specs/chronosrefine_prd_v9.md#infrastructure-requirements`
- [ ] All AI model licenses and API keys secured → **Req:** **ENG-005**, **ENG-006**, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-005-fidelity-tier-implementation`, `docs/specs/chronosrefine_engineering_requirements.md#eng-006-quality-metrics-calculation`, `docs/specs/chronosrefine_prd_v9.md`
- [ ] Heritage Test Set (2,000 items) prepared and accessible → **Req:** **FR-007**, **See:** `docs/specs/chronosrefine_functional_requirements.md#fr-007-human-preference-score-hps-validation`, `docs/specs/chronosrefine_prd_v9.md#beta-exit-criteria-ga-readiness`

**Deliverables:**
-   Integration with Gemini 3 Pro for era classification → **Req:** **ENG-005**, **FR-002**, **Test:** `tests/ml/test_gemini_integration.py`, `tests/ml/test_era_detection.py`, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-005-fidelity-tier-implementation`, `docs/specs/chronosrefine_functional_requirements.md#fr-002-era-detection`
-   Implementation of the AV1 Film Grain Synthesis (FGS) pipeline → **Req:** **ENG-007**, **Test:** `tests/processing/test_av1_fgs.py`, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-007-reproducibility-proof`, `docs/specs/chronosrefine_prd_v9.md#av1-film-grain-synthesis`
-   Integration of the CodeFormer model for facial restoration → **Req:** **ENG-006**, **Test:** `tests/ml/test_codeformer.py`, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-006-quality-metrics-calculation`, `docs/specs/chronosrefine_prd_v9.md#codeformer`
-   A functioning end-to-end processing pipeline that can execute a single job → **Req:** **FR-004**, **Test:** `tests/processing/test_end_to_end_pipeline.py`, **See:** `docs/specs/chronosrefine_functional_requirements.md#fr-004-processing-and-restoration`
-   Quality metrics implementation (E_HF, S_LS, T_TC) → **Req:** **ENG-008**, **ENG-009**, **ENG-010**, **Test:** `tests/quality/test_e_hf_metric.py`, `tests/quality/test_s_ls_metric.py`, `tests/quality/test_t_tc_metric.py`, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-008-gpu-pool-management`, `docs/specs/chronosrefine_engineering_requirements.md#eng-009-deduplication-cache`, `docs/specs/chronosrefine_engineering_requirements.md#eng-010-transformation-manifest-generation`
-   SynthID watermarking integration → **Req:** **ENG-012**, **Test:** `tests/processing/test_synthid.py`, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-012-error-recovery`
-   MediaPipe segmentation integration → **Req:** **ENG-011**, **Test:** `tests/ml/test_mediapipe.py`, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-011-async-processing`

**Exit Criteria:**
- [ ] Gemini 3 Pro integration achieves >90% era classification accuracy on Heritage Test Set → **Req:** **ENG-005**, **FR-002**, **Test:** `tests/ml/test_era_detection.py`, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-005-fidelity-tier-implementation`, `docs/specs/chronosrefine_functional_requirements.md#fr-002-era-detection`
- [ ] AV1 FGS pipeline produces output with grain energy within 10% of source measurement → **Req:** **ENG-007**, **Test:** `tests/processing/test_av1_fgs.py`, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-007-reproducibility-proof`
- [ ] CodeFormer facial restoration maintains LPIPS identity drift < 0.02 on test faces → **Req:** **ENG-006**, **Test:** `tests/ml/test_codeformer.py`, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-006-quality-metrics-calculation`
- [ ] End-to-end pipeline processes a 10-minute 4K video in <20 minutes (p95) → **Req:** **NFR-002**, **Test:** `tests/load/test_processing_performance.py`, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-002-processing-time-slo`
- [ ] All Phase 3 unit tests pass with >85% coverage
- [ ] Integration tests validate correct parameter passing between AI components → **Test:** `tests/integration/test_ai_pipeline_integration.py`
- [ ] E_HF and S_LS metrics calculated correctly for 100% of test videos → **Req:** **ENG-008**, **ENG-009**, **Test:** `tests/quality/test_quality_metrics.py`, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-008-gpu-pool-management`, `docs/specs/chronosrefine_engineering_requirements.md#eng-009-deduplication-cache`
- [ ] Model security and sandboxing tested → **Req:** **SEC-007**, **Test:** `tests/security/test_model_security.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-007-customer-managed-encryption-keys-cmek`
- [ ] GPU resource management tested with autoscaling → **Req:** **OPS-003**, **Test:** `tests/ops/test_gpu_management.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#ops-003-incident-response`

**Phase-Specific Risks:**
- **Risk**: Gemini API rate limits impact development velocity
  - **Mitigation**: Implement aggressive caching; use mock responses for testing
- **Risk**: AV1 encoder performance bottleneck
  - **Mitigation**: Benchmark libaom vs SVT-AV1; optimize encoding parameters
- **Risk**: GPU costs exceed budget during development
  - **Mitigation**: Use preemptible instances; implement auto-shutdown for idle GPUs

**Rationale:** This phase tackles the highest-risk and most complex part of the system. Proving out the core AI/ML pipeline early will provide critical insights and de-risk the project.

### Phase 4: User-Facing Features & Application Logic

**Objective:** Develop the user-facing features, including the web interface, authentication, and job management.

**Requirements Implemented:** **FR-001**, **FR-003**, **FR-004**, **FR-005**, **ENG-013**, **ENG-014**, **ENG-015**, **DS-001**, **DS-002**, **DS-003**, **DS-004**, **DS-005**, **DS-006**, **NFR-003** (14 requirements)  
**Coverage Matrix:** See `docs/specs/ChronosRefine Requirements Coverage Matrix.md`

**Entry Criteria:**
- [ ] Phase 3 complete: Core processing pipeline operational → **See:** `docs/specs/chronosrefine_implementation_plan.md#phase-3-core-processing-pipeline--ai-integration`
- [ ] Design system specifications finalized → **Req:** **DS-007** (completed in Phase 1), **See:** `docs/specs/chronosrefine_design_requirements.md#ds-007-design-system-implementation`, `chronosrefine_companion_docs/ChronosRefine_Design_System_Specification.md`
- [ ] OAuth 2.0 provider selected and configured → **Req:** **SEC-013** (completed in Phase 1), **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-013-authentication-provider-selection-supabase`

**Deliverables:**
-   Secure user authentication and authorization system → **Req:** **SEC-013** (completed in Phase 1), **Test:** `tests/auth/test_oauth_integration.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-013-authentication-provider-selection-supabase`
-   Web interface for file upload, job management, and results viewing → **Req:** **FR-001**, **FR-004**, **FR-005**, **Test:** `tests/ui/test_upload_interface.spec.ts`, `tests/ui/test_job_management.spec.ts`, **See:** `docs/specs/chronosrefine_functional_requirements.md#fr-001-video-upload-and-validation`, `docs/specs/chronosrefine_functional_requirements.md#fr-004-processing-and-restoration`, `docs/specs/chronosrefine_functional_requirements.md#fr-005-output-delivery`
-   API endpoints for all user-facing actions → **Req:** **ENG-002**, **Test:** `tests/api/test_endpoints.py`, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-002-api-endpoint-implementation`
-   Implementation of the resumable upload functionality → **Req:** **FR-001**, **Test:** `tests/upload/test_resumable_upload.py`, **See:** `docs/specs/chronosrefine_functional_requirements.md#fr-001-video-upload-and-validation`
-   Preview generation system → **Req:** **FR-006**, **ENG-014**, **Test:** `tests/processing/test_preview_generation.py`, `tests/ui/test_preview_modal.spec.ts`, **See:** `docs/specs/chronosrefine_functional_requirements.md#fr-006-preview-generation`, `docs/specs/chronosrefine_engineering_requirements.md#eng-014-preview-generation`
-   Fidelity tier selection UI → **Req:** **FR-003**, **Test:** `tests/ui/test_fidelity_tier_selection.spec.ts`, **See:** `docs/specs/chronosrefine_functional_requirements.md#fr-003-fidelity-tier-selection`
-   Cost estimation display → **Req:** **ENG-013**, **Test:** `tests/api/test_cost_estimation.py`, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-013-cost-estimation`
-   Output delivery system → **Req:** **FR-005**, **ENG-015**, **Test:** `tests/processing/test_output_delivery.py`, **See:** `docs/specs/chronosrefine_functional_requirements.md#fr-005-output-delivery`, `docs/specs/chronosrefine_engineering_requirements.md#eng-015-output-encoding`
-   Accessibility features (keyboard nav, screen reader, color contrast, focus indicators) → **Req:** **DS-002**, **DS-003**, **DS-004**, **DS-005**, **Test:** `tests/accessibility/test_keyboard_navigation.spec.ts`, `tests/accessibility/test_screen_reader.spec.ts`, **See:** `docs/specs/chronosrefine_design_requirements.md#ds-002-keyboard-navigation`, `docs/specs/chronosrefine_design_requirements.md#ds-003-screen-reader-support`, `docs/specs/chronosrefine_design_requirements.md#ds-004-color-contrast`, `docs/specs/chronosrefine_design_requirements.md#ds-005-focus-indicators`

**Exit Criteria:**
- [ ] User authentication working with OAuth 2.0 (test with 3 providers: Google, GitHub, Email) → **Req:** **SEC-013**, **Test:** `tests/auth/test_oauth_integration.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-013-authentication-provider-selection-supabase`
- [ ] Web interface implements design system with 100% component coverage → **Req:** **DS-001**, **DS-007**, **Test:** `tests/visual_regression/test_all_screens.spec.ts`, **See:** `docs/specs/chronosrefine_design_requirements.md#ds-001-fidelity-configuration-ux`, `docs/specs/chronosrefine_design_requirements.md#ds-007-design-system-implementation`
- [ ] All API endpoints documented with OpenAPI/Swagger spec → **Req:** **ENG-002**, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-002-api-endpoint-implementation`, `docs/api/openapi.yaml`
- [ ] Resumable uploads tested successfully for files >10GB with simulated network interruptions → **Req:** **FR-001**, **Test:** `tests/upload/test_resumable_upload.py`, **See:** `docs/specs/chronosrefine_functional_requirements.md#fr-001-video-upload-and-validation`
- [ ] Job management UI shows real-time progress updates with <2s latency → **Req:** **FR-004**, **Test:** `tests/ui/test_realtime_progress.spec.ts`, **See:** `docs/specs/chronosrefine_functional_requirements.md#fr-004-processing-and-restoration`
- [ ] Accessibility audit passes WCAG 2.1 AA standards → **Req:** **DS-002**, **DS-003**, **DS-004**, **DS-005**, **DS-006**, **Test:** `tests/accessibility/test_wcag_compliance.spec.ts`, **See:** `docs/specs/chronosrefine_design_requirements.md#ds-002-keyboard-navigation`, `docs/specs/chronosrefine_design_requirements.md#ds-003-screen-reader-support`, `docs/specs/chronosrefine_design_requirements.md#ds-004-color-contrast`, `docs/specs/chronosrefine_design_requirements.md#ds-005-focus-indicators`, `docs/specs/chronosrefine_design_requirements.md#ds-006-error-messages-accessibility`
- [ ] Cross-browser testing complete (Chrome, Firefox, Safari, Edge) → **Req:** **DS-001**, **Test:** `tests/cross_browser/test_all_browsers.spec.ts`, **See:** `docs/specs/chronosrefine_design_requirements.md#ds-001-fidelity-configuration-ux`
- [ ] Preview generation <6s p95 latency → **Req:** **FR-006**, **Test:** `tests/load/test_preview_performance.py`, **See:** `docs/specs/chronosrefine_functional_requirements.md#fr-006-preview-generation`
- [ ] Cost estimation accuracy within ±$0.01 → **Req:** **ENG-013**, **Test:** `tests/api/test_cost_estimation.py`, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-013-cost-estimation`
- [ ] Output encoding tested for all tiers → **Req:** **ENG-015**, **Test:** `tests/processing/test_output_encoding.py`, **See:** `docs/specs/chronosrefine_engineering_requirements.md#eng-015-output-encoding`

**Phase-Specific Risks:**
- **Risk**: Design system implementation diverges from specifications
  - **Mitigation**: Design review checkpoints; automated visual regression testing
- **Risk**: Real-time progress updates create performance issues
  - **Mitigation**: Use WebSockets with connection pooling; load test with 1000 concurrent users

**Rationale:** With the core backend complete, this phase focuses on building the user experience and the application logic that ties everything together.

### Phase 5: Advanced Features & UX Refinement

**Objective:** Implement security/compliance hardening, reliability controls, pricing model controls, and internationalization readiness for advanced tiers.

**Requirements Implemented:** **FR-006**, **SEC-001**, **SEC-002**, **SEC-003**, **SEC-004**, **SEC-005**, **SEC-006**, **NFR-004**, **NFR-005**, **NFR-006**, **NFR-009** (11 requirements)  
**Coverage Matrix:** See `docs/specs/ChronosRefine Requirements Coverage Matrix.md`

**Entry Criteria:**
- [ ] Phase 4 complete: User-facing features operational → **See:** `docs/specs/chronosrefine_implementation_plan.md#phase-4-user-facing-features--application-logic`
- [ ] Pricing tiers finalized with feature allocation → **Req:** **NFR-006**, **NFR-012**, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-006-pricing-model`, `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-012-payment-provider-selection`, `docs/specs/chronosrefine_prd_v9.md#pricing--business-model`
- [ ] Legal review complete for GDPR and data-handling controls → **Req:** **SEC-006**, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-006-gdpr-compliance`

**Deliverables:**
-   Preview generation system hardened for production usage → **Req:** **FR-006**, **Test:** `tests/api/test_preview.py`, **See:** `docs/specs/chronosrefine_functional_requirements.md#fr-006-preview-generation`
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
-   Completed third-party security audit with remediation verification → **Req:** **SEC-015**, **Test:** `tests/security/test_audit_remediation.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-015-third-party-security-audit`, `docs/security/Third_Party_Security_Audit_Report.pdf`
-   Successful load testing that meets all SLOs → **Req:** **NFR-002**, **Test:** `tests/load/test_production_load.py`, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-002-processing-time-slo`, `docs/specs/chronosrefine_prd_v9.md#performance-slos`
-   Log retention and PII-redaction controls validated and documented → **Req:** **SEC-009**, **Test:** `tests/security/test_log_retention_redaction.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-009-log-retention--pii-redaction`
-   Deletion proof generation and verification finalized for launch readiness → **Req:** **SEC-010**, **Test:** `tests/compliance/test_deletion_proof.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-010-deletion-proofs`
-   Dataset provenance chain and evidence model validated → **Req:** **SEC-011**, **Test:** `tests/compliance/test_dataset_provenance.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-011-dataset-provenance`
-   Data residency controls and validation reports finalized → **Req:** **SEC-012**, **Test:** `tests/ops/test_data_residency.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-012-data-residency`
-   Usability and end-user readiness checks finalized → **Req:** **NFR-008**, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-008-usability`
-   Comprehensive internal and user-facing documentation finalized → **Req:** **NFR-010**, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-010-documentation`, `docs/user_guide/`, `docs/api/`, `docs/operations/`
-   Performance monitoring dashboards, baselines, and runbooks finalized → **Req:** **OPS-004**, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#ops-004-performance-monitoring`, `docs/operations/deployment_runbook.md`, `docs/operations/rollback_runbook.md`
-   HPS validation platform and results → **Req:** **FR-007**, **Test:** `tests/hps/test_evaluation_platform.py`, `tests/hps/test_statistical_analysis.py`, **See:** `docs/specs/chronosrefine_functional_requirements.md#fr-007-human-preference-score-hps-validation`, `docs/hps/HPS_Validation_Report.md`
-   Compliance documentation package (usability/legal/security readiness) → **Req:** **NFR-008**, **SEC-015**, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-008-usability`, `docs/compliance/GDPR_Compliance_Report.md`, `docs/compliance/SOC2_Readiness_Assessment.md`

**Exit Criteria:**
- [ ] **HPS Gate**: ≥75% in EACH media category (Daguerreotype, Albumen, 16mm, Super 8, Kodachrome, VHS) → **Req:** **FR-007**, **NFR-001**, **Test:** `tests/hps/test_statistical_analysis.py`, **See:** `docs/specs/chronosrefine_functional_requirements.md#fr-007-human-preference-score-hps-validation`, `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-001-cost-estimate-display`, `docs/specs/chronosrefine_prd_v9.md#beta-exit-criteria-ga-readiness`
- [ ] Security audit complete with zero critical vulnerabilities → **Req:** **SEC-015**, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-015-third-party-security-audit`, `docs/security/Third_Party_Security_Audit_Report.pdf`
- [ ] Log retention and PII redaction controls validated in production-like environment → **Req:** **SEC-009**, **Test:** `tests/security/test_log_retention_redaction.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-009-log-retention--pii-redaction`
- [ ] Deletion proofs generated/verified for required launch scenarios → **Req:** **SEC-010**, **Test:** `tests/compliance/test_deletion_proof.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-010-deletion-proofs`
- [ ] Dataset provenance evidence chain validated for audit samples → **Req:** **SEC-011**, **Test:** `tests/compliance/test_dataset_provenance.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-011-dataset-provenance`
- [ ] Data residency controls validated for supported launch regions → **Req:** **SEC-012**, **Test:** `tests/ops/test_data_residency.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#sec-012-data-residency`
- [ ] Load testing validates 1000 concurrent users with <5% error rate → **Req:** **NFR-002**, **Test:** `tests/load/test_production_load.py`, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-002-processing-time-slo`
- [ ] All SLOs met in staging environment for 7 consecutive days → **Req:** **NFR-002**, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-002-processing-time-slo`, `docs/specs/chronosrefine_prd_v9.md#performance-slos`
- [ ] Usability acceptance checks pass for launch personas → **Req:** **NFR-008**, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-008-usability`
- [ ] User documentation complete with video tutorials for each persona → **Req:** **NFR-010**, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-010-documentation`, `docs/user_guide/`
- [ ] Performance monitoring runbook and regression detection procedures documented → **Req:** **OPS-004**, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#ops-004-performance-monitoring`, `docs/operations/runbooks/`
- [ ] Monitoring-driven rollback decision procedure tested in staging → **Req:** **OPS-004**, **Test:** `tests/ops/test_rollback.py`, **See:** `docs/specs/chronosrefine_security_operations_requirements.md#ops-004-performance-monitoring`
- [ ] Legal review complete for Terms of Service and Privacy Policy → **Req:** **NFR-008**, **SEC-006**, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-008-usability`, `docs/specs/chronosrefine_security_operations_requirements.md#sec-006-gdpr-compliance`
- [ ] SOC 2 Type II readiness assessment complete → **Req:** **NFR-008**, **SEC-015**, **See:** `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-008-usability`, `docs/specs/chronosrefine_security_operations_requirements.md#sec-015-third-party-security-audit`, `docs/compliance/SOC2_Readiness_Assessment.md`

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
