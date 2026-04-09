# ChronosRefine Phase 5 Packet 5C Execution Packet

Status: Hosted-complete execution packet for the first `NFR-006` implementation slice. This file records the decision-complete Packet 5C contract and links the hosted evidence summary in `docs/specs/chronosrefine_phase5_packet5c_closeout_note.md`. It does not change canonical source-of-truth ordering in `AGENTS.md`.

**Packet:** Packet 5C
**Requirement Focus:** `NFR-006`
**Status:** Hosted-complete slice
**Baseline:** `origin/main` after PR #26 (`382b39801b44feddfb8617718cf716526e08f9a2`)
**Predecessor Packet:** `docs/specs/chronosrefine_phase5_packet5b_closeout_note.md`
**Closeout Note:** `docs/specs/chronosrefine_phase5_packet5c_closeout_note.md`

## 1) Decision Summary

Packet 5C starts `NFR-006` implementation by landing the runtime commercial pricebook and replacing the remaining merged hardcoded pricing and entitlement lookups on current user-facing surfaces.

This packet does **not** attempt full `NFR-006` closeout. It is intentionally limited to:

- configuration-driven runtime price and entitlement resolution
- effective-price transparency on existing launch and usage surfaces
- current-surface entitlement enforcement where the merged product already has plan-based behavior

This packet does **not** reopen or broaden:

- Packet 5A/5B preview-review or launch gating
- `NFR-012` Stripe lifecycle scope
- GDPR or Phase 6 launch-readiness work

### 1.1 Packet 5C `NFR-006` claim line

Packet 5C is intended to satisfy the following `NFR-006` acceptance criteria **for the current merged product surfaces only**:

- `AC-NFR-006-01`: pricing identities are sourced from configured Stripe Product/Price IDs rather than hardcoded application values
- `AC-NFR-006-02`: included-usage entitlements are sourced from the active recurring Stripe `price_id` plus the internal commercial pricebook, not hardcoded env-only limits
- `AC-NFR-006-03`: overage rates are sourced from the active configured pricing contract, not hardcoded values
- `AC-NFR-006-04`: existing pricing enforcement stays coherent after the pricebook change on current launch and usage surfaces
- `AC-NFR-006-07`: current UI and API pricing surfaces show the effective configured price and overage rate
- `AC-NFR-006-08`: hosted proof demonstrates that a commercial pricing change can be applied in `chronos_dev` without a code deploy

Packet 5C explicitly defers the rest of `NFR-006`, including:

- `AC-NFR-006-05`: broader Stripe lifecycle and usage-billing implementation beyond the current baseline
- `AC-NFR-006-06`: Museum custom pricing override tooling and enterprise quote workflows
- `AC-NFR-006-09`: audited pricing-configuration change trail and Stripe event provenance
- `AC-NFR-006-10`: full requirement-level margin reporting closeout under the new pricebook model
- any entitlement enforcement beyond the product surfaces already exposed on `main`

## 2) Requirement and Dependency Check

### 2.1 Requirement selection

Packet 5C targets `NFR-006: Pricing Model` because it is the next best remaining Phase 5 requirement that is both product-facing and narrow enough to ship as one packet slice.

Why this is next:

- the commercial policy is already settled in `docs/specs/chronosrefine_phase5_pricing_clearance.md`
- the merged runtime still lacks `COMMERCIAL_PRICEBOOK_JSON` consumption and still uses the legacy monthly-limit env vars plus hardcoded plan gating in current product flows
- the implementation plan already names `tests/billing/test_feature_gating.py` as the missing test surface for this requirement, and that file does not yet exist on `main`

Why this is narrow enough:

- the packet can reuse the existing launch-review, overage-approval, and cost-reporting substrate already merged in Packets 4E, 4H, 5A, and 5B
- the packet is limited to current product surfaces already on `main`
- no schema expansion is planned unless implementation proves a concrete persistence gap

### 2.2 Dependencies

Canonical dependencies from the coverage matrix:

- `NFR-001`
- `NFR-003`
- `NFR-007`
- `NFR-012`

Dependency status:

- `NFR-012`: canonically complete in the Phase 1 matrix row and Phase 1 summary; Packet 5C may rely on Stripe Product/Price identity and billing portal baseline, but must **not** reopen broader Stripe lifecycle work in this packet
- `NFR-007`: complete in Phase 2; Packet 5C reuses the merged overage hard-stop and approval substrate rather than replacing it
- `NFR-003`: complete in Phase 4; Packet 5C reuses the merged cost reconciliation and gross-margin reporting substrate
- `NFR-001`: implementation surface already exists through Packet 4E cost-estimate and launch-review work; Phase 6 later re-validates it as a launch-readiness requirement, but it is sufficiently satisfied for Packet 5C runtime pricing transparency

Dependency caveat to carry into implementation:

- the implementation plan still contains older unchecked Phase 1 Stripe setup bullets even though `NFR-012` is canonically complete in the matrix and Phase 1 summary
- Packet 5C should treat that as documentation drift to be normalized during closeout if needed, not as a reason to expand into new Stripe lifecycle work

## 3) In Scope

Packet 5C should implement all of the following together:

1. A validated runtime commercial pricebook loaded from `COMMERCIAL_PRICEBOOK_JSON`.
2. Pricebook resolution keyed by the active tier-specific recurring Stripe `price_id`.
3. Replacement of the legacy env-only monthly limits as the primary entitlement source on current user-facing surfaces.
4. Additive API response fields so current launch and usage flows expose the effective configured pricing.
5. Current-surface entitlement enforcement driven by the pricebook for:
   - included monthly minutes
   - overage rate visibility
   - fidelity-tier access
   - resolution-cap gating
   - output-retention entitlement
6. Hosted proof that a configuration-only pricebook change changes runtime behavior without code edits.

## 4) Out of Scope

Packet 5C must stay narrow.

- no new billing portal UI
- no new subscription creation/update/cancel flows
- no invoice generation expansion
- no tax/dunning/customer-portal rollout work
- no broader Museum quote-management tooling
- no GDPR or DPA implementation work
- no preview-review or generic launch-gate redesign
- no broader entitlement enforcement for surfaces not already exposed on `main`
- no tracker advancement for `NFR-006` in this packet

## 5) Runtime Contract

### 5.1 Commercial pricebook shape

Packet 5C standardizes `COMMERCIAL_PRICEBOOK_JSON` as JSON with this exact top-level contract:

```json
{
  "version": "2026-04-08",
  "entries": {
    "price_hobbyist": {
      "plan_tier": "hobbyist",
      "included_minutes_monthly": 30,
      "overage": {
        "enabled": false,
        "price_id": "",
        "rate_usd_per_minute": 0.0
      },
      "entitlements": {
        "preview_review": true,
        "fidelity_tiers": ["Enhance"],
        "resolution_cap": "1080p",
        "parallel_jobs": 1,
        "export_retention_days": 7
      }
    },
    "price_pro": {
      "plan_tier": "pro",
      "included_minutes_monthly": 60,
      "overage": {
        "enabled": true,
        "price_id": "price_pro_overage",
        "rate_usd_per_minute": 0.50
      },
      "entitlements": {
        "preview_review": true,
        "fidelity_tiers": ["Enhance", "Restore", "Conserve"],
        "resolution_cap": "4k",
        "parallel_jobs": 5,
        "export_retention_days": 7
      }
    }
  }
}
```

Rules:

- entries are keyed by the active recurring Stripe subscription `price_id`
- the active recurring Stripe `price_id` for the current user request is resolved from the existing tier-specific env mapping:
  - `STRIPE_HOBBYIST_PRICE_ID`
  - `STRIPE_PRO_PRICE_ID`
  - `STRIPE_MUSEUM_PRICE_ID`
- the merged `plan_tier` on the authenticated user remains the tier discriminator for request auth and routing in this packet
- `COMMERCIAL_PRICEBOOK_JSON` is runtime configuration, not a git-managed live pricing artifact

### 5.1a Fail-closed rules

Packet 5C must fail closed for commercial pricing configuration. No silent fallback to legacy monthly-limit env vars or hardcoded entitlement defaults is allowed once the pricebook path is active.

- missing `COMMERCIAL_PRICEBOOK_JSON` in hosted runtime (`chronos_dev` and any future non-local runtime): fail application startup with a deterministic configuration error
- malformed `COMMERCIAL_PRICEBOOK_JSON` JSON or schema: fail application startup with a deterministic configuration error
- inconsistent active environment mapping, including any configured recurring Stripe `price_id` without a matching pricebook entry or with a mismatched `plan_tier`: fail application startup with a deterministic configuration error
- incomplete entry for a current-surface entitlement, such as missing included minutes, missing required overage metadata for a paid tier, missing fidelity tier list, missing resolution cap, or missing export retention days: fail application startup if the defect is detectable from configured tier entries; otherwise fail the affected request with deterministic `503 Billing Pricing Unavailable`
- request-time price resolution for a user or request that cannot be mapped to a valid active pricebook entry: return deterministic `503 Billing Pricing Unavailable`
- local unit-only mode may inject explicit test fixtures or monkeypatched pricebook data, but it must not silently fall back to legacy env-only commercial behavior

### 5.2 Additive response fields

Packet 5C should add an additive `effective_pricing` block to:

- `POST /v1/jobs/estimate`
- `GET /v1/users/me/usage`
- any first-party helper payloads that already consume those responses

Recommended response shape:

```json
{
  "effective_pricing": {
    "pricebook_version": "2026-04-08",
    "subscription_price_id": "price_pro",
    "subscription_price_usd": 29.0,
    "included_minutes_monthly": 60,
    "overage_enabled": true,
    "overage_price_id": "price_pro_overage",
    "overage_rate_usd_per_minute": 0.5,
    "entitlement_source": "commercial_pricebook"
  }
}
```

Rules:

- this is additive only; existing fields such as `price_reference`, `overage_price_reference`, `billing_breakdown_usd`, and `launch_blocker` remain for compatibility in Packet 5C
- estimate and usage responses must return the pricebook-resolved included usage, not the legacy env-only monthly limit fallback, when the pricebook is configured
- current front-end launch and preview-review flows should render the new effective-pricing values instead of relying on hardcoded copy or implicit defaults

### 5.3 Entitlement resolution

Packet 5C should move the following merged runtime paths to pricebook resolution:

- `BillingService.monthly_limit_for_tier` and all usage/estimate paths that depend on it
- hobbyist-only fidelity gating in configuration save/list flows
- current resolution-cap gating in configuration save flows
- output-retention entitlement resolution in output delivery

Packet 5C should **not** broaden into new entitlement surfaces that are not already user-facing on `main`.

## 6) API, Schema, and Persistence Expectations

Expected API and contract edits:

- additive `effective_pricing` response model in `app/api/contracts.py`
- additive OpenAPI examples documenting the effective pricing block and the pricebook-backed launch/usage behavior
- no new public endpoints are planned

Expected runtime/config files:

- new `app/billing/pricebook.py` for parsing and validating `COMMERCIAL_PRICEBOOK_JSON`
- `app/config.py` to load `COMMERCIAL_PRICEBOOK_JSON` explicitly
- `app/services/billing_service.py` to replace env-only monthly-limit lookup with pricebook resolution
- `app/services/cost_estimation.py` and `app/api/users.py` to surface effective pricing
- `app/services/configuration_service.py` and `app/services/output_delivery.py` to replace hardcoded tier gating on current surfaces
- helper/UI files under `web/src/lib/` and current launch-review components for additive display updates only

Schema / migration decision:

- no database migration is planned for Packet 5C
- if implementation proves that durable pricebook provenance must be persisted beyond existing JSON summary fields, stop and amend the packet before adding a migration

## 7) Auth and Security Boundary

Packet 5C touches pricing and entitlements on user-request paths, so the auth boundary is explicit:

- all entitlement enforcement remains owner-scoped on the end-user JWT path
- do not introduce service-role shortcuts for user-request pricing or entitlement resolution
- never expose secret-managed Stripe keys or raw commercial override data in API responses
- do not commit live Stripe Product/Price IDs or live `COMMERCIAL_PRICEBOOK_JSON` values into git-managed files
- staging and hosted proof must continue using Secret Manager and the current runtime verifier hygiene

## 8) Non-Regression Boundary

Packet 5C must preserve:

- Packet 5A preview-review and preview-launch behavior
- Packet 5B generic `/v1/jobs` approved-preview provenance gate
- existing overage approval scopes (`single_job`, `month`, `upgrade_tier`)
- `/v1/jobs/estimate` and `/v1/jobs` problem-detail behavior, except for additive effective-pricing fields
- existing staging runtime-verifier cleanliness and secret-handling posture
- current targeted web and accessibility green state

Explicit non-regression:

- no Packet 5C change may weaken `FR-006` hosted-closeout behavior
- no Packet 5C change may revert `/v1/jobs` to accept bare legacy launch payloads
- no Packet 5C change may reintroduce hardcoded pricing copy into the UI

## 9) Automated Test Plan

Update or add tests in these areas:

- `tests/billing/test_feature_gating.py` (new)
- `tests/billing/test_stripe_integration.py`
- `tests/billing/test_cost_control.py`
- `tests/billing/test_overage_approval.py`
- `tests/billing/test_usage_alerts.py`
- `tests/api/test_cost_estimation.py`
- `tests/api/test_cost_breakdown.py`
- `tests/api/test_fidelity_configuration.py`
- `tests/api/test_output_delivery.py`
- targeted web and accessibility tests covering current launch-review displays

Required automated scenarios:

1. pricebook parse/validation succeeds for the approved tier table and fails deterministically for malformed entries
2. runtime resolves entitlements by active recurring `price_id`, not hardcoded monthly-limit env vars
3. estimate response returns effective subscription price, included minutes, and overage rate from the pricebook
4. usage response returns the same effective pricing view and threshold behavior
5. hobbyist fidelity gating comes from the pricebook and still blocks unsupported tiers
6. hobbyist early-photo resolution gating remains enforced and is driven by the pricebook-backed cap
7. output retention for current delivery paths is driven by the pricebook-backed entitlement
8. `/v1/jobs/estimate` and Packet 5A preview-review flows still work with the additive pricing block
9. compatibility fields (`price_reference`, `overage_price_reference`) remain stable during Packet 5C
10. local unit-only mode still works without live Stripe secrets

Validation commands should include:

- `python3 scripts/validate_test_traceability.py`
- focused backend pytest for billing/configuration/estimate/output paths
- targeted web and accessibility tests for current pricing displays
- `.agents/skills/spec-consistency-audit/scripts/audit_specs.sh <repo-root>`

## 10) Hosted Closeout Proof Required

Hosted `chronos_dev` proof for Packet 5C must include all of the following:

1. staging runtime has `COMMERCIAL_PRICEBOOK_JSON` configured and valid
2. `/v1/jobs/estimate` returns effective pricing derived from the current active pricebook entry
3. `/v1/users/me/usage` returns the same effective included-minute and overage references
4. hobbyist launch/estimate posture reflects the approved `30 min/month` included usage from the pricebook rather than the legacy fallback limit
5. current hobbyist fidelity/resolution gating still blocks unsupported paths using pricebook-backed entitlements
6. output-retention behavior reflects the pricebook-backed entitlement on the current delivery surface
7. Packet 5A preview-review and Packet 5B generic `/v1/jobs` launch gate remain green
8. billing/overage behavior remains unchanged except for the now-configured price and entitlement source
9. runtime evidence confirms billing and overage behavior stays coherent after the pricebook change: hard-stop, approval scopes, and effective-price display all agree on the same configured entry
10. runtime verifier remains clean after the hosted pass

### 10.1 Primary hosted proof

The primary hosted proof for Packet 5C is configuration-only commercial change behavior.

Hosted closeout must explicitly demonstrate this sequence in `chronos_dev`:

1. verify baseline estimate and usage responses for a known tier with the approved staging `COMMERCIAL_PRICEBOOK_JSON`
2. apply a temporary safe alternate `COMMERCIAL_PRICEBOOK_JSON` value to the shared staging runtime without changing the application build
3. verify that estimate and usage responses update to the new effective configured pricing and entitlements
4. verify that billing and overage behavior remains coherent under the alternate configuration
5. restore the approved staging baseline pricebook
6. verify the baseline effective pricing surfaces are restored

## 11) Tracker Advancement Rule

Packet 5C is a hosted-validated `NFR-006` slice only.

Do **not**:

- mark global `NFR-006` complete
- advance the Phase 5 completed-requirement count
- rewrite the Phase 5 snapshot as if pricing-model closeout is done

unless a later packet explicitly closes the remaining `NFR-006` scope and records hosted closeout evidence for that full requirement.

## 12) Hosted Outcome

Packet 5C is now hosted-complete as a slice. The hosted closeout note records:

- baseline `chronos_dev` proof for the approved staging pricebook
- config-only alternate pricebook proof on the same build SHA without a code deploy
- Packet 5A and Packet 5B non-regression on the 5C revision
- runtime signal evidence for `preview_approval_required` and stale `launch_pending` recovery
- preview latency remaining within the canonical `<6s p95` guardrail

This packet still does **not** close global `NFR-006`. Deferred acceptance criteria remain open and the Phase 5 completed-requirement count stays unchanged.

## 13) Open Risks To Carry Forward

- `NFR-012` is canonically complete, but the implementation plan still contains stale unchecked Stripe setup bullets; closeout may need a small canon-normalization pass
- customer-specific Museum quote overrides and pricing-change audit provenance remain outside this packet
- if implementation reveals that current user profiles need a persisted subscription `price_id` rather than tier-to-price mapping, stop and amend the packet before coding
