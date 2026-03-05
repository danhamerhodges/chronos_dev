#!/usr/bin/env python3
"""Analyze commit size against configurable thresholds."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = ROOT / ".agents" / "policies" / "ci_agents_policy.json"


def run_git(args: list[str]) -> str:
    proc = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout).strip() or f"git {' '.join(args)} failed")
    return proc.stdout


def load_policy(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_numstat(raw: str) -> list[tuple[int, int, str]]:
    rows: list[tuple[int, int, str]] = []
    for line in raw.splitlines():
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        added_raw, deleted_raw, path = parts
        added = int(added_raw) if added_raw.isdigit() else 0
        deleted = int(deleted_raw) if deleted_raw.isdigit() else 0
        rows.append((added, deleted, path))
    return rows


def build_diff_args(args: argparse.Namespace) -> list[str]:
    if args.staged:
        return ["diff", "--cached", "--numstat", "--find-renames", "--diff-filter=ACMR"]
    if args.base_ref:
        return [
            "diff",
            "--numstat",
            "--find-renames",
            "--diff-filter=ACMR",
            f"{args.base_ref}...{args.head_ref}",
        ]
    return ["diff", "--numstat", "--find-renames", "--diff-filter=ACMR", "HEAD~1..HEAD"]


def classify(
    rows: list[tuple[int, int, str]],
    policy: dict[str, Any],
) -> dict[str, Any]:
    cs = policy["commit_sizer"]
    total_files = len(rows)
    total_added = sum(item[0] for item in rows)
    total_deleted = sum(item[1] for item in rows)
    total_changed = total_added + total_deleted

    high_risk_paths = cs.get("high_risk_paths", [])
    risk_touched = [
        path
        for _, _, path in rows
        if any(path.startswith(risk_prefix) for risk_prefix in high_risk_paths)
    ]

    by_root: dict[str, int] = defaultdict(int)
    for added, deleted, path in rows:
        root = path.split("/", 1)[0]
        by_root[root] += added + deleted

    status = "ready"
    reasons: list[str] = []

    if total_changed > cs["hard_max_changed_lines"]:
        status = "blocked"
        reasons.append(
            f"Changed lines {total_changed} exceed hard threshold {cs['hard_max_changed_lines']}"
        )
    if total_files > cs["hard_max_files"]:
        status = "blocked"
        reasons.append(f"Changed files {total_files} exceed hard threshold {cs['hard_max_files']}")

    if status != "blocked":
        if total_changed > cs["soft_max_changed_lines"]:
            status = "split-recommended"
            reasons.append(
                f"Changed lines {total_changed} exceed soft threshold {cs['soft_max_changed_lines']}"
            )
        if total_files > cs["soft_max_files"]:
            status = "split-recommended"
            reasons.append(
                f"Changed files {total_files} exceed soft threshold {cs['soft_max_files']}"
            )

    if risk_touched and total_changed > cs["soft_max_changed_lines"]:
        if status == "ready":
            status = "split-recommended"
        reasons.append("High-risk paths are included; keep this commit tighter")

    return {
        "status": status,
        "reasons": reasons,
        "totals": {
            "files": total_files,
            "added": total_added,
            "deleted": total_deleted,
            "changed": total_changed,
        },
        "by_root": dict(sorted(by_root.items(), key=lambda item: item[1], reverse=True)),
        "high_risk_paths_touched": sorted(set(risk_touched)),
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        f"status: {report['status']}",
        (
            "totals: "
            f"files={report['totals']['files']} "
            f"added={report['totals']['added']} "
            f"deleted={report['totals']['deleted']} "
            f"changed={report['totals']['changed']}"
        ),
    ]
    if report["reasons"]:
        lines.append("reasons:")
        lines.extend(f"- {reason}" for reason in report["reasons"])
    if report["high_risk_paths_touched"]:
        lines.append("high-risk files:")
        lines.extend(f"- {item}" for item in report["high_risk_paths_touched"])
    if report["by_root"]:
        lines.append("change distribution:")
        for root, changed in report["by_root"].items():
            lines.append(f"- {root}: {changed} lines")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze commit size policy fit")
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--base-ref", default="")
    parser.add_argument("--head-ref", default="HEAD")
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--enforce", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    policy = load_policy(Path(args.policy))

    diff_args = build_diff_args(args)
    try:
        raw = run_git(diff_args)
    except RuntimeError as exc:
        # Fresh repositories may not have HEAD~1; fall back to working-tree diff.
        if not args.staged and not args.base_ref:
            try:
                raw = run_git(["diff", "--numstat", "--find-renames", "--diff-filter=ACMR"])
            except RuntimeError:
                print(f"commit-size: {exc}", file=sys.stderr)
                return 2
        else:
            print(f"commit-size: {exc}", file=sys.stderr)
            return 2

    rows = parse_numstat(raw)
    report = classify(rows, policy)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render_text(report))

    if args.enforce and report["status"] == "blocked":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
