"""
Maps to:
- SEC-001
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import app.api.dependencies as dependencies
from app.api.problem_details import ProblemException
from app.auth.supabase_auth import SupabaseAuthService


def test_authentication_requires_bearer_token() -> None:
    with pytest.raises(ProblemException) as exc_info:
        dependencies.get_current_user(authorization=None)

    assert exc_info.value.status_code == 401
    assert exc_info.value.title == "Unauthorized"


def test_invalid_supabase_token_returns_unauthorized(monkeypatch: pytest.MonkeyPatch) -> None:
    class StubSupabaseClient:
        def auth_user(self, access_token: str) -> dict[str, object]:
            raise ValueError("invalid token")

    monkeypatch.setattr(dependencies, "settings", SimpleNamespace(test_auth_override=False))
    monkeypatch.setattr(dependencies, "SupabaseClient", lambda: StubSupabaseClient())

    with pytest.raises(ProblemException) as exc_info:
        dependencies.get_current_user(authorization="Bearer invalid-token")

    assert exc_info.value.status_code == 401
    assert exc_info.value.title == "Unauthorized"


def test_supabase_profile_lookup_uses_end_user_access_token(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class StubSupabaseClient:
        def auth_user(self, access_token: str) -> dict[str, object]:
            captured["auth_token"] = access_token
            return {"id": "external-user-1", "email": "user@example.com"}

    class StubUserProfiles:
        def get_or_create(
            self,
            *,
            user_id: str,
            email: str | None,
            role: str,
            plan_tier: str,
            org_id: str,
            access_token: str,
        ) -> dict[str, object]:
            captured["profile_access_token"] = access_token
            return {
                "user_id": user_id,
                "email": email,
                "role": role,
                "plan_tier": plan_tier,
                "org_id": org_id,
            }

    monkeypatch.setattr(dependencies, "settings", SimpleNamespace(test_auth_override=False))
    monkeypatch.setattr(dependencies, "SupabaseClient", lambda: StubSupabaseClient())
    monkeypatch.setattr(dependencies, "_user_profiles", StubUserProfiles())

    user = dependencies.get_current_user(authorization="Bearer jwt-token")

    assert captured == {"auth_token": "jwt-token", "profile_access_token": "jwt-token"}
    assert user.user_id == "external-user-1"
    assert user.access_token == "jwt-token"


def test_museum_api_key_policy_is_declared_but_plan_gated() -> None:
    service = SupabaseAuthService()

    assert service.api_key_policy() == {
        "museum_tier_only": "required",
        "revocation": "required",
        "expiration": "required",
        "rate_limiting": "required",
    }
    assert service.api_key_allowed_for_plan("museum") is True
    assert service.api_key_allowed_for_plan(" Museum ") is True
    assert service.api_key_allowed_for_plan("MUSEUM") is True
    assert service.api_key_allowed_for_plan("pro") is False
    assert service.api_key_allowed_for_plan("hobbyist") is False


def test_api_key_plan_gate_fails_closed_for_missing_or_non_string_tiers() -> None:
    service = SupabaseAuthService()

    assert service.api_key_allowed_for_plan(None) is False
    assert service.api_key_allowed_for_plan(123) is False
