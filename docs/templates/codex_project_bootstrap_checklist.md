# Codex Project Bootstrap Checklist (Template)

Use this checklist to port Chronos multi-agent and skills governance into a new repository.

## 1) Core Files

- [ ] Add root `AGENTS.md`
- [ ] Add `.codex/config.toml`
- [ ] Add `.codex/agents/default.toml`
- [ ] Add `.codex/agents/explorer.toml`
- [ ] Add `.codex/agents/reviewer.toml`
- [ ] Add `.codex/agents/monitor.toml`
- [ ] Add `.codex/agents/worker.toml`
- [ ] Add `.agents/registry/roles_and_skills.yaml`
- [ ] Add `scripts/validate_codex_setup.sh`

## 2) AGENTS Policy

- [ ] Source-of-truth docs are explicit
- [ ] Testing and traceability policy is explicit
- [ ] Security policy is explicit
- [ ] Multi-agent policy is explicit
- [ ] Skills policy is explicit
- [ ] Workflow coverage matrix exists

## 3) Role Baseline

- [ ] `default` role configured
- [ ] `explorer` read-only, medium reasoning
- [ ] `reviewer` read-only, high reasoning
- [ ] `monitor` read-only, low reasoning
- [ ] `worker` writable, medium reasoning
- [ ] all roles include `developer_instructions`

## 4) Orchestration Controls

- [ ] `features.multi_agent = true`
- [ ] `agents.max_depth = 1`
- [ ] conservative `agents.max_threads`
- [ ] single-writer rule documented
- [ ] sub-agent output contract documented

## 5) Skills Baseline

- [ ] project skills under `.agents/skills`
- [ ] each skill has `SKILL.md`
- [ ] each skill has `agents/openai.yaml`
- [ ] state-changing skills set `allow_implicit_invocation: false`
- [ ] read-only skills use implicit invocation only when safe

## 6) Hygiene

- [ ] `.cursor/*` references removed from `AGENTS.md` and `docs/specs`
- [ ] Python caches ignored (`__pycache__/`, `*.pyc`)
- [ ] no generated artifacts tracked in skills tree

## 7) Validation

- [ ] `scripts/validate_codex_setup.sh` passes
- [ ] AGENTS discovery sanity check run
- [ ] role and skill inventories match registry

## 8) Sign-Off

- [ ] canonical docs + runtime configs aligned
- [ ] implementation notes captured
- [ ] carry-forward guidance saved for next project
