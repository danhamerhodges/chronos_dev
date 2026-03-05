---
name: commit-hygiene-guard
description: Evaluate commit size and timing to keep changes requirement-scoped and reviewable. Use before commit or as pre-commit advisory checks.
---

# Commit Hygiene Guard

## When to use

- Before creating a commit.
- During pre-commit checks to detect oversized change sets.
- During long working sessions to decide commit timing.

## When not to use

- Do not use for CI failure root-cause analysis.
- Do not use as a replacement for feature-level test validation.

## Workflow

1. Run `python3 scripts/agents/analyze_commit_size.py --staged` for staged changes.
2. If status is `split-recommended` or `blocked`, split by requirement scope.
3. Run `python3 scripts/agents/recommend_commit_timing.py` to evaluate commit cadence.
4. Commit only when scope and timing recommendation are acceptable.

## Output Contract

- `Commit Size`: status, totals, and risk paths.
- `Timing`: commit-now/continue recommendation.
- `Next Action`: proceed, split, or defer.
