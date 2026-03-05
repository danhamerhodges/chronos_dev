---
name: changelog-generator
description: Generate concise changelogs from git history for Chronos milestones. Use when preparing release notes, sprint summaries, or requirement-level documentation updates.
---

# Changelog Generator (Chronos)

Use this skill to convert commit history into release notes with Chronos context (requirements, specs, tests, and operational changes).

## When to use

- Milestone or phase release notes
- Weekly/monthly engineering updates
- PRD/spec revision summaries
- Internal updates tied to requirement IDs

## When not to use

- Do not use for root-cause analysis or production incident triage.
- Do not use when the user needs code changes rather than reporting.

## Workflow

1. Define scope:
   - by tag range (`vX..vY`), commit range, or date window.
2. Pull commit history:
   - include SHA, subject, and touched paths.
3. Classify entries:
   - `Added`, `Changed`, `Fixed`, `Security`, `Docs`, `Tests`, `Skills`.
4. Link to Chronos requirements when discoverable:
   - include IDs like `FR-*`, `ENG-*`, `SEC-*`, `NFR-*`, `DS-*`.
5. Produce concise markdown output:
   - one headline summary + categorized bullets.
6. Explicitly call out uncertain mappings:
   - if a commit cannot be mapped to requirement IDs, mark as `Unmapped`.

## Multi-agent Orchestration

Use parallel extraction/classification, then one consolidation pass.

1. Spawn `explorer` agents by commit slice (date ranges or tag ranges) to extract raw entries.
2. Spawn one `reviewer` agent to validate category assignment and requirement-ID mapping quality.
3. Parent agent merges and deduplicates entries into final changelog sections.
4. Keep this skill read-only; no `worker` file edits unless user explicitly asks to write output files.

## Output format

- `Title`: release or time window
- `Summary`: 2-4 bullets with most important changes
- `Sections`: Added / Changed / Fixed / Security / Docs / Tests / Skills
- `Traceability`: requirement IDs referenced in this change set
- `Unmapped`: optional list of commits needing manual classification

For multi-agent runs, each sub-agent must return:

- `scope`: commit slice analyzed
- `findings`: extracted entries with proposed category
- `evidence`: commit SHA + subject + touched paths
- `open_risks`: ambiguous categorization or traceability gaps
- `recommended_next_action`: include, reclassify, or drop

## Usage prompts

- `Create a changelog for commits since the last tag, grouped by Added/Changed/Fixed/Security/Docs/Tests/Skills and include requirement IDs.`
- `Generate a weekly changelog for the last 7 days focused on spec and skill updates.`
- `Create release notes for v0.3.0 from v0.2.0 and list unmapped commits separately.`
