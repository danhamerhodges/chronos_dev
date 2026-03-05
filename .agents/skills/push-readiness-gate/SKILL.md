---
name: push-readiness-gate
description: Validate push readiness with branch policy and path-aware checks. Use before initiating git push in local workflows.
---

# Push Readiness Gate

## When to use

- Before `git push`.
- As a `pre-push` automation gate.

## When not to use

- Do not use for post-merge release validation.
- Do not use for unrelated documentation-only advisory tasks unless policy requires it.

## Workflow

1. Run `python3 scripts/agents/push_gate.py --run`.
2. Review deny reasons and failed checks.
3. Fix issues and rerun until gate allows.
4. Push once gate is green.

## Output Contract

- `Decision`: allow/deny.
- `Reasons`: branch policy and check failures.
- `Checks`: command-level pass/fail output.
