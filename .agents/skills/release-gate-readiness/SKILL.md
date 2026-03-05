---
name: release-gate-readiness
description: Evaluate ChronosRefine Beta/GA gate readiness and canary rollback posture using implementation plan criteria, test evidence, and operational controls.
---

# Release Gate Readiness

## Overview

Assess milestone readiness against defined Beta/GA entry/exit criteria and canary/rollback rules.

## When to use

- Before Beta entry.
- Before GA decision.
- During go/no-go reviews and release readiness checks.

## When not to use

- Do not use for normal feature implementation tasks.
- Do not use for low-scope doc changes that do not affect release posture.

## Workflow

1. Extract gate criteria from implementation plan and supporting specs.
2. Gather evidence for each criterion (tests, controls, runbooks, monitoring).
3. Mark each criterion as pass/fail/partial with objective evidence.
4. Identify launch blockers and rollback readiness gaps.
5. Produce a go/no-go recommendation with explicit assumptions.

## Multi-agent Orchestration

Use parallel evidence collection with centralized adjudication.

1. Spawn `explorer` agents by gate domain (quality, security, ops, product).
2. Spawn one `monitor` agent for long-running status checks if needed.
3. Spawn one `reviewer` agent to challenge pass/fail adjudication.
4. Parent agent publishes final gate matrix and recommendation.

## Output Contract

- `Gate Matrix`: criterion-by-criterion pass/fail/partial
- `Evidence`: objective references for each criterion
- `Blockers`: must-fix items before release
- `Rollback Readiness`: canary/rollback status and gaps
- `Recommendation`: go, no-go, or conditional go

For multi-agent runs, each sub-agent must return:

- `scope`
- `findings`
- `evidence`
- `open_risks`
- `recommended_next_action`
