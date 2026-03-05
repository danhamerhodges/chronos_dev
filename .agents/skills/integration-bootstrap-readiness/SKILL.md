---
name: integration-bootstrap-readiness
description: Validate ChronosRefine third-party integration bootstrap readiness (Supabase, cloud runtime, docs/tooling connectors, and CI prerequisites) before feature implementation.
---

# Integration Bootstrap Readiness

## Overview

Run a preflight readiness audit for external integrations and environment prerequisites needed before implementation begins.

## When to use

- Before Phase 1 or initial implementation in a new environment.
- Before enabling integration-dependent features.

## When not to use

- Do not use for requirement-level design planning without integration dependencies.
- Do not use when the user requests direct production changes without a preflight review.

## Workflow

1. Enumerate integration dependencies from specs and project config.
2. Validate presence of required environment variables and config entries.
3. Check access/auth readiness for required tooling (CLI, MCP, cloud credentials).
4. Flag missing prerequisites, risk level, and recommended sequencing.
5. Produce a bootstrap checklist with pass/fail per dependency.

## Multi-agent Orchestration

Use parallel preflight checks by integration domain.

1. Spawn `explorer` agents for database/auth, cloud runtime, and docs/tooling connectors.
2. Spawn one `reviewer` agent to evaluate risk and sequencing.
3. Parent agent consolidates into one bootstrap checklist and unblock plan.

## Output Contract

- `Dependency Inventory`: required integrations
- `Readiness Checklist`: pass/fail by item
- `Blockers`: missing prerequisites and impact
- `Recommended Order`: setup sequence
- `Verification Commands`: exact commands to validate readiness

For multi-agent runs, each sub-agent must return:

- `scope`
- `findings`
- `evidence`
- `open_risks`
- `recommended_next_action`
