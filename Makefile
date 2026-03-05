.PHONY: validate-traceability test-backend test-frontend test-storybook test-design phase1-verify install-hooks agent-commit-size agent-commit-timing agent-push-gate agent-pr-validate

validate-traceability:
	python3 scripts/validate_test_traceability.py

test-backend:
	pytest tests/infrastructure tests/database tests/auth tests/billing tests/ops -q

test-frontend:
	pnpm -C web test

test-storybook:
	pnpm -C web storybook:test

test-design:
	pytest tests/design_system tests/visual_regression -q

phase1-verify: validate-traceability test-backend test-frontend test-storybook test-design
	pytest -q

install-hooks:
	./scripts/agents/install_git_hooks.sh

agent-commit-size:
	python3 scripts/agents/analyze_commit_size.py --staged

agent-commit-timing:
	python3 scripts/agents/recommend_commit_timing.py

agent-push-gate:
	python3 scripts/agents/push_gate.py --run

agent-pr-validate:
	python3 scripts/agents/pr_validation_orchestrator.py
