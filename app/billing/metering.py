"""Metering semantics baseline for NFR-012."""

from __future__ import annotations


def usage_event_key(account_id: str, metric_name: str, window: str) -> str:
    return f"{account_id}:{metric_name}:{window}"


def billable_units(events_count: int) -> int:
    return max(events_count, 0)
