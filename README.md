# ChronosRefine

This repository contains the active ChronosRefine codebase plus the canonical requirements and runbooks under `docs/specs/`.

Use the canonical docs, coverage matrix, and implementation plan under `docs/specs/` as the source of truth for current phase and packet status.

## Current Repo State

- Canonical source of truth lives under `docs/specs/` in the ordering defined by `AGENTS.md`.
- The checked-in API contract lives at `docs/api/openapi.yaml`.
- The environment model is documented in `docs/specs/chronos_environment_strategy_runbook.md`.
- The environment variable contract is documented in `docs/specs/ENVIRONMENT_VARIABLES.md`.

## Environment Model

- `local` is the default contributor environment.
- `chronos_dev` is the only shared hosted environment and is treated operationally as staging / pre-prod.
- `production` is deferred and not implemented yet.
- Local Supabase is optional and not required for baseline local development.

See `docs/specs/chronos_environment_strategy_runbook.md` for the governing model and `docs/specs/ENVIRONMENT_VARIABLES.md` for the current env-var contract.

## Historical Phase 1 Scope

- ENG-016: Supabase database baseline (schema, migrations, RLS, pooling notes, backup/restore pointers)
- SEC-013: Supabase Auth baseline (email/password, OAuth hooks, magic links, RBAC/session policy scaffolding)
- OPS-001: Monitoring and alerting baseline (/v1/metrics, structured logging, alert wiring placeholders)
- OPS-002: SLO baseline (definitions, error budget model, reporting placeholders)
- NFR-012: Stripe billing baseline (Product/Price ID configuration, lifecycle and webhook security scaffolding)
- DS-007: Design-system baseline (tokens, core components, Storybook setup, visual regression placeholders)

## Quickstart

1. Copy `.env.example` to `.env` for local app defaults and optional hosted integration values.
2. Copy `.env.test.example` to `.env.test` for unit-only test mode; local Supabase is not required.
3. Uncomment hosted integration values only when you intentionally want to target the shared `chronos_dev` environment.
4. Run the verification commands below or the phase-specific commands referenced from the canonical docs.

## Common Verification Commands

```bash
./scripts/validate_codex_setup.sh
python3 scripts/validate_test_traceability.py
pytest tests/infrastructure tests/database tests/auth tests/billing tests/ops -q
pnpm -C web test
pnpm -C web storybook:test
pytest tests/design_system tests/visual_regression -q
pytest -q
```

## Agent Automation Baseline

This repo now includes advisory-first commit and PR automation helpers:

- Commit sizing: `python3 scripts/agents/analyze_commit_size.py --staged`
- Commit timing: `python3 scripts/agents/recommend_commit_timing.py`
- Push gate: `python3 scripts/agents/push_gate.py --run`
- PR validation summary: `python3 scripts/agents/pr_validation_orchestrator.py`

Install local hooks:

```bash
./scripts/agents/install_git_hooks.sh
```

Policy file:

- `.agents/policies/ci_agents_policy.json` (`mode` defaults to `advisory`; switch to `enforce` when ready)

## CI Integration Job Setup

The GitHub Actions `integration` job runs only on `push` to `main` and only when required secrets are present.

`chronos_dev` is the shared hosted staging / pre-prod GitHub environment for this repository. The authoritative deploy/runtime contract lives in `docs/specs/ENVIRONMENT_VARIABLES.md`.

Legacy `*_DEV` secret names are retained as compatibility-only names in this pass; they are documented rather than renamed.

Additional agent-oriented workflows:

- `.github/workflows/agent-pr-validation.yml` (PR and merge-group advisory checks)
- `.github/workflows/agent-ci-followup.yml` (workflow_run diagnostics on failed `ci`/`security`)
- `.github/workflows/nightly-e2e.yml` (nightly validation baseline)
- `.github/workflows/weekly-performance.yml` (weekly performance placeholder)

## Notes

- Prices must never be hardcoded; billing uses Stripe Product/Price IDs from config only.
- Secrets are never committed. Use environment variables.
- Integration tests for Supabase/Stripe are env-gated via `CHRONOS_RUN_SUPABASE_INTEGRATION=1` and `CHRONOS_RUN_STRIPE_INTEGRATION=1`.
