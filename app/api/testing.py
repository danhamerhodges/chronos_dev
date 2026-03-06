"""Test-only helpers."""

from __future__ import annotations

from fastapi import APIRouter

from app.services.rate_limits import reset_rate_limits

router = APIRouter()


@router.post("/v1/testing/reset-rate-limits")
def reset_rate_limit_state() -> dict[str, str]:
    return reset_rate_limits()

