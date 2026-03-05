---
name: requirement-implementation-planner
description: Build implementation packets for ChronosRefine requirement IDs (FR/ENG/SEC/OPS/NFR/DS) using docs/specs as canon. Use when scoping a requirement, planning implementation, validating dependencies, mapping tests, or preparing a patch plan before coding.
---

# Requirement Implementation Planner

## Overview

Convert one or more requirement IDs into an execution-ready plan: dependencies, phase alignment, impacted files, tests, and verification commands.

## When to use

- Requirement scoping before implementation.
- Dependency and phase gating checks.
- Test mapping and verification planning.

## When not to use

- Do not use to apply code edits directly; use implementation-focused skills.
- Do not use for release-note generation.

## Workflow

1. Validate each requirement ID and locate its canonical definition section.
2. Locate the requirement row in the coverage matrix and confirm assigned phase/dependencies.
3. Confirm implementation-plan alignment and flag drift.
4. Map required tests using test templates and matrix references.
5. Produce a minimal implementation packet with explicit assumptions and risks.

## Multi-agent Orchestration

Use parallel read-only analysis by concern, then one parent merge.

1. Spawn `explorer` agents per concern:
   - Canonical requirement extraction.
   - Matrix dependency/phase extraction.
   - Implementation-plan alignment extraction.
   - Test-template mapping extraction.
2. Spawn one `reviewer` agent to challenge dependency assumptions and missing tests.
3. Parent agent merges all artifacts into one packet per requirement ID.
4. Do not spawn concurrent `worker` edits from this skill; this skill is planning-first.

## Input

- Required: one or more requirement IDs, e.g. `ENG-002`, `FR-004`.
- Optional: target phase and user constraints (timebox, files, no-refactor constraints).

## Output Packet

For each requirement ID, provide:

1. `Requirement`: ID + title + canonical file reference.
2. `Phase`: matrix phase and implementation-plan alignment status.
3. `Dependencies`: required IDs and whether each dependency appears satisfied.
4. `Acceptance Scope`: acceptance criteria summary and out-of-scope notes.
5. `Files to Change`: minimal expected files.
6. `Tests`: existing tests to update and new tests to add.
7. `Verification`: exact commands to run.
8. `Risks`: security/data/auth implications and rollback notes if applicable.

For multi-agent runs, each sub-agent must return:

- `scope`: extraction scope
- `findings`: structured data extracted
- `evidence`: file paths + lines
- `open_risks`: unresolved dependency/test uncertainties
- `recommended_next_action`: proceed, clarify, or block

See `references/output-template.md` for a fill-in template.

## Scripts

- Use `scripts/plan_requirement.sh <REQ-ID> <repo-root>` for deterministic discovery of canonical sections and matrix/plan hits.
- If scripts are unavailable, reproduce discovery with `rg` commands and include exact command traces.

## Guardrails

- Preserve function signatures unless required by acceptance criteria.
- Prefer minimal diffs.
- Do not infer dependency satisfaction without evidence.
- If code is absent (spec-only repo), produce a docs-first implementation packet and call out blockers.
