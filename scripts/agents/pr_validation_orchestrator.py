#!/usr/bin/env python3
"""Advisory PR validation orchestrator for commit sizing and traceability checks."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = ROOT / ".agents" / "policies" / "ci_agents_policy.json"
COMMIT_SIZER = ROOT / "scripts" / "agents" / "analyze_commit_size.py"
TRACEABILITY_CHECK = ROOT / "scripts" / "validate_test_traceability.py"


def run_command(cmd: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    return proc.returncode, proc.stdout, proc.stderr


def load_event() -> dict[str, Any]:
    event_path = os.getenv("GITHUB_EVENT_PATH", "")
    if not event_path:
        return {}
    path = Path(event_path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def commit_size_report(event: dict[str, Any]) -> dict[str, Any]:
    pr = event.get("pull_request", {})
    base_sha = pr.get("base", {}).get("sha", "")
    head_sha = pr.get("head", {}).get("sha", "")

    cmd = [sys.executable, str(COMMIT_SIZER), "--json"]
    if base_sha and head_sha:
        cmd.extend(["--base-ref", base_sha, "--head-ref", head_sha])

    rc, out, err = run_command(cmd)
    if rc != 0:
        return {
            "status": "error",
            "error": (err or out).strip() or "commit size analysis failed",
        }
    return json.loads(out)


def traceability_report() -> dict[str, Any]:
    rc, out, err = run_command([sys.executable, str(TRACEABILITY_CHECK)])
    return {
        "ok": rc == 0,
        "output": (out or "").strip(),
        "error": (err or "").strip(),
    }


def render_summary(event: dict[str, Any], size: dict[str, Any], traceability: dict[str, Any]) -> str:
    event_name = os.getenv("GITHUB_EVENT_NAME", "local")
    action = event.get("action", "n/a")
    pr_number = event.get("pull_request", {}).get("number", "n/a")

    lines = [
        "## Agent PR Validator",
        f"- Event: `{event_name}`",
        f"- Action: `{action}`",
        f"- PR: `{pr_number}`",
        "",
        "### Commit Sizing",
    ]

    if size.get("status") == "error":
        lines.append(f"- Status: `error` ({size.get('error', 'unknown')})")
    else:
        lines.append(f"- Status: `{size.get('status', 'unknown')}`")
        totals = size.get("totals", {})
        lines.append(
            "- Totals: "
            f"files={totals.get('files', 0)} "
            f"added={totals.get('added', 0)} "
            f"deleted={totals.get('deleted', 0)} "
            f"changed={totals.get('changed', 0)}"
        )
        if size.get("reasons"):
            lines.append("- Reasons:")
            lines.extend([f"  - {reason}" for reason in size["reasons"]])

    lines.append("")
    lines.append("### Traceability Check")
    lines.append(f"- Status: `{'pass' if traceability['ok'] else 'fail'}`")
    if traceability["output"]:
        lines.append("- Output:")
        lines.append("```text")
        lines.append(traceability["output"])
        lines.append("```")
    if traceability["error"]:
        lines.append("- Error:")
        lines.append("```text")
        lines.append(traceability["error"])
        lines.append("```")

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run advisory PR validation")
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--write-summary", default="")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    event = load_event()
    size = commit_size_report(event)
    traceability = traceability_report()

    summary = render_summary(event, size, traceability)

    if args.write_summary:
        Path(args.write_summary).write_text(summary + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps({"commit_size": size, "traceability": traceability}, indent=2))
    else:
        print(summary)

    mode = json.loads(Path(args.policy).read_text(encoding="utf-8")).get("mode", "advisory")
    if mode == "enforce" and (size.get("status") == "blocked" or not traceability["ok"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
