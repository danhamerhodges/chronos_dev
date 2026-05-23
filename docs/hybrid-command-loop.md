# ChronosRefine Hybrid Command Loop

Status: Workflow guidance. This document does not replace `AGENTS.md` or the canonical requirements under `docs/specs/*`.

Use this loop when moving ChronosRefine forward with product direction, Codex implementation, reviewer challenge, and evidence-based closeout. One loop should produce one PR-sized result: a merged implementation PR, a merged docs/governance PR, a merged spike/evidence PR, or a blocked decision with the missing approval or prerequisite named.

Do not implement directly from the full roadmap or from historical PRD prose. Bind each slice to current canonical specs, the Coverage Matrix, the implementation plan, and mapped tests before editing.

## Source Of Truth

ChronosRefine is spec-first. When wording or status conflicts exist, follow the source-of-truth order in `AGENTS.md`.

For this workflow:

- Generic "roadmap" means `docs/specs/chronosrefine_implementation_plan.md` plus `docs/specs/ChronosRefine Requirements Coverage Matrix.md`.
- Generic "phase packet" means the current spec kickoff, packet, closeout, or evidence artifact under `docs/specs/`.
- `docs/implementation-index.md` is navigation only. It helps agents find the right docs, but it does not define product truth.
- `docs/templates/*` files are portable examples and are non-governing unless copied into a project-specific operational doc.

## Role Mapping

Use the existing Chronos role model. PLAID and Lead/Integrator are process hats, not new executable roles.

| Process hat | Chronos role usage | Owns | Does not own |
|---|---|---|---|
| PLAID | `default`, with `explorer` or `reviewer` support when useful | Product direction, pressure testing, scope reconciliation, next-slice choice | Code diffs, branch mechanics, CI claims |
| Lead/Integrator | `default` or `worker` after approval | Branch boundary, read set, staging paths, validation commands, PR/merge gate | Expanding product scope without approval |
| Explorer | `explorer` | Read-only discovery, specs, dependency evidence, feasibility checks | Production implementation |
| Worker | `worker` | Approved implementation or docs patch inside the active boundary | Product reframing, broad refactors, unrelated cleanup |
| Reviewer | `reviewer` | Correctness, security, privacy, UX, tests, traceability, and scope drift review | Rubber-stamp approval before evidence exists |
| Monitor | `monitor` | CI polling, hosted status checks, long-running command collection | Changing scope or code |

## The Five-Step Loop

### 1. Choose The Requirement Slice

Identify the smallest next outcome using the canonical specs, Coverage Matrix, implementation plan, and any active kickoff or closeout notes.

Output:

- requirement IDs and titles,
- current Coverage Matrix status,
- current implementation plan phase,
- expected PR-sized outcome,
- explicit non-goals and future-phase boundaries,
- required human, hosted, vendor, legal, compliance, or release gates.

Stop if the slice depends on a requirement whose dependency, phase placement, or test mapping is unclear.

### 2. Bind The Implementation Boundary

Before edits, bind the slice to a concrete execution boundary.

Required boundary:

- branch name or existing branch context,
- read set, starting with `AGENTS.md` and `docs/implementation-index.md`,
- requirement IDs and dependency checks,
- expected files or directories to change,
- files, surfaces, and requirements out of scope,
- validation commands,
- manual gates and evidence paths,
- reviewer checklist,
- risk and rollback notes,
- explicit staging paths.

If the current docs lack this boundary, update the relevant planning or packet artifact first and keep it under `docs/specs/*` when it affects requirement truth.

### 3. Execute In The Smallest Safe Unit

Worker implementation must stay inside the approved boundary.

Rules:

- Use explicit staging paths only.
- Preserve unrelated local changes.
- Keep function signatures, schemas, and public contracts stable unless the active requirement demands otherwise.
- Add or update mapped tests for behavior changes.
- Do not advance trackers, closeout notes, or launch claims without the required evidence.
- Stop for approval before installs, migrations, destructive commands, remote/service configuration, credential changes, auth changes, payment changes, retention changes, or data-residency changes.

### 4. Review And Gate

Reviewer checks the diff against `AGENTS.md`, this loop, the active specs, the Coverage Matrix, the implementation plan, and mapped tests.

Minimum review questions:

- Does the PR match the named requirement IDs and phase?
- Are dependencies satisfied and phase order preserved?
- Did future-phase work stay out of scope?
- Are tests mapped in `docs/specs/chronosrefine_test_templates.md` or otherwise justified?
- Are security, privacy, auth, payment, retention, and data-residency constraints preserved?
- Are hosted, manual, vendor, legal, compliance, and release gates claimed only when performed?
- Are residual risks and rollback notes explicit?

### 5. Reconcile Specs And Select The Next Move

After merge, reconcile what actually landed with canonical docs and evidence.

Reconciliation should answer:

- Which requirement acceptance criteria moved from open to done?
- Which items remain open, blocked, or deferred?
- Did any product, architecture, security, or operational assumption change?
- Do the Coverage Matrix, implementation plan, test templates, packet/closeout notes, evidence docs, and launch claims still agree?
- What is the next smallest requirement slice?

## Stop Conditions

Stop and ask before continuing when:

- specs disagree on scope, status, privacy, security, phase order, or release claims,
- the change would weaken a non-negotiable security, privacy, billing, retention, or data-residency control,
- required hosted/manual/legal/vendor/compliance evidence has not been performed,
- the requested work is larger than one PR-sized result,
- a UI worker would need to edit backend, persistence, auth, payment, model, infrastructure, or privacy-boundary files,
- a portable template conflicts with Chronos canonical specs or `AGENTS.md`.

## Validation Defaults

Replace these with narrower commands whenever the active slice has better targeted checks.

Documentation-only workflow changes:

```bash
git diff --check -- AGENTS.md docs/implementation-index.md docs/hybrid-command-loop.md docs/templates/hybrid-loop-transfer-kit.md
rg -n "coverage_matrix\\.md|chronosrefine_prd_final|\\bagents\\.md\\b" docs/specs
scripts/validate_codex_setup.sh
```

Requirement or spec changes:

```bash
rg --files docs/specs
rg -n "^## Phase [1-6]:" "docs/specs/ChronosRefine Requirements Coverage Matrix.md"
rg -n "^### Phase [1-6]:|\\*\\*Requirements Implemented:\\*\\*|Phase [56] Requirement Set" docs/specs/chronosrefine_implementation_plan.md
python3 scripts/validate_test_traceability.py
```

Behavior changes must also run the focused tests named by the active requirement mapping. Integration, hosted, or E2E checks must skip gracefully when prerequisites are absent unless the active closeout gate explicitly requires live proof.
