# ChronosRefine Phase 5 Packet 5A Execution Packet

**Date:** 2026-04-04
**Phase:** Phase 5 - Advanced Features & UX Refinement
**Packet:** Packet 5A
**Requirement Focus:** `FR-006`
**Status:** Hosted-complete execution record for Packet 5A; closeout evidence is recorded in `docs/specs/chronosrefine_phase5_packet5a_closeout_note.md`
**Source of truth:** `docs/specs/*` canonical ordering in `AGENTS.md`

---

**Boundary note:** This packet is derived from merged `origin/main` at merge commit `76aa3cd`. The dirty local workspace at `/Users/geekboy/Projects/chronos_dev` is reference-only and must not be used as the implementation base.

## 1) Requirement

- `FR-006` Preview Generation
- Canonical requirement: `docs/specs/chronosrefine_functional_requirements.md#fr-006-preview-generation`
- Canonical kickoff packet: `docs/specs/chronosrefine_phase5_packet5a_kickoff.md`

## 2) Phase

- Assigned phase: Phase 5
- Coverage matrix status before packet closeout: `0/11` full requirements complete, with Packet 5A later closing the first hosted `FR-006` slice
- Implementation-plan status before packet closeout: Phase 5 entry criteria were satisfied in merged canon, but no Phase 5 requirement had hosted evidence yet

## 3) Dependencies

### Satisfied on merged `main`

- `FR-001`
- `FR-002`
- `ENG-007`
- `ENG-014`
- Phase 5 pricing kickoff governance recorded in `docs/specs/chronosrefine_phase5_pricing_clearance.md`
- Phase 5 GDPR / legal kickoff governance recorded in:
  - `docs/specs/chronosrefine_phase5_gdpr_legal_clearance.md`
  - `docs/specs/chronosrefine_phase5_dpa_status.md`

### Remaining gate for Packet completion, not kickoff

- Hosted rollout evidence in `chronos_dev`
- Any required preview-review persistence migration evidence

## 4) Acceptance Scope

Packet 5A should implement the smallest requirement-complete preview-review gate for `FR-006` on top of the merged Packet 4F preview substrate.

### In scope

1. Add review-state support to preview sessions:
   - `review_status`
   - `reviewed_at`
2. Add owner-scoped preview review and launch routes:
   - `POST /v1/previews/{preview_id}/review`
   - `POST /v1/previews/{preview_id}/launch`
3. Block launch until the current preview is approved.
4. Keep preview reread, stale-preview handling, and owner scoping intact.
5. Add a preview-review UI path using the existing saved configuration flow.
6. Keep the Packet 4E launch-cost review path as an integration point rather than replacing launch semantics wholesale.
7. Packet 5A gates preview-launch and first-party UI only; generic `POST /v1/jobs` preview-approval enforcement remains deferred.
8. Canonical NFR numbering and ownership follow `docs/specs/chronosrefine_nonfunctional_requirements.md`; Packet 5A references `NFR-008` as a quality bar only, and formal `NFR-008` completion remains Phase 6 work.
9. Update OpenAPI and tests for the new API shape and preview-review flow.

### Out of scope

- `NFR-006` pricing enforcement and tier-gating implementation
- broader `SEC-006` GDPR workflow delivery
- `SEC-001` through `SEC-005`
- `NFR-004`, `NFR-005`, `NFR-009`
- Phase 6 rollout / launch-readiness work
- any assumption that the dirty local preview-review implementation is already merged
- claiming global `FR-006` closeout from Packet 5A alone

## 5) Files To Change

### Backend / contract

- `app/api/contracts.py`
  - Add `PreviewReviewStatus`
  - Add review request payload
  - Extend `PreviewSessionResponse` with review-state fields
- `app/api/previews.py`
  - Add preview review and preview launch routes
- `app/services/preview_generation.py`
  - Add review-state update and approved-preview launch orchestration
  - Preserve existing create/reread preview behavior
- `app/db/phase2_store.py`
  - Persist preview review-state fields in memory and Supabase-backed repositories

### Persistence / schema

- `supabase/migrations/`
  - Add a preview-review migration only if the current persistent preview-session schema needs new review-state fields

### UI

- `web/src/App.tsx`
  - Integrate preview creation, review, and launch gating into the existing launch flow
- `web/src/lib/previewHelpers.ts`
  - Add frontend API helpers for preview create/review/launch
- `web/src/components/PreviewReviewModal.tsx`
  - Add preview-review UI shell if the implementation uses a dedicated modal
- `web/src/lib/processingHelpers.ts`
  - Keep changes minimal and limited to launch integration points

### Docs

- `docs/api/openapi.yaml`
  - Add only the new Packet 5A preview-review routes and schema fields

### Tests

- `tests/api/test_preview_sessions.py`
- `tests/integration/test_preview_pipeline.py`
- `tests/database/test_schema_migrations.py`
- `tests/load/test_preview_performance.py`
- `tests/api/test_endpoints.py`
- `tests/ui/test_preview_modal.spec.ts`
- `tests/accessibility/test_preview_review_modal_a11y.spec.ts`

## 6) Planned Implementation Sequence

1. Backend contract and persistence
   - add review-state enums / request model
   - add repository support for `review_status` and `reviewed_at`
2. Backend review and launch flow
   - add review route
   - add approved-preview launch route
   - preserve stale/expired/owner-scoped protections
3. OpenAPI and endpoint coverage
   - document route additions and new response fields
   - update endpoint smoke assertions
4. UI integration
   - add preview review modal/surface
   - wire review and launch into the saved configuration flow
   - avoid mixing Packet 5A with pricing-upgrade policy changes
5. UI / accessibility tests
   - add or adapt Packet 5A modal coverage
6. Hosted evidence
   - only after local/CI proof is stable

## 7) Tests

### Existing tests to update

- `tests/api/test_preview_sessions.py`
  - add review-state default assertions
  - add approve/reject transitions
  - add blocked launch before approval
  - add launch success after approval
- `tests/integration/test_preview_pipeline.py`
  - extend for launch gating and stale-preview invalidation behavior
- `tests/database/test_schema_migrations.py`
  - add migration assertions only if a review-state migration lands
- `tests/load/test_preview_performance.py`
  - keep preview-generation latency guardrail intact
- `tests/api/test_endpoints.py`
  - assert new OpenAPI paths and schemas

### New tests to add

- `tests/ui/test_preview_modal.spec.ts`
  - preview review flow, selection, approve/reject, and launch handoff
- `tests/accessibility/test_preview_review_modal_a11y.spec.ts`
  - preview-review accessibility coverage if a dedicated modal lands

## 8) Verification

### Planning / docs checks

```bash
./.agents/skills/requirement-implementation-planner/scripts/plan_requirement.sh FR-006 /tmp/chronos_phase5_packet5a_impl
./.agents/skills/spec-consistency-audit/scripts/audit_specs.sh /tmp/chronos_phase5_packet5a_impl
```

### Expected implementation checks once code lands

```bash
python3 scripts/validate_test_traceability.py
./.venv/bin/pytest tests/api/test_preview_sessions.py tests/api/test_endpoints.py tests/database/test_schema_migrations.py tests/integration/test_preview_pipeline.py tests/load/test_preview_performance.py -q
./.venv/bin/pytest tests/processing/test_preview_generation.py tests/processing/test_scene_detection.py -q
./node_modules/.bin/pnpm -C web test -- ../tests/ui/test_preview_modal.spec.ts ../tests/accessibility/test_preview_review_modal_a11y.spec.ts
```

### Hosted proof recorded for Packet 5A closeout

Packet 5A closeout evidence now lives in `docs/specs/chronosrefine_phase5_packet5a_closeout_note.md`, including:

1. local validation gates
2. `chronos_dev` migration evidence through `0024`
3. least-privilege Secret Manager / IAM unblock for `STRIPE_SECRET_KEY`
4. hosted smoke for preview pending/approval/idempotent launch/stale anti-replay/cross-user denial
5. publish-failure retry proof with stable bound `job_id`
6. generic `/v1/jobs` non-regression proof
7. hosted preview latency sample under the canonical `<6s p95` guardrail

## 9) Risks

1. **Preview-review flow absorbs pricing enforcement**
   - Keep all `upgrade_required` or broader entitlement-policy changes out of Packet 5A
2. **Launch semantics drift**
   - Reuse Packet 4E launch-cost review and existing job-launch semantics where possible
3. **Stale preview reuse**
   - Bind launch approval to the current configuration fingerprint
4. **Counting local-only work as done**
   - Require merged code plus hosted rollout evidence

## 10) Dirty Workspace Triage

The local dirty workspace contains candidate Packet 5A code and unrelated broader Phase 5 changes. Triage it before reusing anything.

### Reuse candidates

These align closely with Packet 5A scope and can be cherry-picked or manually reapplied in small slices:

- `app/api/contracts.py`
  - review-state enum and response/request model additions
- `app/api/previews.py`
  - review and launch route shape
- `app/db/phase2_store.py`
  - review-state persistence additions
- `app/services/preview_generation.py`
  - review-state updates and approved-preview launch guard
- `tests/api/test_preview_sessions.py`
  - backend review/launch acceptance coverage
- `tests/database/test_schema_migrations.py`
  - review-state migration assertions
- `web/src/lib/previewHelpers.ts`
  - narrow API helper surface for preview create/review/launch
- `web/src/components/PreviewReviewModal.tsx`
  - UI shell and interaction model
- `tests/ui/test_preview_modal.spec.ts`
  - preview-review UI coverage
- `tests/accessibility/test_preview_review_modal_a11y.spec.ts`
  - modal accessibility coverage

### Defer

These may be useful later, but they should not be carried into the first narrow implementation slice until the core Packet 5A flow is stable:

- `scripts/ops/run_packet5a_live_smoke.py`
  - useful for hosted closeout, not required to begin implementation
- `supabase/migrations/0024_phase5_preview_review_gate.sql`
  - use only if the final implementation truly needs a schema migration
- `docs/api/openapi.yaml` from the dirty workspace
  - recreate the FR-006 route/schema additions cleanly instead of copying the full local diff
- larger `web/src/App.tsx` changes
  - reapply only the minimal Packet 5A launch-gating slice, not the full local UI rewrite

### Discard from Packet 5A

These are out of scope for the first Packet 5A implementation pass and should not be pulled in:

- pricing / entitlement changes outside FR-006:
  - `app/billing/pricebook.py`
  - billing-service and Stripe lifecycle work
  - `upgrade_required` launch-blocker policy additions
- broader GDPR work:
  - `tests/compliance/test_gdpr_compliance.py`
  - GDPR closeout claims
- local closeout artifacts that imply implementation is already done before hosted proof exists

## 11) Recommended Next Action

Merge Packet 5A to `main`, preserve `docs/specs/chronosrefine_phase5_packet5a_closeout_note.md` as the canonical hosted-closeout record for this packet slice, and continue the remaining `FR-006` follow-on work without claiming global `FR-006` complete yet.
