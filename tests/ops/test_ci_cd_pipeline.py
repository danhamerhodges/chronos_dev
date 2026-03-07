"""Maps to: OPS-001"""

from pathlib import Path


def test_required_workflows_exist() -> None:
    root = Path(__file__).resolve().parents[2]
    assert (root / ".github/workflows/ci.yml").exists()
    assert (root / ".github/workflows/security.yml").exists()
    assert (root / ".github/workflows/deploy-staging.yml").exists()
    assert (root / ".github/workflows/agent-pr-validation.yml").exists()
    assert (root / ".github/workflows/agent-ci-followup.yml").exists()
    assert (root / ".github/workflows/nightly-e2e.yml").exists()
    assert (root / ".github/workflows/weekly-performance.yml").exists()


def test_agent_hook_and_script_baseline_exists() -> None:
    root = Path(__file__).resolve().parents[2]
    assert (root / ".githooks/pre-commit").exists()
    assert (root / ".githooks/pre-push").exists()
    assert (root / ".githooks/post-commit").exists()
    assert (root / "scripts/agents/analyze_commit_size.py").exists()
    assert (root / "scripts/agents/recommend_commit_timing.py").exists()
    assert (root / "scripts/agents/push_gate.py").exists()
    assert (root / "scripts/agents/pr_validation_orchestrator.py").exists()
    assert (root / "scripts/ops/verify_cloud_run_runtime.py").exists()


def test_staging_deploy_workflow_is_non_placeholder() -> None:
    root = Path(__file__).resolve().parents[2]
    workflow = (root / ".github/workflows/deploy-staging.yml").read_text(encoding="utf-8")

    assert "push:" in workflow
    assert "branches: [ main ]" in workflow
    assert "gcloud run deploy" in workflow
    assert "--set-secrets" in workflow
    assert "verify_cloud_run_runtime.py" in workflow
    assert "workload_identity_provider" in workflow
    assert "placeholder" not in workflow.lower()
