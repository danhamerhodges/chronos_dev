#!/usr/bin/env python3
"""Validate that test files include a leading Maps to header."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"

MAPS_RE = re.compile(r"Maps to:\s*[A-Z]+-[0-9]{3}")
ALLOWED_SUFFIXES = (".py", ".ts", ".tsx")


def read_head(path: Path, lines: int = 8) -> str:
    with path.open("r", encoding="utf-8") as f:
        return "".join([next(f, "") for _ in range(lines)])


def validate() -> list[str]:
    failures: list[str] = []
    for path in sorted(TESTS_DIR.rglob("*")):
        if not path.is_file() or path.suffix not in ALLOWED_SUFFIXES:
            continue
        if path.name.startswith("__"):
            continue

        head = read_head(path)
        if not MAPS_RE.search(head):
            failures.append(str(path.relative_to(ROOT)))
    return failures


def main() -> int:
    failures = validate()
    if failures:
        print("Traceability validation failed. Missing 'Maps to:' headers in:")
        for item in failures:
            print(f"- {item}")
        return 1

    print("Traceability validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
