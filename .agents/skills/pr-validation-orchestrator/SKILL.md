---
name: pr-validation-orchestrator
description: Run advisory PR validation for commit sizing and test traceability; summarize readiness for review and merge.
---

# PR Validation Orchestrator

## When to use

- On PR opened, synchronized, reopened, or ready-for-review events.
- On merge-group checks.

## When not to use

- Do not use for direct code remediation; hand off to `gh-fix-ci` for failing checks.

## Workflow

1. Load PR event context from `GITHUB_EVENT_PATH`.
2. Run commit sizing against base/head range.
3. Run traceability validation.
4. Publish markdown summary to workflow step summary.
5. If policy mode is `enforce`, fail on blocked size or traceability failure.

## Output Contract

- `Commit Sizing`: status, totals, reasons.
- `Traceability`: pass/fail and evidence output.
- `Recommendation`: advisory or enforce result.
