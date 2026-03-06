"""Maps to: ENG-002, SEC-013"""

from types import SimpleNamespace

import pytest

from app.api.dependencies import get_current_user
from app.api.problem_details import ProblemException


def test_test_auth_override_allows_test_token_headers(monkeypatch) -> None:
    import app.api.dependencies as dependencies

    monkeypatch.setattr(dependencies, "settings", SimpleNamespace(test_auth_override=True))

    user = get_current_user(
        authorization="Bearer test-token-for-local-user",
        x_chronos_role="admin",
        x_chronos_tier="museum",
        x_chronos_org="org-test",
    )

    assert user.user_id == "local-user"
    assert user.role == "admin"
    assert user.plan_tier == "museum"
    assert user.org_id == "org-test"


def test_non_test_auth_uses_supabase_identity_and_persisted_profile(monkeypatch) -> None:
    import app.api.dependencies as dependencies

    monkeypatch.setattr(dependencies, "settings", SimpleNamespace(test_auth_override=False))
    monkeypatch.setattr(
        dependencies.SupabaseClient,
        "auth_user",
        lambda self, token: {"id": "550e8400-e29b-41d4-a716-446655440000", "email": "archivist@example.com"},
    )
    monkeypatch.setattr(
        dependencies,
        "_user_profiles",
        SimpleNamespace(
            get_or_create=lambda **kwargs: {
                "user_id": kwargs["user_id"],
                "email": kwargs["email"],
                "role": "member",
                "plan_tier": "pro",
                "org_id": "org-from-db",
            }
        ),
    )

    user = get_current_user(
        authorization="Bearer real-access-token",
        x_chronos_role="admin",
        x_chronos_tier="museum",
        x_chronos_org="org-forged",
    )

    assert user.user_id == "550e8400-e29b-41d4-a716-446655440000"
    assert user.email == "archivist@example.com"
    assert user.role == "member"
    assert user.plan_tier == "pro"
    assert user.org_id == "org-from-db"


def test_non_test_invalid_token_returns_unauthorized(monkeypatch) -> None:
    import app.api.dependencies as dependencies

    monkeypatch.setattr(dependencies, "settings", SimpleNamespace(test_auth_override=False))

    def _raise_invalid(self, token):
        raise ValueError("bad token")

    monkeypatch.setattr(dependencies.SupabaseClient, "auth_user", _raise_invalid)

    with pytest.raises(ProblemException) as exc_info:
        get_current_user(authorization="Bearer invalid-token")

    assert exc_info.value.status_code == 401
    assert exc_info.value.title == "Unauthorized"
