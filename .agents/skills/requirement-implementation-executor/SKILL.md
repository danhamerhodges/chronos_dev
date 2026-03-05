---
name: requirement-implementation-executor
description: Execute approved ChronosRefine requirement packets with minimal diffs, mapped tests, and explicit verification evidence. Use when a requirement packet is already approved and implementation work should begin.
---

# Requirement Implementation Executor

## Overview

Implement an approved requirement packet safely: smallest viable code/doc changes, mapped tests, and explicit verification output.

## When to use

- A requirement packet is approved and implementation should start.
- A user asks to implement one or more requirement IDs with tight scope.

## When not to use

- Do not use to create requirement packets from scratch.
- Do not use for release-note generation or governance-only audits.

## Preconditions

- Requirement ID(s) and accepted scope are explicit.
- Dependency requirements are satisfied or accepted as blockers.
- For multi-file or >50-line edits, provide a 3-7 step plan and wait for approval.

## Workflow

1. Validate target requirement IDs against canonical docs and coverage matrix.
2. Confirm phase/dependency alignment and affected files.
3. Produce an implementation plan with minimal diffs and test updates.
4. Apply edits with single-writer execution.
5. Add or update tests with `Maps to:` traceability headers.
6. Run verification commands or provide exact commands when execution is not possible.
7. Report blockers, risks, and deferred items explicitly.

## Multi-agent Orchestration

Use parallel analysis then single-writer implementation.

1. Spawn one `explorer` agent for dependency and file-impact mapping.
2. Spawn one `reviewer` agent for risk and missing-test challenge.
3. Parent agent merges findings and proposes the implementation plan.
4. After approval, spawn one `worker` agent for edits and validation.
5. Do not run concurrent `worker` agents on overlapping file sets.

## Output Contract

- `Requirement IDs`: implemented IDs and scope boundaries
- `Changes`: files changed and why
- `Tests`: added/updated tests and mappings
- `Verification`: commands run (or exact command list)
- `Open Risks`: unresolved issues and recommended next action

For multi-agent runs, each sub-agent must return:

- `scope`: analyzed slice or implementation slice
- `findings`: concrete observations
- `evidence`: file/line refs or command output
- `open_risks`: unresolved concerns
- `recommended_next_action`: proceed, revise, or block
