# ChronosRefine Phase 5 Pricing Clearance Note

**Status:** Approved for Phase 5 entry-criteria recording
**Recorded On:** 2026-03-20
**Recorded Approval Source:** Repository operator approval captured in Codex session on 2026-03-20. Repo-local note intentionally omits personal identifiers.
**Scope:** `NFR-006`, `NFR-012`, `FR-006` Packet 5A kickoff governance

## Purpose

This note records the approved pricing tiers, feature allocation, Packet 5A preview-review availability, and the approved billing/commercial source-of-truth contract for Phase 5 kickoff governance.

This note is a repo-safe approval artifact. It does not publish live Stripe Product or Price IDs. Live values must remain in deployment configuration and secret-managed systems, not in git.

## Canonical Basis

- `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-006-pricing-model`
- `docs/specs/chronosrefine_nonfunctional_requirements.md#nfr-012-payment-provider-selection`
- `docs/specs/chronosrefine_functional_requirements.md#fr-006-preview-generation`
- `docs/specs/chronosrefine_prd_v9.md#pricing--business-model`

## Approved Tier Table

This approval adopts the PRD's revised hybrid subscription + usage model as the Phase 5 target commercial policy.

| Tier | Base subscription | Included usage | Overage policy | Packet 5A preview-review | Notes |
|---|---|---:|---|---|---|
| `Hobbyist` | `$0/month` | `30 min/month` | No overage; upgrade required | `Available` | Acquisition tier with strict capability limits |
| `Pro` | `$29/month` | `60 min/month` | `$0.50/min` with explicit approval flow | `Available` | Primary paid self-serve tier |
| `Museum` | `$500/month` base or approved commercial quote | `500 min/month` | `$0.40/min` or approved contract override | `Available` | Enterprise/institutional tier with contract flexibility |

## Approved Feature Allocation

| Capability | Hobbyist | Pro | Museum |
|---|---|---|---|
| Fidelity tiers | `Enhance` only | `Enhance`, `Restore`, `Conserve` | All three plus approved custom profiles |
| Resolution cap | `1080p` | `4K` | Native scan / uncapped within approved workflow |
| Parallel jobs | `1` | `5` | `20` plus priority queue |
| Transformation manifest | No | Yes | Yes plus rerun proof |
| Deletion proof | No | No | Yes |
| Uncertainty surface | Simplified | Full | Full plus exportable detail |
| Export retention entitlement | `7 days` | `7 days` until a later approved implementation change extends it | Configurable, including extended retention |
| Packet 5A preview-review gate | Yes | Yes | Yes |
| Deterministic reproducibility | No | Yes | Yes |
| Bit-identical reproducibility | No | No | Museum-only when separately enabled |

## Packet 5A Allocation Decision

`FR-006` preview-review is approved as a launch-safety gate for all tiers, not a premium-only upsell.

Commercial differentiation for Packet 5A should come from the underlying processing entitlements attached to each tier rather than from removing preview approval/rejection from lower tiers.

## Approved Source Of Truth

Pricing and entitlement decisions must remain configuration-driven and auditable.

Stripe is the source of truth for:

- recurring subscription price identity per tier
- overage price identity per paid tier
- invoicing
- billing portal access
- payment collection and subscription lifecycle

An internal commercial pricebook is the source of truth for:

- included monthly minutes
- preview-review availability
- fidelity tier access
- resolution cap
- parallel job cap
- manifest / deletion-proof entitlements
- retention entitlement
- reproducibility entitlement

The internal commercial pricebook must be keyed by the active recurring Stripe `price_id` so pricing changes remain configuration-only and do not require code edits.

## Approved Target Config Contract

The following configuration contract is approved for Phase 5 implementation. Existing keys already present on `main` remain valid unless explicitly marked as migration-only.

### Required Stripe config keys

- `STRIPE_HOBBYIST_PRICE_ID`
- `STRIPE_PRO_PRICE_ID`
- `STRIPE_MUSEUM_PRICE_ID`
- `STRIPE_PRO_OVERAGE_PRICE_ID`
- `STRIPE_MUSEUM_OVERAGE_PRICE_ID`
- `STRIPE_BILLING_PORTAL_RETURN_URL`

### Migration-only Stripe fallback keys

- `STRIPE_PRODUCT_ID`
- `STRIPE_PRICE_ID`
- `STRIPE_OVERAGE_PRODUCT_ID`
- `STRIPE_OVERAGE_PRICE_ID`

These fallback keys may be used during transition but must not remain the sole effective source for tier-specific paid pricing or tier-specific overage pricing after Phase 5 pricing enforcement is complete.

### Required internal commercial config

- `COMMERCIAL_PRICEBOOK_JSON`

## Current Merged-Baseline Context

The merged repo already includes the tier-specific Stripe environment-key surface and the environment-contract documentation required to support this policy:

1. `app/config.py` defines `STRIPE_HOBBYIST_PRICE_ID`, `STRIPE_PRO_PRICE_ID`, and `STRIPE_MUSEUM_PRICE_ID`.
2. `docs/specs/ENVIRONMENT_VARIABLES.md` records the tier-specific Stripe IDs, overage IDs, and `COMMERCIAL_PRICEBOOK_JSON` as the relevant billing/runtime contract.

This note does **not** claim that `NFR-006` or `NFR-012` are already implemented on `main`.

Phase 5 remains `0/11` until pricing enforcement, entitlement resolution, and their mapped tests are implemented and merged.

## Gate Effect

This note satisfies the Phase 5 kickoff need to record finalized pricing tiers and feature allocation in merged canon.

Packet 5A `FR-006` preview-review planning is therefore no longer blocked by unresolved pricing-policy decisions, even though the Phase 5 pricing implementation itself remains future work.

## Rollout Caveats

- Do not commit live Stripe resource IDs, quote IDs, customer-specific discounts, or contract values into git-managed files.
- Do not market retention or entitlement changes beyond what is recorded in this note until implementation and enforcement land together.
- Treat this note as a governance artifact, not as evidence that broader Phase 5 pricing enforcement is complete.
