# ChronosRefine: Engineering Requirements (Reviewed + Corrected)

**Purpose:** Technical implementation, architecture, and infrastructure requirements  
**Audience:** Backend engineers, ML engineers, DevOps/SRE  
**Companion Documents:** No separate engineering companion spec is checked in on `main`; use this canonical file plus repo-local implementation artifacts such as `docs/api/openapi.yaml`.  
**Last Updated:** February 2026  
**Change Note (this revision):** Corrected Supabase/Auth consistency, aligned tier thresholds + metric definitions with Functional Requirements, fixed API endpoint count/table, and tempered a few DB performance claims while keeping intent.

**Repo Note:** Test-file references for requirements not yet implemented on `main` are canonical target mappings and may not exist until the corresponding phase lands.

**Change Note (final revision - Feb 12, 2026):** Applied 5 critical Codex alignment recommendations: (1) Chose Prometheus as canonical metrics format, (2) 22 Phase 1 endpoints; 2 deferred to Phase 2, (3) Enhanced idempotency hash with fidelity_tier + processing_mode, (4) Added model_version + prompt_version to job_era_detections schema, (5) Chose Supabase Realtime as canonical real-time update approach.

**Change Note (security hardening - Feb 12, 2026):** Fixed 3 critical gotchas: (1) Explicit authorization patterns for JWT/RLS vs service-role key usage (prevents silent security regression), (2) Added canonical source note to ENG-005 to prevent threshold drift, (3) Hardened ENG-006 latency requirement with concrete <2s per segment budget. Sampling density MAY be reduced dynamically to maintain latency budget under load.

**Change Note (final consistency pass - Feb 12, 2026):** Fixed 2 remaining issues: (1) Aligned ENG-011 AC-ENG-011-02 with ENG-016's Supabase Realtime canonical choice (was WebSocket/SSE), (2) Clarified ENG-006 AC-ENG-006-07 latency budget applies to 10s default segment with linear scaling for different durations.

**Change Note (accuracy/completeness fixes - Feb 12, 2026):** Applied 6 critical fixes: (1) Added API Hosting Decision section (Cloud Run service for REST API, Edge Functions deferred to Phase 2), (2) Expanded idempotency hash to include source_asset_checksum + segment boundaries + config_hash (prevents cache collisions), (3) Added Supabase Realtime event contract with explicit channel/payload schema (AC-ENG-011-11), (4) Added deterministic sampling protocol for latency budget compliance (AC-ENG-006-11: 10-20 frames/segment, 720p downscale, L4 GPU assumption), (5) Expanded job_era_detections schema with audit fields (source, raw_response_gcs_uri, created_by) + indexes, (6) Updated health check to support dual endpoints (/health for infra probes, /v1/health for API clients).

**Change Note (final regression fixes - Feb 12, 2026):** Applied 7 remaining fixes: (1) Added GET /health to API endpoints table (count updated to 22), (2) Fixed /metrics path inconsistency (changed API Hosting Decision to /v1/metrics), (3) Clarified Realtime mode as Broadcast in AC-ENG-011-11, (4) Added Realtime subscription authorization (AC-ENG-011-12: prevents users from subscribing to other users' job progress channels - critical security fix), (5) Removed job_id from idempotency hash to enable cross-job deduplication per ENG-009, (6) Added ROI selection rule to AC-ENG-006-11 (center crop with coordinates in manifest), (7) Fixed created_by reference to auth.users(id) in job_era_detections schema.

**Change Note (accuracy/regression fixes - Feb 12, 2026):** Applied 7 critical accuracy/regression fixes: (1) Added user_id to idempotency hash to prevent cross-user cache leakage (critical privacy fix - reverted partial change from previous session), (2-4) Corrected AC-ENG-011-12 Realtime authorization description (authorization enforced by Supabase Realtime at join time, not backend; policies on realtime.messages, not jobs; error via subscribe callback, not HTTP 403), (5) Added note about center crop ROI limitation (edge artifacts not captured), (6) Split health check SLOs (GET /health: 50ms shallow, GET /v1/health: 500ms deep with dependency checks), (7) Added CHECK constraint to job_era_detections.source field for audit integrity.

**Change Note (patch pack v3 - Feb 12, 2026):** Applied 7 patch fixes for internal consistency and completeness: (1) Updated endpoint count from 21 to 22 in change note (consistency fix), (2) Added explicit requirement for both /health endpoints in OpenAPI DoD (prevents omission), (3) Added publishing authorization to AC-ENG-011-12 (critical security fix - prevents fake progress injection), (4) Added sampling + ROI metadata to Transformation Manifest AC-ENG-010-01 (reproducibility and forensic auditability), (5) Clarified latency scaling rule assumes constant sampling density in AC-ENG-006-07 (removes ambiguity), (6) Clarified webhook scope vs deferred endpoints in ENG-011 (prevents scope confusion), (7) Clarified reproducibility threshold definitions in AC-ENG-007-01 (technical accuracy - perceptual hash Hamming distance, encoder non-determinism acknowledged).

**Change Note (concrete accuracy/completeness fixes - Feb 12, 2026):** Applied 7 concrete accuracy/completeness fixes: (1) Added implementation note to AC-ENG-011-12 RLS policy example (critical - clarifies policy is illustrative, requires integration testing), (2) Added Phase 1 webhook configuration mechanism (webhook_subscriptions table, admin-managed), (3) Added per-user dedup clarification to ENG-009 AC-ENG-009-05 (consistency with ENG-003), (4) Changed sampling from fixed count to density-based in AC-ENG-006-11 (1–2 frames/second, removes scaling ambiguity), (5) Specified deterministic hash stage in AC-ENG-007-01 (pre-encode normalized frames, technical accuracy), (6) Specified Pub/Sub as canonical API invocation method (architectural clarity), (7) Added created_by/source CHECK constraint to job_era_detections schema (schema integrity for system classifications).

**Change Note (accuracy/regression risk fixes - Feb 12, 2026):** Applied 7 accuracy/regression risk fixes: (1) Clarified endpoint count wording in change note ("22 Phase 1 endpoints; 2 deferred to Phase 2" removes total count ambiguity), (2) Added explicit Phase 1 outbound-only clarification to AC-ENG-011-04 (webhook notifications are outbound delivery only, no customer-managed registration UI/API in Phase 1), (3) Added Realtime Authorization risk/mitigation note to AC-ENG-011-02 (Supabase Realtime Authorization is Public Beta, fallback serves both availability and feature maturity mitigation), (4) Added note about brittle regex extraction in AC-ENG-011-12 RLS policy example (recommends storing topic string in jobs table or using mapping table), (5) Clarified backend publishing mechanism in AC-ENG-011-12 (backend uses service-role key, warns against enabling client INSERT policies), (6) Labeled health check response as example with server current time (prevents literal timestamp interpretation), (7) Clarified Prometheus metrics rationale (service implements metrics, Cloud Run hosts endpoint - avoids overclaim about "native support").

---

## Technical Architecture

**Infrastructure:** GCP (Cloud Run Jobs + Vertex AI L4/RTX 6000 GPUs)  
**Lead Dev Tool:** Codex 5.3 (Interaction Mode: Steering & SDD Enforcement)

### System Architecture Overview

ChronosRefine consists of 5 architectural layers:

1. **User Layer**: React-based web interface with REST API backend
2. **Application Layer**: Job orchestration with schema validation and authentication
3. **AI/ML Layer**: Five specialized models (Gemini 3 Pro, CodeFormer, MediaPipe, AV1 FGS, SynthID)
4. **Infrastructure Layer**: Cloud Run Jobs for GPU orchestration with monitoring
5. **Data Layer**: **Supabase Postgres** for job metadata/audit, **Redis** for dedup cache, **GCS** for media storage

### API Hosting Decision (Phase 1)

**Canonical Choice:** REST API runs on **Cloud Run (service)** with the following architecture:

- **Cloud Run (service)**: Hosts the primary REST API (all /v1/* endpoints)
  - Handles JWT verification using Supabase Auth
  - Uses end-user JWT for DB operations (RLS enforced)
  - Service-role key only for background jobs (not user requests)
  - Exposes /v1/metrics for Prometheus scraping
  - Scales 0-N instances based on load

- **Cloud Run Jobs**: GPU-accelerated video processing (triggered by API)
  - Receives work via **Pub/Sub** (canonical for Phase 1, enables buffering + retry). Direct invocation reserved for internal admin operations only.
  - No direct user-facing endpoints

- **Supabase Edge Functions**: Deferred to Phase 2
  - Potential use: Webhook glue, lightweight transformations
  - Not used for primary API in Phase 1

**Network Topology:**
- User → Cloud Run (service) → Supabase Postgres (RLS enforced)
- Cloud Run (service) → Cloud Run Jobs (via Pub/Sub)
- Cloud Run Jobs → GCS (media I/O)

**Rationale:** Cloud Run (service) provides:
- Ability to expose Prometheus-format `/v1/metrics` endpoint for scraping (service implements metrics, Cloud Run hosts the HTTP endpoint)
- Flexible JWT verification patterns
- Easier correlation ID propagation
- Standard Cloud Logging integration

---

## Engineering Requirements

### ENG-001: JSON Schema Validation

**Description:** System must validate all processing jobs against Era Profile JSON Schema v2020-12 before execution.

**Acceptance Criteria:**
- AC-ENG-001-01: JSON Schema v2020-12 specification implemented in validation layer
- AC-ENG-001-02: All 10 validation rules (VR-001 through VR-010) enforced with severity levels
- AC-ENG-001-03: Locked vs tunable parameter matrix enforced by tier/mode
- AC-ENG-001-04: Schema validation occurs before job submission (fail-fast)
- AC-ENG-001-05: Validation errors return user-facing error messages (not raw JSON Schema errors)
- AC-ENG-001-06: Canonical enum definitions enforced (capture_medium, mode, resolution_cap, grain_intensity)
- AC-ENG-001-07: Conditional validation rules enforced (VHS→deinterlace, Conserve→hallucination_limit≤0.05, low confidence→manual confirmation)
- AC-ENG-001-08: Validation latency <100ms for 95th percentile
- AC-ENG-001-09: Invalid jobs rejected with HTTP 400 + detailed error response
- AC-ENG-001-10: Validation logic unit tested with 50+ test cases covering all rules

**Definition of Done / Test Files / Related Requirements:** *(no changes)*

---

### ENG-002: API Endpoint Implementation

**Description:** System must implement RESTful API endpoints for all user journey steps with proper authentication, error handling, and monitoring.

**Acceptance Criteria (corrected):**
- AC-ENG-002-01: All API endpoints implemented with OpenAPI 3.0 specification
- AC-ENG-002-02: Authentication via **Supabase Auth** (OAuth 2.0 providers + email/password) issuing JWTs. Authorization MUST be enforced by:
  - **(a)** Executing user-scoped DB operations using the end-user JWT so Postgres RLS is enforced, OR
  - **(b)** If using service-role key for privileged operations, implementing equivalent authorization checks in the service layer AND limiting service-role usage to strictly necessary system tasks (e.g., background jobs, admin operations)
  - **Security Note:** Service-role key bypasses RLS; never use it for user-initiated requests without explicit authorization checks
- AC-ENG-002-03: Rate limiting enforced (example: **Hobbyist 100 req/min**, **Pro 1,000 req/min**, **Museum 1,000 req/min**; exact values configurable)
- AC-ENG-002-04: CORS configured for web UI origin(s)
- AC-ENG-002-05: Request/response logging with correlation IDs
- AC-ENG-002-06: Error responses follow RFC 7807 (Problem Details for HTTP APIs)
- AC-ENG-002-07: API versioning via URL path (/v1/, /v2/)
- AC-ENG-002-08: Health check endpoints:
  - **GET /health** (unversioned, for infrastructure probes):
    - Shallow check (process alive, no dependency checks)
    - Must respond within **50ms p95**
    - Returns 200 OK with minimal JSON: `{"status": "ok"}`
  - **GET /v1/health** (versioned, detailed status for API clients):
    - Deep check (includes DB, Redis, GCS connectivity)
    - Must respond within **500ms p95**
    - Returns 200 OK with detailed JSON (example):
      ```json
      {
        "status": "healthy",
        "components": {
          "database": "healthy",
          "redis": "healthy",
          "gcs": "healthy"
        },
        "timestamp": "2026-02-12T10:30:00Z"  // Server current time (ISO 8601)
      }
      ```
- AC-ENG-002-09: Metrics endpoint exposed in **Prometheus format** (canonical SRE scrape path at `/v1/metrics`); optionally forwarded to Cloud Monitoring via OTEL collector
- AC-ENG-002-10: API documentation auto-generated from OpenAPI spec (Swagger UI)

**API Endpoints (22 total) — Phase 1 scope:**

| Method | Endpoint | Description |
|---|---|---|
| POST | `/v1/upload` | Generate signed GCS URL for resumable upload |
| POST | `/v1/detect-era` | Trigger Gemini era detection |
| GET | `/v1/eras` | List all supported era profiles |
| POST | `/v1/preview` | Generate 10 scene-aware keyframes |
| POST | `/v1/jobs` | Create restoration job |
| GET | `/v1/jobs/{id}` | Get job status and progress |
| GET | `/v1/jobs` | List jobs (paged) |
| DELETE | `/v1/jobs/{id}` | Cancel running job |
| POST | `/v1/jobs/{id}/retry` | Retry failed job segments |
| GET | `/v1/jobs/{id}/export` | Generate signed download URL for results |
| GET | `/v1/manifests/{id}` | Get transformation manifest |
| GET | `/v1/deletion-proofs/{id}` | Get deletion proof (Museum tier) |
| GET | `/v1/uncertainty-callouts/{id}` | Get uncertainty callouts for a job |
| GET | `/v1/users/me` | Get current user profile |
| PATCH | `/v1/users/me` | Update user profile/preferences |
| GET | `/v1/users/me/usage` | Get monthly usage statistics |
| POST | `/v1/users/me/approve-overage` | Approve overage charges |
| POST | `/v1/webhooks/stripe` | Stripe webhook receiver |
| GET | `/health` | Health check (unversioned, for infrastructure probes) |
| GET | `/v1/health` | Health check (versioned, detailed status for API clients) |
| GET | `/v1/metrics` | Metrics endpoint (Prometheus format) |
| GET | `/v1/version` | Build/version info (commit SHA, build time) |

**Phase 2 Endpoints (deferred):**
- `POST /v1/webhooks/job-events` - Outbound job event relay for third-party integrations
- `POST /v1/support/ticket` - In-app support ticket creation

**Definition of Done:** keep as-is, but replace "Auth0 or Firebase Auth" with **Supabase Auth** and ensure the endpoint count matches the final OpenAPI, including both `/health` (infrastructure probes) and `/v1/health` (client-facing status).

**Related Requirements (corrected):** ENG-001, **SEC-013 (Supabase Auth selection)**, OPS-001

---

### ENG-003: Video Processing Pipeline

No correctness regressions found in the excerpt.

**Idempotency Hash (AC-ENG-003-03 - Applied):**
- Idempotency key includes user identity, source asset identity, segment boundaries, tier/mode, and all configuration to prevent cache collisions:
  - `hash(user_id + source_asset_checksum + segment_index + segment_start_ts + segment_end_ts + segment_duration + fidelity_tier + processing_mode + config_hash + model_digest + era_profile_digest + encoder_digest)`
  - `user_id`: User/account identifier (ensures tenant boundary - prevents cross-user cache leakage)
  - `source_asset_checksum`: SHA-256 of input file (ensures different uploads don't collide)
  - `segment_start_ts`, `segment_end_ts`, `segment_duration`: Segment time boundaries in milliseconds (ensures different segmentation configs don't collide)
  - `config_hash`: SHA-256 of all effective tunables JSON (ensures parameter changes trigger reprocessing)
  - **Note**: `job_id` is excluded to enable cross-job deduplication **within a user** (identical reruns as separate jobs can reuse cached results within 1-hour window per ENG-009)
  - **Security Note**: `user_id` is included to prevent privacy violation (without it, User B could receive User A's cached outputs if processing the same video with the same config)
- This ensures that changing any input, segmentation, tier, mode, or configuration creates a new processing attempt, while identical reruns by the same user (even as separate jobs) can reuse cached results

---

### ENG-004: Era Detection Model

**Consistency Adjustments (Applied):**

1. **Fallback Behavior:** If "fallback to rule-based classification" (AC-ENG-004-08) is triggered, preserve FR-002's ultimate fallback ("Unknown Era + manual selection required") when rule-based inference is also low-confidence (<0.70).

2. **Model Versioning for Auditability:** The `job_era_detections` table now includes `model_version` and `prompt_version` columns for ML auditability and A/B testing:

```sql
CREATE TABLE job_era_detections (
    id UUID PRIMARY KEY,
    job_id UUID REFERENCES jobs(id),
    era TEXT NOT NULL,
    confidence FLOAT NOT NULL,
    forensic_markers JSONB,
    overridden_by_user BOOLEAN DEFAULT FALSE,
    override_reason TEXT,
    model_version TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('system', 'user_override', 'admin_override')),  -- Enforced enum for audit integrity
    raw_response_gcs_uri TEXT,  -- Pointer to full Gemini response for forensics
    created_at TIMESTAMP DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id),  -- NULL for system classifications, required for user/admin overrides
    CONSTRAINT created_by_source_consistency CHECK (
        (source = 'system' AND created_by IS NULL) OR
        (source IN ('user_override', 'admin_override') AND created_by IS NOT NULL)
    )
);

-- Indexes for typical queries
CREATE INDEX idx_era_detections_job_latest 
    ON job_era_detections(job_id, created_at DESC);
CREATE INDEX idx_era_detections_overridden 
    ON job_era_detections(job_id, overridden_by_user) 
    WHERE overridden_by_user = TRUE;
CREATE INDEX idx_era_detections_source 
    ON job_era_detections(source, created_at DESC);
```

**Query Pattern for Latest Detection:**
```sql
SELECT * FROM job_era_detections 
WHERE job_id = $1 
ORDER BY created_at DESC 
LIMIT 1;
```

**Benefits:**
- Enables tracking which Gemini model version produced each classification
- Supports A/B testing of different prompt strategies
- Critical for reproducing classification results during audits
- **Audit fields** (`source`, `raw_response_gcs_uri`, `created_by`) enable forensic debugging
- **Indexes** optimize typical queries (latest detection, overridden jobs, source filtering)

---

### ENG-005: Fidelity Tier Implementation

**Issue fixed:** ENG-005 tier thresholds conflicted with Functional Requirements’ canonical Anti-Plastic metrics + FR-003.

**Acceptance Criteria (aligned):**
- AC-ENG-005-01: Three fidelity tiers implemented with distinct processing parameters:
  - **Enhance**: `E_HF ≥ 0.55`, `S_LS within ±6 dB of original`, `T_TC ≥ 0.90`, `hallucination_limit ≤ 0.30`, grain preset **"Subtle"**
  - **Restore**: `E_HF ≥ 0.70`, `S_LS within ±4 dB of original`, `T_TC ≥ 0.90`, `hallucination_limit ≤ 0.15`, grain preset **"Matched"**
  - **Conserve**: `E_HF ≥ 0.85`, `S_LS within ±2 dB of original`, `T_TC ≥ 0.90`, `hallucination_limit ≤ 0.05`, preserve all original grain, **Identity Lock enabled**
- AC-ENG-005-02: Identity Lock (Conserve): LPIPS identity drift <0.02 for facial ROI
- AC-ENG-005-03: Grain intensity presets implemented for each tier (**Subtle / Matched / Heavy**) with tier defaults as above
- AC-ENG-005-04: Tier-specific reconstruction weights for CodeFormer (Conserve: <0.05, Restore: 0.05-0.15, Enhance: 0.15-0.30)
- AC-ENG-005-05: Tier selection persists throughout job execution
- AC-ENG-005-06: Tier parameters validated against locked/tunable matrix
- AC-ENG-005-07: Tier-specific error handling (Conserve: strict, Enhance: permissive)
- AC-ENG-005-08: Tier-specific Uncertainty Callout thresholds

**Canonical Source of Truth:**
> All tier thresholds in AC-ENG-005-01 are derived from the **"Anti-Plastic Metrics Definitions"** section in Functional Requirements.
> If any per-requirement AC text differs from the canonical definitions, it MUST be updated to match.
> This prevents threshold drift across FR-003, ENG-005, and ENG-006.

---

### ENG-006: Quality Metrics Calculation

**Issue fixed:** Metric names/definitions diverged from Functional Requirements.

**Acceptance Criteria (aligned):**
- AC-ENG-006-01: **E_HF (Texture Energy, High-Frequency)** calculated as mean energy in high-frequency components (DCT or FFT) above an era-normalized threshold (e.g., **>8 cycles/degree**), reported as a ratio vs original; include **noise-floor correction**
- AC-ENG-006-02: **S_LS (Spectral Low-Slope)** computed as slope of PSD in low-frequency band (**<2 cycles/degree**) in **CIE L\*a\*b\*** space; compare to original and enforce tier band (±2/±4/±6 dB)
- AC-ENG-006-03: **T_TC (Temporal Coherence)** computed via motion-compensated frame differences (optical flow) and cross-correlation; enforce **T_TC ≥ 0.90** for all tiers
- AC-ENG-006-04: Metrics computed for all frames or a deterministic sampling protocol; protocol included in manifest
- AC-ENG-006-05: Violations trigger fallback (and Conserve pause/manual review for hallucination_limit violations)
- AC-ENG-006-06: Metrics stored in Transformation Manifest
- AC-ENG-006-07: Metric calculation latency budget: **<2s per segment** for all 3 metrics (E_HF, S_LS, T_TC) combined; sampling protocol (if used) must maintain this budget while ensuring statistical validity. Budget applies to the default **10s segment duration**; if segment duration changes, latency budget scales approximately linearly with segment duration **because sampling density remains constant** (e.g., 20s segment → <4s budget)
- AC-ENG-006-08: Validate against reference implementations (MATLAB / SciPy)
- AC-ENG-006-09: Tolerance <1% deviation from reference
- AC-ENG-006-10: Retain noise-floor correction intent for E_HF
- AC-ENG-006-11: Deterministic sampling protocol for latency budget compliance:
  - Sample at **1–2 frames/second** density (10–20 frames per 10s segment, 20–40 frames per 20s segment, etc.; deterministic, evenly spaced)
  - Optical flow computed on **720p downscaled frames** (if source >720p)
  - **ROI Selection Rule**: Center crop (256×256 for E_HF, 512×512 for S_LS) from each sampled frame; ROI coordinates (top-left x,y) documented in Transformation Manifest
  - **E_HF**: FFT on center 256×256 ROI per sampled frame
  - **S_LS**: PSD on center 512×512 ROI per sampled frame in CIE L\*a\*b\* space
  - **T_TC**: Optical flow on consecutive sampled frame pairs (full 720p frame, not ROI)
  - **Hardware assumption**: 1× NVIDIA L4 GPU or equivalent
  - Sampling protocol + ROI coordinates documented in Transformation Manifest for reproducibility
  - Budget applies to default 10s segment; scales linearly for other durations
  - **Note**: Metrics are computed on center ROI by design; edge artifacts (vignetting, border noise, tracking errors) are not captured by these metrics. For comprehensive quality assessment, consider multi-ROI sampling in Phase 2.

---

### ENG-007: Reproducibility Proof

**Description:** System must provide three reproducibility modes (Perceptual Equivalence, Deterministic, Bit-Identical) with environment pinning and failure handling.

**Acceptance Criteria:**
- AC-ENG-007-01: Three reproducibility modes implemented:
  - **Perceptual Equivalence** (Default): ≥99.999% of frames produce identical perceptual hashes (defined by Hamming distance threshold ≤3 for 64-bit pHash), metrics within 0.5%
  - **Deterministic** (Pro/Museum): Deterministic frame hashes computed on **pre-encode normalized frames** (YUV/RGB pixel data after restoration but before final encoding) under fixed environment. Final encoded output may vary due to encoder non-determinism across platforms, but restoration quality is reproducible. 6-decimal metric precision.
  - **Bit-Identical** (Museum only): Complete byte-for-byte output (2-3x slower)
- AC-ENG-007-02: Environment pinning for Deterministic/Bit-Identical modes (container digest, model versions, encoder version, GPU driver)
- AC-ENG-007-03: Frame-equivalence tolerance verification (SHA-256 hash comparison)
- AC-ENG-007-04: Anti-plastic metrics stability verification (E_HF, S_LS, T_TC within epsilon)
- AC-ENG-007-05: Failure handling: auto-rerun, segment isolation, escalation after 2 failed attempts
- AC-ENG-007-06: Segment-to-job rollup rules (0% = PASS, <5% = PARTIAL, >20% = CRITICAL)
- AC-ENG-007-07: Reproducibility mode selection persists throughout job execution
- AC-ENG-007-08: Performance trade-off documented (Bit-Identical: 2-3x slower)

**Definition of Done:**
- DoD-ENG-007-01: All 3 reproducibility modes implemented and tested
- DoD-ENG-007-02: Environment pinning tested for Deterministic/Bit-Identical modes
- DoD-ENG-007-03: Frame-equivalence tolerance tested with SHA-256 hash comparison
- DoD-ENG-007-04: Metrics stability tested with epsilon verification
- DoD-ENG-007-05: Failure handling tested (auto-rerun, segment isolation, escalation)
- DoD-ENG-007-06: Rollup rules tested (0%, <5%, >20% thresholds)
- DoD-ENG-007-07: Mode selection persistence tested (end-to-end workflow)
- DoD-ENG-007-08: Performance trade-off verified (Bit-Identical: 2-3x slower measured)
- DoD-ENG-007-09: Code review approved by 2+ engineers

**Verification Method:** Automated (pytest unit tests + integration tests + performance testing)

**Test Files:**
- `tests/processing/test_reproducibility_modes.py`
- `tests/processing/test_environment_pinning.py`
- `tests/processing/test_frame_equivalence.py`
- `tests/processing/test_metrics_stability.py`
- `tests/processing/test_failure_handling.py`

**Related Requirements:** ENG-003 (Video Processing Pipeline), ENG-006 (Quality Metrics Calculation), OPS-002 (SLO Monitoring)

---

### ENG-008: GPU Pool Management

**Description:** System must pre-warm GPU pool to meet processing time SLOs with autoscaling and cost optimization.

**Acceptance Criteria:**
- AC-ENG-008-01: GPU pool pre-warming with configurable minimum warm pool size
- AC-ENG-008-02: Cold-start to ready latency <120s for 99th percentile
- AC-ENG-008-03: Autoscaler maintains minimum warm pool (N instances based on demand forecast)
- AC-ENG-008-04: Autoscaler scales up when queue depth exceeds threshold (e.g., 10 jobs)
- AC-ENG-008-05: Autoscaler scales down when idle for >5 minutes
- AC-ENG-008-06: GPU instance types: L4 (default), RTX 6000 (Museum tier)
- AC-ENG-008-07: GPU allocation latency <30s for 95th percentile
- AC-ENG-008-08: Target 60–70% sustained utilization (cost optimization target)
- AC-ENG-008-09: GPU pool monitoring dashboard with real-time metrics
- AC-ENG-008-10: Cost tracking per job (GPU time, storage, API calls)

**Definition of Done:**
- DoD-ENG-008-01: GPU pool pre-warming tested with cold-start latency measurement
- DoD-ENG-008-02: Cold-start latency <120s verified for 99th percentile
- DoD-ENG-008-03: Autoscaler tested with simulated load (scale up/down)
- DoD-ENG-008-04: Minimum warm pool size tested (N instances maintained)
- DoD-ENG-008-05: GPU allocation latency <30s verified for 95th percentile
- DoD-ENG-008-06: GPU utilization >70% verified with monitoring dashboard
- DoD-ENG-008-07: Cost tracking tested per job (accurate GPU time + storage + API calls)
- DoD-ENG-008-08: Monitoring dashboard created with real-time metrics
- DoD-ENG-008-09: Code review approved by 2+ engineers

**Verification Method:** Automated (integration tests + load testing) + Manual (monitoring dashboard verification)

**Test Files:**
- `tests/infrastructure/test_gpu_pool.py`
- `tests/infrastructure/test_autoscaler.py`

**Related Requirements:** OPS-001 (Monitoring & Alerting), OPS-004 (Performance Monitoring), NFR-002 (Processing Time SLO)

---

### ENG-009: Deduplication Cache

**Description:** System must implement Redis-based deduplication cache to reuse segment outputs for identical reruns within 1-hour window.

**Acceptance Criteria:**
- AC-ENG-009-01: Redis cache for processed segment outputs (key: idempotency key, value: GCS path)
- AC-ENG-009-02: Cache TTL: 1 hour (configurable)
- AC-ENG-009-03: Cache hit detection latency <500ms for 95th percentile
- AC-ENG-009-04: Cache hit rate >40% for duplicate jobs (measured by SRE dashboard)
- AC-ENG-009-05: Deduplication is scoped **per-user** (cache keys include `user_id` to prevent cross-user cache leakage per ENG-003). Identical reruns by different users are processed independently.
- AC-ENG-009-06: Cache miss triggers full segment processing
- AC-ENG-009-07: Cache invalidation on model version change
- AC-ENG-009-08: Cache size monitoring with eviction policy (LRU)
- AC-ENG-009-09: Cache hit/miss metrics tracked in monitoring dashboard
- AC-ENG-009-10: GPU cost reduction >40% for cached segments
- AC-ENG-009-11: Cache resilience: degraded mode if Redis unavailable (no caching, full processing)

**Definition of Done:**
- DoD-ENG-009-01: Redis cache integration tested with segment outputs
- DoD-ENG-009-02: Cache TTL tested (1-hour expiration verified)
- DoD-ENG-009-03: Cache hit detection latency <500ms verified
- DoD-ENG-009-04: Cache hit rate >40% verified with duplicate job submissions
- DoD-ENG-009-05: Cache miss tested (triggers full processing)
- DoD-ENG-009-06: Cache invalidation tested on model version change
- DoD-ENG-009-07: Cache size monitoring tested with eviction policy
- DoD-ENG-009-08: Cache hit/miss metrics tracked in dashboard
- DoD-ENG-009-09: GPU cost reduction >40% verified for cached segments
- DoD-ENG-009-10: Cache resilience tested (degraded mode if Redis unavailable)
- DoD-ENG-009-11: Code review approved by 2+ engineers

**Verification Method:** Automated (pytest integration tests + load testing)

**Test Files:**
- `tests/infrastructure/test_cache_dedup.py`
- `tests/integration/test_partial_results.py`

**Related Requirements:** ENG-003 (Video Processing Pipeline), OPS-001 (Monitoring & Alerting), NFR-003 (Cost Optimization)

---

### ENG-010: Transformation Manifest Generation

**Description:** System must generate comprehensive transformation manifest documenting all processing steps for audit trail.

**Acceptance Criteria:**
- AC-ENG-010-01: Transformation Manifest includes:
  - Job ID, timestamp, user ID
  - Era Profile selected (capture_medium, mode, era_range)
  - Fidelity Tier and parameters
  - Anti-plastic metrics (E_HF, S_LS, T_TC) per frame range
  - Uncertainty Callouts with frame ranges
  - Model versions (CodeFormer, Gemini, AV1 encoder)
  - Environment pinning (container digest, GPU driver version)
  - Processing time and GPU usage
  - **Sampling + ROI Metadata** (for reproducibility and forensic auditability):
    - Sampling protocol parameters (frames per segment, evenly spaced)
    - Sampled frame timestamps/indices
    - Downscale rules used (e.g., 720p for optical flow)
    - ROI coordinates per sampled frame (top-left x,y, width, height)
    - Indicator whether metrics were ROI-derived or full-frame
- AC-ENG-010-02: Manifest format: JSON with JSON Schema validation
- AC-ENG-010-03: Manifest generation latency <5s for 95th percentile
- AC-ENG-010-04: Manifest stored in GCS with job results
- AC-ENG-010-05: Manifest downloadable via API endpoint
- AC-ENG-010-06: Manifest includes cryptographic signature (SHA-256) for tamper detection
- AC-ENG-010-07: Manifest includes reproducibility proof (frame hashes, environment versions)
- AC-ENG-010-08: Manifest size <10MB (compressed if needed)

**Definition of Done:**
- DoD-ENG-010-01: Manifest generation tested with all required fields
- DoD-ENG-010-02: Manifest JSON Schema validation tested
- DoD-ENG-010-03: Manifest generation latency <5s verified
- DoD-ENG-010-04: Manifest storage tested in GCS
- DoD-ENG-010-05: Manifest download tested via API endpoint
- DoD-ENG-010-06: Cryptographic signature tested (SHA-256 verification)
- DoD-ENG-010-07: Reproducibility proof tested (frame hashes, environment versions)
- DoD-ENG-010-08: Manifest size tested (<10MB for typical jobs)
- DoD-ENG-010-09: Code review approved by 2+ engineers

**Verification Method:** Automated (pytest unit tests + integration tests)

**Test Files:**
- `tests/api/test_transformation_manifest.py`
- `tests/processing/test_manifest_generation.py`

**Related Requirements:** ENG-003 (Video Processing Pipeline), FR-005 (Output Delivery), SEC-011 (Dataset Provenance)

---

### ENG-011: Async Processing

**Description:** System must implement asynchronous job processing with real-time progress updates and webhook notifications.

**Note**: Webhook notifications refer to **outbound system callbacks** (backend initiates HTTP POST to user-configured URLs) and do not require exposing additional public API endpoints in Phase 1. The `/v1/webhooks/job-events` endpoint (for webhook registration/management) is deferred to Phase 2.

**Phase 1 Webhook Configuration**: Webhook URLs are configured via:
- **Internal admin-managed table** (`webhook_subscriptions` with columns: `user_id UUID`, `webhook_url TEXT`, `event_types TEXT[]`, `enabled BOOLEAN`, `created_at TIMESTAMP`)
- **Admin-only access** (no public API endpoint in Phase 1; managed via database migrations or internal admin tools). Webhook ownership must match user_id; ops tooling must enforce tenant isolation.
- **Manual configuration** by ops team for early adopters/beta users
- Phase 2 will expose `/v1/webhooks/job-events` API for user-managed webhook registration

**Acceptance Criteria:**
- AC-ENG-011-01: Jobs submitted asynchronously (return job ID immediately)
- AC-ENG-011-02: Real-time progress updates via **Supabase Realtime** (canonical); fallback to SSE or polling if Realtime unavailable
  - **Risk/Mitigation Note**: Supabase Realtime Authorization is currently in Public Beta with specific client/library requirements. Fallback to SSE/polling serves both availability resilience and feature maturity/limits mitigation. Monitor Supabase Realtime changelog for GA status and authorization API changes.
- AC-ENG-011-03: Progress includes: current segment, total segments, estimated time remaining
- AC-ENG-011-04: Webhook notifications for job events (started, completed, failed). **Phase 1 scope**: Outbound delivery only (backend initiates HTTP POST to admin-configured webhook URLs); no customer-managed registration UI/API (deferred to Phase 2 `/v1/webhooks/job-events` endpoint).
- AC-ENG-011-05: Webhook retry logic (exponential backoff, max 3 retries)
- AC-ENG-011-06: Job status polling endpoint (GET /v1/jobs/{id}) with 1s cache TTL
- AC-ENG-011-07: Job cancellation support (DELETE /v1/jobs/{id})
- AC-ENG-011-08: Job timeout: 6 hours maximum (configurable per tier)
- AC-ENG-011-09: Job queue management with priority (Museum > Pro > Hobbyist)
- AC-ENG-011-10: Dead letter queue for failed jobs (manual review)
- AC-ENG-011-11: Progress update event contract (Supabase Realtime):
  - **Realtime Mode**: Broadcast (not postgres_changes)
  - **Channel**: `job_progress:{job_id}`
  - **Event**: `progress_update`
  - **Payload schema**:
    ```json
    {
      "job_id": "uuid",
      "segment_index": "integer (0-based current segment)",
      "segment_count": "integer (total segments)",
      "percent_complete": "float (0.0-100.0)",
      "eta_seconds": "integer (estimated seconds remaining)",
      "status": "enum (processing|paused|failed|completed)",
      "current_operation": "string (e.g., 'Enhancing segment 5/20')",
      "updated_at": "ISO 8601 timestamp"
    }
    ```
  - **Authorization**: See AC-ENG-011-12 for channel access control
- AC-ENG-011-12: Realtime subscription authorization:
  - Authorization enforced by **Supabase Realtime** at channel join time using RLS policies
  - Policies defined on `realtime.messages` table (Realtime schema, not `jobs` table)
  - Policy checks `realtime.topic()` matches `job_progress:{job_id}` pattern and validates job ownership via:
    ```sql
    -- Example RLS policy on realtime.messages (ILLUSTRATIVE)
    CREATE POLICY "Users can only subscribe to their own job progress"
    ON realtime.messages
    FOR SELECT
    USING (
      realtime.topic() LIKE 'job_progress:%' AND
      EXISTS (
        SELECT 1 FROM jobs
        WHERE id = (regexp_match(realtime.topic(), 'job_progress:(.+)'))[1]::uuid
        AND user_id = auth.uid()
      )
    );
    ```
  - **Implementation Note**: The SQL policy shown is **illustrative** for conceptual understanding. The `regexp_match()` approach for extracting `job_id` from topic is brittle (requires careful casting, array indexing, and topic format consistency). For production, consider:
    - **Option A (Recommended)**: Store topic string in `jobs` table (e.g., `topic TEXT DEFAULT 'job_progress:' || id::text`) and compare equality directly: `realtime.topic() IN (SELECT topic FROM jobs WHERE user_id = auth.uid())`
    - **Option B**: Maintain a small `realtime_topic_permissions` mapping table keyed by topic for explicit authorization
    - Supabase Realtime Broadcast authorization is enforced via RLS policies on the `realtime.messages` table. Authorization must be validated with integration tests simulating cross-user subscription attempts. Consult Supabase Realtime documentation for production-ready policy examples.
  - Unauthorized join attempts fail at subscribe time (client receives error via subscribe callback, not HTTP 403)
  - **Publishing Authorization**: Backend publishes progress updates using **service-role key** (or Realtime server API with trusted backend credentials). INSERT permission on `realtime.messages` MUST be restricted to service-role or trusted backend roles only. Clients MUST NOT have permission to publish progress events (prevents fake progress injection). Do not enable client INSERT policies to "make it work" - this creates a critical security vulnerability.
  - **Security Note**: Without subscription authorization, users could subscribe to other users' job progress channels (privacy violation). Without publishing authorization, malicious clients could inject fake job progress updates.

**Definition of Done:**
- DoD-ENG-011-01: Async job submission tested (returns job ID immediately)
- DoD-ENG-011-02: Real-time progress updates tested via Supabase Realtime (with SSE/polling fallback)
- DoD-ENG-011-03: Progress accuracy tested (current segment, total segments, ETA)
- DoD-ENG-011-04: Webhook notifications tested for all job events
- DoD-ENG-011-05: Webhook retry logic tested (exponential backoff, max 3 retries)
- DoD-ENG-011-06: Job status polling tested with 1s cache TTL
- DoD-ENG-011-07: Job cancellation tested (DELETE /v1/jobs/{id})
- DoD-ENG-011-08: Job timeout tested (6-hour maximum)
- DoD-ENG-011-09: Job queue priority tested (Museum > Pro > Hobbyist)
- DoD-ENG-011-10: Dead letter queue tested (failed jobs captured)
- DoD-ENG-011-11: Code review approved by 2+ engineers

**Verification Method:** Automated (pytest integration tests + load testing)

**Test Files:**
- `tests/api/test_async_processing.py`
- `tests/api/test_progress_updates.py`
- `tests/api/test_webhook_notifications.py`
- `tests/integration/test_job_lifecycle.py`

**Related Requirements:** ENG-002 (API Endpoint Implementation), ENG-003 (Video Processing Pipeline), OPS-001 (Monitoring & Alerting)

---

### ENG-012: Error Recovery

**Description:** System must implement comprehensive error recovery with automatic retry, segment isolation, and partial results delivery.

**Acceptance Criteria:**
- AC-ENG-012-01: Transient failures trigger automatic retry (max 3 attempts)
- AC-ENG-012-02: Exponential backoff between retries (1s, 2s, 4s)
- AC-ENG-012-03: Persistent failures (3 consecutive) mark segment as failed
- AC-ENG-012-04: Failed segments isolated (other segments complete successfully)
- AC-ENG-012-05: Partial results delivered with failed segment flagged
- AC-ENG-012-06: Retry logic respects idempotency key (no duplicate processing)
- AC-ENG-012-07: Error types classified: transient (network, GPU OOM) vs persistent (invalid input, model error)
- AC-ENG-012-08: Error notifications sent to user (email, in-app)
- AC-ENG-012-09: Error logs captured with correlation IDs for debugging
- AC-ENG-012-10: Error metrics tracked in monitoring dashboard (error rate, error types)

**Definition of Done:**
- DoD-ENG-012-01: Automatic retry tested with simulated transient failures
- DoD-ENG-012-02: Exponential backoff tested (1s, 2s, 4s verified)
- DoD-ENG-012-03: Persistent failures tested (3 consecutive failures mark segment as failed)
- DoD-ENG-012-04: Segment isolation tested (other segments complete)
- DoD-ENG-012-05: Partial results delivery tested (failed segment flagged)
- DoD-ENG-012-06: Idempotency key tested (no duplicate processing on retry)
- DoD-ENG-012-07: Error classification tested (transient vs persistent)
- DoD-ENG-012-08: Error notifications tested (email, in-app)
- DoD-ENG-012-09: Error logs tested with correlation IDs
- DoD-ENG-012-10: Error metrics tracked in dashboard
- DoD-ENG-012-11: Code review approved by 2+ engineers

**Verification Method:** Automated (pytest integration tests + chaos engineering)

**Test Files:**
- `tests/processing/test_error_recovery.py`
- `tests/processing/test_retry_logic.py`
- `tests/processing/test_segment_isolation.py`
- `tests/integration/test_partial_results.py`

**Related Requirements:** ENG-003 (Video Processing Pipeline), ENG-011 (Async Processing), OPS-001 (Monitoring & Alerting)

---

### ENG-013: Cost Estimation

**Description:** System must calculate and display cost estimates before job launch with accuracy target of 10-15%.

**Acceptance Criteria:**
- AC-ENG-013-01: Cost estimate displayed in preview modal before job launch
- AC-ENG-013-02: Cost breakdown: GPU time, storage, API calls, total
- AC-ENG-013-03: Cost estimate updates when user changes settings (resolution, mode, etc.)
- AC-ENG-013-04: Estimate accuracy target: 90% of jobs have error <15%, 95% have error <20%
- AC-ENG-013-05: Estimate calculation latency <1s for 95th percentile
- AC-ENG-013-06: Estimate includes overage rate if monthly limit exceeded
- AC-ENG-013-07: Estimate model trained on historical job data (updated monthly)
- AC-ENG-013-08: Estimate confidence interval displayed (e.g., "$12.50 ± $1.80")
- AC-ENG-013-09: Actual cost tracked and compared to estimate (reconciliation report)
- AC-ENG-013-10: Outliers flagged for investigation and estimate model refinement

**Definition of Done:**
- DoD-ENG-013-01: Cost estimate calculation tested with 100+ sample jobs
- DoD-ENG-013-02: Cost breakdown tested (GPU time, storage, API calls)
- DoD-ENG-013-03: Dynamic estimate updates tested (settings changes)
- DoD-ENG-013-04: Estimate accuracy verified (90% <15% error, 95% <20% error)
- DoD-ENG-013-05: Estimate calculation latency <1s verified
- DoD-ENG-013-06: Overage rate inclusion tested (monthly limit exceeded)
- DoD-ENG-013-07: Estimate model trained on historical data (monthly updates)
- DoD-ENG-013-08: Confidence interval tested (displayed correctly)
- DoD-ENG-013-09: Reconciliation report tested (estimate vs actual)
- DoD-ENG-013-10: Outlier detection tested (flagged for investigation)
- DoD-ENG-013-11: Code review approved by 2+ engineers

**Verification Method:** Automated (pytest unit tests) + Manual (reconciliation report analysis)

**Test Files:**
- `tests/api/test_cost_estimation.py`
- `tests/api/test_cost_breakdown.py`
- `tests/integration/test_cost_reconciliation.py`

**Related Requirements:** NFR-001 (Cost Estimate Display), NFR-002 (Processing Time SLO), FR-006 (Preview Generation)

---

### ENG-014: Preview Generation

**Description:** System must generate 10 scene-aware keyframes for user review with p95 generation time <6 seconds.

**Acceptance Criteria:**
- AC-ENG-014-01: Scene detection algorithm identifies scene cuts
- AC-ENG-014-02: 10 keyframes distributed evenly across scenes (not clustered at beginning)
- AC-ENG-014-03: Keyframe selection algorithm: max(3, total_target_samples / scene_count) per scene
- AC-ENG-014-04: Keyframes cover beginning, middle, end of video
- AC-ENG-014-05: Keyframe generation latency: p95 <6s (measured by Cloud Monitoring)
- AC-ENG-014-06: Keyframes stored in GCS with job preview
- AC-ENG-014-07: Keyframe thumbnails generated (320x180 resolution)
- AC-ENG-014-08: Keyframe metadata includes: timestamp, scene number, confidence score
- AC-ENG-014-09: Keyframe generation respects cache (reuse if video unchanged)
- AC-ENG-014-10: Keyframe generation fails gracefully (fallback to uniform sampling if scene detection fails)

**Definition of Done:**
- DoD-ENG-014-01: Scene detection tested with 20+ sample videos
- DoD-ENG-014-02: Keyframe distribution tested (not clustered at beginning)
- DoD-ENG-014-03: Keyframe selection algorithm tested (3+ per scene)
- DoD-ENG-014-04: Keyframe coverage tested (beginning, middle, end)
- DoD-ENG-014-05: Keyframe generation latency p95 <6s verified
- DoD-ENG-014-06: Keyframe storage tested in GCS
- DoD-ENG-014-07: Thumbnail generation tested (320x180 resolution)
- DoD-ENG-014-08: Keyframe metadata tested (timestamp, scene number, confidence)
- DoD-ENG-014-09: Keyframe caching tested (reuse if video unchanged)
- DoD-ENG-014-10: Fallback logic tested (uniform sampling if scene detection fails)
- DoD-ENG-014-11: Code review approved by 2+ engineers

**Verification Method:** Automated (pytest unit tests + load testing)

**Test Files:**
- `tests/processing/test_preview_generation.py`
- `tests/processing/test_scene_detection.py`
- `tests/load/test_preview_performance.py`

**Related Requirements:** FR-006 (Preview Generation), ENG-013 (Cost Estimation), DS-001 (Fidelity Configuration UX)

---

### ENG-015: Output Encoding

**Description:** System must encode final output in MP4/AV1 container with tier-specific quality settings and metadata preservation.

**Acceptance Criteria:**
- AC-ENG-015-01: Output container: MP4 with AV1 codec (default), H.264 fallback for compatibility
- AC-ENG-015-02: AV1 encoder: libaom-3.8.2 with deterministic build flags
- AC-ENG-015-03: Bitrate: tier-dependent (Hobbyist: 8 Mbps, Pro: 16 Mbps, Museum: 32 Mbps)
- AC-ENG-015-04: Resolution: tier-dependent (Hobbyist: 1080p, Pro: 4K, Museum: native_scan)
- AC-ENG-015-05: Frame rate preserved from source (no interpolation)
- AC-ENG-015-06: Color space preserved (Rec. 709, Rec. 2020, or source)
- AC-ENG-015-07: Metadata preserved: EXIF, XMP, timecode (if present in source)
- AC-ENG-015-08: SynthID watermark embedded in bitstream (imperceptible)
- AC-ENG-015-09: AV1 FGS parameters embedded in bitstream
- AC-ENG-015-10: Encoding latency: <2x video duration for 95th percentile

**Definition of Done:**
- DoD-ENG-015-01: AV1 encoding tested with bitstream analysis
- DoD-ENG-015-02: H.264 fallback tested (compatibility mode)
- DoD-ENG-015-03: Bitrate tested for all tiers (8/16/32 Mbps)
- DoD-ENG-015-04: Resolution tested for all tiers (1080p/4K/native_scan)
- DoD-ENG-015-05: Frame rate preservation tested (no interpolation)
- DoD-ENG-015-06: Color space preservation tested (Rec. 709, Rec. 2020)
- DoD-ENG-015-07: Metadata preservation tested (EXIF, XMP, timecode)
- DoD-ENG-015-08: SynthID watermark tested (embedded in bitstream)
- DoD-ENG-015-09: AV1 FGS parameters tested (embedded in bitstream)
- DoD-ENG-015-10: Encoding latency <2x video duration verified
- DoD-ENG-015-11: Code review approved by 2+ engineers

**Verification Method:** Automated (pytest unit tests + bitstream analysis)

**Test Files:**
- `tests/processing/test_output_encoding.py`
- `tests/processing/test_av1_encoding.py`
- `tests/processing/test_metadata_preservation.py`
- `tests/processing/test_encoding_performance.py`

**Related Requirements:** ENG-003 (Video Processing Pipeline), FR-005 (Output Delivery), ENG-007 (Reproducibility Proof)

---

### ENG-016: Database Technology Selection (Supabase)

**Issues fixed:**
- Supabase Storage “GCS backend” phrasing is misleading; ChronosRefine already uses **GCS** for media, so DB stores pointers/metadata.
- Removed unrealistic perf claims (10k QPS / 1k concurrent connections) while preserving measurable quality targets.

**Description (corrected):**  
System must use **Supabase (PostgreSQL + Auth)** as the primary system-of-record for user/job metadata, audit artifacts, and structured evaluation data, with **GCS** as the primary media object store (uploads, previews, outputs, downloadable bundles).

**Acceptance Criteria (corrected):**
- AC-ENG-016-01: Supabase project provisioned with production-grade configuration (connection pooling enabled)
- AC-ENG-016-02: PostgreSQL schema defined with all required tables (users, jobs, assets, processing_logs, audit_trail, quality_metrics, billing_usage, etc.)
- AC-ENG-016-03: DB migrations managed with version control (Supabase migrations / Prisma / Alembic — pick one)
- AC-ENG-016-04: RLS policies defined for all user-owned tables
- AC-ENG-016-05: Indexes created for performance-critical queries (job_id, user_id, created_at, status)
- AC-ENG-016-06: Media storage is **GCS**; DB stores **only pointers/metadata** (bucket/key, size, checksums, retention)
- AC-ENG-016-07: Optional: Supabase Edge Functions for lightweight webhooks/glue logic; **core GPU orchestration remains in GCP services**
- AC-ENG-016-08: Real-time updates via **Supabase Realtime** for job status updates (canonical approach); fallback polling interval configurable (default 5s) if Realtime unavailable or client disconnected
- AC-ENG-016-09: Connection pooling configured and tested under expected concurrency
- AC-ENG-016-10: Backup/restore strategy tested (aligned to SEC/NFR requirements)
- AC-ENG-016-11: Monitoring configured (slow queries, connection saturation, storage growth)
- AC-ENG-016-12: Supabase client libraries integrated for frontend/backend where appropriate

**Definition of Done (corrected / tempered):**
- DoD-ENG-016-01: Supabase provisioned; secrets secured; pooling verified
- DoD-ENG-016-02: Schema + constraints + FKs implemented; migration scripts committed
- DoD-ENG-016-03: Migration tool verified with create/alter/rollback scenarios (10+)
- DoD-ENG-016-04: RLS tested with 30+ scenarios; no cross-user access possible
- DoD-ENG-016-05: Index strategy validated; p95 query times for top 10 queries **<100ms** on realistic volumes (document assumptions)
- DoD-ENG-016-06: GCS integration verified: signed URL flows, pointer integrity, lifecycle policy tests
- DoD-ENG-016-07: Realtime path verified: job status updates delivered in **<2s** p95 under expected load
- DoD-ENG-016-08: Backup restore drills performed (2+) with documented RTO/RPO
- DoD-ENG-016-09: Monitoring + alerts configured for slow queries, pool saturation, storage growth
- DoD-ENG-016-10: Security review passed: RLS verified, secrets not hardcoded, parameterized queries enforced

**Related Requirements (corrected):**
- SEC-013 (Authentication Provider Selection – Supabase Auth)
- FR-001 (Video Upload and Validation)
- FR-004 (Processing and Restoration)
- OPS-001 (Monitoring and Alerting)

---

## References

- JSON Schema v2020-12: https://json-schema.org/draft/2020-12/schema
- AV1 Specification: https://aomedia.org/av1/specification/
- Gemini API Documentation: https://cloud.google.com/vertex-ai/docs/generative-ai/model-reference/gemini
- CodeFormer: https://github.com/sczhou/CodeFormer
- MediaPipe Face Mesh: https://google.github.io/mediapipe/solutions/face_mesh.html
- SynthID: https://deepmind.google/technologies/synthid/

---

**End of Engineering Requirements**
