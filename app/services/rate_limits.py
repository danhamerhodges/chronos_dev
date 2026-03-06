"""Simple per-user rate limiting for Phase 2 routes."""

from __future__ import annotations

import time
from collections import defaultdict

from app.api.problem_details import ProblemException
from app.config import settings


_WINDOW_SECONDS = 60
_RATE_BUCKETS: dict[tuple[str, str], list[float]] = defaultdict(list)


def reset_rate_limits() -> dict[str, str]:
    _RATE_BUCKETS.clear()
    return {"status": "reset"}


def _limit_for_tier(plan_tier: str) -> int:
    if plan_tier.lower() == "museum":
        return settings.museum_rate_limit_per_minute
    if plan_tier.lower() == "pro":
        return settings.pro_rate_limit_per_minute
    return settings.hobbyist_rate_limit_per_minute


def enforce_rate_limit(*, user_id: str, plan_tier: str, route: str) -> None:
    limit = _limit_for_tier(plan_tier)
    bucket_key = (user_id, route)
    now = time.monotonic()
    timestamps = [stamp for stamp in _RATE_BUCKETS[bucket_key] if now - stamp < _WINDOW_SECONDS]
    if len(timestamps) >= limit:
        raise ProblemException(
            title="Rate Limit Exceeded",
            detail=f"Rate limit exceeded for {route}. Retry in under a minute.",
            status_code=429,
        )
    timestamps.append(now)
    _RATE_BUCKETS[bucket_key] = timestamps

