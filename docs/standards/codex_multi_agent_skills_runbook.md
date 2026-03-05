# Codex Multi-Agent and Skills Runbook (Chronos)

Version: 1.1
Last Updated: 2026-03-04

## 1) Purpose

Operational procedures for maintaining and verifying the canonical multi-agent and skills setup.

## 2) Quick Verification

Run from repo root:

```bash
scripts/validate_codex_setup.sh
```

Expected: all checks pass and script exits `0`.

Run baseline agent checks:

```bash
python3 scripts/agents/analyze_commit_size.py --staged
python3 scripts/agents/recommend_commit_timing.py
python3 scripts/agents/push_gate.py
python3 scripts/agents/pr_validation_orchestrator.py
```

Expected:

- scripts execute without syntax/runtime errors
- push gate denies protected direct push when policy requires it
- PR validator emits summary output

## 3) Instruction Discovery Verification

Use these checks when validating AGENTS precedence behavior:

```bash
codex --ask-for-approval never "Summarize the current instructions."
codex --cd docs --ask-for-approval never "Show which instruction files are active."
```

Expected:

- root AGENTS guidance is detected
- closer nested AGENTS (if present) override broader rules

## 4) Role Verification

Check repo role config files:

```bash
ls -la .codex/agents
rg -n "^model|^model_reasoning_effort|^sandbox_mode|^developer_instructions" .codex/agents/*.toml
```

Expected:

- all 5 canonical role files exist
- read-only roles define read-only sandbox
- every role defines `developer_instructions`

## 5) Skill Inventory Verification

```bash
find .agents/skills -mindepth 1 -maxdepth 1 -type d | sort
find .agents/skills -mindepth 2 -maxdepth 3 -type f -name SKILL.md | sort
find .agents/skills -mindepth 2 -maxdepth 4 -type f -path "*/agents/openai.yaml" | sort
```

Expected:

- every skill folder has `SKILL.md`
- every project skill has `agents/openai.yaml`

## 6) Policy Verification

### 6.1 High-risk implicit invocation

```bash
rg -n "allow_implicit_invocation" .agents/skills/*/agents/openai.yaml
```

Expected:

- high-risk state-changing skills set `allow_implicit_invocation: false`

### 6.2 Deprecated references

```bash
rg -n "\.cursor/" AGENTS.md docs/specs
```

Expected: no matches.

### 6.3 Artifact hygiene

```bash
find .agents/skills -type d -name __pycache__ -o -name '*.pyc'
```

Expected: no output.

## 7) Change Procedure

1. Update canonical files first (`docs/standards`, registry).
2. Update runtime files (`.codex/*`, `.agents/skills/*`) second.
3. Run validator.
4. Document results in PR/change summary.

For agent deployment changes, also:

5. Run script sanity checks:
   - `python3 -m py_compile scripts/agents/*.py`
6. Run targeted tests:
   - `.venv/bin/pytest tests/infrastructure/test_agent_automation_baseline.py tests/ops/test_ci_cd_pipeline.py -q`
7. Confirm workflow files exist and are tracked:
   - `rg --files .github/workflows | rg -n "agent-pr-validation|agent-ci-followup|nightly-e2e|weekly-performance"`

## 8) Troubleshooting

- Validator fails on missing role file:
  - recreate expected role TOML in `.codex/agents/`
- Validator fails on missing skill metadata:
  - add `agents/openai.yaml` for that skill
- AGENTS guidance appears stale:
  - restart Codex session in target directory
- policy mismatch for implicit invocation:
  - update `agents/openai.yaml` according to risk tier
- `pytest` command not found in local shell:
  - use `.venv/bin/pytest` or `python3 -m pytest` in policy/check scripts
- first-commit or no-upstream diff failures:
  - use working-tree fallback (`git diff --numstat`) and ensure branch upstream is set before push gate enforcement

## 9) Onboarding Flow (New Maintainer)

1. Read `docs/standards/codex_multi_agent_skills_standard.md`.
2. Review `.agents/registry/roles_and_skills.yaml`.
3. Run `scripts/validate_codex_setup.sh`.
4. Read `AGENTS.md` and workflow matrix.
5. Execute one dry-run audit task with `explorer + reviewer` pattern.
6. Install local hooks:
   - `./scripts/agents/install_git_hooks.sh`
7. Validate local hook chain:
   - `git config --get core.hooksPath` should return `.githooks`

## 10) Release Gate for Setup Changes

A setup change is merge-ready only when:

- validator passes
- canonical docs and registry are in sync
- role/skill policy changes are explicit in change summary
- carry-forward checklist impact is documented

## 11) New-Project Copy/Adapt Command Set

Use this sequence to bootstrap a new repository from Chronos canon.

```bash
SRC="/Users/geekboy/Projects/chronos"
NEW="/Users/geekboy/Projects/my-next-project"   # change
NEW_PROJECT_NAME="MyNextProject"                # change

mkdir -p "$NEW"/docs/standards "$NEW"/docs/templates "$NEW"/scripts \
         "$NEW"/.codex/agents "$NEW"/.agents/registry "$NEW"/.agents/skills \
         "$NEW"/.agents/policies "$NEW"/scripts/agents "$NEW"/.github/workflows \
         "$NEW"/.githooks

cp "$SRC/AGENTS.md" "$NEW/AGENTS.md"
cp "$SRC/docs/standards/codex_multi_agent_skills_standard.md" "$NEW/docs/standards/"
cp "$SRC/docs/standards/codex_multi_agent_skills_runbook.md" "$NEW/docs/standards/"
cp "$SRC/docs/templates/codex_project_bootstrap_checklist.md" "$NEW/docs/templates/"
cp "$SRC/scripts/validate_codex_setup.sh" "$NEW/scripts/"
cp "$SRC/scripts/agents/"*.py "$NEW/scripts/agents/"
cp "$SRC/scripts/agents/install_git_hooks.sh" "$NEW/scripts/agents/"
cp "$SRC/.codex/config.toml" "$NEW/.codex/config.toml"
cp "$SRC/.codex/agents/"*.toml "$NEW/.codex/agents/"
cp "$SRC/.agents/registry/roles_and_skills.yaml" "$NEW/.agents/registry/"
cp "$SRC/.agents/policies/ci_agents_policy.json" "$NEW/.agents/policies/"
rsync -a "$SRC/.agents/skills/" "$NEW/.agents/skills/"
cp "$SRC/.githooks/pre-commit" "$NEW/.githooks/"
cp "$SRC/.githooks/post-commit" "$NEW/.githooks/"
cp "$SRC/.githooks/pre-push" "$NEW/.githooks/"
cp "$SRC/.github/workflows/agent-pr-validation.yml" "$NEW/.github/workflows/"
cp "$SRC/.github/workflows/agent-ci-followup.yml" "$NEW/.github/workflows/"
cp "$SRC/.github/workflows/nightly-e2e.yml" "$NEW/.github/workflows/"
cp "$SRC/.github/workflows/weekly-performance.yml" "$NEW/.github/workflows/"
chmod +x "$NEW/scripts/validate_codex_setup.sh"
chmod +x "$NEW/scripts/agents/"*.py "$NEW/scripts/agents/install_git_hooks.sh" "$NEW/.githooks/"*

perl -i -pe "s|^  name: \".*\"|  name: \"$NEW_PROJECT_NAME\"|" \
  "$NEW/.agents/registry/roles_and_skills.yaml"
perl -i -pe "s|^  repository_root: \".*\"|  repository_root: \"$NEW\"|" \
  "$NEW/.agents/registry/roles_and_skills.yaml"
```

## 12) Step 6/7 Detailed Remediation Loop

After copying files, resolve project-specific carryover before validation:

1. Find all inherited Chronos references:
   - `rg -n "ChronosRefine|/Users/geekboy/Projects/chronos" "$NEW/AGENTS.md" "$NEW/docs/standards" "$NEW/.agents/registry/roles_and_skills.yaml"`
2. Edit all hits, prioritizing:
   - `AGENTS.md` source-of-truth doc list and any project naming
   - registry `project.name`, `project.repository_root`, and workflow labels as needed
   - standards/runbook wording that still names Chronos where project-specific
   - policy thresholds in `.agents/policies/ci_agents_policy.json` for team velocity and repo size
3. Install local hooks in the new repo:
   - `cd "$NEW" && ./scripts/agents/install_git_hooks.sh`
4. Run validator:
   - `cd "$NEW" && ./scripts/validate_codex_setup.sh`
5. If validator fails, fix only reported items, then rerun step 4.
6. Repeat until validator exits `0` with `Validation passed with no issues.`

Do not port user-local `~/.codex/*` into the new repository. Keep team policy in repo `.codex/*` and personal defaults in home config.
