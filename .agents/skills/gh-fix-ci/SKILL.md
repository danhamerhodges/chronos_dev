---
name: gh-fix-ci
description: Diagnose failing GitHub PR checks with gh, extract actionable GitHub Actions failures, propose a minimal fix plan, and implement after approval. Use when CI is failing and the user asks for root cause plus repair.
metadata:
  short-description: Diagnose and fix failing GH CI
---

# GH Fix CI (Chronos)

Use this skill to triage failing GitHub Actions checks and drive a safe fix loop.

## When to use

- CI checks are failing and the user asks for diagnosis plus remediation.
- A PR needs a minimal, evidence-backed fix plan for failing Actions runs.

## Preconditions

- `gh` authenticated with repo/workflow access.
- Run `gh auth status`; if blocked by sandbox/keychain restrictions, rerun with escalation.
- Default target is current branch PR unless user specifies a PR number/URL.

## When not to use

- Do not use for non-GitHub Actions providers beyond reporting their URLs.
- Do not use when the user only wants comment-thread addressing; use `gh-address-comments`.

## Quick start

- `python scripts/inspect_pr_checks.py --repo "." --pr "<number-or-url>"`
- Add `--json` for machine-readable output.

## Workflow

1. Verify gh authentication.
   - Run `gh auth status`.
   - If sandboxed auth status fails, rerun with escalation.
   - If unauthenticated, ask the user to log in before proceeding.
2. Resolve the PR.
   - Prefer the current branch PR: `gh pr view --json number,url`.
   - If the user provides a PR number or URL, use that directly.
3. Inspect failing checks (GitHub Actions only).
   - Preferred: run `python scripts/inspect_pr_checks.py --repo "." --pr "<number-or-url>"`.
   - Use manual `gh pr checks` / `gh run view` only if script output is insufficient.
4. Scope non-GitHub Actions checks.
   - If `detailsUrl` is not a GitHub Actions run, label it as external and only report the URL.
   - Do not attempt Buildkite or other providers; keep the workflow lean.
5. Summarize failures for the user.
   - Include failing check, likely root cause, evidence snippet, and impacted files.
   - Call out missing logs or uncertain root cause explicitly.
6. Create a plan.
   - Propose a small fix plan (3-7 steps) and request approval before edits.
7. Implement after approval.
   - Keep changes minimal and aligned to repository requirements.
   - If this repo is still spec-only for the target issue, stop at triage + plan and call out blocker.
8. Recheck status.
   - After changes, suggest re-running the relevant tests and `gh pr checks` to confirm.

## Multi-agent Orchestration

Use parallel triage and evidence gathering, then one implementation agent.

1. Spawn one `explorer` agent to enumerate failing checks and collect logs.
2. Spawn one `reviewer` agent to analyze probable root causes and risk.
3. For long-running checks, use one `monitor` agent to poll status while other analysis continues.
4. Parent agent consolidates diagnosis and proposes a minimal fix plan.
5. After approval, spawn one `worker` agent to implement and validate.
6. Do not run concurrent `worker` agents for the same CI failure set.

## Output Contract

- `Failing Checks`: check name, run URL, failure snippet
- `Diagnosis`: likely root cause and confidence level
- `Plan`: approved minimal fix steps
- `Validation`: commands run and current status
- `Remaining`: unresolved external/non-actions checks

## Bundled Resources

### scripts/inspect_pr_checks.py

Fetch failing PR checks, pull GitHub Actions logs, and extract a failure snippet. Exits non-zero when failures remain so it can be used in automation.

Usage examples:
- `python scripts/inspect_pr_checks.py --repo "." --pr "123"`
- `python scripts/inspect_pr_checks.py --repo "." --pr "https://github.com/org/repo/pull/123" --json`
- `python scripts/inspect_pr_checks.py --repo "." --max-lines 200 --context 40`

## Sub-agent Output Contract

Each sub-agent must return:

- `scope`: checks/log slice handled
- `findings`: failing checks and suspected cause
- `evidence`: run URL + log snippet
- `open_risks`: confidence gaps and external-system blockers
- `recommended_next_action`: monitor, patch, or defer
