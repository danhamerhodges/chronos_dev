#!/usr/bin/env python3
"""Recommend when to commit based on change volume and elapsed time."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = ROOT / ".agents" / "policies" / "ci_agents_policy.json"


def run_git(args: list[str], allow_failure: bool = False) -> str:
    proc = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True)
    if proc.returncode != 0 and not allow_failure:
        raise RuntimeError((proc.stderr or proc.stdout).strip() or f"git {' '.join(args)} failed")
    return proc.stdout


def parse_numstat(raw: str) -> tuple[int, int, int]:
    files = 0
    added = 0
    deleted = 0
    for line in raw.splitlines():
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        files += 1
        if parts[0].isdigit():
            added += int(parts[0])
        if parts[1].isdigit():
            deleted += int(parts[1])
    return files, added, deleted


def load_policy(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def recommend(policy: dict[str, Any]) -> dict[str, Any]:
    timing = policy["commit_timing"]
    staged = parse_numstat(run_git(["diff", "--cached", "--numstat", "--diff-filter=ACMR"]))
    unstaged = parse_numstat(run_git(["diff", "--numstat", "--diff-filter=ACMR"]))

    staged_files, staged_added, staged_deleted = staged
    unstaged_files, unstaged_added, unstaged_deleted = unstaged

    staged_changed = staged_added + staged_deleted
    unstaged_changed = unstaged_added + unstaged_deleted
    total_changed = staged_changed + unstaged_changed

    last_commit_raw = run_git(["log", "-1", "--format=%ct"], allow_failure=True).strip()
    now_ts = int(time.time())
    minutes_since_last = None
    if last_commit_raw.isdigit():
        minutes_since_last = int((now_ts - int(last_commit_raw)) / 60)

    reason = "Changes are still small; continue until the next checkpoint."
    status = "continue"

    if total_changed == 0:
        status = "no-op"
        reason = "Working tree is clean."
    elif total_changed >= timing["max_uncommitted_lines"]:
        status = "commit-now"
        reason = (
            f"Uncommitted change volume ({total_changed} lines) exceeded "
            f"max_uncommitted_lines ({timing['max_uncommitted_lines']})."
        )
    elif minutes_since_last is not None and minutes_since_last >= timing["target_commit_interval_minutes"]:
        status = "commit-now"
        reason = (
            f"Last commit was {minutes_since_last} minutes ago, beyond target interval "
            f"({timing['target_commit_interval_minutes']} minutes)."
        )
    elif staged_changed >= timing["recommended_min_lines"]:
        status = "commit-now"
        reason = (
            f"Staged changes ({staged_changed} lines) are above recommended minimum "
            f"({timing['recommended_min_lines']} lines)."
        )

    return {
        "status": status,
        "reason": reason,
        "metrics": {
            "staged_files": staged_files,
            "staged_changed_lines": staged_changed,
            "unstaged_files": unstaged_files,
            "unstaged_changed_lines": unstaged_changed,
            "total_changed_lines": total_changed,
            "minutes_since_last_commit": minutes_since_last,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recommend commit timing")
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    policy = load_policy(Path(args.policy))
    result = recommend(policy)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"status: {result['status']}")
        print(f"reason: {result['reason']}")
        print(
            "metrics: "
            f"staged_files={result['metrics']['staged_files']} "
            f"staged_changed={result['metrics']['staged_changed_lines']} "
            f"unstaged_files={result['metrics']['unstaged_files']} "
            f"unstaged_changed={result['metrics']['unstaged_changed_lines']} "
            f"total_changed={result['metrics']['total_changed_lines']} "
            f"minutes_since_last={result['metrics']['minutes_since_last_commit']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
