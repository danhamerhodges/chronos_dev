---
name: spec-consistency-audit
description: Audit ChronosRefine specification documents for consistency, requirement-ID drift, phase misalignment, and stale references. Use when updating docs/specs, reviewing requirement changes, reconciling implementation plan vs coverage matrix, or before closing documentation-heavy work.
---

# Spec Consistency Audit

## Overview

Run deterministic checks against `docs/specs` and produce a concise findings report with exact file/line references and minimal patch recommendations.

## When to use

- Before merging spec/documentation-heavy changes.
- When requirement IDs, phase mapping, or canonical references changed.
- When implementation plan and coverage matrix may have drifted.

## Workflow

1. Run `scripts/audit_specs.sh <repo-root>` to collect baseline findings.
2. Classify findings by severity.
3. Propose minimal edits that preserve canonical precedence from `AGENTS.md`.
4. Re-run `scripts/audit_specs.sh` after edits.
5. Report final status with unresolved risks.

## When not to use

- Do not use for code-level bug triage or runtime failures.
- Do not use when the request is to implement product behavior; use implementation-focused skills instead.

## Multi-agent Orchestration

Use read-heavy fan-out with one consolidation pass.

1. Spawn `explorer` agents in parallel by scope:
   - Canonical docs presence and stale reference scan.
   - Coverage matrix phase header and count checks.
   - Implementation plan phase/count alignment checks.
2. Optionally spawn one `reviewer` agent to validate severity labels (`P1/P2/P3`) before final report.
3. Parent agent aggregates all findings, deduplicates evidence, and produces one prioritized report.
4. If edits are required, execute edits with a single `worker` agent only after aggregation.

## Severity Rules

- `P1`: Canonical conflicts, broken requirement IDs, or phase misalignment between matrix and implementation plan.
- `P2`: Stale references that can mislead implementation, including deprecated internal paths.
- `P3`: Hygiene issues (wording drift, weak anchors) that do not change requirement meaning.

## Required Checks

- Canonical docs exist in `docs/specs`.
- No deprecated assistant-workspace path references in specs.
- No legacy `chronosrefine_prd_final` references.
- Coverage matrix phase headers present and complete.
- Implementation plan phase requirement counts match matrix counts.
- Requirement IDs are discoverable in canonical docs.

See `references/checklist.md` for the full checklist and output contract.

## Output Contract

Return findings in this format:

- `Priority`: `P1|P2|P3`
- `Issue`: short statement
- `Evidence`: absolute file path with line number
- `Fix`: minimal exact change

If no findings remain, state: `No consistency findings detected.`

For multi-agent runs, each sub-agent must return:

- `scope`: scan slice handled
- `findings`: list of issues
- `evidence`: absolute path + line numbers or exact command output
- `open_risks`: uncertainty or possible false positives
- `recommended_next_action`: merge, escalate, or ignore with reason

## Scripts

- Use `scripts/audit_specs.sh` for deterministic scan output.
- If a script check fails due missing tools, fall back to equivalent `rg`/`sed` commands and note the fallback.
