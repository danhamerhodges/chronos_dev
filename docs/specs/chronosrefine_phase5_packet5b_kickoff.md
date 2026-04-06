# ChronosRefine Phase 5 Packet 5B Kickoff

Status: Planned kickoff packet. This file records the next `FR-006` packet after Packet 5A hosted closeout and does not change canonical source-of-truth ordering in `AGENTS.md`.

**Packet:** Packet 5B
**Requirement Focus:** `FR-006`
**Status:** Planned
**Predecessor Packet:** `docs/specs/chronosrefine_phase5_packet5a_closeout_note.md`

## 1) Objective

Close the remaining global `FR-006` gap after Packet 5A by extending preview-approval enforcement beyond the first-party preview-launch flow to the remaining public launch surfaces, starting with generic `POST /v1/jobs`.

Packet 5B should turn Packet 5A’s hosted-complete first-party preview-review slice into the canonical launch policy for the rest of the product-facing processing entrypoints without pulling pricing enforcement, GDPR delivery, or Phase 6 launch readiness forward.

## 2) Current Merged Baseline

- Packet 4F (`ENG-014`) preview generation substrate is merged on `main`.
- Packet 5A is hosted-complete in `chronos_dev` and records:
  - preview create returning `pending`
  - preview approval and rejection
  - preview-launch idempotency and `launch_pending` recovery
  - stale anti-replay and cross-user denial
  - first-party UI gating plus generic `/v1/jobs` non-regression
- Global `FR-006` remains open because generic `/v1/jobs` preview-approval enforcement is still deferred.

## 3) Canonical Requirement Mapping

`FR-006` requires:

- 10 scene-aware preview keyframes in the review surface
- full-size preview inspection
- cost estimate and processing-time estimate in the preview flow
- explicit approve/reject before full processing launch
- `<6s p95` preview generation

Packet 5A closed the first-party preview-review and preview-launch route slice. Packet 5B should close the remaining launch-surface gap needed before global `FR-006` can be claimed complete.

## 4) Packet 5B Scope

Packet 5B is the next planned `FR-006` slice and should cover:

- generic `POST /v1/jobs` preview-approval enforcement for launch requests derived from the saved upload configuration flow
- deterministic, documented problem details for API clients that attempt full processing launch without a current approved preview
- alignment between generic launch, preview session freshness, and the configuration fingerprint/version contract added in Packet 5A
- OpenAPI and automated test coverage for non-first-party launch clients
- hosted `chronos_dev` evidence that the remaining public launch surfaces honor the `FR-006` approval contract

## 5) Out of Scope

Packet 5B must stay narrow.

- no pricing-enforcement or Stripe rollout work from `NFR-006` / `NFR-012`
- no GDPR export/deletion delivery work from `SEC-006`
- no Phase 6 launch-readiness work from `FR-007`, `NFR-008`, `NFR-010`, `SEC-015`, or `OPS-004`
- no reopening of Packet 5A first-party UI scope except where generic launch enforcement requires a compatibility adjustment

## 6) Likely Implementation Surfaces

The current merged baseline suggests Packet 5B will likely touch:

- `app/api/jobs.py`
- `app/services/job_service.py`
- `app/api/contracts.py`
- `docs/api/openapi.yaml`
- preview/job integration tests covering generic launch enforcement

If a remaining public launch surface other than generic `POST /v1/jobs` is discovered during implementation, record it explicitly and keep the packet scoped to that same global `FR-006` closeout goal.

## 7) Acceptance Contract

Packet 5B should not be counted complete until all of the following are true:

1. Generic `POST /v1/jobs` rejects launch attempts that require preview approval when no current approved preview exists.
2. Generic launch accepts the request once the current preview is approved and fingerprint-aligned.
3. Stale preview anti-replay still blocks launch deterministically after configuration changes.
4. Owner scoping remains enforced across preview review, preview launch, and generic launch.
5. OpenAPI documents the generic launch approval contract and the exact problem-detail types returned by the remaining public launch surfaces.
6. Packet 5A first-party preview-review flow remains green after the generic-route enforcement lands.
7. Hosted `chronos_dev` smoke demonstrates the generic-route enforcement and preserves Packet 5A latency/idempotency expectations.
8. Packet 5B is recorded as the packet that closes global `FR-006`; do not advance the full-requirement count until that hosted evidence exists.

## 8) Test Planning

Likely automated coverage additions or updates:

- `tests/api/test_async_processing.py`
- `tests/integration/test_processing_launch_flow.py`
- `tests/api/test_endpoints.py`
- `tests/api/test_preview_sessions.py`
- a narrow generic-launch enforcement test file if the existing suites become too broad

Validation should continue to include:

- `python3 scripts/validate_test_traceability.py`
- `.agents/skills/spec-consistency-audit/scripts/audit_specs.sh <repo-root>`
- the Packet 5A preview generation and UI suites needed to prove non-regression

## 9) Risks

- **Risk:** Packet 5B expands into pricing or broader launch readiness.
  - **Mitigation:** keep the packet limited to the remaining `FR-006` launch-surface contract.
- **Risk:** generic `/v1/jobs` enforcement breaks existing internal or automated launch paths.
  - **Mitigation:** document allowed launch shapes explicitly and keep the problem-detail contract deterministic.
- **Risk:** Packet 5A hosted-complete scope is accidentally reopened.
  - **Mitigation:** treat Packet 5A as the preserved baseline and limit changes to the remaining global closeout gap.

## 10) Packet Outcome

Packet 5B is the next planned product packet for `FR-006`.

- Packet 5A status: `hosted-complete`
- Packet 5B status: `planned`
- Global `FR-006` status: `open until Packet 5B hosted closeout`
