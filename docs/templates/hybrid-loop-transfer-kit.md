# Hybrid Loop Transfer Kit

Status: Portable template only. This file is not ChronosRefine operational canon. In this repository, current product truth and requirement governance remain in `docs/specs/*` according to the source-of-truth order in `AGENTS.md`; use `docs/hybrid-command-loop.md` for the Chronos-specific workflow.

Use this file to copy the hybrid PLAID/Codex/Claude execution loop into another Codex project. It is intentionally portable: replace the bracketed placeholders with the target project's product docs, phases, branches, validation commands, and safety rules.

This is a workflow setup guide, not a product specification. Product truth should live in the target project's vision, PRD, roadmap, technical plan, phase packets, ADRs, and repo instructions.

## Goals

The hybrid loop exists to keep product direction, implementation, UI handoff, review, and merge discipline in a repeatable order.

One loop should produce one PR-sized result:

- a merged implementation PR,
- a merged docs or governance PR,
- a merged spike or evidence PR, or
- a clear blocked decision with the missing human, device, vendor, or product approval named.

The loop is designed to prevent three common failures:

- implementing directly from a full roadmap instead of a bounded slice,
- letting implementation agents expand product scope while coding,
- merging work without reconciling docs, evidence, validation, and next steps.

## Required Project Files

Create or update these files in the target project.

| File | Purpose |
|---|---|
| `AGENTS.md` | Project instruction surface that Codex sessions load first. |
| `docs/implementation-index.md` | Navigation layer that tells agents which docs to read for each task. |
| `docs/hybrid-command-loop.md` | The project-specific version of the five-step loop. |
| `docs/product-roadmap.md` | Phase sequencing and Codex role map. |
| `docs/phase-packets/` | One packet per active phase or slice, with branch, read set, scope, non-goals, validation, and reviewer gates. |
| `docs/code-review.md` | Review checklist for correctness, scope, security, privacy, tests, UX, and release claims. |
| `docs/repo-governance.md` | Branch protection, required checks, PR, merge, and release policy. |
| `.github/pull_request_template.md` | PR checklist that forces phase/read-set/evidence/manual-gate disclosure. |
| `docs/adr/` | Accepted architecture or product decisions that should outlive PR discussion. |

For UI-heavy projects, also add:

| File | Purpose |
|---|---|
| `CLAUDE.md` | UI-worker instruction surface, if Claude Code or a UI-specialized worker is used. |
| `design/screen-index.json` | Screen routing index for view-specific implementation. |
| `design/README.md` or equivalent | Design asset, token, and validation instructions. |

## Role Model

Use the smallest set of roles that covers the work. Personal-level Codex roles are usually enough; add project-level skills or agents only when the same product-specific prompt is repeated and cannot be captured in `AGENTS.md`, a phase packet, or the loop doc.

| Role | Owns | Does not own |
|---|---|---|
| PLAID | Product direction, pressure testing, scope reconciliation, next-slice choice | Code diffs, branch mechanics, CI details |
| Lead/Integrator | Branch discipline, read set, staging paths, validation commands, commits, push, PR, merge gate | Expanding product scope without approval |
| Explorer | Read-only research, spike evidence, device notes, feasibility decisions | Production implementation unless approved |
| Worker | Scoped implementation inside the active packet | Product reframing, broad refactors, unrelated cleanup |
| Claude/UI Worker | UI/view implementation from approved screen packets and view-state contracts | Persistence, auth, payments, package, project, privacy, data, or backend-boundary changes |
| Reviewer | Adversarial review for correctness, safety, UX risk, tests, and scope drift | Rubber-stamp approval before evidence exists |
| Monitor | CI polling, long-running command/status collection | Changing scope or code |

Rename roles if your team uses different labels, but keep the ownership boundaries.

## Setup Steps

### 1. Add Project Instructions

Create or update `AGENTS.md` with:

- source-of-truth order,
- context-loading rules,
- phase and role guidance,
- stop conditions,
- validation expectations,
- security, privacy, auth, payment, data, model, or infrastructure guardrails,
- state-changing command policy,
- definition of done.

Starter snippet:

```markdown
# Project Agent Instructions

## Source Of Truth

Use `docs/implementation-index.md` as the first navigation layer. Do not load the entire `docs/` tree by default.

Canonical product docs are `[LIST PRODUCT DOCS]`. If docs disagree, stop and report the conflict before changing code or docs.

## Product Guardrails

- Preserve `[NON-NEGOTIABLE PRODUCT PROMISE]`.
- Do not introduce `[DISALLOWED DEPENDENCIES OR SERVICES]` without approval.
- Do not hardcode secrets.
- Treat `[SENSITIVE DATA CATEGORIES]` as private.
- For risky changes touching `[AUTH/PAYMENTS/DATA/AI/INFRA]`, pause and ask before implementing.

## Codex Workflow

Before work, identify the current roadmap phase and use the role guidance in `docs/product-roadmap.md`.

For roadmap execution loops, follow `docs/hybrid-command-loop.md`: PLAID selects or reconciles the slice, Lead/Integrator binds the branch/read-set/validation boundary, workers execute only that scope, reviewers gate, and merged results update roadmap or phase packet state.

Keep changes PR-sized. Use explicit staging paths only when git exists. Preserve unrelated local changes.

## Validation Expectations

- Documentation-only changes: run `[DOC CHECK COMMANDS]`.
- Feature changes: run `[TEST COMMANDS]`.
- Release or infrastructure changes: run `[RELEASE/INFRA CHECKS]`.

If a command cannot be run, report the missing prerequisite and the exact command.
```

### 2. Add An Implementation Index

Create `docs/implementation-index.md` as the first navigation layer. It should tell agents what to read for the current task instead of asking them to load every planning doc.

Minimum sections:

- current state,
- how to load context,
- phase read sets,
- UI or surface-specific read sets,
- validation commands,
- scope preservation rules.

Starter structure:

````markdown
# Implementation Index

## Current State

- Current roadmap state: `[PHASE AND STATUS]`.
- Current branch discipline: `[BRANCH/PR/MERGE POLICY]`.
- Current repo contents: `[BOOTSTRAP SUMMARY]`.
- Current release-train decision: `[RELEASE SCOPE]`.

## How To Load Context

Always read:

1. `AGENTS.md`
2. This `docs/implementation-index.md`
3. The read set for the current roadmap phase or the surface-specific packet for the work

For roadmap execution loops that start from PLAID product direction, also read `docs/hybrid-command-loop.md` before selecting the branch or worker scope.

## Phase Read Sets

| Read set | Use when | Required context |
|---|---|---|
| Phase 0: Bootstrap | `[WHEN]` | `[DOCS]` |
| Phase 1: `[NAME]` | `[WHEN]` | `[DOCS]` |

## Validation Commands

Documentation-only changes:

```bash
[DOC CHECK COMMANDS]
```

Feature changes:

```bash
[FEATURE TEST COMMANDS]
```

## Scope Preservation Rules

- Keep `[COMMITTED SCOPE]` unless a documented product decision changes it.
- Keep `[FUTURE PHASE]` out of `[CURRENT PHASE]`.
- Stop if docs disagree.
````

### 3. Add The Hybrid Command Loop

Create `docs/hybrid-command-loop.md`.

Starter content:

```markdown
# Hybrid Command Loop

Use this loop when moving the roadmap forward with PLAID, Codex, Claude, and reviewer agents.

This document is a workflow guide, not a product source of truth. Product scope remains in `[CANONICAL PRODUCT DOCS]`.

## Operating Rule

One loop should produce one PR-sized result:

- a merged implementation PR,
- a merged docs/governance PR,
- a merged spike/evidence PR, or
- a clear blocked decision with the missing approval named.

Do not implement directly from the full roadmap. Start from the current phase packet or create/update a packet first.

## Role Split

[PASTE ROLE TABLE FROM THIS TRANSFER KIT AND CUSTOMIZE]

## The Five-Step Loop

### 1. Choose The Slice

PLAID identifies the next product outcome and pressure-tests whether it is the right next move.

Output:

- one branch-sized scope statement,
- expected worker roles,
- explicit non-goals,
- required human/device/vendor gates.

### 2. Bind The Implementation Boundary

Lead/Integrator turns the chosen slice into an execution boundary before edits begin.

Required boundary:

- branch name,
- read set,
- files or directories expected to change,
- files or surfaces explicitly out of scope,
- validation commands,
- manual gates,
- reviewer checklist,
- commit/push/merge plan.

If the current packet is missing this boundary, add or update the packet before implementation.

### 3. Execute In The Smallest Safe Unit

The assigned worker implements only the approved slice.

Rules:

- Use explicit staging paths only.
- Keep branch changes PR-sized.
- Preserve committed product scope.
- Leave unrelated local changes unstaged.
- Stop for explicit approval before risky state-changing work.

### 4. Review And Gate

Reviewer checks the diff against `docs/code-review.md`, the active phase packet, and the PR template.

Minimum review questions:

- Does the PR match the named phase or packet?
- Did it preserve committed scope and future-phase boundaries?
- Did it avoid forbidden services, dependencies, data flows, or runtime behavior?
- Are tests and evidence appropriate for the touched behavior?
- Are manual gates claimed only when the user performed them?
- Are residual risks named rather than hidden?

### 5. Reconcile And Select The Next Move

After merge, PLAID reconciles roadmap state with what actually landed.

Reconciliation should answer:

- Which acceptance criteria moved from open to done?
- Which items remain open, blocked, or deferred?
- Did any product assumption change?
- Do phase packets, roadmap checkboxes, evidence docs, and launch claims still agree?
- What is the next smallest slice?
```

### 4. Add Roadmap Role Guidance

In `docs/product-roadmap.md`, add a role map near the top.

Starter snippet:

```markdown
## Codex Agent Map

This roadmap is the planning map for phase ownership. Root `AGENTS.md` is the project instruction surface; future Codex sessions should use `AGENTS.md` to find this roadmap and then follow the role guidance below.

The hybrid PLAID/Codex/Claude execution workflow lives in `docs/hybrid-command-loop.md`. Use it before starting a branch when the next move comes from product-roadmap iteration rather than a fully bounded packet.

| Phase | Primary agent role | Inputs | Outputs and done signal |
|---|---|---|---|
| Phase 0: Bootstrap | `worker` with `reviewer` signoff | `[INPUTS]` | `[DONE SIGNAL]` |
| Phase 1: `[NAME]` | `worker` with `reviewer` signoff | `[INPUTS]` | `[DONE SIGNAL]` |
| Phase N: Hardening | `reviewer` lead, `worker` for approved fixes, `monitor` for long-running checks | `[INPUTS]` | `[DONE SIGNAL]` |

Use:

- `explorer` for read-only research, feasibility, spikes, and evidence gathering.
- `worker` for implementation with a disjoint write scope and PR-sized changes.
- `reviewer` for adversarial review of correctness, safety, security, UX, regression risk, and missing tests.
- `monitor` only for long-running checks, CI polling, or repeated status collection.
- `default` only when the work does not fit a more specific role.

Do not treat the role map as permission to expand scope. Follow the phase gate and ask for approval before risky or state-changing work.
```

### 5. Add Phase Packets

Create a packet per active implementation slice under `docs/phase-packets/`.

Packet template:

````markdown
# Phase Packet: [PHASE OR SLICE NAME]

## Status

- State: `[planned | active | blocked | complete]`
- Branch: `[codex/branch-name]`
- Owner role: `[explorer | worker | reviewer | monitor | default]`
- Reviewer role: `[reviewer or named gate]`

## Goal

[One paragraph describing the branch-sized outcome.]

## Read Set

- `AGENTS.md`
- `docs/implementation-index.md`
- `docs/product-roadmap.md`
- `[FEATURE DOC]`
- `[TECH DOC]`

## In Scope

- [ ] `[BOUNDARY ITEM]`

## Non-Goals

- `[EXPLICITLY OUT OF SCOPE]`

## Expected Changes

- `[FILE OR DIRECTORY]`: `[EXPECTED CHANGE]`

## Validation

```bash
[COMMAND]
```

Manual gates:

- `[HUMAN/DEVICE/VENDOR GATE]`

## Reviewer Checklist

- [ ] Scope matches this packet.
- [ ] Future-phase work did not leak in.
- [ ] Required tests or evidence exist.
- [ ] Manual gates are not claimed unless performed.
- [ ] Docs and implementation truth still agree.
````

### 6. Add Review And Governance Gates

Create `docs/code-review.md` with project-specific review criteria.

Minimum sections:

- review stance,
- scope and phase checks,
- security and privacy checks,
- data/auth/payment/model/infrastructure checks as applicable,
- tests and evidence,
- UX/accessibility checks if applicable,
- docs and release claims,
- approval language.

Create `docs/repo-governance.md` with:

- branch naming,
- required checks,
- PR size expectation,
- merge policy,
- emergency override policy,
- release tagging policy if applicable,
- who can approve manual gates.

Add `.github/pull_request_template.md` fields:

```markdown
## Phase / Packet

- Phase packet:
- Read set used:
- Non-goals preserved:

## Changes

-

## Validation

- [ ] Automated checks:
- [ ] Manual gates:
- [ ] Evidence paths:

## Risk / Rollback

- Risk:
- Rollback:

## Reviewer Notes

- Scope drift checked:
- Future-phase boundaries preserved:
- Product docs updated if implementation truth changed:
```

## Operating Workflow

Run the project through this sequence.

### Before A Branch

1. Confirm the current roadmap phase.
2. Read `AGENTS.md`, `docs/implementation-index.md`, and the active phase packet.
3. Use PLAID to choose or reconcile the next product slice.
4. Have Lead/Integrator bind branch, read set, expected changed files, out-of-scope surfaces, validation, and review gate.
5. Create or update the phase packet if any boundary is missing.

### During Implementation

1. Worker implements only the packet.
2. Worker gives short checkpoints after each meaningful step.
3. Worker runs focused tests and validation.
4. Worker stages explicit paths only.
5. Lead/Integrator opens the PR with phase, read set, validation, evidence, residual risks, and manual gates.

### Review

1. Reviewer checks correctness, scope, tests, security/privacy/data boundaries, UX risk, and docs consistency.
2. Worker fixes only approved findings.
3. Monitor tracks long-running checks if needed.
4. Reviewer signs off only after evidence exists.

### After Merge

1. Update local main.
2. Prune branch when safe.
3. PLAID reconciles roadmap or packet state.
4. Record product or architecture decisions in product docs or ADRs.
5. Select the next smallest slice.

## Stop Conditions

Stop and ask before continuing when:

- docs disagree on scope, privacy, security, phase order, or release claims,
- the change would weaken a non-negotiable product promise,
- a package install, production asset download, migration, destructive command, remote/service configuration, credential change, payment change, auth change, or data-retention change is required,
- human, device, vendor, legal, compliance, or release evidence is required and has not been performed,
- a UI worker would need to edit project, backend, persistence, auth, payment, model, infrastructure, or privacy-boundary files,
- the requested change is larger than one PR-sized result.

Customize this list for the target project. The stop conditions should be stricter than normal coding preferences because they protect product truth and user trust.

## Validation Defaults

Use a small matrix so agents know what to run.

| Change type | Expected validation |
|---|---|
| Documentation only | `git diff --check`, focused `rg` checks for stale references, review touched sections |
| Frontend/UI | Unit tests, component tests, visual screenshot checks, accessibility checks, responsive checks |
| Backend/API | Unit tests, integration tests, contract tests, migration checks if applicable |
| Auth/security/privacy/payment/data | Targeted tests plus reviewer signoff and explicit risk/rollback note |
| Infrastructure/CI | Local lint or dry run where available, CI status, rollback plan |
| Release docs | Product docs, privacy/security/support copy, launch checklist, actual app behavior evidence |

Replace these with exact project commands.

## Configuration Checklist

Use this checklist when installing the loop in a new project.

- [ ] `AGENTS.md` points to `docs/implementation-index.md` first.
- [ ] `AGENTS.md` names canonical product docs and conflict behavior.
- [ ] `AGENTS.md` includes state-changing command policy.
- [ ] `docs/implementation-index.md` has current state and phase read sets.
- [ ] `docs/hybrid-command-loop.md` exists and names the role split.
- [ ] `docs/product-roadmap.md` has phase sequencing and Codex agent map.
- [ ] Active work has a phase packet with branch, read set, scope, non-goals, validation, and reviewer checklist.
- [ ] `docs/code-review.md` defines adversarial review gates.
- [ ] `docs/repo-governance.md` defines branch, PR, checks, and merge policy.
- [ ] PR template asks for phase packet, read set, validation, manual gates, risk, and rollback.
- [ ] Future-phase boundaries are explicit.
- [ ] Stop conditions cover the project's highest-risk surfaces.
- [ ] Validation commands are exact, copyable, and current.

## First Loop Prompt

Use this prompt in the target project after the setup files exist.

```text
Use the hybrid command loop for this project.

Current goal: [GOAL]

First, identify the current roadmap phase from docs/implementation-index.md and docs/product-roadmap.md. Then use PLAID to choose the smallest PR-sized slice, and have Lead/Integrator bind the implementation boundary before any edits.

Return:
- branch name
- read set
- files expected to change
- files/surfaces out of scope
- validation commands
- manual gates
- reviewer checklist
- explicit stop conditions

Do not edit until the boundary is approved.
```

## Maintenance Rules

Keep the loop useful by maintaining it as the project changes.

- When implementation truth changes, update the phase packet or roadmap in the same PR if the change affects future work.
- When a review catches repeated misses, add the check to `docs/code-review.md` or the relevant packet.
- When agents keep loading too much context, tighten `docs/implementation-index.md`.
- When agents overbuild, make non-goals and future-phase boundaries more explicit.
- When validation changes, update exact commands immediately.
- When a product or architecture decision becomes durable, record it in the right product doc or ADR.
