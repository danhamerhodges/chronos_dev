#!/usr/bin/env python3
"""Run policy-based checks before push and decide whether to allow push."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = ROOT / ".agents" / "policies" / "ci_agents_policy.json"


def run_git(args: list[str], allow_failure: bool = False) -> tuple[int, str, str]:
    proc = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True)
    if proc.returncode != 0 and not allow_failure:
        raise RuntimeError((proc.stderr or proc.stdout).strip() or f"git {' '.join(args)} failed")
    return proc.returncode, proc.stdout, proc.stderr


def load_policy(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def current_branch() -> str:
    _, out, _ = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    return out.strip()


def changed_paths() -> list[str]:
    rc, out, _ = run_git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"], allow_failure=True)
    if rc == 0 and out.strip():
        upstream = out.strip()
        _, diff, _ = run_git(["diff", "--name-only", f"{upstream}...HEAD"])
    else:
        rc_head, _, _ = run_git(["rev-parse", "HEAD~1"], allow_failure=True)
        if rc_head == 0:
            _, diff, _ = run_git(["diff", "--name-only", "HEAD~1..HEAD"])
        else:
            _, diff, _ = run_git(["diff", "--name-only", "--cached"])
    return [line.strip() for line in diff.splitlines() if line.strip()]


def group_needed(paths: list[str], path_groups: dict[str, list[str]]) -> dict[str, bool]:
    result: dict[str, bool] = {group: False for group in path_groups}
    if not paths:
        return result
    for group, prefixes in path_groups.items():
        result[group] = any(any(path.startswith(prefix) for prefix in prefixes) for path in paths)
    return result


def run_check(command: str) -> tuple[bool, str]:
    proc = subprocess.run(command, cwd=ROOT, text=True, shell=True, capture_output=True)
    ok = proc.returncode == 0
    combined = "\n".join(part for part in [proc.stdout.strip(), proc.stderr.strip()] if part)
    return ok, combined


def evaluate(policy: dict[str, Any], do_run: bool) -> dict[str, Any]:
    gate = policy["push_gate"]
    branch = current_branch()
    mode = policy.get("mode", "advisory")
    allow_env = gate.get("allow_direct_push_env", "")

    blocked_direct_push = (
        branch in gate.get("block_direct_push_branches", []) and os.getenv(allow_env, "") != "1"
    )

    paths = changed_paths()
    needed = group_needed(paths, gate.get("path_groups", {}))

    command_list: list[str] = []
    command_list.extend(gate["checks"].get("always", []))
    for group, required in needed.items():
        if required:
            command_list.extend(gate["checks"].get(group, []))

    unique_commands: list[str] = []
    seen: set[str] = set()
    for cmd in command_list:
        if cmd not in seen:
            unique_commands.append(cmd)
            seen.add(cmd)

    checks: list[dict[str, Any]] = []
    if do_run:
        for cmd in unique_commands:
            ok, output = run_check(cmd)
            checks.append({"command": cmd, "ok": ok, "output": output})
    else:
        checks = [{"command": cmd, "ok": None, "output": ""} for cmd in unique_commands]

    failed_checks = [check for check in checks if check.get("ok") is False]

    decision = "allow"
    reasons: list[str] = []
    if blocked_direct_push:
        decision = "deny"
        reasons.append(
            f"Direct push to {branch} is blocked. Set {allow_env}=1 to bypass intentionally."
        )
    if failed_checks and mode == "enforce":
        decision = "deny"
        reasons.append("One or more required checks failed in enforce mode.")
    elif failed_checks:
        reasons.append("Checks failed, but mode=advisory so push is still allowed.")

    return {
        "mode": mode,
        "branch": branch,
        "changed_paths": paths,
        "decision": decision,
        "reasons": reasons,
        "checks": checks,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate push readiness")
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--run", action="store_true", help="Run checks; otherwise dry-run")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    policy = load_policy(Path(args.policy))
    result = evaluate(policy, do_run=args.run)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"decision: {result['decision']}")
        print(f"mode: {result['mode']}")
        print(f"branch: {result['branch']}")
        print(f"changed_paths: {len(result['changed_paths'])}")
        if result["reasons"]:
            print("reasons:")
            for reason in result["reasons"]:
                print(f"- {reason}")
        if result["checks"]:
            print("checks:")
            for check in result["checks"]:
                suffix = "pending"
                if check["ok"] is True:
                    suffix = "pass"
                elif check["ok"] is False:
                    suffix = "fail"
                print(f"- [{suffix}] {check['command']}")

    return 1 if result["decision"] == "deny" else 0


if __name__ == "__main__":
    raise SystemExit(main())
