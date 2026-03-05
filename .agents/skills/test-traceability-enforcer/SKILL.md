---
name: test-traceability-enforcer
description: Enforce ChronosRefine test traceability rules (`Maps to:` headers, unit-only mode behavior, and test-mode contracts). Use when adding/updating tests or before merge readiness checks.
---

# Test Traceability Enforcer

## Overview

Validate and enforce test governance requirements from `docs/specs/chronosrefine_test_templates.md`.

## When to use

- Before merge when tests changed.
- When new tests are added and requirement mapping is required.
- When validating unit-only mode or integration skip behavior.

## When not to use

- Do not use as a replacement for feature implementation planning.
- Do not use for CI provider triage unrelated to test traceability.

## Workflow

1. Identify changed test files and verify `Maps to:` headers.
2. Validate requirement ID mappings are canonical and specific.
3. Run `python3 scripts/validate_test_traceability.py` when available.
4. Confirm unit-only mode and integration/E2E skip contracts remain valid.
5. Propose minimal fixes for missing headers, mappings, or test-mode guardrails.
6. Re-run checks and return final status.

## Multi-agent Orchestration

Use parallel auditing with one optional fix agent.

1. Spawn `explorer` agents for header checks and requirement-ID mapping checks.
2. Spawn one `reviewer` agent for governance/risk verification.
3. Parent agent consolidates findings and remediation list.
4. If edits are approved, run one `worker` agent for targeted fixes.

## Output Contract

- `Findings`: missing/invalid traceability items
- `Evidence`: file/line references and validator output
- `Fixes`: exact minimal changes
- `Verification`: validator/test commands and results
- `Residual Risks`: what remains unresolved

For multi-agent runs, each sub-agent must return:

- `scope`
- `findings`
- `evidence`
- `open_risks`
- `recommended_next_action`
