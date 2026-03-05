"""Test-mode reset helper for deterministic rate-limiter tests."""

from __future__ import annotations


def reset_rate_limits() -> dict[str, str]:
    return {"status": "reset"}
