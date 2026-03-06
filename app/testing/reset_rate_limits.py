"""Test-mode reset helper for deterministic rate-limiter tests."""

from __future__ import annotations

from app.services.rate_limits import reset_rate_limits as _reset_rate_limits


def reset_rate_limits() -> dict[str, str]:
    return _reset_rate_limits()
