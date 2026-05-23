# ChronosRefine Phase 5 Packet 5A Kickoff

**Date:** 2026-04-03
**Phase:** Phase 5 - Advanced Features & UX Refinement
**Packet:** Packet 5A
**Requirement Focus:** `FR-006`
**Status:** Hosted-complete Packet 5A kickoff and scope record; hosted closeout evidence is recorded in `docs/specs/chronosrefine_phase5_packet5a_closeout_note.md`
**Source of truth:** `docs/specs/*` canonical ordering in `AGENTS.md`

---

**Repository note:** This packet is anchored to merged `main` only. Local workspace-only preview-review, pricing, compliance, or migration code is reference material for future implementation work but does not count as merged baseline truth.

## 1) Objective

Close the Phase 5 gap between the merged Packet 4F preview substrate and the full `FR-006` user flow by planning the first preview-review packet on top of the existing owner-scoped preview session APIs.

Packet 5A starts Phase 5 with the smallest requirement-scoped slice that:

1. keeps the merged Packet 4 preview-generation substrate intact
2. adds a real approve/reject gate before processing launch
3. preserves existing Packet 4E launch-cost review and Packet 4C job-launch semantics where possible
4. avoids pulling pricing enforcement, broader GDPR work, or Phase 6 rollout scope forward

## 2) Dependency And Gate Check

Confirmed against merged canon on `main`:

- Phase 4 is complete on `main`; Packet 4F already delivers the preview-generation substrate required by `ENG-014`.
- Phase 5 kickoff criteria are recorded in merged canon:
  - pricing clearance: `docs/specs/chronosrefine_phase5_pricing_clearance.md`
  - GDPR / legal gate: `docs/specs/chronosrefine_phase5_gdpr_legal_clearance.md`
  - DPA status: `docs/specs/chronosrefine_phase5_dpa_status.md`
- `FR-006` dependencies in the coverage matrix remain:
  - `FR-001`
  - `FR-002`
  - `ENG-007`
  - `ENG-014`

Merged-baseline preview evidence already present:

- `app/api/previews.py` exposes `POST /v1/previews` and `GET /v1/previews/{preview_id}` only.
- `app/services/preview_generation.py` already generates scene-aware preview sessions, estimated cost/time metadata, cached rereads, and stale/expired preview handling.
- `tests/api/test_preview_sessions.py`, `tests/integration/test_preview_pipeline.py`, `tests/processing/test_preview_generation.py`, `tests/processing/test_scene_detection.py`, and `tests/load/test_preview_performance.py` already cover the Packet 4F substrate.
- `docs/api/openapi.yaml` documents the create/reread preview routes only.
- `web/src/App.tsx` still launches processing through the existing Packet 4E launch-cost review flow; no merged preview-review UI exists yet.

## 3) In Scope

Packet 5A is the merged-main kickoff packet for `FR-006`. It should implement the smallest end-to-end preview-review gate that satisfies the canonical requirement without expanding into unrelated Phase 5 requirements.

### 3.1 Backend / API Scope

1. Add owner-scoped preview review actions on top of the existing preview-session model:
   - `POST /v1/previews/{preview_id}/review`
   - `POST /v1/previews/{preview_id}/launch`
2. Extend the preview-session contract with review-state fields needed for deterministic launch gating:
   - `review_status` with `pending | approved | rejected`
   - `reviewed_at`
3. Enforce the preview approval gate on the backend:
   - preview launch succeeds only from an approved, current, owner-scoped preview
   - stale or expired previews cannot launch
   - Packet 5A gates preview-launch and the first-party UI only; generic `POST /v1/jobs` preview-approval enforcement remains deferred
4. Reuse the existing Packet 4 preview substrate and Packet 4 job-launch logic rather than replacing them.
5. Add any required persistence changes for preview review state, including migration work if the persisted preview-session model needs new fields.

### 3.2 UI Scope

1. Add a preview-review flow on top of the saved launch-ready configuration:
   - render the 10-keyframe grid
   - support full-size inspection from the grid
   - show preview cost and processing-time estimate
   - expose explicit approve / reject actions
2. Change the primary launch path so users review the preview before full processing starts.
3. Keep the Packet 4E launch-cost review path as a downstream integration target rather than deleting it in Packet 5A.
4. Canonical NFR numbering and ownership follow `docs/specs/chronosrefine_nonfunctional_requirements.md`; Packet 5A may reference `NFR-008` as a quality bar only, and formal `NFR-008` completion remains Phase 6 work.

### 3.3 Documentation / Test Scope

1. Update OpenAPI and API contract docs for the new review / launch routes and review-state fields.
2. Extend or add mapped tests for:
   - backend review-state transitions
   - launch-blocking behavior before approval
   - approved-preview launch success
   - UI preview modal and review interactions
   - accessibility coverage for any new preview-review modal
   - preview latency guardrails under load

## 4) Out Of Scope

Packet 5A must not absorb the rest of Phase 5.

- `NFR-006` pricing enforcement, entitlement resolution, billing portal wiring, and broader Stripe rollout work
- broader `SEC-006` GDPR implementation beyond the already-recorded kickoff gate
- `SEC-001` through `SEC-005` hardening packets
- `NFR-004`, `NFR-005`, and disaster-recovery work
- `NFR-009` i18n foundations
- production rollout, canary, or Phase 6 launch-readiness tasks
- any assumption that local preview-review routes, modal code, tests, or migrations are already merged
- claiming global `FR-006` closeout from Packet 5A alone

## 5) Required Extension Surfaces

These are the likely merged-main extension points for Packet 5A implementation:

- `app/api/previews.py`
- `app/api/contracts.py`
- `app/services/preview_generation.py`
- `app/db/phase2_store.py`
- `supabase/migrations/`
- `docs/api/openapi.yaml`
- `web/src/App.tsx`
- `web/src/lib/processingHelpers.ts`
- `tests/api/test_preview_sessions.py`
- `tests/integration/test_preview_pipeline.py`
- `tests/load/test_preview_performance.py`

The following canonical Phase 5 test targets do not exist on merged `main` yet and should be treated as planned additions, not merged evidence:

- `tests/ui/test_preview_modal.spec.ts`
- a dedicated preview-review accessibility suite if the packet introduces a new modal

## 6) Requirement Mapping

### Primary Requirement

- `FR-006` Preview Generation

### Dependencies Already Satisfied On `main`

- `FR-001`
- `FR-002`
- `ENG-007`
- `ENG-014`

### Supporting Constraints

Packet 5A should continue to honor already-merged accessibility and launch-flow patterns from Phase 4 without re-opening those packets as new requirement scope.

## 7) Acceptance Contract For Packet 5A

Packet 5A should not be counted as merged progress until all of the following are true:

1. Preview creation on the approved implementation returns a deterministic `review_status = pending`.
2. Preview review can transition the current preview to `approved` or `rejected`.
3. Launch attempts without an approved current preview fail with a deterministic `409 Preview Approval Required`-style response.
4. Launch from an approved current preview succeeds through the existing processing pipeline and reaches terminal state in integration coverage.
5. Preview rereads remain owner-scoped, stale/expired behavior remains correct, and preview approval cannot be replayed across changed configurations.
6. The preview UI renders the 10-keyframe grid, supports full-size inspection, and displays cost/time estimate data.
7. Packet 5A accessibility coverage exists for any new preview-review modal or equivalent interaction surface.
8. OpenAPI is updated for the new preview-review API shape.
9. Packet 5A is recorded as an `FR-006` slice only; global `FR-006` closeout is not yet claimed.
9. Preview generation remains under the canonical `<6s p95` Phase 5 guardrail.

## 8) Planned Test Mapping

### Existing merged-main tests to extend

- `tests/api/test_preview_sessions.py`
- `tests/integration/test_preview_pipeline.py`
- `tests/processing/test_preview_generation.py`
- `tests/processing/test_scene_detection.py`
- `tests/load/test_preview_performance.py`
- `tests/api/test_endpoints.py`

### Planned Packet 5A additions

- `tests/ui/test_preview_modal.spec.ts`
- preview-review accessibility coverage for the new modal or review surface

## 9) Rollout Evidence

Local and CI proof:

1. Packet 5A mapped tests pass locally and in CI.
2. `python3 scripts/validate_test_traceability.py` passes if new tests are added.
3. `.agents/skills/spec-consistency-audit/scripts/audit_specs.sh <repo-root>` passes after docs/OpenAPI updates.

Hosted proof in `chronos_dev`:

1. Deploy the Packet 5A candidate revision to the shared hosted environment.
2. Capture a live smoke showing:
   - preview creation succeeds and returns `review_status = pending`
   - direct launch without approval is blocked
   - preview approval succeeds
   - launch from the approved preview succeeds
3. Capture preview latency evidence against the hosted runtime and confirm the canonical p95 guardrail remains satisfied.
4. If Packet 5A adds persistent review-state columns, dry-run and apply the required migration against the hosted database before counting the packet complete.

Hosted closeout for the delivered packet is recorded in `docs/specs/chronosrefine_phase5_packet5a_closeout_note.md`.

## 10) Risks And Mitigations

1. **Risk:** Preview-review UI changes accidentally bypass or replace the existing Packet 4E launch-cost review logic.
   **Mitigation:** Treat the Packet 4E modal as an integration point, not a redesign target, and keep `/v1/jobs` semantics stable except for the new approval gate.

2. **Risk:** Review state becomes detached from the saved configuration and allows stale-preview launches.
   **Mitigation:** Bind launch eligibility to the current preview session and configuration fingerprint, not to upload ownership alone.

3. **Risk:** The packet expands into pricing or GDPR implementation because those gate notes now exist in canon.
   **Mitigation:** Keep pricing and GDPR work explicitly out of scope for Packet 5A and count only `FR-006`.

4. **Risk:** Packet 5A is counted complete from local workspace-only evidence.
   **Mitigation:** Require hosted `chronos_dev` smoke plus any required migration evidence before the packet is marked merged progress.

## 11) Exit Definition For This Planning Packet

This kickoff artifact is complete when:

1. Packet 5A scope is defined against merged `main`, not against the dirty local Phase 5 workspace.
2. `FR-006` is identified as the Phase 5 kickoff packet with explicit in-scope and out-of-scope boundaries.
3. Backend, UI, OpenAPI, and test surfaces are named clearly enough to start implementation without reopening Phase 5 gating.
4. Required rollout evidence is defined before any implementation branch claims Packet 5A progress.
