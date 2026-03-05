# ChronosRefine Non-Functional Requirements

**Purpose:** Performance, scalability, cost, and business requirements  
**Audience:** All team members, product managers, finance  
**Companion Documents:** ChronosRefine PRD (main document)  
**Last Updated:** February 2026

**Change Note (February 2026):** Applied 9-patch accuracy/completeness pack + 7-patch regression fix pack + 6-patch high-priority regression fix pack:

**Initial 9-patch pack:**
1. NFR-004 renamed to "Reliability & Availability" with realistic DB performance targets (no hardcoded 10k connections claim)
2. Health check latency fixed (1s → 100ms p95) with dual endpoints (/health, /v1/health)
3. GCS multi-region removed (single-region default for data residency compliance per SEC-012)
4. Database replication replaced with RPO/RTO targets (RPO <=15min, RTO <=60min)
5. NFR-008 progress indicators cross-referenced to Supabase Realtime (ENG-011, ENG-016)
6. NFR-012 numbering fixed (AC-NFR-011-01 → AC-NFR-012-01, DoD-NFR-011-01 → DoD-NFR-012-01)
7. NFR-012 hardcoded pricing removed (Stripe Products/Prices configuration)
8. SLO vs SLA clarification note added at top of document
9. This change note added for traceability

**Additional 7-patch regression fix pack:**
1. NFR-006 hardcoded pricing removed (replaced with 10 new ACs referencing Stripe Products/Prices configuration)
2. NFR-007 AC-NFR-007-07 hardcoded overage rate removed (now references "active configured Stripe price")
3. NFR-005 renamed to "Museum SLA & Disaster Recovery" with AC-NFR-005-00 clarifying Museum-only scope
4. NFR-005 AC-NFR-005-02 data residency fixed (us-central1/us-west1 → tenant-selected residency region + paired DR region)
5. "Pricing & Business Model" section replaced with "Pricing (Source of Truth)" referencing Stripe/PRD (removes hardcoded pricing table and "Rejected Pricing Alternative")
6. NFR-002 AC-NFR-002-01a added to clarify end-to-end SLO applies to submit → results ready
7. NFR-005 AC-NFR-005-06a added to clarify /health is infra probe, /v1/health is client-facing

**High-priority 6-patch regression fix pack:**
1. NFR-006 DoD-NFR-006-02/03 hardcoded pricing removed (30/60/500 min, $0.50/$0.40 → configuration-driven validation)
2. NFR-006 description + AC-NFR-006-10 clarified: implementation focus (not margin target), margin reporting added
3. NFR-012 DoD "plans" terminology replaced with "Products/Prices" (DoD-NFR-012-02/05/08)
4. NFR-002 AC-NFR-002-03 alerting destinations made configurable (PagerDuty/Slack → configurable per environment)
5. NFR-012 AC-NFR-012-03a/b/c added: billable unit semantics (ceiling to nearest minute, retry exclusion, reconciliation source of truth)
6. NFR-004 AC-NFR-004-10 multi-region clarified: compliant paired-region DR only, not global multi-region for Strict Residency

---

**SLO vs SLA Note:** Unless explicitly labeled "SLA", targets in this document are internal SLOs (Service Level Objectives) used for engineering and monitoring. Customer-facing SLAs (if any) are defined in contractual Museum Tier terms and may differ.

---

## Non-Functional Requirements Overview

Non-functional requirements define system qualities, performance targets, business constraints, and operational characteristics that are not directly tied to specific features but are critical for product success..

---

## Non-Functional Requirements

### NFR-001: Cost Estimate Display

**Description:** System must calculate and display accurate cost estimates before job launch to prevent bill shock and improve user trust.

**Acceptance Criteria:**
- AC-NFR-001-01: Cost estimate displayed in preview modal before job launch
- AC-NFR-001-02: Cost breakdown includes: GPU time, storage, API calls, total
- AC-NFR-001-03: Cost estimate updates dynamically when user changes settings (resolution, mode, era profile)
- AC-NFR-001-04: Estimate accuracy target: 90% of jobs have error <15%, 95% have error <20%
- AC-NFR-001-05: Estimate calculation latency <1s for 95th percentile
- AC-NFR-001-06: Estimate includes overage rate if monthly limit exceeded
- AC-NFR-001-07: Estimate model trained on historical job data (updated monthly)
- AC-NFR-001-08: Estimate confidence interval displayed (e.g., "$12.50 ± $1.80")
- AC-NFR-001-09: Actual cost tracked and compared to estimate (reconciliation report)
- AC-NFR-001-10: Outliers flagged for investigation and estimate model refinement

**Definition of Done:**
- DoD-NFR-001-01: Cost estimate calculation tested with 100+ sample jobs
- DoD-NFR-001-02: Cost breakdown tested (GPU time, storage, API calls)
- DoD-NFR-001-03: Dynamic estimate updates tested (settings changes)
- DoD-NFR-001-04: Estimate accuracy verified (90% <15% error, 95% <20% error)
- DoD-NFR-001-05: Estimate calculation latency <1s verified
- DoD-NFR-001-06: Overage rate inclusion tested (monthly limit exceeded)
- DoD-NFR-001-07: Estimate model trained on historical data (monthly updates)
- DoD-NFR-001-08: Confidence interval tested (displayed correctly)
- DoD-NFR-001-09: Reconciliation report tested (estimate vs actual)
- DoD-NFR-001-10: Outlier detection tested (flagged for investigation)
- DoD-NFR-001-11: Code review approved by 2+ engineers

**Verification Method:** Automated (pytest unit tests) + Manual (reconciliation report analysis)

**Test Files:**
- `tests/api/test_cost_estimation.py`
- `tests/api/test_cost_breakdown.py`
- `tests/integration/test_cost_reconciliation.py`

**Related Requirements:** ENG-013 (Cost Estimation), NFR-003 (Cost Optimization), FR-006 (Preview Generation)

---

### NFR-002: Processing Time SLO

**Description:** System must meet processing time Service Level Objective (SLO) of p95 <2x video duration to ensure acceptable user experience.

**Acceptance Criteria:**
- AC-NFR-002-01: Processing time SLO: p95 <2x video duration (e.g., 10-minute video processes in <20 minutes)
- AC-NFR-002-01a: Clarification: This SLO applies to **end-to-end job completion time** (submit → results ready). Stage-level targets (e.g., encoding) must be budgeted so the sum of stages still meets the end-to-end SLO.
- AC-NFR-002-02: Processing time tracked per job and reported to monitoring dashboard
- AC-NFR-002-03: SLO violations trigger alerts to configured alert sinks (default: PagerDuty for critical alerts, Slack for warnings; configurable per environment).
- AC-NFR-002-04: Processing time breakdown tracked: upload, era detection, processing, encoding, download
- AC-NFR-002-05: GPU pool pre-warming reduces cold-start latency to <120s (p99)
- AC-NFR-002-06: Autoscaler maintains minimum warm pool size based on demand forecast
- AC-NFR-002-07: Processing time optimization: cache hit rate >40% for duplicate jobs
- AC-NFR-002-08: Processing time regression detection: automated alerts when p95 degrades >10%
- AC-NFR-002-09: Processing time SLO compliance tracked monthly (error budget)
- AC-NFR-002-10: Processing time SLO included in Museum Tier SLA

**Definition of Done:**
- DoD-NFR-002-01: Processing time SLO tracked (p95 <2x video duration)
- DoD-NFR-002-02: Processing time reported to monitoring dashboard
- DoD-NFR-002-03: SLO violation alerts tested (configurable alert sinks: PagerDuty for critical, Slack for warnings)
- DoD-NFR-002-04: Processing time breakdown tracked (5 stages)
- DoD-NFR-002-05: GPU pool pre-warming tested (cold-start <120s p99)
- DoD-NFR-002-06: Autoscaler tested (minimum warm pool maintained)
- DoD-NFR-002-07: Cache hit rate tested (>40% for duplicate jobs)
- DoD-NFR-002-08: Regression detection tested (alerts for >10% degradation)
- DoD-NFR-002-09: SLO compliance tracked monthly (error budget)
- DoD-NFR-002-10: SLO included in Museum Tier SLA
- DoD-NFR-002-11: Code review approved by 2+ engineers

**Verification Method:** Automated (pytest integration tests + load testing) + Manual (SLO dashboard verification)

**Test Files:**
- `tests/ops/test_processing_time_slo.py`
- `tests/load/test_processing_time.py`
- `tests/ops/test_slo_compliance.py`

**Related Requirements:** ENG-008 (GPU Pool Management), ENG-009 (Deduplication Cache), OPS-002 (SLO Monitoring)

---

### NFR-003: Cost Optimization

**Description:** System must optimize infrastructure costs to achieve 60% gross margin target while maintaining performance and quality.

**Acceptance Criteria:**
- AC-NFR-003-01: GPU utilization target: >70% (cost optimization)
- AC-NFR-003-02: Cache hit rate target: >40% for duplicate jobs (reduces GPU costs)
- AC-NFR-003-03: Autoscaler scales down when idle for >5 minutes (reduces idle costs)
- AC-NFR-003-04: Storage lifecycle management: automatic deletion of expired data (reduces storage costs)
- AC-NFR-003-05: API cost optimization: batch Gemini requests when possible
- AC-NFR-003-06: Cost tracking per job: GPU time, storage, API calls (enables margin analysis)
- AC-NFR-003-07: Cost monitoring dashboard: real-time cost metrics and margin tracking
- AC-NFR-003-08: Cost anomaly detection: automated alerts when costs spike >20%
- AC-NFR-003-09: Cost optimization recommendations generated quarterly
- AC-NFR-003-10: Target gross margin: >60% across all tiers

**Definition of Done:**
- DoD-NFR-003-01: GPU utilization >70% verified (monitoring dashboard)
- DoD-NFR-003-02: Cache hit rate >40% verified (duplicate jobs)
- DoD-NFR-003-03: Autoscaler tested (scales down after 5 min idle)
- DoD-NFR-003-04: Storage lifecycle management tested (automatic deletion)
- DoD-NFR-003-05: API cost optimization tested (batch Gemini requests)
- DoD-NFR-003-06: Cost tracking tested per job (GPU, storage, API)
- DoD-NFR-003-07: Cost monitoring dashboard created (real-time metrics)
- DoD-NFR-003-08: Cost anomaly detection tested (alerts for >20% spikes)
- DoD-NFR-003-09: Cost optimization recommendations generated (quarterly)
- DoD-NFR-003-10: Gross margin >60% verified (financial reporting)
- DoD-NFR-003-11: Code review approved by 2+ engineers

**Verification Method:** Automated (pytest integration tests) + Manual (cost dashboard verification + financial reporting)

**Test Files:**
- `tests/ops/test_cost_optimization.py`
- `tests/ops/test_gpu_utilization.py`
- `tests/ops/test_cost_tracking.py`

**Related Requirements:** ENG-008 (GPU Pool Management), ENG-009 (Deduplication Cache), NFR-001 (Cost Estimate Display)

---

### NFR-004: Reliability & Availability

**Description:** System must meet availability targets per tier and scale to support expected production volumes without performance degradation.

**Acceptance Criteria:**
- AC-NFR-004-01: Availability targets:
  - Hobbyist: best-effort (no SLA)
  - Pro: 99.9% monthly availability goal (internal SLO)
  - Museum: 99.9% monthly availability goal (SLO); SLA to be defined separately
- AC-NFR-004-02: Downtime reference: 99.9% ≈ 43.2 minutes/month (informational)
- AC-NFR-004-03: Database performance (Supabase Postgres):
  - Top 10 queries p95 <100ms at expected production volumes (document assumptions)
  - Connection pooling enabled; max concurrent DB connections validated under load test (define target concurrency in test plan; do not hardcode specific numbers)
  - Database query performance benchmarks documented and monitored
- AC-NFR-004-04: Storage scaling:
  - Media scaling handled by GCS; database stores pointers/metadata only (per ENG-016)
  - Define an explicit growth envelope (e.g., jobs/day, manifests/day, log volume) and test against that
- AC-NFR-004-05: Job recovery:
  - Job processing failures (e.g., GPU failure) must recover automatically with retry mechanism
  - Retry/backoff/isolation semantics defined in ENG-012
- AC-NFR-004-06: Horizontal scaling: API layer scales via Cloud Run autoscaling based on demand
- AC-NFR-004-07: GPU pool scaling: autoscaler provisions GPU instances based on queue depth and demand forecast
- AC-NFR-004-08: Scalability monitoring: real-time metrics for active users, active jobs, GPU pool size
- AC-NFR-004-09: Scalability limits documented: maximum concurrent users, jobs, GPU instances (based on load testing results)
- AC-NFR-004-10: Scalability roadmap: plan for scaling beyond initial targets (sharding, multi-region). Note: multi-region scaling is limited to compliant paired-region DR (NFR-005) for Museum tier; global multi-region storage/processing is not supported for Strict Residency tenants (SEC-012).

**Definition of Done:**
- DoD-NFR-004-01: Availability targets documented per tier (Hobbyist/Pro/Museum)
- DoD-NFR-004-02: Database query performance benchmarked (top 10 queries p95 <100ms)
- DoD-NFR-004-03: Connection pooling tested under load (target concurrency defined in test plan)
- DoD-NFR-004-04: Storage scaling architecture documented (GCS for media, DB for metadata)
- DoD-NFR-004-05: Growth envelope defined and tested (jobs/day, manifests/day, log volume)
- DoD-NFR-004-06: Job retry mechanism tested (GPU failures, network errors)
- DoD-NFR-004-07: Horizontal scaling tested (API layer autoscaling)
- DoD-NFR-004-08: GPU pool autoscaling tested (queue depth-based provisioning)
- DoD-NFR-004-09: Scalability monitoring dashboard created
- DoD-NFR-004-10: Scalability limits documented (based on load testing)
- DoD-NFR-004-11: Scalability roadmap created
- DoD-NFR-004-12: Code review approved by 2+ engineers

**Verification Method:** Automated (load testing) + Manual (scalability dashboard verification)

**Test Files:**
- `tests/ops/test_availability_slo.py`
- `tests/ops/test_database_performance.py`
- `tests/ops/test_job_retry.py`
- `tests/load/test_scalability.py`

**Related Requirements:** ENG-008 (GPU Pool Management), ENG-012 (Job Retry Logic), ENG-016 (Database Technology Selection), OPS-001 (Monitoring & Alerting), OPS-004 (Performance Monitoring)

---

### NFR-005: Museum SLA & Disaster Recovery

**Description:** For Museum Tier only, the system must meet a customer-facing availability SLA and implement a tested Disaster Recovery (DR) posture aligned to data residency constraints.

**Acceptance Criteria:**
- AC-NFR-005-00: Scope: Museum tier only. Pro/Hobbyist availability targets are defined in NFR-004 as internal SLOs.
- AC-NFR-005-01: Availability SLA: 99.9% uptime for Museum Tier (43.2 minutes downtime per month)
- AC-NFR-005-02: Multi-region DR (Museum): primary region = tenant-selected residency region; DR region = an approved paired region within the same compliance boundary. Region pairs must be documented (e.g., US pair, EU pair) and must not violate SEC-012.
- AC-NFR-005-03: Disaster Recovery objectives (Museum tier):
  - RPO target: <= 15 minutes
  - RTO target: <= 60 minutes
- AC-NFR-005-04: DR implementation may use provider-supported HA/replication features, logical replication, backups + restore drills, or an approved managed DR pattern. Run DR drills at least quarterly; document results and gaps.
- AC-NFR-005-05: Storage residency: GCS buckets must be **single-region** by default, aligned to the tenant's selected data residency region (SEC-012). Multi-region storage (if ever offered) must be explicitly incompatible with Strict Residency Mode and must be opt-in per tenant with compliance review.
- AC-NFR-005-06: Health check endpoints must respond within 100ms (p95):
  - GET /health (infra probe, minimal JSON {"status":"ok"})
  - GET /v1/health (client health, detailed JSON)
- AC-NFR-005-06a: `/health` is an infra probe endpoint and may be restricted from public access; `/v1/health` is the client-facing health endpoint defined in the OpenAPI spec.
- AC-NFR-005-07: Monitoring: uptime tracking via Cloud Monitoring + external monitoring (Pingdom/UptimeRobot)
- AC-NFR-005-08: Incident response: on-call rotation with PagerDuty for critical alerts
- AC-NFR-005-09: Disaster recovery testing: quarterly DR drills to verify failover procedures
- AC-NFR-005-10: Availability reporting: monthly uptime reports for Museum Tier customers

**Definition of Done:**
- DoD-NFR-005-01: Availability SLA documented (99.9% uptime Museum Tier)
- DoD-NFR-005-02: Multi-region deployment tested (primary + DR region)
- DoD-NFR-005-03: DR objectives documented (RPO <=15min, RTO <=60min)
- DoD-NFR-005-04: DR implementation tested (quarterly drills, results documented)
- DoD-NFR-005-05: Storage residency tested (GCS single-region buckets aligned to tenant region)
- DoD-NFR-005-06: Health checks tested (/health and /v1/health respond <100ms p95)
- DoD-NFR-005-07: Monitoring tested (Cloud Monitoring + external monitoring)
- DoD-NFR-005-08: Incident response tested (on-call rotation + PagerDuty)
- DoD-NFR-005-09: DR testing completed (quarterly DR drills)
- DoD-NFR-005-10: Availability reporting tested (monthly uptime reports)
- DoD-NFR-005-11: Code review approved by 2+ engineers

**Verification Method:** Automated (integration tests + DR drills) + Manual (availability dashboard verification)

**Test Files:**
- `tests/ops/test_availability.py`
- `tests/ops/test_failover.py`
- `tests/ops/test_disaster_recovery.py`

**Related Requirements:** OPS-001 (Monitoring & Alerting), OPS-003 (Incident Response)

---

### NFR-006: Pricing Model

**Description:** System must implement hybrid subscription + usage pricing model with configuration-driven pricing (Stripe Products/Prices) to enable flexible pricing changes without code deployments.

**Acceptance Criteria:**
- AC-NFR-006-01: Pricing tiers (Hobbyist/Pro/Museum) must be defined and managed in **Stripe Products/Prices** (and referenced by IDs in config), not hardcoded in application logic.
- AC-NFR-006-02: Included-usage entitlements (e.g., minutes/month) are sourced from the active Stripe price configuration and/or internal commercial configuration (PRD), not hardcoded.
- AC-NFR-006-03: Overage rates are sourced from the active Stripe price configuration and/or internal commercial configuration (PRD), not hardcoded.
- AC-NFR-006-04: Pricing enforcement: users cannot exceed monthly limit without explicit overage approval (see NFR-007).
- AC-NFR-006-05: Stripe integration: subscriptions, usage-based billing, invoicing, and customer portal are implemented per NFR-012.
- AC-NFR-006-06: Museum tier supports custom enterprise pricing via Stripe pricing overrides/quotes (commercial process).
- AC-NFR-006-07: Pricing transparency: the UI must show the **effective** configured price and overage rates prior to job launch, derived from current configuration.
- AC-NFR-006-08: Pricing configuration changes must not require code changes or deployments (configuration-only change).
- AC-NFR-006-09: Pricing configuration changes are audited (who/when/what), including Stripe event IDs.
- AC-NFR-006-10: Margin reporting: system must track actual costs (GPU, storage, API) and revenue per job to enable gross margin analysis (target: >60% across tiers, see NFR-003). Margin calculations must use current configured prices/costs.

**Definition of Done:**
- DoD-NFR-006-01: All 3 pricing tiers implemented (Hobbyist/Pro/Museum)
- DoD-NFR-006-02: Included-usage entitlements tested: system correctly retrieves entitlements from Stripe price configuration and/or internal commercial config (PRD), and pricing changes via Stripe require no code deployment.
- DoD-NFR-006-03: Overage rates tested: system correctly retrieves overage rates from Stripe price configuration and/or internal commercial config (PRD), and pricing changes via Stripe require no code deployment.
- DoD-NFR-006-04: Pricing enforcement tested (hard stop without overage approval)
- DoD-NFR-006-05: Overage approval workflow tested (in-app + email notifications)
- DoD-NFR-006-06: Stripe integration tested (payment processing)
- DoD-NFR-006-07: Usage tracking tested (minute-level accuracy)
- DoD-NFR-006-08: Invoice generation tested (monthly invoices with breakdown)
- DoD-NFR-006-09: Pricing transparency tested (cost estimate before job launch)
- DoD-NFR-006-10: Custom enterprise pricing documented (Museum Tier)
- DoD-NFR-006-11: Code review approved by 2+ engineers + finance review

**Verification Method:** Automated (pytest integration tests) + Manual (finance review + billing verification)

**Test Files:**
- `tests/billing/test_pricing_tiers.py`
- `tests/billing/test_overage_approval.py`
- `tests/billing/test_stripe_integration.py`
- `tests/billing/test_usage_tracking.py`

**Related Requirements:** NFR-001 (Cost Estimate Display), NFR-003 (Cost Optimization), NFR-007 (Cost Control Requirements)

---

### NFR-007: Cost Control Requirements

**Description:** System must implement cost control mechanisms to prevent unexpected charges and improve user trust.

**Acceptance Criteria:**
- AC-NFR-007-01: Cost estimate displayed before job launch (REQ-501)
- AC-NFR-007-02: Hard stop when monthly limit exceeded without overage approval (REQ-502)
- AC-NFR-007-03: Overage transparency: user receives notification when approaching limit (80%, 90%, 100%) (REQ-503)
- AC-NFR-007-04: Estimate accuracy target: 90% of jobs have error <15%, 95% have error <20% (REQ-504)
- AC-NFR-007-05: Overage approval workflow: explicit user confirmation required before exceeding limit
- AC-NFR-007-06: Overage approval options: approve once, approve for month, upgrade tier
- AC-NFR-007-07: Overage rate displayed clearly using the **active configured Stripe price** (no hardcoded dollar amounts).
- AC-NFR-007-08: Monthly usage dashboard: real-time usage tracking with remaining credits
- AC-NFR-007-09: Usage alerts: email notifications at 80%, 90%, 100% of monthly limit
- AC-NFR-007-10: Cost reconciliation: monthly report comparing estimated vs actual costs

**Definition of Done:**
- DoD-NFR-007-01: Cost estimate tested (displayed before job launch)
- DoD-NFR-007-02: Hard stop tested (monthly limit exceeded without approval)
- DoD-NFR-007-03: Overage transparency tested (notifications at 80%, 90%, 100%)
- DoD-NFR-007-04: Estimate accuracy verified (90% <15% error, 95% <20% error)
- DoD-NFR-007-05: Overage approval workflow tested (explicit user confirmation)
- DoD-NFR-007-06: Overage approval options tested (once, month, upgrade)
- DoD-NFR-007-07: Overage rate tested (displayed clearly)
- DoD-NFR-007-08: Monthly usage dashboard tested (real-time tracking)
- DoD-NFR-007-09: Usage alerts tested (email notifications at thresholds)
- DoD-NFR-007-10: Cost reconciliation tested (monthly report)
- DoD-NFR-007-11: Code review approved by 2+ engineers

**Verification Method:** Automated (pytest integration tests) + Manual (user acceptance testing)

**Test Files:**
- `tests/billing/test_cost_control.py`
- `tests/billing/test_overage_approval.py`
- `tests/billing/test_usage_alerts.py`

**Related Requirements:** NFR-001 (Cost Estimate Display), NFR-006 (Pricing Model), ENG-013 (Cost Estimation)

---

### NFR-008: Usability

**Description:** System must provide intuitive user experience with <5 clicks to launch a restoration job and <10 minute onboarding time.

**Acceptance Criteria:**
- AC-NFR-008-01: Job launch workflow: <5 clicks from upload to job launch
- AC-NFR-008-02: Onboarding time: <10 minutes for new users to complete first job
- AC-NFR-008-03: Error messages: user-friendly, actionable error messages (no raw JSON Schema errors)
- AC-NFR-008-04: Progress indicators: real-time progress updates during processing. Real-time progress delivery should use Supabase Realtime as canonical; fallback to polling if unavailable (ENG-011, ENG-016).
- AC-NFR-008-05: Preview generation: 10 scene-aware keyframes in <6s (p95)
- AC-NFR-008-06: Fidelity tier selection: clear visual comparison of Enhance/Restore/Conserve modes
- AC-NFR-008-07: Era detection: auto-suggest era profile with confidence score
- AC-NFR-008-08: Uncertainty Callouts: clear explanations for low-confidence decisions
- AC-NFR-008-09: Help documentation: in-app tooltips and help links for all features
- AC-NFR-008-10: Accessibility: WCAG 2.1 AA compliance (keyboard navigation, screen reader support, color contrast)

**Definition of Done:**
- DoD-NFR-008-01: Job launch workflow tested (<5 clicks verified)
- DoD-NFR-008-02: Onboarding time tested (<10 min for first job)
- DoD-NFR-008-03: Error messages tested (user-friendly, actionable)
- DoD-NFR-008-04: Progress indicators tested (real-time updates)
- DoD-NFR-008-05: Preview generation tested (<6s p95)
- DoD-NFR-008-06: Fidelity tier selection tested (visual comparison)
- DoD-NFR-008-07: Era detection tested (auto-suggest with confidence)
- DoD-NFR-008-08: Uncertainty Callouts tested (clear explanations)
- DoD-NFR-008-09: Help documentation tested (in-app tooltips + help links)
- DoD-NFR-008-10: Accessibility tested (WCAG 2.1 AA compliance)
- DoD-NFR-008-11: Code review approved by 2+ engineers + UX review

**Verification Method:** Automated (pytest integration tests + accessibility testing) + Manual (user acceptance testing)

**Test Files:**
- `tests/ui/test_job_launch_workflow.py`
- `tests/ui/test_onboarding.py`
- `tests/ui/test_accessibility.py`

**Related Requirements:** DS-001 through DS-006 (Design Requirements), FR-001 through FR-006 (Functional Requirements)

---

### NFR-009: Internationalization (i18n)

**Description:** System must support UTF-8 encoding for non-English metadata and provide multi-language UI support (roadmap: GA+6 months).

**Acceptance Criteria:**
- AC-NFR-009-01: UTF-8 encoding supported for all user-facing text fields
- AC-NFR-009-02: Transformation Manifest supports UTF-8 metadata (description, notes, custom_metadata)
- AC-NFR-009-03: Job names support UTF-8 characters
- AC-NFR-009-04: Era profile overrides support UTF-8 descriptions
- AC-NFR-009-05: Uncertainty Callout notes support UTF-8
- AC-NFR-009-06: UI translation support (roadmap: French, German, Spanish at GA+6 months)
- AC-NFR-009-07: UI translation support (roadmap: Mandarin Chinese, Japanese at GA+12 months)
- AC-NFR-009-08: Language selection persists across sessions
- AC-NFR-009-09: Date/time formatting localized per user locale
- AC-NFR-009-10: Number formatting localized per user locale (decimal separators, currency)

**Definition of Done:**
- DoD-NFR-009-01: UTF-8 encoding tested (all user-facing text fields)
- DoD-NFR-009-02: Transformation Manifest tested (UTF-8 metadata)
- DoD-NFR-009-03: Job names tested (UTF-8 characters)
- DoD-NFR-009-04: Era profile overrides tested (UTF-8 descriptions)
- DoD-NFR-009-05: Uncertainty Callout notes tested (UTF-8)
- DoD-NFR-009-06: UI translation framework implemented (i18next or similar)
- DoD-NFR-009-07: Language selection tested (persists across sessions)
- DoD-NFR-009-08: Date/time formatting tested (localized per locale)
- DoD-NFR-009-09: Number formatting tested (localized per locale)
- DoD-NFR-009-10: Translation roadmap documented (French/German/Spanish at GA+6, Mandarin/Japanese at GA+12)
- DoD-NFR-009-11: Code review approved by 2+ engineers

**Verification Method:** Automated (pytest integration tests) + Manual (translation verification)

**Test Files:**
- `tests/i18n/test_utf8_encoding.py`
- `tests/i18n/test_ui_translation.py`
- `tests/i18n/test_localization.py`

**Related Requirements:** SEC-012 (Data Residency), DS-001 through DS-006 (Design Requirements)

---

### NFR-010: Documentation

**Description:** System must provide comprehensive documentation for developers, users, and institutional customers.

**Acceptance Criteria:**
- AC-NFR-010-01: API documentation: OpenAPI 3.0 specification with Swagger UI
- AC-NFR-010-02: Developer documentation: setup guide, architecture overview, contribution guidelines
- AC-NFR-010-03: User documentation: getting started guide, feature tutorials, FAQ
- AC-NFR-010-04: Institutional documentation: compliance documentation (GDPR, SOC 2), DPA template, audit trail guide
- AC-NFR-010-05: Operations documentation: runbooks for common incidents, deployment guide, monitoring guide
- AC-NFR-010-06: Security documentation: security best practices, encryption guide, access control guide
- AC-NFR-010-07: Documentation versioning: documentation versioned with product releases
- AC-NFR-010-08: Documentation search: full-text search across all documentation
- AC-NFR-010-09: Documentation feedback: users can submit feedback on documentation quality
- AC-NFR-010-10: Documentation maintenance: quarterly documentation review and updates

**Definition of Done:**
- DoD-NFR-010-01: API documentation created (OpenAPI 3.0 + Swagger UI)
- DoD-NFR-010-02: Developer documentation created (setup, architecture, contribution)
- DoD-NFR-010-03: User documentation created (getting started, tutorials, FAQ)
- DoD-NFR-010-04: Institutional documentation created (compliance, DPA, audit trail)
- DoD-NFR-010-05: Operations documentation created (runbooks, deployment, monitoring)
- DoD-NFR-010-06: Security documentation created (best practices, encryption, access control)
- DoD-NFR-010-07: Documentation versioning tested (versioned with releases)
- DoD-NFR-010-08: Documentation search tested (full-text search)
- DoD-NFR-010-09: Documentation feedback tested (users can submit feedback)
- DoD-NFR-010-10: Documentation maintenance scheduled (quarterly reviews)
- DoD-NFR-010-11: Code review approved by 2+ engineers + technical writer review

**Verification Method:** Manual (documentation review + user feedback)

**Test Files:**
- N/A (manual verification via documentation review)

**Related Requirements:** ENG-002 (API Endpoint Implementation), SEC-006 (GDPR Compliance), OPS-003 (Incident Response)

---

### NFR-011: Reserved for Future Use

---

### NFR-012: Payment Provider Selection

**Description:** System must integrate with Stripe as the primary payment provider, supporting subscription billing, usage-based billing (overage charges), payment method management, and invoice generation for Pro and Museum tier customers.

**Acceptance Criteria:**
- AC-NFR-012-01: Stripe account configured with production API keys (publishable key, secret key)
- AC-NFR-012-02: Pricing configuration must be managed via Stripe Products/Prices; do not hardcode pricing in code. Pricing and included-usage values are defined in the PRD/commercial configuration and may change without code changes.
- AC-NFR-012-03: The system must correctly meter billable usage and apply the active Stripe price configuration.
- AC-NFR-012-03a: Billable unit: processing time is metered in **seconds** and rounded **up to the nearest minute** (ceiling function) per job. Minimum billable unit is 1 minute per job.
- AC-NFR-012-03b: Retry/idempotency: failed job retries (e.g., GPU failure, transient errors) do not count toward billable usage. Only successful job completions are metered. Retries are tracked separately for cost analysis.
- AC-NFR-012-03c: Reconciliation source of truth: billable usage is calculated from job completion timestamps (job_started_at → job_completed_at) stored in the database. Segment-level timestamps are for internal monitoring only, not billing.
- AC-NFR-012-04: Payment method management supported (credit card, debit card, ACH for Museum tier)
- AC-NFR-012-05: Subscription lifecycle managed (create, update, cancel, reactivate)
- AC-NFR-012-06: Invoice generation automated (monthly invoices, overage invoices)
- AC-NFR-012-07: Payment retry logic implemented (failed payment retry, dunning emails)
- AC-NFR-012-08: Webhook integration configured (payment success, payment failure, subscription updates)
- AC-NFR-012-09: Tax calculation integrated (Stripe Tax for automated tax calculation)
- AC-NFR-012-10: PCI DSS compliance verified (Stripe handles card data, no card data stored in ChronosRefine)
- AC-NFR-012-11: Customer portal enabled (self-service billing management via Stripe Customer Portal)
- AC-NFR-012-12: Payment analytics tracked (MRR, churn rate, overage revenue)

**Definition of Done:**
- DoD-NFR-012-01: Stripe account configured: production API keys secured in environment variables (publishable key, secret key), Stripe account verified (business information, bank account connected), webhook signing secret configured
- DoD-NFR-012-02: Pricing configuration via Stripe Products/Prices (no hardcoded pricing in code), pricing configuration tested with 30+ scenarios (subscription creation, pricing changes, cancellation), pricing changes tested (update Stripe price configuration without code changes)
- DoD-NFR-012-03: Usage-based billing configured: overage metering implemented (processing minutes tracked in real-time), overage charges calculated using active Stripe price configuration, overage billing tested with 40+ scenarios (overage calculation, invoice generation, payment collection)
- DoD-NFR-012-04: Payment method management tested: credit card payment tested (Stripe Elements integration, 3D Secure support), debit card payment tested, ACH payment tested (Museum tier only, 5-7 day settlement), payment method update tested (25+ scenarios)
- DoD-NFR-012-05: Subscription lifecycle tested: subscription creation tested (50+ scenarios, including trial periods, promo codes), subscription update tested (pricing tier upgrade, pricing tier downgrade, proration), subscription cancellation tested (immediate cancellation, end-of-period cancellation), subscription reactivation tested (15+ scenarios)
- DoD-NFR-012-06: Invoice generation tested: monthly invoices generated automatically (subscription charges + overage charges), invoice PDF generated (Stripe-hosted invoice), invoice email sent to customers (30+ scenarios), invoice payment status tracked (paid, unpaid, overdue)
- DoD-NFR-012-07: Payment retry logic implemented: failed payment retry configured (3 retry attempts over 7 days), dunning emails sent (payment failure notification, retry reminders, final notice), retry logic tested with 30+ scenarios (temporary card decline, insufficient funds, expired card)
- DoD-NFR-012-08: Webhook integration tested: payment success webhook handled (subscription activated, invoice marked paid), payment failure webhook handled (subscription suspended, dunning email sent), subscription update webhook handled (pricing tier change, cancellation), webhook signature verification tested (security), webhook retry logic tested (webhook delivery failure)
- DoD-NFR-012-09: Tax calculation tested: Stripe Tax integrated (automated tax calculation for US, EU, and other regions), tax rates applied correctly (sales tax, VAT, GST), tax exemption supported (Museum tier with tax-exempt certificate), tax reporting tested (tax summary on invoices, tax reports for accounting)
- DoD-NFR-012-10: PCI DSS compliance verified: Stripe handles all card data (no card data stored in ChronosRefine database), Stripe Elements used for card input (PCI-compliant iframe), PCI compliance attestation obtained (Stripe SAQ A)
- DoD-NFR-012-11: Customer portal tested: Stripe Customer Portal enabled (self-service billing management), portal tested with 40+ scenarios (view invoices, update payment method, cancel subscription, download receipts), portal customization tested (branding, allowed actions)
- DoD-NFR-012-12: Payment analytics implemented: MRR (Monthly Recurring Revenue) tracked (dashboard visualization), churn rate tracked (subscription cancellations), overage revenue tracked (usage-based billing revenue), analytics tested with 20+ scenarios (data accuracy, dashboard performance)
- DoD-NFR-012-13: Stripe integration tested: 200+ integration test scenarios (subscription lifecycle, payment methods, invoicing, webhooks, tax calculation, customer portal), error handling tested (API errors, network errors, rate limits), idempotency tested (duplicate request prevention)
- DoD-NFR-012-14: Code review approved by 2+ engineers with payment integration checklist (API key security, webhook security, error handling, idempotency, PCI compliance)
- DoD-NFR-012-15: Security audit passed: API key security verified (no hardcoded keys, environment variables only), webhook signature verification verified (HMAC-SHA256), payment data security verified (no card data stored)

**Verification Method:** Automated (integration tests + webhook tests) + Manual (payment flow testing + security audit)

**Test Files:**
- `tests/billing/test_stripe_integration.py`
- `tests/billing/test_subscription_lifecycle.py`
- `tests/billing/test_usage_based_billing.py`
- `tests/billing/test_payment_methods.py`
- `tests/billing/test_invoice_generation.py`
- `tests/billing/test_payment_retry.py`
- `tests/billing/test_stripe_webhooks.py`
- `tests/billing/test_tax_calculation.py`
- `tests/billing/test_customer_portal.py`

**Related Requirements:** NFR-006 (Pricing Model), NFR-007 (Cost Control Requirements), SEC-001 (Data Encryption at Rest), SEC-002 (Data Encryption in Transit)

**Implementation Guidance:**
- 📄 **Stripe Setup:** `docs/specs/chronosrefine_implementation_plan.md#phase-1-foundation--core-infrastructure` (to be cross-referenced)
- 📄 **Subscription Plans:** `docs/specs/chronosrefine_prd_v9.md#pricing--business-model`
- 📄 **Usage Metering:** `companion_docs/ChronosRefine_Billing_Spec.md` (to be created)
- 📄 **Webhook Handlers:** `companion_docs/ChronosRefine_Stripe_Webhooks.md` (to be created)

---

## Pricing (Source of Truth)

Pricing, included usage, and overage rates are defined in the PRD/commercial configuration and implemented via Stripe Products/Prices (see NFR-012). This NFR document intentionally does not hardcode pricing values to prevent drift.

---

## References

- Cloud Run Pricing: https://cloud.google.com/run/pricing
- GCS Pricing: https://cloud.google.com/storage/pricing
- Vertex AI GPU Pricing: https://cloud.google.com/vertex-ai/pricing
- Stripe Pricing: https://stripe.com/pricing

---

**End of Non-Functional Requirements**
