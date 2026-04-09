# ChronosRefine Phase 5 Packet 5C Kickoff

Status: Hosted-complete slice scope note for Packet 5C. The decision-complete implementation contract lives in `docs/specs/chronosrefine_phase5_packet5c_execution_packet.md`, and hosted evidence is summarized in `docs/specs/chronosrefine_phase5_packet5c_closeout_note.md`. This file does not change canonical source-of-truth ordering in `AGENTS.md`.

**Packet:** Packet 5C
**Requirement Focus:** `NFR-006`
**Status:** Hosted-complete slice
**Predecessor Packet:** `docs/specs/chronosrefine_phase5_packet5b_closeout_note.md`
**Execution Packet:** `docs/specs/chronosrefine_phase5_packet5c_execution_packet.md`
**Closeout Note:** `docs/specs/chronosrefine_phase5_packet5c_closeout_note.md`

## 1) Objective

Start the first implementation slice of `NFR-006` by replacing the remaining hardcoded pricing and entitlement resolution paths with a configuration-driven commercial pricebook keyed by the active Stripe recurring `price_id`, then surface the effective configured pricing back through the current launch and usage flows.

Packet 5C is intentionally narrower than full `NFR-006` closeout. It should cover the runtime pricebook, current-surface entitlement enforcement, and effective-price transparency without pulling Stripe lifecycle expansion, GDPR delivery, or Phase 6 launch work forward.

## 2) Why Packet 5C Is Next

- `FR-006` is now globally complete via Packets 5A and 5B.
- `NFR-006` is the next best Phase 5 packet because the governing commercial policy is already recorded in `docs/specs/chronosrefine_phase5_pricing_clearance.md`, but the merged runtime still uses legacy monthly-limit env vars and hardcoded plan gating on current user-facing surfaces.
- This packet is narrow enough to ship because it can reuse the merged Packet 4E/4H billing and cost-reporting substrate plus Packet 5A/5B launch gating, while limiting scope to the pricebook-backed runtime paths already exercised by launch review, usage, configuration gating, and output retention.

## 3) Current Merged Baseline

- `NFR-012` is canonically complete in the coverage matrix and Phase 1 summary as the Stripe Product/Price and webhook baseline.
- `NFR-007` is complete in Phase 2 as the cost-control and overage-approval substrate.
- `NFR-003` is complete in Phase 4 as the cost-ops and gross-margin reporting substrate.
- Packet 4E already exposes cost-estimate and launch-time pricing surfaces.
- Packet 5A and Packet 5B already preserve the preview-review and launch gate on top of those pricing surfaces.
- `docs/specs/chronosrefine_phase5_pricing_clearance.md` already records the approved commercial policy, required env contract, and `COMMERCIAL_PRICEBOOK_JSON` requirement.

## 4) Packet 5C Scope

Packet 5C should cover:

- a runtime commercial pricebook contract keyed by active Stripe recurring `price_id`
- replacement of the legacy monthly-limit env vars as the primary source for current-surface plan entitlements
- additive API fields so launch/usage flows expose the effective configured subscription price, included minutes, and overage price/rate
- current-surface entitlement enforcement for the product areas already exposed on `main`:
  - launch/usage limits
  - fidelity-tier access
  - current resolution cap gating
  - output-retention entitlement
- hosted `chronos_dev` proof that a configuration-only commercial change is reflected without code edits

## 5) Out of Scope

- Stripe subscription lifecycle, invoicing, tax, or billing-portal expansion beyond the existing `NFR-012` baseline
- broader customer-specific contract override tooling for Museum quotes
- GDPR/DPA implementation work from `SEC-006`
- Phase 6 launch-readiness work such as `NFR-008`, `NFR-010`, `SEC-015`, or `OPS-004`
- broader entitlement enforcement for surfaces not yet exposed on `main`
- tracker advancement for `NFR-006`; this packet is a hosted-validated slice, not automatic full requirement closeout

## 6) Packet Outcome

Packet 5C is now a hosted-complete `NFR-006` slice for current merged pricing-model surfaces.

- Packet 5B status: `hosted-complete`
- Packet 5C status: `hosted-complete slice`
- Global `NFR-006` status after Packet 5C closeout: `still partial pending deferred acceptance criteria`
- Phase 5 full-requirement count after Packet 5C: unchanged at `1/11`
