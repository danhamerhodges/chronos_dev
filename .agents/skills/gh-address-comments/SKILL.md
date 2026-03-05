---
name: gh-address-comments
description: Address review comments on the active GitHub PR with gh CLI. Use when a user asks to process PR feedback, summarize open threads, and apply selected fixes with minimal, requirement-aligned changes.
metadata:
  short-description: Address PR review comments with gh
---

# GH Address Comments (Chronos)

Use this skill to pull open PR review threads, summarize them as actionable items, and apply only the user-selected fixes.

## When to use

- A PR has review feedback and the user wants selected threads addressed.
- The user wants an actionable summary before choosing fixes.

## Preconditions

- `gh` must be authenticated.
- Run `gh auth status`; if sandbox blocks keychain/network access, rerun with escalation.
- Work against current branch PR unless the user specifies a different PR.

## When not to use

- Do not use for CI failure triage without review comments; use `gh-fix-ci`.
- Do not use when there is no PR context or review thread source.

## Workflow

1. Collect comments and threads:
   - Run `python scripts/fetch_comments.py` from this skill directory or with absolute path.
2. Build a numbered action list:
   - One line per thread: summary, likely files, risk level.
   - Mark blocked items (missing context, external dependency).
3. Ask the user which items to address.
4. Apply selected fixes only:
   - Keep scope tight; no drive-by refactors.
   - Respect repo requirement traceability and security constraints.
5. Report:
   - Files changed.
   - Tests run (or exact commands if not run).
   - Remaining unresolved threads.

## Multi-agent Orchestration

Use parallel triage, single-writer implementation.

1. Spawn one `explorer` agent to fetch and normalize PR threads/comments.
2. Spawn one `reviewer` agent to classify thread risk and likely fix complexity.
3. Parent agent presents numbered options to user and requests selection.
4. After selection, spawn one `worker` agent to implement chosen fixes.
5. Do not run multiple `worker` agents for comment fixes in parallel.

## Output Contract

- `Selected Threads`: numbered list addressed
- `Changes`: file-level summary
- `Validation`: commands + results
- `Remaining`: threads intentionally deferred

For multi-agent runs, each sub-agent must return:

- `scope`: PR/thread slice analyzed
- `findings`: thread summaries and risk labels
- `evidence`: thread IDs/URLs and cited files
- `open_risks`: uncertain behavior or missing context
- `recommended_next_action`: defer, patch, or escalate

## Failure Handling

- If auth/rate-limit fails: prompt user to run `gh auth login`, then retry.
- If no PR is associated with branch: ask for PR URL/number.
