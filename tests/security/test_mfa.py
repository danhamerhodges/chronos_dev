"""
Maps to:
- SEC-001
"""

from __future__ import annotations

from app.auth.supabase_auth import SupabaseAuthService


PREFLIGHT_POLICY_METADATA = {
    "policy_stage": "local_preflight_metadata",
    "runtime_enforcement": "deferred_to_hosted_auth_integration",
}


def test_mfa_policy_requires_museum_admins() -> None:
    service = SupabaseAuthService()

    assert service.mfa_policy() == {
        "optional_for_all_tiers": "enabled",
        "museum_admin_required": "enabled",
        "platform_admin_required": "enabled",
        "supported_methods": "deferred_to_hosted_mfa_integration",
        **PREFLIGHT_POLICY_METADATA,
    }
    assert service.is_mfa_required(plan_tier="museum", role="admin") is True
    assert service.is_mfa_required(plan_tier=" Museum ", role="admin") is True
    assert service.is_mfa_required(plan_tier="MUSEUM", role="platform_admin") is True
    assert service.is_mfa_required(plan_tier="museum", role="platform_admin") is True
    assert service.is_mfa_required(plan_tier="pro", role="platform_admin") is True
    assert service.is_mfa_required(plan_tier=None, role="platform_admin") is True


def test_mfa_policy_normalizes_identity_provider_role_aliases() -> None:
    service = SupabaseAuthService()

    assert service.is_mfa_required(plan_tier="pro", role="platform-admin") is True
    assert service.is_mfa_required(plan_tier="pro", role="Platform Admin") is True
    assert service.is_mfa_required(plan_tier="museum", role="tenant_admin") is True
    assert service.is_mfa_required(plan_tier="museum", role="museum_admin") is True


def test_mfa_policy_remains_optional_for_non_museum_or_non_admin_users() -> None:
    service = SupabaseAuthService()

    assert service.is_mfa_required(plan_tier="museum", role="member") is False
    assert service.is_mfa_required(plan_tier="pro", role="admin") is False
    assert service.is_mfa_required(plan_tier="hobbyist", role="admin") is False


def test_mfa_policy_fails_closed_for_missing_or_non_string_tiers() -> None:
    service = SupabaseAuthService()

    assert service.is_mfa_required(plan_tier=None, role="admin") is False
    assert service.is_mfa_required(plan_tier=123, role="user") is False
