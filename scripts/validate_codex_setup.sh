#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAILURES=0

pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; FAILURES=$((FAILURES + 1)); }

check_file() {
  local file="$1"
  local label="$2"
  if [[ -f "$file" ]]; then
    pass "$label ($file exists)"
  else
    fail "$label ($file missing)"
  fi
}

echo "Validating Codex multi-agent + skills setup in: $ROOT"

# 1) Canonical files
check_file "AGENTS.md" "Root AGENTS"
check_file "docs/standards/codex_multi_agent_skills_standard.md" "Canonical standard"
check_file "docs/standards/codex_multi_agent_skills_runbook.md" "Canonical runbook"
check_file "docs/templates/codex_project_bootstrap_checklist.md" "Bootstrap template"
check_file ".agents/registry/roles_and_skills.yaml" "Registry"
check_file ".codex/config.toml" "Repo Codex config"
check_file ".agents/policies/ci_agents_policy.json" "CI agent policy"

# 2) Required AGENTS sections
if rg -q "## 9\) Skills Policy" AGENTS.md; then pass "AGENTS skills policy section"; else fail "AGENTS skills policy section missing"; fi
if rg -q "## 9\.1 Multi-agent orchestration policy" AGENTS.md; then pass "AGENTS multi-agent section"; else fail "AGENTS multi-agent section missing"; fi
if rg -q "## 9\.2 Workflow Coverage Matrix" AGENTS.md; then pass "AGENTS workflow matrix section"; else fail "AGENTS workflow matrix section missing"; fi

# 3) Repo runtime config controls
if rg -q "^\[features\]" .codex/config.toml && rg -q "^multi_agent\s*=\s*true" .codex/config.toml; then
  pass "Repo multi_agent feature enabled"
else
  fail "Repo multi_agent feature not enabled"
fi

if rg -q "^\[agents\]" .codex/config.toml && rg -q "^max_depth\s*=\s*1" .codex/config.toml; then
  pass "Repo max_depth set to 1"
else
  fail "Repo max_depth not set to 1"
fi

if rg -q "^max_threads\s*=\s*[0-9]+" .codex/config.toml; then
  pass "Repo max_threads configured"
else
  fail "Repo max_threads missing"
fi

# 4) Role files and role-level instructions
for role in default explorer reviewer monitor worker; do
  file=".codex/agents/${role}.toml"
  if [[ -f "$file" ]]; then
    pass "Role file present: $role"
  else
    fail "Role file missing: $role"
    continue
  fi

  if rg -q '^developer_instructions\s*=' "$file"; then
    pass "Role developer_instructions set: $role"
  else
    fail "Role developer_instructions missing: $role"
  fi

done

for role in explorer reviewer monitor; do
  file=".codex/agents/${role}.toml"
  if rg -q '^sandbox_mode\s*=\s*"read-only"' "$file"; then
    pass "Read-only sandbox enforced for $role"
  else
    fail "Read-only sandbox missing for $role"
  fi
done

# 5) Skills integrity
if [[ -d .agents/skills ]]; then
  pass "Skills directory present"
else
  fail "Skills directory missing"
fi

skill_count=0
for dir in .agents/skills/*; do
  [[ -d "$dir" ]] || continue
  skill_count=$((skill_count + 1))
  if [[ -f "$dir/SKILL.md" ]]; then
    pass "SKILL.md present: $(basename "$dir")"
  else
    fail "SKILL.md missing: $(basename "$dir")"
  fi
  if [[ -f "$dir/agents/openai.yaml" ]]; then
    pass "openai.yaml present: $(basename "$dir")"
  else
    fail "openai.yaml missing: $(basename "$dir")"
  fi
done

if [[ "$skill_count" -gt 0 ]]; then
  pass "Detected $skill_count skill directories"
else
  fail "No skills detected under .agents/skills"
fi

# 6) High-risk implicit invocation checks
check_implicit_false() {
  local path="$1"
  local name="$2"
  if rg -q '^\s*allow_implicit_invocation:\s*false\s*$' "$path"; then
    pass "High-risk skill explicit-only: $name"
  else
    fail "High-risk skill must set allow_implicit_invocation: false ($name)"
  fi
}

check_implicit_false ".agents/skills/gh-address-comments/agents/openai.yaml" "gh-address-comments"
check_implicit_false ".agents/skills/gh-fix-ci/agents/openai.yaml" "gh-fix-ci"
check_implicit_false ".agents/skills/requirement-implementation-executor/agents/openai.yaml" "requirement-implementation-executor"
check_implicit_false ".agents/skills/push-readiness-gate/agents/openai.yaml" "push-readiness-gate"

# 7) No deprecated references in operational guidance/specs
if rg -n "\\.cursor/" AGENTS.md docs/specs >/tmp/codex_cursor_refs.txt 2>/dev/null; then
  fail "Deprecated .cursor references found in AGENTS/specs (see /tmp/codex_cursor_refs.txt)"
else
  pass "No deprecated .cursor references in AGENTS/specs"
fi

# 8) No generated cache artifacts in skills
if find .agents/skills -type d -name __pycache__ -o -name '*.pyc' | grep -q .; then
  fail "Generated Python cache artifacts detected under .agents/skills"
else
  pass "No Python cache artifacts under .agents/skills"
fi

# 9) Basic repo hygiene for Python cache ignores
if [[ -f .gitignore ]] && rg -q '^__pycache__/$' .gitignore && rg -q '^\*\.pyc$' .gitignore; then
  pass "Python cache ignores present in .gitignore"
else
  fail "Missing Python cache ignore entries in .gitignore"
fi

# 10) Local override safety for service-role key
if [[ -f .env.local ]] && rg -q '^SUPABASE_SERVICE_ROLE_KEY=test_service_role$' .env.local; then
  fail ".env.local contains placeholder SUPABASE_SERVICE_ROLE_KEY override"
else
  pass ".env.local does not contain placeholder service-role override"
fi

# 11) Top-level web_search placement sanity (if configured in repo config)
if rg -q '^\[sandbox_workspace_write\]' .codex/config.toml; then
  if awk '
    BEGIN{in_ws=0; bad=0}
    /^\[sandbox_workspace_write\]/{in_ws=1; next}
    /^\[/{in_ws=0}
    {if(in_ws && $0 ~ /^web_search\s*=/) bad=1}
    END{exit bad}
  ' .codex/config.toml; then
    pass "No web_search key nested under sandbox_workspace_write in repo config"
  else
    fail "web_search incorrectly nested under sandbox_workspace_write in repo config"
  fi
else
  pass "sandbox_workspace_write table absent in repo config (no nesting risk)"
fi

if [[ "$FAILURES" -gt 0 ]]; then
  echo "Validation failed with $FAILURES issue(s)."
  exit 1
fi

echo "Validation passed with no issues."
