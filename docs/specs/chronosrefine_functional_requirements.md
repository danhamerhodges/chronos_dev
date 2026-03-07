# ChronosRefine: Functional Requirements

**Purpose:** User-facing features and core product functionality  
**Audience:** Product managers, UX designers, developers  
**Last Updated:** March 2026

**Repo Note:** Test-file references for requirements not yet implemented on `main` are canonical target mappings and may not exist until the corresponding phase lands.

---

## Product Vision

ChronosRefine is the first media restoration system optimized for **historical authenticity** rather than hyperreal enhancement, utilizing "Anti-Plastic" AI to preserve the unique visual DNA of analog eras.

**Positioning Statement:** ChronosRefine addresses the "AI Slop" problem created by mass-market restoration tools (Remini, Topaz Labs) that aggressively optimize for hyper-sharpness, resulting in a waxy, artificial look that erases historical authenticity. ChronosRefine prioritizes historical authenticity over hyperrealism by leveraging AV1 Film Grain Synthesis (FGS) and Gemini 3 Pro-level visual reasoning to preserve the intended data density and texture of the original format [1][2].

---

## User Personas

To guide product decisions, we have defined three primary user personas, each with a distinct Job-to-Be-Done (JTBD).

| Persona | Role | Primary JTBD | Default Tier |
|---|---|---|---|
| **Institutional Archivist** | Digital Preservation Specialist | "Restore archival holdings to publication-grade quality while maintaining a verifiable provenance audit trail that satisfies our institutional review board." | **Conserve** |
| **Documentary Filmmaker** | Post-Production Editor | "Restore decades-old footage to broadcast spec without losing the era-specific texture that tells the story." | **Restore** |
| **Family Historian** | Prosumer Hobbyist | "Make my grandparents' home movies look their best for a reunion without losing the feeling of real memories." | **Enhance** |

### Tradeoff Resolution Framework

When feature development presents conflicts between persona needs, this framework provides a clear decision-making matrix:

| Conflict Scenario | Conserve (Archivist) | Restore (Filmmaker) | Enhance (Prosumer) |
|---|---|---|---|
| **Speed vs. Audit Depth** | Archivist wins: Full, auditable manifest is required. | Filmmaker wins: Manifest is optional for faster processing. | Prosumer wins: Fastest path with no manifest required. |
| **Grain Intensity Default** | Preserve all original grain. | "Matched" preset that is era-accurate. | "Subtle" preset with reduced grain for a cleaner look. |
| **Preview Complexity** | Show all uncertainty callouts and technical details. | Show 10 representative keyframes. | Show 3 keyframes and a simple fidelity slider. |
| **Error UX Detail** | Full technical error codes for detailed diagnostics. | Summarized error with a one-click retry option. | Plain language explanation with an automatic retry. |

---

## User Journey

The user journey is designed to be intuitive for prosumers while offering the depth required by institutional professionals.

1. **Ingest**: Users may upload multiple assets (MP4, TIFF, PNG, etc.) via a secure web interface, which are processed individually. The system supports resumable uploads of 10GB+ per file, leveraging Google Cloud Storage (GCS) for robust, scalable intake. Batch processing orchestration is not supported in the current phase.

2. **Detection**: Gemini 3 Pro analyzes the visual signatures of each asset to automatically suggest an **Era Profile** (e.g., "1960s Kodachrome Film," "1980s VHS Tape"). This includes identifying key forensic markers like film grain structure, color saturation patterns, and format-specific artifacts like VHS tracking noise [3].

3. **Preview**: The system generates 10 scene-aware keyframes for user review, allowing for a quick assessment of the suggested restoration. The acceptance criteria for this step is a p95 generation time of less than 6 seconds.

4. **Configure**: Users select their Fidelity Tier (Enhance/Restore/Conserve) and can override the era classification if needed. The system displays a cost estimate before launching the job.

5. **Launch**: After reviewing the preview and the estimated processing cost, the user launches the full restoration job, which is executed as a series of parallel tasks on GCP Cloud Run Jobs.

6. **Audit Review**: Upon completion, users can review the results, including any "Uncertainty Callouts." These callouts flag areas where the AI had low confidence, such as historical ambiguity in colorized uniforms or potential identity shifts in facial restoration. This feature is critical for the Institutional Archivist persona.

7. **Export**: Users can download the final deliverables, which include a ZIP file containing the restored media, a detailed **Transformation Manifest** (a JSON file documenting every step of the restoration), and a cryptographically signed **Deletion Proof** for compliance workflows.

---

## Error State Catalog

To ensure a robust and user-friendly experience, ChronosRefine defines clear product behaviors and recovery paths for error scenarios. Implementation details (retry counts, idempotency keys, node failures) are specified in Engineering Requirements.

| Error Scenario | Trigger Condition | Product Behavior | User-Facing UX & Recovery Path |
|---|---|---|---|
| **Low-Confidence Era** | Era detection confidence < 70% | Block auto-processing; surface top 3 candidate eras with confidence scores | Modal: "We're not confident about this media's era. Please confirm or select from our best guesses." User selects correct era to proceed. |
| **Processing Failure (Transient)** | Temporary processing error (network, resource) | System retries automatically; user sees progress state | Progress bar pauses briefly, shows "Reprocessing segment..." then continues. Recovery is automatic and transparent. |
| **Processing Failure (Persistent)** | Processing segment fails repeatedly | System completes other segments; provides partial results with retry option | Notification: "One segment failed. Download partial result now or retry failed segment?" User chooses download or retry. |
| **E_HF Violation (Texture Loss)** | Texture Energy metric below threshold | System applies fallback to lower-intensity restoration; generates Uncertainty Callout | Uncertainty Callout: "Frames X-Y may appear softer to preserve original texture." User can accept or manually adjust Fidelity Slider. |
| **Hallucination Limit Exceeded** | Generated content ratio exceeds tier threshold (Conserve: 5%) | Job paused for manual review of problematic segment | Notification: "Segment exceeded authenticity threshold and requires manual review." User approves or rejects restoration for that segment. |
| **Upload Interruption** | Network failure during large file upload | System preserves completed upload progress; enables resume | Banner: "Upload interrupted. [Resume] to continue from where you left off." Resume button continues from last confirmed byte. |
| **Monthly Limit Reached** | User reaches included processing minutes | Jobs blocked; overage approval required | Modal: "You've used X/Y minutes. Approve overage at $Z/min to continue?" Job proceeds only after explicit approval. |
| **Cost Estimate Unavailable** | Cost calculation fails (API error, invalid input) | Job launch blocked; error message with retry option | Error: "Unable to calculate cost estimate. Please try again or contact support." User can retry or cancel. |

**Implementation Notes:**
- **Transient failure handling:** See `ENG-002: API Endpoint Implementation` for retry logic (max 3 attempts, exponential backoff)
- **Idempotency:** See `ENG-002: API Endpoint Implementation` for idempotency key implementation
- **Node failures:** See `OPS-003: Scalability & Load Balancing` for infrastructure resilience
- **Resumable uploads:** See `FR-001: Video Upload and Validation` for GCS resumable upload protocol details

---

## System Boundaries & Out of Scope

**Purpose:** Define what ChronosRefine will NOT build to prevent scope creep and agent confusion.

### Out-of-Scope Media Formats
- **Audio-only files** (MP3, WAV, FLAC) - No video content
- **RAW camera formats** (CR2, NEF, ARW, DNG) - Requires specialized processing
- **Film scans without metadata** - Cannot determine era without context
- **Live streaming video** - Real-time processing not supported
- **360° / VR video** - Specialized restoration algorithms required

### Out-of-Scope Restoration Tasks
- **Colorization** - Adding color to black & white footage (changes historical authenticity)
- **Face reconstruction** - Synthesizing missing facial details (violates "anti-plastic" principle)
- **Frame interpolation** - Creating new frames between existing ones (introduces synthetic motion)
- **Audio restoration** - Noise reduction, dialogue enhancement (separate product domain)
- **Upscaling beyond 4K** - Diminishing returns, not historically authentic

### Out-of-Scope "Authenticity" Features
- **Beautification filters** - Smoothing skin, whitening teeth (violates heritage preservation)
- **Modern sharpening** - Aggressive edge enhancement (creates "plastic" look)
- **HDR tone mapping** - Expanding dynamic range beyond original (not authentic)
- **Slow-motion generation** - Creating slow-motion from normal footage (synthetic)

### Out-of-Scope Business Features
- **Batch processing** - Processing multiple files simultaneously (Phase 2 feature)
- **Team collaboration** - Shared workspaces, comments, approvals (Phase 3 feature)
- **White-label / API access** - Third-party integration (Enterprise tier only)
- **On-premise deployment** - Self-hosted installation (not supported)

---

## Anti-Plastic Metrics Definitions

ChronosRefine uses four core metrics to enforce historical authenticity and prevent "AI Slop" (the waxy, artificial look created by hyperreal enhancement). These metrics are canonically defined here and referenced throughout the requirements.

### E_HF: Texture Energy (High-Frequency)

**Definition:** Measures preservation of fine-grained texture detail in restored media (prevents over-smoothing).

**Calculation:** Mean energy in high-frequency DCT coefficients (>8 cycles/degree) compared to original.

**Units:** Normalized energy ratio (0.0-1.0)

**Acceptable Ranges:**
- **Conserve:** E_HF ≥ 0.85 (preserve 85%+ of original texture)
- **Restore:** E_HF ≥ 0.70 (preserve 70%+ of original texture)
- **Enhance:** E_HF ≥ 0.55 (preserve 55%+ of original texture)

**Violation Behavior:** E_HF below threshold triggers fallback to lower-intensity restoration for affected frames.

**Reference:** See `ENG-003: Quality Metric Calculations` for implementation details.

---

### S_LS: Spectral Low-Slope

**Definition:** Measures color saturation authenticity (prevents over-saturation and "plastic" look).

**Calculation:** Slope of power spectral density in low-frequency range (<2 cycles/degree) in CIE L*a*b* color space.

**Units:** dB/octave

**Acceptable Ranges:**
- **Conserve:** S_LS within ±2 dB of original
- **Restore:** S_LS within ±4 dB of original
- **Enhance:** S_LS within ±6 dB of original

**Violation Behavior:** S_LS outside range triggers adaptive color correction adjustment.

**Reference:** See `ENG-003: Quality Metric Calculations` for implementation details.

---

### T_TC: Temporal Coherence

**Definition:** Measures frame-to-frame consistency (prevents temporal artifacts like flickering).

**Calculation:** Cross-correlation of motion-compensated frame differences using optical flow.

**Units:** Correlation coefficient (0.0-1.0)

**Acceptable Ranges:**
- **All tiers:** T_TC ≥ 0.90 (90%+ temporal consistency required)

**Violation Behavior:** T_TC < 0.90 triggers temporal smoothing filter with 3-frame window.

**Reference:** See `ENG-003: Quality Metric Calculations` for implementation details.

---

### hallucination_limit

**Definition:** Maximum ratio of AI-generated content to original content (prevents "hallucinated" details).

**Calculation:** (generated_pixels / total_pixels) per frame, where generated_pixels are those with <50% confidence in source attribution.

**Units:** Ratio (0.0-1.0)

**Acceptable Ranges:**
- **Conserve:** hallucination_limit ≤ 0.05 (5% max generated content)
- **Restore:** hallucination_limit ≤ 0.15 (15% max generated content)
- **Enhance:** hallucination_limit ≤ 0.30 (30% max generated content)

**Violation Behavior:**
- **Conserve:** Job paused for manual review (user must approve or reject affected segments)
- **Restore/Enhance:** Automatic fallback to lower-intensity restoration

**Reference:** See `SEC-010: Deletion Proofs` for audit trail requirements.

---

### Cross-References

- **Glossary:** See `chronosrefine_glossary.md` for additional metric definitions and era-specific parameters
- **Implementation:** See `ENG-003: Quality Metric Calculations` for code-level implementation details
- **Validation:** See `FR-007: HPS Validation` for human preference scoring methodology
- **Error Handling:** See Error State Catalog below for metric violation behaviors

---

## Functional Requirements

### FR-001: Video Upload and Validation

**Description:** System must support secure, resumable uploads for large media files with format validation.

**Acceptance Criteria:**
- AC-FR-001-01: System supports resumable uploads for files >10GB using signed GCS URLs
- AC-FR-001-02: Signed URLs are generated in <1 second
- AC-FR-001-03: Upload resumes successfully after network interruption without data loss
- AC-FR-001-04: System validates file format (MP4, AVI, MOV, MKV, TIFF, PNG, JPEG) before processing
- AC-FR-001-05: Invalid formats are rejected with clear error message
- AC-FR-001-06: Upload progress is displayed in real-time with percentage and ETA

**Definition of Done:**
- DoD-FR-001-01: Unit tests pass with >95% coverage (measured by pytest-cov, 30+ test cases covering happy path, edge cases, and error scenarios)
- DoD-FR-001-02: Integration tests pass for all 7 supported formats (MP4, AVI, MOV, MKV, TIFF, PNG, JPEG) with 10+ test scenarios per format
- DoD-FR-001-03: API response time < 1s (p50 < 500ms, p95 < 1.2s, p99 < 2s) for signed URL generation (measured by k6 load testing with 100 concurrent users, 1000 requests)
- DoD-FR-001-04: Resumable upload tested with 6 simulated network interruption scenarios (disconnect at 0%, 10%, 25%, 50%, 75%, 99% completion)
- DoD-FR-001-05: Edge case tests pass: 0-byte file (rejected), 100GB file (accepted), corrupted file (rejected), unsupported format (rejected with clear error), expired signed URL (regenerated)
- DoD-FR-001-06: Code review approved by 2+ engineers with security checklist (OWASP Top 10, input validation, authentication, signed URL expiry)
- DoD-FR-001-07: API documentation updated with upload endpoints, request/response examples, error codes (400, 401, 413, 415, 500), rate limits (100 req/min)
- DoD-FR-001-08: Code quality: flake8 passes, pylint score >8.5, cyclomatic complexity <10, no critical/high security issues (Bandit scan)
- DoD-FR-001-09: Performance baseline established: 10GB file uploads complete in <5 minutes on 100Mbps connection (measured by integration tests)

**Verification Method:** Automated (pytest unit tests + integration tests + load testing)

**Test Files:** 
- `tests/api/test_upload.py`
- `tests/integration/test_resumable_upload.py`
- `tests/load/test_upload_performance.py`

**Related Requirements:** ENG-001 (JSON Schema Validation), ENG-002 (API Endpoint Implementation), ENG-016 (Database Technology Selection), SEC-013 (Authentication Provider Selection), OPS-001 (Monitoring & Alerting)

---

### FR-002: Era Detection

**Description:** System must automatically classify media era using Gemini 3 Pro with confidence scoring and manual override capability.

**Inputs:**
- Media file (MP4, AVI, MOV, MKV, TIFF, PNG, JPEG) accessible via GCS signed URL
- File metadata (upload timestamp, file size, original filename, MIME type)
- User ID (for audit trail and billing)
- Job ID (for result storage and tracking)

**Outputs:**
- Era classification (string: "1960s Kodachrome Film", "1980s VHS Tape", etc. from predefined list of 20+ eras)
- Confidence score (float: 0.0-1.0, calibrated probability)
- Top 3 candidate eras with confidence scores (array of {era: string, confidence: float}, only if primary confidence <0.70)
- Forensic markers (JSON object: {grain_structure: string, color_saturation: float, format_artifacts: array})
- Processing timestamp (ISO 8601 format)

**Side Effects:**
- Era classification logged to Cloud Logging (INFO level) with job_id, user_id, era, confidence, latency
- Metrics recorded: classification latency (histogram), confidence distribution (histogram), manual override rate (counter)
- Classification result stored in Supabase (`jobs.era_detection` JSONB column) with TTL of 90 days (automated cleanup job)
- Gemini API usage tracked for billing (tokens consumed, API calls)
- Manual override events logged to audit trail (if user overrides classification)

**Dependencies:**
- Gemini 3 Pro API (Google Cloud Vertex AI) - Required for era classification
- GCS signed URLs (for secure media file access) - Required
- Supabase PostgreSQL (for result storage) - Required
- Cloud Logging (for audit trail) - Required
- Cloud Monitoring (for metrics and alerting) - Required

**Acceptance Criteria:**
- AC-FR-002-01: Gemini 3 Pro analyzes visual signatures to classify era (e.g., "1960s Kodachrome Film," "1980s VHS Tape")
- AC-FR-002-02: Era classification accuracy >90% on Heritage Test Set (2,000 items)
- AC-FR-002-03: Confidence score <0.70 triggers manual user confirmation workflow
- AC-FR-002-04: System surfaces top 3 candidate eras with confidence scores when confidence <0.70
- AC-FR-002-05: User can manually override era classification at any confidence level
- AC-FR-002-06: Manual override triggers warning modal: "AI confidence is X%. Confirm override to [selected era]?"
- AC-FR-002-07: Era classification includes forensic markers: grain structure, color saturation, format-specific artifacts

**Definition of Done:**
- DoD-FR-002-01: Heritage Test Set evaluation shows >92% accuracy (1,840+ correct classifications out of 2,000 items, measured by automated test suite)
- DoD-FR-002-02: Confidence scoring tested with 150+ samples across all confidence ranges (0.0-0.3: 30 samples, 0.3-0.7: 50 samples, 0.7-1.0: 70 samples)
- DoD-FR-002-03: Manual override workflow tested with 12+ UI automation scenarios (Playwright): low confidence trigger, high confidence override, era switching, cancel workflow
- DoD-FR-002-04: Warning modal displays correct confidence score (±0.01 precision) and era name (verified by 8+ Playwright assertions)
- DoD-FR-002-05: Era classification latency <5s for p95, <7s for p99 (measured by Cloud Monitoring with 500+ sample requests)
- DoD-FR-002-06: Fallback logic tested: Gemini API failure → default to "Unknown Era" with manual classification required (5+ failure scenarios)
- DoD-FR-002-07: Code review approved by 2+ engineers with ML model validation checklist (bias testing, edge case coverage, confidence calibration)
- DoD-FR-002-08: API documentation updated with era detection endpoints, confidence score interpretation, supported eras list (20+ eras), error handling
- DoD-FR-002-09: Code quality: pytest passes with >90% coverage, no critical ML bias issues (Fairlearn scan), model versioning documented

**Verification Method:** Automated (pytest unit tests + Heritage Test Set evaluation + Playwright UI tests)

**Test Files:**
- `tests/ml/test_era_detection_service.py`
- `tests/ml/test_gemini_integration.py`
- `tests/api/test_era_detection.py`
- `tests/integration/test_era_detection_e2e.py`

**Related Requirements:** ENG-004 (Era Detection Model), ENG-006 (Quality Metrics Calculation), FR-003 (Fidelity Tier Selection), DS-001 (Fidelity Configuration UX)

---

### FR-003: Fidelity Tier Selection

**Description:** System must allow users to select Fidelity Tier (Enhance/Restore/Conserve) with tier-specific processing parameters.

**Inputs:**
- User persona (string: "Archivist", "Filmmaker", "Prosumer") from user profile
- Job ID (for configuration persistence)
- User ID (for audit trail)
- Previous tier selection (if exists, for persistence)

**Outputs:**
- Selected fidelity tier (string: "Enhance", "Restore", "Conserve")
- Tier-specific processing parameters (JSON object: {E_HF: float, S_LS: float, T_TC: float, hallucination_limit: float, grain_preset: string})
- Cost estimate multiplier (float: 1.0x for Enhance, 1.5x for Restore, 2.0x for Conserve)
- Processing time estimate (minutes per minute of video)

**Side Effects:**
- Tier selection stored in Supabase (`jobs.config` JSONB column, `fidelity_tier` key) with TTL of 90 days (automated cleanup job)
- User preference updated if different from persona default (stored in `users.preferences` JSONB column)
- Metrics recorded: tier selection distribution (counter per tier), override rate (counter)
- Tier selection logged to Cloud Logging (INFO level) with job_id, user_id, tier, override_flag

**Dependencies:**
- Supabase PostgreSQL (for configuration storage) - Required
- User profile service (for persona lookup) - Required
- Cost estimation service (for cost multiplier) - Required
- Cloud Logging (for audit trail) - Required

**Acceptance Criteria:**
- AC-FR-003-01: Three Fidelity Tiers available: Enhance, Restore, Conserve
- AC-FR-003-02: Each tier binds to canonical Anti-Plastic Metrics thresholds (see Anti-Plastic Metrics Definitions section):
  - **Enhance**: E_HF ≥0.55, S_LS within ±6dB of original, T_TC ≥0.90, hallucination_limit ≤0.30, "Subtle" grain preset
  - **Restore**: E_HF ≥0.70, S_LS within ±4dB of original, T_TC ≥0.90, hallucination_limit ≤0.15, "Matched" grain preset
  - **Conserve**: E_HF ≥0.85, S_LS within ±2dB of original, T_TC ≥0.90, hallucination_limit ≤0.05, preserve all original grain, Identity Lock enabled
- AC-FR-003-03: Default tier is persona-specific: Archivist→Conserve, Filmmaker→Restore, Prosumer→Enhance
- AC-FR-003-04: User can override default tier via dropdown selector
- AC-FR-003-05: Tier selection persists for job execution
- AC-FR-003-06: Grain intensity presets (Matched/Subtle/Heavy) are available for each tier
- AC-FR-003-07: User can override grain preset on a per-job basis

**Definition of Done:**
- DoD-FR-003-01: UI audit shows Fidelity Tier selector with all 3 tiers (verified by 15+ Playwright visual regression tests using Percy)
- DoD-FR-003-02: Processing parameters verified for each tier with 25+ unit tests (pytest coverage >95%)
- DoD-FR-003-03: Default tier logic tested for all 3 personas with 12+ test scenarios (Archivist→Conserve, Filmmaker→Restore, Prosumer→Enhance)
- DoD-FR-003-04: Tier override tested with 18+ UI automation scenarios (Playwright): tier switching, parameter updates, warning modals, cancel workflow
- DoD-FR-003-05: Grain preset override tested with 15+ integration tests covering all combinations (3 tiers × 3 presets × edge cases)
- DoD-FR-003-06: Parameter validation: E_HF/S_LS/T_TC thresholds enforced (verified by 20+ unit tests with boundary value analysis)
- DoD-FR-003-07: Code review approved by 2+ engineers with UX checklist (accessibility, responsiveness, error handling)
- DoD-FR-003-08: User documentation updated with tier descriptions, use cases, parameter explanations, and decision matrix
- DoD-FR-003-09: Code quality: flake8 passes, pylint score >8.5, no accessibility violations (axe-core scan)

**Verification Method:** Automated (pytest unit tests) + UI Validation (Playwright tests)

**Test Files:**
- `tests/api/test_fidelity_tiers.py`
- `tests/processing/test_tier_parameters.py`
- `tests/ui/test_tier_selection.spec.ts`

**Related Requirements:** ENG-005 (Fidelity Tier Implementation), ENG-006 (Quality Metrics Calculation), DS-001 (Fidelity Configuration UX), FR-002 (Era Detection)

---

### FR-004: Processing and Restoration

**Description:** System must execute restoration jobs with tier-specific quality metrics, uncertainty callouts, and error handling.

**Inputs:**
- Media file (accessible via GCS signed URL)
- Fidelity tier configuration (from FR-003)
- Era classification (from FR-002)
- Job ID (for result storage and tracking)
- User ID (for billing and audit trail)
- Idempotency key (for deterministic retry behavior)

**Outputs:**
- Restored media file (MP4/TIFF/PNG) stored in GCS with signed download URL
- Quality metrics report (JSON: {E_HF: float, S_LS: float, T_TC: float, hallucination_ratio: float} per frame/segment)
- Uncertainty Callouts (array of {type: string, severity: string, frame_range: array, description: string})
- Processing manifest (JSON: segments processed, fallback events, retry count, cache hits)
- SynthID watermark metadata (JSON: watermark_id, strength, verification_url)
- Processing timestamp (ISO 8601 format)

**Side Effects:**
- Restored file written to GCS bucket (`gs://chronosrefine-outputs/{job_id}/`)
- Processing metrics logged: latency per segment (histogram), GPU utilization (gauge), cache hit rate (counter)
- Uncertainty Callouts stored in Supabase (`uncertainty_callouts` table with `job_id` foreign key)
- Billing event emitted for processing minutes consumed
- SynthID watermark registered in watermark registry
- Failed segments logged to error tracking system (Sentry) with retry count

**Dependencies:**
- GCP Cloud Run Jobs (with GPU acceleration) - Required for processing
- Gemini 3 Pro API (for AI-powered restoration) - Required
- GCS (for input/output file storage) - Required
- Supabase PostgreSQL (for metadata and callouts storage) - Required
- SynthID watermarking service (Google DeepMind) - Required
- Cloud Logging & Monitoring (for observability) - Required

**Acceptance Criteria:**
- AC-FR-004-01: Processing jobs execute as parallel tasks on GCP Cloud Run Jobs with GPU acceleration
- AC-FR-004-02: Anti-plastic metrics (E_HF, S_LS, T_TC) are calculated for all frames
- AC-FR-004-03: Metric violations trigger automatic fallback to lower-intensity restoration
- AC-FR-004-04: Uncertainty Callouts are generated for:
  - E_HF violations (texture loss)
  - Hallucination limit exceeded
  - Low-confidence era classification
  - Identity drift in facial restoration (LPIPS >0.02)
- AC-FR-004-05: Idempotency key ensures deterministic results for retried segments
- AC-FR-004-06: Transient failures trigger automatic retry (max 3 attempts)
- AC-FR-004-07: Persistent failures (3 consecutive failures) result in partial results with failed segment flagged
- AC-FR-004-08: SynthID watermarking applied to all outputs (imperceptible)
- AC-FR-004-09: AV1 Film Grain Synthesis (FGS) parameters injected based on Era Profile
- AC-FR-004-10: Deduplication: cached segment outputs reused for identical reruns within 1-hour window

**Definition of Done:**
- DoD-FR-004-01: Processing pipeline tested end-to-end with 25+ sample videos across all eras and formats (pytest coverage >90%, 150+ test cases)
- DoD-FR-004-02: Anti-plastic metrics calculated correctly with <0.5% error margin (verified against Heritage Test Set with 2,000 items, correlation >0.98)
- DoD-FR-004-03: Fallback logic tested for all metric violations with 30+ scenarios (E_HF, S_LS, T_TC violations × 3 tiers × edge cases)
- DoD-FR-004-04: Uncertainty Callouts generated for all 8 error scenarios with 40+ integration tests (texture loss, hallucination, era confidence, identity drift, etc.)
- DoD-FR-004-05: Idempotency key tested with 20+ duplicate job submissions (100% deterministic results, verified by SHA-256 hash comparison)
- DoD-FR-004-06: Retry logic tested with 15+ simulated transient failures (network timeout, GPU OOM, API rate limit) with exponential backoff verification
- DoD-FR-004-07: SynthID watermark verified with bitstream analysis tool (100% detection rate, imperceptible with PSNR >45dB, 50+ samples)
- DoD-FR-004-08: AV1 FGS parameters verified with bitstream analysis (grain intensity ±5% of target, 30+ samples per era)
- DoD-FR-004-09: Cache hit rate >45% for duplicate jobs (measured by SRE dashboard with 500+ job samples, p95 cache lookup <50ms)
- DoD-FR-004-10: Performance: p95 processing time <2 minutes per minute of video for Enhance tier, <4 min/min for Restore, <8 min/min for Conserve (measured by Cloud Monitoring)
- DoD-FR-004-11: Code review approved by 2+ engineers with ML/GPU optimization checklist (memory efficiency, batch processing, error recovery)
- DoD-FR-004-12: Processing pipeline documentation updated with architecture diagrams, error handling flowcharts, and performance benchmarks
- DoD-FR-004-13: Code quality: pytest passes, no critical GPU memory leaks (profiled with NVIDIA Nsight), error rate <0.1% (measured by SRE)

**Verification Method:** Automated (pytest unit tests + integration tests + bitstream analysis)

**Test Files:**
- `tests/processing/test_restoration_pipeline.py`
- `tests/processing/test_anti_plastic_metrics.py`
- `tests/processing/test_fallback_logic.py`
- `tests/processing/test_uncertainty_callouts.py`
- `tests/processing/test_idempotency.py`
- `tests/processing/test_retry_logic.py`
- `tests/processing/test_synthid_watermark.py`
- `tests/processing/test_av1_fgs.py`
- `tests/processing/test_deduplication.py`

**Related Requirements:** ENG-003 (Video Processing Pipeline), ENG-005 (Fidelity Tier Implementation), ENG-006 (Quality Metrics Calculation), ENG-007 (Reproducibility Proof), ENG-011 (Async Processing), SEC-003 (Data Classification), OPS-004 (Performance Monitoring)

---

### FR-005: Output Delivery

**Description:** System must deliver restored media with transformation manifest, deletion proof, and export options.

**Inputs:**
- Job ID (for result retrieval)
- User ID (for authorization check)
- Restored media file (from FR-004, accessible via GCS signed URL)
- Processing manifest (from FR-004)
- Uncertainty Callouts (from FR-004)

**Outputs:**
- Download package (ZIP file containing: restored media, quality report PDF, uncertainty callouts JSON, transformation manifest JSON)
- Signed download URL (GCS, expires in 7 days)
- Deletion proof (cryptographic hash of original file + restoration parameters, for audit trail)
- Download expiration timestamp (ISO 8601 format)

**Side Effects:**
- Download package created in GCS (`gs://chronosrefine-downloads/{job_id}/`)
- Signed URL generated with 7-day expiration
- Deletion proof stored in Supabase (`deletion_proofs` table with `job_id` foreign key) with permanent retention
- Download event logged to Cloud Logging (INFO level) with job_id, user_id, package_size, timestamp
- Metrics recorded: download latency (histogram), package size distribution (histogram), download success rate (counter)
- Email notification sent to user with download link (if enabled in user preferences)

**Dependencies:**
- GCS (for download package storage) - Required
- Supabase PostgreSQL (for deletion proof storage) - Required
- Cloud Logging (for audit trail) - Required
- Email service (SendGrid) - Optional for notifications
- Cryptographic hash service (SHA-256) - Required for deletion proofs

**Acceptance Criteria:**
- AC-FR-005-01: Final deliverables include:
  - Restored media file (MP4/AV1 container)
  - Transformation Manifest (JSON file documenting every restoration step)
  - Deletion Proof (cryptographically signed, exportable as PDF)
- AC-FR-005-02: Transformation Manifest includes:
  - Job ID, timestamp, user ID
  - Era Profile selected
  - Fidelity Tier and parameters
  - Anti-plastic metrics (E_HF, S_LS, T_TC) per frame range
  - Uncertainty Callouts with frame ranges
  - Model versions (CodeFormer, Gemini, AV1 encoder)
  - Environment pinning (container digest, GPU driver version)
- AC-FR-005-03: Deletion Proof includes:
  - Cloud Audit Log `ObjectDelete` event
  - Timestamp (UTC)
  - Cryptographic signature (SHA-256)
  - Exportable as PDF within 10 seconds
- AC-FR-005-04: Export Completion Rate >85% (percentage of started jobs that result in successful download)
- AC-FR-005-05: Download links expire after 7 days (configurable per tier)
- AC-FR-005-06: Museum Tier customers can request extended download link retention (up to 90 days)

**Definition of Done:**
- DoD-FR-005-01: Transformation Manifest generated for 100% of jobs (verified with 50+ integration tests across all tiers and error scenarios)
- DoD-FR-005-02: Manifest includes all 15+ required fields with JSON Schema v2020-12 validation (automated validation in CI/CD pipeline)
- DoD-FR-005-03: Deletion Proof generated and verified with Cloud Audit Logs (100% match rate, tested with 30+ deletion scenarios)
- DoD-FR-005-04: Deletion Proof PDF export completes in <8 seconds p95, <10 seconds p99 (measured by load testing with 100 concurrent requests)
- DoD-FR-005-05: Export Completion Rate >87% (measured by analytics with 1,000+ job samples, failure reasons categorized and logged)
- DoD-FR-005-06: Download link expiration tested with 20+ scenarios (7-day default, 90-day Museum Tier, manual extension, expired link handling)
- DoD-FR-005-07: ZIP integrity verified: all files present, no corruption (tested with 40+ samples, CRC32 validation)
- DoD-FR-005-08: Code review approved by 2+ engineers with compliance checklist (GDPR deletion rights, audit trail completeness, data retention)
- DoD-FR-005-09: API documentation updated with export endpoints, manifest schema, deletion proof format, error codes (404, 410, 500)
- DoD-FR-005-10: Code quality: flake8 passes, no security issues in PDF generation (Bandit scan), manifest serialization tested for injection attacks

**Verification Method:** Automated (pytest unit tests + integration tests) + Manual (PDF export verification)

**Test Files:**
- `tests/api/test_output_delivery.py`
- `tests/api/test_transformation_manifest.py`
- `tests/api/test_deletion_proof.py`
- `tests/integration/test_export_workflow.py`

**Related Requirements:** ENG-010 (Transformation Manifest Generation), ENG-015 (Output Encoding), SEC-010 (Deletion Proofs), SEC-011 (Dataset Provenance), OPS-001 (Monitoring & Alerting)

---

### FR-006: Preview Generation

**Description:** System must generate 10 scene-aware keyframes for user review before full processing.

**Inputs:**
- Job ID (for preview generation)
- User ID (for authorization check)
- Source media file (original upload, accessible via GCS signed URL)
- Era classification (from FR-002)
- Fidelity tier configuration (from FR-003)
- Preview request (optional: specific timestamp or segment)

**Outputs:**
- Preview artifacts (lightweight restoration of 10 keyframes using tier configuration)
- Preview thumbnail grid (JPEG, 3x3 grid showing before/after comparison)
- Preview metadata (JSON: {keyframe_count: int, scene_diversity: float, estimated_cost: float, estimated_time: float})
- Preview signed URL (GCS, expires in 24 hours)

**Side Effects:**
- Preview file generated and stored in GCS (`gs://chronosrefine-previews/{job_id}/`)
- Signed URL generated with 24-hour expiration
- Preview generation logged to Cloud Logging (INFO level) with job_id, user_id, preview_duration, latency
- Metrics recorded: preview generation latency (histogram), preview size (histogram), preview view count (counter)
- Preview cached for 24 hours (subsequent requests return cached preview)

**Dependencies:**
- GCS (for preview storage) - Required
- FFmpeg (for video encoding and thumbnail generation) - Required
- Cloud Run Jobs (for preview generation) - Required
- Cloud Logging (for audit trail) - Required
- Cloud CDN (for preview delivery) - Optional for performance

**Acceptance Criteria:**
- AC-FR-006-01: System generates exactly 10 keyframes per video
- AC-FR-006-02: Keyframes are scene-aware (distributed across scenes, not just first 10 frames)
- AC-FR-006-03: Scene detection algorithm identifies scene cuts and distributes keyframes evenly
- AC-FR-006-04: p95 generation time <6 seconds (measured by Cloud Monitoring)
- AC-FR-006-05: Keyframes are representative of full video (cover beginning, middle, end)
- AC-FR-006-06: Preview modal displays all 10 keyframes in a grid layout
- AC-FR-006-07: User can click keyframe to view full-size preview
- AC-FR-006-08: Preview includes cost estimate and processing time estimate
- AC-FR-006-09: User can approve or reject preview before launching full processing

**Definition of Done:**
- DoD-FR-006-01: Scene detection algorithm tested with 35+ sample videos across all eras and scene types (fast cuts, slow fades, static shots, action sequences)
- DoD-FR-006-02: Keyframe distribution verified with statistical analysis: Gini coefficient <0.3 (not clustered), coverage of beginning/middle/end (tested with 50+ videos)
- DoD-FR-006-03: p95 generation time <5.5s, p99 <8s (measured by k6 load testing with 200 concurrent requests, 1,000+ samples)
- DoD-FR-006-04: Preview modal tested with 25+ UI automation scenarios (Playwright): grid layout, responsive design (320px-2560px), image loading, error states
- DoD-FR-006-05: Full-size preview tested with 15+ UI automation scenarios: click to expand, close modal, keyboard navigation (ESC key), touch gestures
- DoD-FR-006-06: Cost estimate displayed correctly in preview modal with ±$0.01 accuracy (verified by 30+ test cases with known cost calculations)
- DoD-FR-006-07: Approve/reject workflow tested with 20+ integration tests: approve→launch job, reject→return to config, timeout handling
- DoD-FR-006-08: Scene diversity metric >0.7 (measured by histogram difference between keyframes, tested with 40+ videos)
- DoD-FR-006-09: Code review approved by 2+ engineers with performance checklist (GPU optimization, parallel processing, caching strategy)
- DoD-FR-006-10: API documentation updated with preview endpoints, scene detection algorithm, keyframe selection logic, performance SLAs
- DoD-FR-006-11: Code quality: pytest coverage >92%, no performance regressions (benchmarked against baseline), image quality verified (PSNR >40dB)

**Verification Method:** Automated (pytest unit tests + load testing + Playwright UI tests)

**Test Files:**
- `tests/processing/test_preview_generation.py`
- `tests/processing/test_scene_detection.py`
- `tests/ui/test_preview_modal.spec.ts`
- `tests/load/test_preview_performance.py`

**Related Requirements:** ENG-014 (Preview Generation), DS-001 (Fidelity Configuration UX), NFR-001 (Cost Estimate Display), FR-002 (Era Detection), FR-003 (Fidelity Tier Selection)

---

### FR-007: Human Preference Score (HPS) Validation

**Description:** System must achieve ≥75% Human Preference Score (HPS) in EACH of the 6 media categories before General Availability (GA) launch. HPS measures whether human evaluators prefer the restored output over the original for the stated goal of "historical authenticity preservation."

**Inputs:**
- Heritage Test Set (2,000 curated media items, stratified by era and damage severity)
- Restored outputs (from FR-004, for all 2,000 test items)
- Evaluator pool (≥20 qualified evaluators with credentials and consent forms)
- HPS evaluation platform (blind A/B comparison interface)
- Evaluation responses (array of {item_id: string, evaluator_id: string, preference: string, timestamp: ISO8601})

**Outputs:**
- HPS score per category (float: 0.0-1.0, percentage of evaluations preferring restored output)
- Confidence intervals per category (95% CI: [lower_bound, upper_bound])
- Statistical significance results (Chi-square test, p-value, Krippendorff's alpha for inter-rater reliability)
- Category-specific launch decision (boolean: true if HPS ≥75%, false otherwise)
- Failure analysis report (for categories <75%: common failure modes, evaluator feedback, improvement recommendations)

**Side Effects:**
- HPS evaluation results stored in Supabase (`hps_evaluations` table with `evaluation_id` primary key) with permanent retention
- Evaluation responses logged to Cloud Logging (INFO level) with anonymized evaluator IDs
- Metrics recorded: HPS per category (gauge), evaluation completion rate (counter), inter-rater reliability (gauge)
- Launch decision documented in formal report (PDF, stored in GCS)
- Email notification sent to product team with HPS results
- GA launch blocked for categories <75% (feature flag updated in LaunchDarkly)

**Dependencies:**
- Heritage Test Set (curated dataset with provenance and rights) - Required
- HPS evaluation platform (custom web app with blind A/B testing) - Required
- Supabase PostgreSQL (for evaluation data storage) - Required
- Statistical analysis library (scipy, statsmodels) - Required for significance testing
- LaunchDarkly (for feature flag management) - Required for launch gating
- Cloud Logging (for audit trail) - Required

**Acceptance Criteria:**
- AC-FR-007-01: HPS protocol defined with formal methodology (blind A/B testing, evaluator qualification criteria, scoring rubric)
- AC-FR-007-02: Heritage Test Set prepared with ≥333 items per media category (Daguerreotype, Albumen, 16mm, Super 8, Kodachrome, VHS)
- AC-FR-007-03: Evaluator pool recruited with ≥20 qualified evaluators (mix of archivists, filmmakers, historians)
- AC-FR-007-04: HPS measured independently for each media category (not averaged across categories)
- AC-FR-007-05: HPS ≥75% threshold met in ALL 6 categories individually before GA launch
- AC-FR-007-06: HPS results documented with statistical significance (p<0.05, confidence intervals reported)
- AC-FR-007-07: Category-specific launch strategy defined for categories failing to meet 75% threshold
- AC-FR-007-08: HPS re-validation triggered after any changes to core AI models or quality metrics

**Definition of Done:**
- DoD-FR-007-01: HPS protocol document created with formal methodology: evaluator qualification criteria (minimum 2 years experience in relevant field), blind A/B testing procedure, scoring rubric (1-5 scale with detailed anchors), statistical analysis plan
- DoD-FR-007-02: Heritage Test Set curated with 2,000 items total (333 per category, stratified by damage severity: 33% light, 33% moderate, 33% severe)
- DoD-FR-007-03: Dataset governance validated: all test items have documented provenance, usage rights, PII compliance (see `docs/specs/chronosrefine_prd_v9.md#dataset-governance--rights`)
- DoD-FR-007-04: Evaluator pool recruited with ≥20 qualified evaluators: 8 institutional archivists, 8 documentary filmmakers, 4 historians/curators
- DoD-FR-007-05: HPS evaluation platform built: blind A/B comparison interface, randomized presentation order, evaluator authentication, response collection, statistical analysis dashboard
- DoD-FR-007-06: HPS measured for all 6 categories with ≥50 evaluations per item (1,000 total evaluations per category, 6,000 total)
- DoD-FR-007-07: Statistical analysis complete: HPS calculated per category with 95% confidence intervals, inter-rater reliability (Krippendorff's alpha >0.7), significance testing (Chi-square test, p<0.05)
- DoD-FR-007-08: HPS results documented in formal report: methodology, results per category, confidence intervals, evaluator demographics, failure analysis for categories <75%
- DoD-FR-007-09: Category-specific launch strategy documented: categories ≥75% proceed to GA, categories <75% remain in beta with improvement roadmap
- DoD-FR-007-10: HPS re-validation process defined: trigger conditions (model updates, metric changes), re-validation timeline (within 30 days of changes), delta threshold for re-launch (±5% HPS change)
- DoD-FR-007-11: Legal review complete: evaluator consent forms, data usage agreements, Heritage Test Set licensing confirmed
- DoD-FR-007-12: Code quality: HPS evaluation platform tested with 50+ test scenarios (UI automation, data collection, statistical analysis), security audit passed (evaluator PII protection)

**Verification Method:** Manual (human evaluation) + Automated (statistical analysis + platform testing)

**Test Files:**
- `tests/hps/test_evaluation_platform.py`
- `tests/hps/test_statistical_analysis.py`
- `tests/hps/test_heritage_test_set.py`
- `tests/ui/test_hps_evaluation_interface.spec.ts`

**Related Requirements:** FR-003 (Fidelity Tier Selection), ENG-003 (Quality Metric Calculations), ENG-005 (Era Classification)

**Implementation Guidance:**
- 📄 **HPS Protocol:** `docs/specs/chronosrefine_prd_v9.md#beta-exit-criteria-ga-readiness`
- 📄 **Heritage Test Set:** `docs/specs/chronosrefine_implementation_plan.md#phase-3-core-processing-pipeline--ai-integration`
- 📄 **Dataset Governance:** `docs/specs/chronosrefine_prd_v9.md#dataset-governance--rights`
- 📄 **Statistical Methods:** derive from this requirement plus `tests/hps/test_statistical_analysis.py`; no separate canonical companion engineering spec currently exists

---

**End of Functional Requirements**

---

## References

[1] User complaints about "AI Slop" and plastic-looking faces in mass-market restoration tools  
[2] AV1 Film Grain Synthesis (FGS) specification: https://aomedia.org/av1/specification/  
[3] Gemini 3 Pro visual reasoning capabilities for era detection  

---
