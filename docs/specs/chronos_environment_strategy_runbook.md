# Chronos Environment Strategy Runbook

## Canonical Model
- `local` is the default contributor environment.
- `chronos_dev` is the only shared hosted environment and is treated operationally as staging / pre-prod.
- `production` is deferred and not implemented yet.

## Runtime Mapping
- GitHub environment: `chronos_dev`
- Deployed Cloud Run runtime: `ENVIRONMENT=staging`
- Local unit-only test mode: `ENVIRONMENT=test` with `TEST_AUTH_OVERRIDE=true`

This mapping is intentional. `chronos_dev` is the shared hosted validation target, not a disposable sandbox.

## Operating Rules
- Default local development must not require local Supabase.
- Hosted integrations must be explicit and opt-in.
- Do not assume a live production environment exists.
- Do not introduce schema-based environment partitioning.
- Do not change runtime selection logic in this pass unless a concrete bug is proven.

## Local Supabase
Local Supabase is an optional future enhancement, not a baseline requirement.

Only introduce it as a default workflow if at least one of these becomes recurring work:
- migration rehearsal before shared-hosted apply
- RLS policy debugging
- auth or session database debugging
- database-heavy feature work where shared remote risk is too high

## Environment Variable Contract
The authoritative variable contract lives in [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md).

In this pass:
- legacy names such as `SUPABASE_*_DEV` and `VITE_SUPABASE_*_DEV` are documented, not renamed
- stale stage-suffixed aliases are removed from active hosted verification
- a dedicated `OUTPUT_DELIVERY_SIGNING_SECRET` is required for hosted validation

## Verification Targets
- Local unit-only mode runs without external services.
- Active contributor-facing docs clearly state `chronos_dev -> staging`.
- Hosted deploy and runtime verification use a dedicated `OUTPUT_DELIVERY_SIGNING_SECRET`.
- Active docs do not imply a live production environment.

## Future Production Path
- Add `production` only when rollout risk and operational maturity justify it.
- Treat production as a separate future environment, not as a schema split inside the current hosted setup.
