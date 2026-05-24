# ChronosRefine Implementation Index

Status: Navigation aid only. Product truth, requirement status, phase order, and test obligations remain in `AGENTS.md` and the canonical documents under `docs/specs/*`.

Use this index to load the smallest useful context for a task. Do not load the entire `docs/` tree by default.

## Start Here

Always read:

1. `AGENTS.md`
2. This `docs/implementation-index.md`
3. The canonical spec or packet documents for the active requirement slice

For roadmap execution, requirement selection, implementation packets, review gates, or merge closeout, also read `docs/hybrid-command-loop.md`.

## Canonical Specs

When conflicts exist, follow the source-of-truth order in `AGENTS.md`.

| Use when | Read |
|---|---|
| Functional behavior or user-facing requirement scope | `docs/specs/chronosrefine_functional_requirements.md` |
| Engineering architecture, API, processing, or integration requirements | `docs/specs/chronosrefine_engineering_requirements.md` |
| Auth, permissions, retention, deletion, audit, or operational security | `docs/specs/chronosrefine_security_operations_requirements.md` |
| Performance, cost, reliability, scalability, or platform requirements | `docs/specs/chronosrefine_nonfunctional_requirements.md` |
| UI, accessibility, interaction, and design requirements | `docs/specs/chronosrefine_design_requirements.md` |
| Requirement placement, status, phase ownership, and test mapping overview | `docs/specs/ChronosRefine Requirements Coverage Matrix.md` |
| Phase sequencing, packet gates, implementation notes, and entry criteria | `docs/specs/chronosrefine_implementation_plan.md` |
| Required test templates and traceability contract | `docs/specs/chronosrefine_test_templates.md` |

`docs/specs/chronosrefine_prd_v9.md` is context only. Do not use it to override current specs.

## Current Phase Navigation

Before changing requirement scope or status:

- Confirm the requirement ID exists in the Coverage Matrix.
- Confirm dependency requirements are satisfied.
- Confirm phase order matches the implementation plan and matrix.
- Confirm mapped tests exist in the test templates.
- Check whether an active kickoff, closeout, legal, pricing, DPA, GDPR, or hosted-proof artifact under `docs/specs/` applies.

Do not advance trackers, closeout notes, or launch claims without the evidence required by the active requirement or gate.

## Workflow Read Sets

| Workflow | Minimum read set |
|---|---|
| Spec consistency or drift audit | `AGENTS.md`, this index, Coverage Matrix, implementation plan, affected requirement specs |
| Requirement packet planning | `AGENTS.md`, this index, hybrid loop, Coverage Matrix, implementation plan, test templates, affected requirement specs |
| Implementation execution | Approved packet/boundary, affected requirement specs, mapped tests, relevant code owners or modules |
| Test traceability work | `AGENTS.md`, test templates, Coverage Matrix, target tests, `scripts/validate_test_traceability.py` |
| Security or operations readiness | Security/operations specs, nonfunctional specs, implementation plan, evidence or runbooks for the active gate |
| PR validation or closeout | Hybrid loop, changed paths, mapped tests, Coverage Matrix, implementation plan, active packet/closeout notes |

## Validation Commands

Use focused checks from the active slice. For documentation-only workflow changes, start with:

```bash
git diff --check -- AGENTS.md docs/implementation-index.md docs/hybrid-command-loop.md docs/templates/hybrid-loop-transfer-kit.md
rg -n "coverage_matrix\\.md|chronosrefine_prd_final|\\bagents\\.md\\b" docs/specs
scripts/validate_codex_setup.sh
```

For requirement, implementation plan, matrix, or test-template changes, also use:

```bash
rg --files docs/specs
rg -n "^## Phase [1-6]:" "docs/specs/ChronosRefine Requirements Coverage Matrix.md"
rg -n "^### Phase [1-6]:|\\*\\*Requirements Implemented:\\*\\*|Phase [56] Requirement Set" docs/specs/chronosrefine_implementation_plan.md
python3 scripts/validate_test_traceability.py
```

Behavior changes must run the mapped tests for the touched requirement IDs. Integration, E2E, hosted, and manual gates must be reported honestly when prerequisites are absent.

## Scope Preservation

- Keep portable templates under `docs/templates/` out of operational governance unless copied into a project-specific doc.
- Keep canonical spec references under `docs/specs/`.
- Keep future-phase requirements out of the current packet unless the Coverage Matrix and implementation plan are updated in the same approved change.
- Preserve exact evidence wording when closeout, hosted proof, legal, vendor, compliance, or release status is canonical.
- Use explicit staging paths and leave unrelated local changes alone.
