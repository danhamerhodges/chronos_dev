"""
Maps to:
- SEC-001
"""

from __future__ import annotations

from app.auth.supabase_auth import SupabaseAuthService


def test_mfa_policy_requires_museum_admins() -> None:
    service = SupabaseAuthService()

    assert service.mfa_policy() == {
        "optional_for_all_tiers": "enabled",
        "museum_admin_required": "enabled",
        "supported_methods": "totp,sms,backup_codes",
    }
    assert service.is_mfa_required(plan_tier="museum", role="admin") is True
    assert service.is_mfa_required(plan_tier="museum", role="platform_admin") is True


def test_mfa_policy_remains_optional_for_non_museum_or_non_admin_users() -> None:
    service = SupabaseAuthService()

    assert service.is_mfa_required(plan_tier="museum", role="member") is False
    assert service.is_mfa_required(plan_tier="pro", role="admin") is False
    assert service.is_mfa_required(plan_tier="hobbyist", role="admin") is False
