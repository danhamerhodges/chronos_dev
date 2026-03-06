#!/usr/bin/env python3
"""Validate that test files include a leading Maps to header."""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"

REQ_ID_RE = re.compile(r"\b(?:FR|NFR|ENG|DS|SEC|OPS)-\d{3}\b")
ALLOWED_SUFFIXES = (".py", ".ts", ".tsx")


def read_head(path: Path, lines: int = 20) -> str:
    with path.open("r", encoding="utf-8") as f:
        return "".join([next(f, "") for _ in range(lines)])


def _validate_python_header(path: Path) -> bool:
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return False

    docstring = ast.get_docstring(tree, clean=False)
    if docstring is None:
        return False

    stripped = docstring.strip()
    if not stripped.startswith("Maps to:"):
        return False

    return bool(REQ_ID_RE.search(stripped))


def _validate_ts_header(path: Path) -> bool:
    head = read_head(path)
    lines = [line for line in head.splitlines() if line.strip()]
    if not lines:
        return False

    if not lines[0].lstrip().startswith("/**"):
        return False

    close_idx = head.find("*/")
    if close_idx == -1:
        return False

    header_block = head[: close_idx + 2]
    if "Maps to:" not in header_block:
        return False

    return bool(REQ_ID_RE.search(header_block))


def validate() -> list[str]:
    failures: list[str] = []
    for path in sorted(TESTS_DIR.rglob("*")):
        if not path.is_file() or path.suffix not in ALLOWED_SUFFIXES:
            continue
        if path.name.startswith("__"):
            continue

        is_valid = _validate_python_header(path) if path.suffix == ".py" else _validate_ts_header(path)
        if not is_valid:
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
