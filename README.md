# Chronos Phase 1 Bootstrap

This repository contains the Phase 1 implementation baseline for ChronosRefine.

## Phase 1 Scope

- ENG-016: Supabase database baseline (schema, migrations, RLS, pooling notes, backup/restore pointers)
- SEC-013: Supabase Auth baseline (email/password, OAuth hooks, magic links, RBAC/session policy scaffolding)
- OPS-001: Monitoring and alerting baseline (/v1/metrics, structured logging, alert wiring placeholders)
- OPS-002: SLO baseline (definitions, error budget model, reporting placeholders)
- NFR-012: Stripe billing baseline (Product/Price ID configuration, lifecycle and webhook security scaffolding)
- DS-007: Design-system baseline (tokens, core components, Storybook setup, visual regression placeholders)

## Quickstart

1. Copy `.env.example` to `.env` and fill values.
2. Copy `.env.test.example` to `.env.test` for test-only values.
3. Run verification commands listed in `Makefile` targets or project docs.

## Verification Commands

```bash
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

Required `chronos_dev` environment secrets:

- `SUPABASE_URL_DEV`
- `SUPABASE_ANON_KEY_DEV`
- `STRIPE_SECRET_KEY`
- `STRIPE_SUBSCRIPTION_PRODUCT_ID`
- `STRIPE_SUBSCRIPTION_PRICE_ID`

Optional (enables deeper integration assertions):

- `CHRONOS_TEST_EMAIL`
- `CHRONOS_TEST_PASSWORD`
- `CHRONOS_TEST_STRIPE_CUSTOMER_ID`
- `STRIPE_WEBHOOK_SECRET`

Additional agent-oriented workflows:

- `.github/workflows/agent-pr-validation.yml` (PR and merge-group advisory checks)
- `.github/workflows/agent-ci-followup.yml` (workflow_run diagnostics on failed `ci`/`security`)
- `.github/workflows/nightly-e2e.yml` (nightly validation baseline)
- `.github/workflows/weekly-performance.yml` (weekly performance placeholder)

## Notes

- Prices must never be hardcoded; billing uses Stripe Product/Price IDs from config only.
- Secrets are never committed. Use environment variables.
- Integration tests for Supabase/Stripe are env-gated via `CHRONOS_RUN_SUPABASE_INTEGRATION=1` and `CHRONOS_RUN_STRIPE_INTEGRATION=1`.
