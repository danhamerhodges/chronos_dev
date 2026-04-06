# AGENTS.md — ChronosRefine Codex Operating Guide (v5)

This file defines how coding agents must operate in this repository.

## 0) Scope and Instruction Loading

- This is the root project instruction file for Codex.
- Canonical filename is `AGENTS.md`.
- Codex merges instruction files from root to current directory; closer files override earlier guidance.
- Keep this file concise, explicit, and implementation-oriented.
- If subdirectories get specialized workflows later, add nested `AGENTS.md` files there.

## 1) Project Context

- Project: ChronosRefine.
- Current repository state: active application, test, workflow, and canonical spec stack.
- Canonical requirements and implementation governance live under `docs/specs/`.
- If implementation code is missing for a requested change, update specs and call out the gap explicitly.

## 2) Canonical Documents (Source of Truth)

When conflicts exist, resolve in this order:

1. `docs/specs/chronosrefine_functional_requirements.md`
2. `docs/specs/chronosrefine_engineering_requirements.md`
3. `docs/specs/chronosrefine_security_operations_requirements.md`
4. `docs/specs/chronosrefine_nonfunctional_requirements.md`
5. `docs/specs/chronosrefine_design_requirements.md`
6. `docs/specs/ChronosRefine Requirements Coverage Matrix.md`
7. `docs/specs/chronosrefine_implementation_plan.md`
8. `docs/specs/chronosrefine_test_templates.md`

Additional context only (non-governing):

- `docs/specs/chronosrefine_prd_v9.md`

Rule:

- If code/tests/docs conflict with canonical specs, update implementation/docs to align with canon.

## 3) Working Agreements

### 3.1 Change size and scope

- Prefer small, testable, PR-sized changes.
- No drive-by refactors unless requested.
- No silent scope creep; propose deferred phases explicitly.

### 3.2 Assumptions

- If requirements are ambiguous and not safety-critical, make the smallest safe assumption and state it in one line.
- Ask at most one blocking clarifying question when correctness/safety requires it.

### 3.3 Patch-pack output for non-trivial work

For substantial changes, provide:

- Intent (what/why)
- Files changed
- Exact edits
- Tests added/updated
- Verification commands and expected outcomes

## 4) Build/Test Commands (Current Repo State)

This repository now contains executable backend/frontend code, tests, CI helpers, and canonical specs.

Recommended local bootstrap:

- Python venv: `python3 -m venv .venv`
- Python deps: `./.venv/bin/pip install -e .[dev]`
- Root JS tooling: `npm install`
- Web workspace deps: `./node_modules/.bin/pnpm -C web install`

Recommended verification commands:

- Codex/project setup sanity: `./scripts/validate_codex_setup.sh`
- Traceability validator: `python3 scripts/validate_test_traceability.py`
- Spec consistency audit: `bash .agents/skills/spec-consistency-audit/scripts/audit_specs.sh .`
- Backend targeted suite: `./.venv/bin/python -m pytest tests/infrastructure tests/database tests/auth tests/billing tests/ops -q`
- Frontend rendered suite: `./node_modules/.bin/pnpm -C web test`
- Storybook baseline: `./node_modules/.bin/pnpm -C web storybook:test`
- Design/visual suites: `./.venv/bin/python -m pytest tests/design_system tests/visual_regression -q`
- Full backend suite: `./.venv/bin/python -m pytest -q`

Docs-only checks:

- List specs: `rg --files docs/specs`
- Find stale internal references: `rg -n "coverage_matrix\\.md|chronosrefine_prd_final|\\bagents\\.md\\b" docs/specs`
- Verify canonical phase headers: `rg -n "^## Phase [1-6]:" "docs/specs/ChronosRefine Requirements Coverage Matrix.md"`
- Verify implementation plan phase declarations: `rg -n "^### Phase [1-6]:|\*\*Requirements Implemented:\*\*|Phase [56] Requirement Set" docs/specs/chronosrefine_implementation_plan.md`

- Do not claim tests ran unless commands were actually executed.

## 5) Requirement and Phase Gating

Before implementing or documenting any requirement:

- Confirm requirement ID exists in the Coverage Matrix.
- Confirm dependency requirements are satisfied.
- Confirm phase order matches `chronosrefine_implementation_plan.md` and matrix.
- Confirm mapped tests exist in `chronosrefine_test_templates.md`.

## 6) Testing and Traceability (Mandatory)

ChronosRefine test contract is defined in:

- `docs/specs/chronosrefine_test_templates.md`

### 6.1 Unit-only mode support

- Unit-only mode must work without Supabase secrets.
- Integration/E2E tests must skip gracefully when prerequisites are absent.

### 6.2 Traceability headers required

Every test file must begin with a `Maps to:` docstring including requirement IDs.

CI validator:

- `python3 scripts/validate_test_traceability.py`

### 6.3 Deterministic rate limiting

- Key rate limiter by user ID (not IP).
- Use `/v1/testing/reset-rate-limits` in test mode.
- Use `TestClient(app)` with auth headers for reset flows.

### 6.4 Canonical enums only

- Never hardcode status strings.
- Use `JobStatus` and `UploadStatus` from canonical model files.

## 7) Security Guardrails (Non-Negotiable)

- Do not use Supabase service-role key in user-request paths without explicit equivalent authorization enforcement.
- Prefer end-user JWT for RLS-protected operations.
- Use least privilege by default.
- Changes touching auth, permissions, retention, deletion, or data residency require conservative handling and explicit risk callout.

## 8) Documentation Hygiene

- Keep all canonical spec references under `docs/specs/`.
- Do not introduce deprecated assistant-workspace path references or editor-specific metadata into canonical docs.
- Keep requirement IDs/titles consistent across specs, matrix, and implementation plan.
- If IDs/titles change, update the Coverage Matrix in the same change.
- Use stable anchors/paths; avoid dead internal links.

## 9) Skills Policy

Yes, account for skills in this file.

Current policy:

- Use skills when explicitly requested by the user/system, or when task fit is clear and improves correctness/speed.
- Keep this file tool-agnostic; do not hardcode transient local skill paths.
- Repository-local skills live under `.agents/skills/`.
- Every skill should define `When to use`, `When not to use`, `Workflow`, and output expectations.
- Invoke a project-local skill by name (for example: `use spec-consistency-audit on docs/specs`).

### 9.1 Multi-agent orchestration policy

- Multi-agent workflows are supported and currently experimental; ensure `features.multi_agent = true` in `~/.codex/config.toml` (or enable via `/experimental` and restart Codex).
- Prefer multi-agent for read-heavy parallel tasks: audits, exploration, triage, summarization, and dependency mapping.
- Use a fan-out/fan-in pattern:
  - Fan-out: spawn focused sub-agents with narrow task statements and clear output contract.
  - Fan-in: wait for all sub-agents, reconcile conflicts, then produce one consolidated answer.
- Enforce single-writer execution:
  - At most one `worker` agent may edit files at a time.
  - All other concurrent agents must run read-only or analysis-only tasks.
- Default role usage:
  - `explorer`: discovery, scans, traceability evidence.
  - `reviewer`: risk analysis, correctness/security gaps.
  - `worker`: approved implementation changes.
  - `monitor`: long-running waits/polling/status checks.
- Sub-agents inherit sandbox and run non-interactive approvals:
  - If a sub-agent hits an approval-required action, treat it as failed and continue with other agents.
  - Parent agent must summarize failed sub-agent actions and decide whether to retry manually.
- Keep depth shallow:
  - Default `agents.max_depth = 1`; do not nest agents unless explicitly required.
- Do not parallelize overlapping writes to the same file set.
- When orchestrating, each sub-agent response must include:
  - `scope`, `findings`, `evidence` (file/line or command output), `open_risks`, and `recommended_next_action`.

### 9.2 Workflow Coverage Matrix

| Workflow | Primary Role | Secondary Role | Skill | Output Contract |
|---|---|---|---|---|
| Spec consistency and drift audit | `explorer` | `reviewer` | `spec-consistency-audit` | Prioritized findings with evidence and minimal fixes |
| Requirement packet planning | `explorer` | `reviewer` | `requirement-implementation-planner` | Requirement packet (phase, deps, tests, risks, verification) |
| Requirement implementation execution | `worker` | `reviewer` | `requirement-implementation-executor` | Minimal patch + tests + verification results |
| Test traceability and gating | `explorer` | `worker` | `test-traceability-enforcer` | Traceability violations + exact fixes/commands |
| PR review comment processing | `explorer` | `worker` | `gh-address-comments` | Selected-thread changes + validation + remaining items |
| CI failure triage and repair | `explorer` | `worker` | `gh-fix-ci` | Root-cause summary + approved minimal remediation |
| Security and operations readiness audit | `reviewer` | `explorer` | `security-ops-readiness-audit` | SEC/OPS control gap report with risk ranking |
| Integration/bootstrap readiness | `explorer` | `reviewer` | `integration-bootstrap-readiness` | Preflight checklist with blockers and next actions |
| Beta/GA gate readiness | `reviewer` | `monitor` | `release-gate-readiness` | Gate pass/fail matrix, blockers, rollback readiness |
| Changelog/release notes | `explorer` | `reviewer` | `changelog-generator` | Categorized changelog with requirement traceability |
| Commit sizing and timing guard | `explorer` | `reviewer` | `commit-hygiene-guard` | Commit scope/timing verdict with split recommendations |
| Push initiation gate | `worker` | `reviewer` | `push-readiness-gate` | Allow/deny push decision with path-aware check results |
| PR validation orchestration | `explorer` | `monitor` | `pr-validation-orchestrator` | PR advisory summary with size + traceability status |

Current registry:

- `spec-consistency-audit`
  - Path: `.agents/skills/spec-consistency-audit/SKILL.md`
  - Use for: spec drift checks, stale-reference scans, phase/count alignment checks.
  - Helper script: `.agents/skills/spec-consistency-audit/scripts/audit_specs.sh`
- `requirement-implementation-planner`
  - Path: `.agents/skills/requirement-implementation-planner/SKILL.md`
  - Use for: building requirement execution packets before implementation.
  - Helper script: `.agents/skills/requirement-implementation-planner/scripts/plan_requirement.sh <REQ-ID> [repo-root]`
- `requirement-implementation-executor`
  - Path: `.agents/skills/requirement-implementation-executor/SKILL.md`
  - Use for: implementing approved requirement packets with minimal diffs and mapped tests.
- `test-traceability-enforcer`
  - Path: `.agents/skills/test-traceability-enforcer/SKILL.md`
  - Use for: enforcing `Maps to:` headers, test-mode rules, and traceability validation.
- `gh-address-comments`
  - Path: `.agents/skills/gh-address-comments/SKILL.md`
  - Use for: fetching PR review threads, summarizing actionable items, and applying selected fixes.
  - Helper script: `.agents/skills/gh-address-comments/scripts/fetch_comments.py`
- `gh-fix-ci`
  - Path: `.agents/skills/gh-fix-ci/SKILL.md`
  - Use for: triaging failing GitHub Actions checks and guiding minimal CI fixes after approval.
  - Helper script: `.agents/skills/gh-fix-ci/scripts/inspect_pr_checks.py`
- `security-ops-readiness-audit`
  - Path: `.agents/skills/security-ops-readiness-audit/SKILL.md`
  - Use for: auditing SEC/OPS requirement coverage and operational control readiness.
- `integration-bootstrap-readiness`
  - Path: `.agents/skills/integration-bootstrap-readiness/SKILL.md`
  - Use for: validating third-party integration prerequisites before implementation.
- `release-gate-readiness`
  - Path: `.agents/skills/release-gate-readiness/SKILL.md`
  - Use for: evaluating Beta/GA gate criteria and canary rollback readiness.
- `changelog-generator`
  - Path: `.agents/skills/changelog-generator/SKILL.md`
  - Use for: generating requirement-aware release notes and sprint summaries from git history.
- `commit-hygiene-guard`
  - Path: `.agents/skills/commit-hygiene-guard/SKILL.md`
  - Use for: commit size and timing governance before local commits.
- `push-readiness-gate`
  - Path: `.agents/skills/push-readiness-gate/SKILL.md`
  - Use for: pre-push branch policy enforcement and path-aware checks.
- `pr-validation-orchestrator`
  - Path: `.agents/skills/pr-validation-orchestrator/SKILL.md`
  - Use for: advisory PR event validation (commit size + traceability summary).

## 10) Definition of Done

A change is complete only when all apply:

- Target requirement IDs are implemented/documented correctly.
- Tests are added/updated and mapped to requirements where relevant.
- Verification commands are run, or exact commands are provided when execution is not possible.
- No regressions introduced in existing requirements coverage.
- Security constraints are preserved.

## 11) Delivery Checklist

- Requirement IDs addressed: ____
- Dependencies checked against Coverage Matrix
- Tests added/updated with traceability headers (if test changes)
- Traceability validator run (or command provided)
- Relevant verification commands run (or command list provided)
- No hardcoded status strings
- Security constraints reviewed
- Spec links and references valid (`docs/specs/*`)
