"""
Maps to:
- SEC-004
"""

from __future__ import annotations

from fastapi.testclient import TestClient

import app.services.rate_limits as rate_limits
from app.main import app
from tests.helpers.auth import fake_auth_header

client = TestClient(app)


def test_rate_limit_response_includes_retry_after_without_problem_body_leak(monkeypatch) -> None:
    monkeypatch.setattr(rate_limits, "_limit_for_tier", lambda plan_tier: 1)
    headers = fake_auth_header("rate-limited-user", tier="hobbyist")

    first = client.get("/v1/users/me", headers=headers)
    second = client.get("/v1/users/me", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.headers["Retry-After"] == "60"
    assert "Retry-After" not in second.text
    assert "headers" not in second.json()


def test_rate_limit_buckets_are_scoped_by_user_and_route(monkeypatch) -> None:
    monkeypatch.setattr(rate_limits, "_limit_for_tier", lambda plan_tier: 1)

    user_a = fake_auth_header("bucket-user-a", tier="hobbyist")
    user_b = fake_auth_header("bucket-user-b", tier="hobbyist")

    assert client.get("/v1/users/me", headers=user_a).status_code == 200
    assert client.get("/v1/users/me", headers=user_a).status_code == 429
    assert client.get("/v1/users/me", headers=user_b).status_code == 200
    assert client.get("/v1/fidelity-tiers", headers=user_a).status_code == 200


def test_testing_reset_rate_limits_clears_buckets(monkeypatch) -> None:
    monkeypatch.setattr(rate_limits, "_limit_for_tier", lambda plan_tier: 1)
    headers = fake_auth_header("reset-rate-user", tier="hobbyist")

    assert client.get("/v1/users/me", headers=headers).status_code == 200
    assert client.get("/v1/users/me", headers=headers).status_code == 429

    reset = client.post("/v1/testing/reset-rate-limits", headers=headers)

    assert reset.status_code == 200
    assert reset.json() == {"status": "reset"}
    assert client.get("/v1/users/me", headers=headers).status_code == 200
