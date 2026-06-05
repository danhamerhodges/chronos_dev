"""
Maps to:
- SEC-001
"""

from __future__ import annotations

from app.auth.supabase_auth import SupabaseAuthService


def test_session_policy_matches_sec001_token_lifetime_contract() -> None:
    policy = SupabaseAuthService().session_policy()

    assert policy["rotation"] == "enabled"
    assert policy["short_lived_access_tokens"] == "enabled"
    assert policy["refresh_token_required"] == "enabled"
    assert policy["access_token_ttl_minutes"] == "60"
    assert policy["refresh_token_rolling_days"] == "7"


def test_secure_cookie_flags_are_required() -> None:
    assert SupabaseAuthService().session_cookie_policy() == {
        "httponly": "required",
        "secure": "required",
        "samesite": "Strict",
    }


def test_password_and_lockout_policies_match_sec001_contract() -> None:
    service = SupabaseAuthService()

    assert service.password_policy() == {
        "minimum_length": "12",
        "complexity_rules": "required",
        "weak_password_screening": "offline_or_k_anonymity",
    }
    assert service.lockout_policy() == {
        "failed_attempts_threshold": "configurable",
        "lockout_window": "configurable",
        "max_failed_attempts": "5",
        "lockout_window_minutes": "15",
        "reset_on_success": "enabled",
    }


def test_token_revocation_and_auth_audit_event_contracts_are_declared() -> None:
    service = SupabaseAuthService()

    assert service.token_revocation_policy() == {
        "immediate_logout": "required",
        "revoked_token_rejection": "required",
        "propagation_p95_seconds": "5",
    }
    assert service.auth_audit_events() == (
        "login",
        "logout",
        "failed_attempt",
        "mfa_enrollment",
        "password_reset",
        "token_refresh",
        "account_lockout",
        "admin_action",
    )
