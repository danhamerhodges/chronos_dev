# Contributing

## Workflow

1. Keep changes small and requirement-scoped.
2. Update tests and traceability headers (`Maps to:`) with behavior changes.
3. Run relevant verification commands before proposing merge.
4. Do not introduce `.cursor/*` references in canonical docs.

## Commit Guidance

- Use clear requirement-scoped commit messages.
- Avoid drive-by refactors.
- Call out security or data-handling risk in PR summaries.
- Run commit/push agent checks for local readiness:
  - `python3 scripts/agents/analyze_commit_size.py --staged`
  - `python3 scripts/agents/push_gate.py --run`
