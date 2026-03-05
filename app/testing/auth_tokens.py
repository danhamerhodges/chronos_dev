"""Test token helpers."""

from __future__ import annotations


def test_bearer_token(user_id: str) -> str:
    return f"test-token-for-{user_id}"
