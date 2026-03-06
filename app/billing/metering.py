"""Metering semantics baseline for NFR-012."""

from __future__ import annotations

import math


def usage_event_key(account_id: str, metric_name: str, window: str) -> str:
    return f"{account_id}:{metric_name}:{window}"


def billable_units(duration_seconds: int) -> int:
    if duration_seconds <= 0:
        return 0
    return math.ceil(duration_seconds / 60)
