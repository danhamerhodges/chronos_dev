---
name: security-ops-readiness-audit
description: Audit ChronosRefine SEC/OPS requirement readiness, focusing on auth, permissions, retention, deletion, monitoring, and incident operations. Use before major milestones and release gates.
---

# Security & Ops Readiness Audit

## Overview

Evaluate implementation or spec readiness against `SEC-*` and `OPS-*` requirement families and report concrete gaps with severity.

## When to use

- Before phase transitions and release gates.
- After changes touching auth, permissions, retention, deletion, residency, monitoring, or incident response.

## When not to use

- Do not use as a substitute for penetration testing execution.
- Do not use for product UX or design-only reviews.

## Workflow

1. Collect relevant SEC/OPS requirements from canonical docs and matrix.
2. Map current implementation/docs evidence to each control requirement.
3. Classify gaps by severity (`P1/P2/P3`) and exploitability/impact.
4. Propose minimal remediations with rollback or containment guidance.
5. Summarize pass/fail status for each audited control domain.

## Multi-agent Orchestration

Use parallel control-family analysis and one consolidation pass.

1. Spawn `explorer` agents by control family (auth, data handling, ops).
2. Spawn one `reviewer` agent for adversarial risk assessment.
3. Parent agent reconciles conflicts and publishes one prioritized report.
4. If implementation edits are requested, use one `worker` agent only.

## Output Contract

- `Coverage Map`: SEC/OPS requirement-to-evidence mapping
- `Findings`: prioritized control gaps
- `Evidence`: file/line or command output
- `Fix Plan`: minimal remediation actions
- `Open Risks`: residual risk and recommended owner/action

For multi-agent runs, each sub-agent must return:

- `scope`
- `findings`
- `evidence`
- `open_risks`
- `recommended_next_action`
