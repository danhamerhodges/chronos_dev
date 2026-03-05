"""Maps to: OPS-001"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_agent_policy_file_has_required_sections() -> None:
    root = Path(__file__).resolve().parents[2]
    policy_path = root / ".agents/policies/ci_agents_policy.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))

    assert policy["mode"] in {"advisory", "enforce"}
    assert "commit_sizer" in policy
    assert "commit_timing" in policy
    assert "push_gate" in policy


def test_agent_scripts_expose_help() -> None:
    root = Path(__file__).resolve().parents[2]
    scripts = [
        "scripts/agents/analyze_commit_size.py",
        "scripts/agents/recommend_commit_timing.py",
        "scripts/agents/push_gate.py",
        "scripts/agents/pr_validation_orchestrator.py",
    ]

    for rel_path in scripts:
        proc = subprocess.run(
            [sys.executable, str(root / rel_path), "--help"],
            cwd=root,
            text=True,
            capture_output=True,
        )
        assert proc.returncode == 0, proc.stderr
