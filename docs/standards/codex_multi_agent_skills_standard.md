# Codex Multi-Agent and Skills Standard

Version: 1.1
Status: Active
Owner: Project Maintainers
Last Updated: 2026-03-04

## 1) Purpose

Define canonical policy for:

- `AGENTS.md` structure and behavior
- multi-agent role configuration and orchestration
- skill governance, invocation policy, and safety constraints
- portability requirements for reuse in future projects

This document is normative for Chronos and is intended to be copied and adapted for future repositories.

## 2) Normative Language

The key words `MUST`, `MUST NOT`, `SHOULD`, and `MAY` are to be interpreted as requirement levels.

## 3) Canonical Artifacts

The following files comprise the canonical set:

- `AGENTS.md`
- `.codex/config.toml`
- `.codex/agents/*.toml`
- `.agents/policies/ci_agents_policy.json`
- `.agents/skills/*/SKILL.md`
- `.agents/skills/*/agents/openai.yaml`
- `.agents/registry/roles_and_skills.yaml`
- `scripts/agents/*.py`
- `scripts/agents/install_git_hooks.sh`
- `.githooks/pre-commit`
- `.githooks/post-commit`
- `.githooks/pre-push`
- `.github/workflows/agent-pr-validation.yml`
- `.github/workflows/agent-ci-followup.yml`
- `.github/workflows/nightly-e2e.yml`
- `.github/workflows/weekly-performance.yml`
- `scripts/validate_codex_setup.sh`

## 4) AGENTS.md Scope and Best-Practice Alignment

### 4.1 Scope Rules

- `AGENTS.md` MUST hold repository-level durable guidance.
- `AGENTS.md` MUST remain concise and implementation-oriented.
- Directory-specific rules SHOULD be placed in nested `AGENTS.md` files only when behavior differs by subtree.

### 4.2 Required AGENTS Sections

Chronos root `AGENTS.md` MUST include:

- project context and source-of-truth ordering
- change-size and patch scope rules
- testing and traceability requirements
- security guardrails
- skills policy
- multi-agent orchestration policy
- workflow coverage matrix

### 4.3 Discovery and Precedence Model

- Codex guidance is layered (global then project path-depth).
- Closer instruction files override broader guidance.
- Teams SHOULD treat `AGENTS.md` updates as a feedback loop when recurring mistakes appear.

## 5) Agent Role Model (Canonical)

### 5.1 Role Inventory


| Role       | Reasoning                 | Sandbox                 | Primary Function                       | Edit Authority |
| ---------- | ------------------------- | ----------------------- | -------------------------------------- | -------------- |
| `default`  | Inherit global UI control | Inherit session default | fallback synthesis and routing         | conditional    |
| `explorer` | `medium`                  | `read-only`             | discovery, scans, evidence gathering   | none           |
| `reviewer` | `high`                    | `read-only`             | risk/correctness/security challenge    | none           |
| `monitor`  | `low`                     | `read-only`             | long-running status polling and waits  | none           |
| `worker`   | `medium`                  | writable                | approved implementation and validation | yes            |


### 5.2 Invocation and Task Ownership

- Parent agent SHOULD fan out read-heavy work to `explorer` and `reviewer` first.
- `monitor` SHOULD be used for polling and long-running checks.
- `worker` MUST be invoked only after plan approval for non-trivial edits.

### 5.3 Single-Writer Constraint

- At most one `worker` MAY edit overlapping file sets at any time.
- Concurrent `worker` edits on overlapping files are prohibited.

### 5.4 Role Config Requirements

Each role config in `.codex/agents/*.toml` MUST specify:

- `model`
- `developer_instructions`

Read-only roles (`explorer`, `reviewer`, `monitor`) MUST include `sandbox_mode = "read-only"`.

## 6) Multi-Agent Orchestration Policy

### 6.1 Runtime Controls

- `features.multi_agent` MUST be enabled.
- `agents.max_depth` MUST remain `1` unless explicitly justified.
- `agents.max_threads` SHOULD remain conservative (`4` baseline) unless workload warrants changes.

### 6.2 Fan-Out/Fan-In Contract

Each sub-agent response MUST include:

- `scope`
- `findings`
- `evidence`
- `open_risks`
- `recommended_next_action`

Parent agent MUST reconcile conflicts and publish one consolidated result.

### 6.3 Failure Handling

If a sub-agent hits approval/sandbox blockers:

- parent MUST continue non-blocked branches
- parent MUST report failed branch scope and exact blocker
- parent MAY retry manually when user approves

## 7) Skills Policy and Governance

### 7.1 Skill Placement

- Project-local skills MUST live under `.agents/skills/`.
- Every skill directory MUST include `SKILL.md`.
- Every project-local skill SHOULD include `agents/openai.yaml` for metadata and policy.

### 7.2 Skill Design Contract

Each skill MUST define:

- `When to use`
- `When not to use`
- `Workflow`
- output contract
- multi-agent behavior when relevant

### 7.3 Invocation Policy

- Explicit invocation (`$skill`) is always allowed.
- Implicit invocation policy MUST be set by risk tier:
  - state-changing/remediation skills: `allow_implicit_invocation: false`
  - read-only analysis/report skills: implicit allowed unless risk dictates otherwise

### 7.4 Dependency Metadata

Skills that rely on specific tooling or MCP integrations SHOULD declare dependencies in `agents/openai.yaml`.

## 8) Security, Privacy, and Safety Requirements

- Secrets MUST NOT be committed in repo-level Codex config.
- Service-role style privileged keys MUST NOT be used in end-user request paths without equivalent authorization controls.
- Deprecated editor-specific path references (e.g. `.cursor/*`) MUST NOT appear in operational guidance and specs (`AGENTS.md`, `docs/specs`).
- Generated artifacts (`__pycache__/`, `*.pyc`) MUST NOT be tracked.

## 9) Config and Registry Requirements

### 9.1 Config Hygiene

- `web_search` MUST be a top-level config key when used.
- `sandbox_workspace_write` table MUST only contain supported sandbox keys.

### 9.2 Registry as Source of Operational Truth

`.agents/registry/roles_and_skills.yaml` MUST capture:

- canonical role profiles and reasoning levels
- workflow-to-role-to-skill mappings
- skill risk tier and implicit invocation policy
- governance controls and validation expectations

## 10) Drift Prevention and Validation

`scripts/validate_codex_setup.sh` MUST pass before accepting setup changes.

Validation covers at least:

- required canonical files exist
- AGENTS includes core multi-agent and skills sections
- role files exist and contain `developer_instructions`
- all project skills have `SKILL.md` and `agents/openai.yaml`
- expected implicit invocation policy for high-risk skills
- no `.cursor/*` references in `AGENTS.md` or `docs/specs`
- no Python cache artifacts in `.agents/skills`
- CI agent policy file present and parseable

## 11) Agent Deployment Pipeline (Canonical)

### 11.1 Policy Mode Rollout

- CI agent policy MUST start in `advisory` mode in new projects.
- Teams SHOULD switch to `enforce` only after measuring low false-positive rate in at least one sprint.
- High-risk state-changing skills (for example push/merge gates) MUST keep `allow_implicit_invocation: false`.

### 11.2 Trigger/Event Matrix

The following trigger map is the canonical baseline for future projects:

| Domain | Trigger/Event | Canonical Action |
|---|---|---|
| local commit hygiene | `pre-commit` | run commit sizing guard (`scripts/agents/analyze_commit_size.py --staged`) |
| local commit cadence | `post-commit` | run commit timing advisor (`scripts/agents/recommend_commit_timing.py`) |
| local push safety | `pre-push` | run push readiness gate (`scripts/agents/push_gate.py --run`) |
| PR readiness | `pull_request` (`opened`, `reopened`, `synchronize`, `ready_for_review`) | run PR validation orchestrator and publish summary |
| review feedback drift | `pull_request_review` (`submitted`) | rerun PR validation orchestrator |
| merge queue parity | `merge_group` | run PR validation orchestrator |
| CI/security failure follow-up | `workflow_run` (`ci`, `security`, `completed`) | run failure diagnostics and publish actionable summary |
| nightly regression baseline | `schedule` (nightly) | run E2E/validation baseline |
| weekly performance baseline | `schedule` (weekly) | run performance baseline workflow |

### 11.3 Canonical Output Contracts

- Commit hygiene output MUST include: status, totals, reasons, high-risk paths.
- Push gate output MUST include: allow/deny decision, reasons, check-level results.
- PR validator output MUST include: commit sizing summary, traceability status, evidence snippet.
- CI follow-up output MUST include: source workflow, conclusion, PR linkage, diagnostic payload.

## 12) Carry-Forward Requirements for Future Projects

When bootstrapping a new repo, carry forward these controls by default:

- role set and reasoning profile matrix
- single-writer worker rule
- fan-out/fan-in output contract
- skill risk-tier implicit invocation policy
- canonical registry + validator pair
- docs + runtime parity checks in CI or pre-merge checks

## 13) Implementation Plan (Adoption)

1. Create canonical artifacts and baseline registry.
2. Align role configs and skill metadata to policy.
3. Add and run setup validator.
4. Fix all validation failures.
5. Record verification evidence and freeze version.
6. Reuse template checklist for new projects.

## 14) Definition of Done

Adoption is complete only when:

- canonical files exist and are current
- validator passes cleanly
- role/skill mappings match runtime config
- no prohibited artifacts or references remain
- portability checklist is ready for reuse
