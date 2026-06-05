"""
Maps to:
- SEC-001
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.auth.supabase_auth import SupabaseAuthService
from app.config import settings


PREFLIGHT_POLICY_METADATA = {
    "policy_stage": "local_preflight_metadata",
    "runtime_enforcement": "deferred_to_hosted_auth_integration",
}


def test_session_policy_matches_sec001_token_lifetime_contract() -> None:
    policy = SupabaseAuthService().session_policy()

    assert policy["rotation"] == "enabled"
    assert policy["short_lived_access_tokens"] == "enabled"
    assert policy["refresh_token_required"] == "enabled"
    assert policy["access_token_ttl_minutes"] == str(settings.auth_session_ttl_minutes)
    assert policy["refresh_token_rolling_days"] == "7"
    assert policy["runtime_config_status"] == "valid"
    assert policy["runtime_config_issues"] == "none"


def test_secure_cookie_flags_are_required() -> None:
    assert SupabaseAuthService().session_cookie_policy() == {
        "domain": "host_only",
        "httponly": "required",
        "secure": "required",
        "samesite": "Strict",
        **PREFLIGHT_POLICY_METADATA,
    }


def test_session_cookie_policy_is_preflight_only_until_auth_flow_evidence_exists() -> None:
    assert not hasattr(SupabaseAuthService(), "set_session_cookie")


def test_password_and_lockout_policies_match_sec001_contract() -> None:
    service = SupabaseAuthService()

    assert service.password_policy() == {
        "minimum_length": "12",
        "complexity_rules": "required",
        "weak_password_screening": "offline_or_k_anonymity",
        **PREFLIGHT_POLICY_METADATA,
    }
    lockout_policy = service.lockout_policy()
    assert lockout_policy == {
        "failed_attempts_threshold": "configurable",
        "lockout_window": "configurable",
        "max_failed_attempts": str(settings.auth_max_failed_attempts),
        "lockout_window_minutes": str(settings.auth_lockout_minutes),
        "reset_on_success": "enabled",
        "runtime_config_status": "valid",
        "runtime_config_issues": "none",
        **PREFLIGHT_POLICY_METADATA,
    }


def test_auth_policy_settings_validator_accepts_current_config() -> None:
    service = SupabaseAuthService()

    validated = service.validate_auth_policy_settings()

    assert int(validated["access_token_ttl_minutes"]) == settings.auth_session_ttl_minutes
    assert int(validated["access_token_ttl_minutes"]) <= 60
    assert int(validated["max_failed_attempts"]) == settings.auth_max_failed_attempts
    assert int(validated["max_failed_attempts"]) <= 5
    assert int(validated["lockout_window_minutes"]) == settings.auth_lockout_minutes
    assert int(validated["lockout_window_minutes"]) >= 15


def test_session_and_lockout_readbacks_reflect_valid_stricter_config() -> None:
    service = SupabaseAuthService()
    stricter_config = SimpleNamespace(
        auth_session_ttl_minutes=30,
        auth_max_failed_attempts=3,
        auth_lockout_minutes=20,
    )

    assert service.session_policy(stricter_config)["access_token_ttl_minutes"] == "30"
    assert service.session_policy(stricter_config)["runtime_config_status"] == "valid"
    lockout_policy = service.lockout_policy(stricter_config)
    assert lockout_policy["max_failed_attempts"] == "3"
    assert lockout_policy["lockout_window_minutes"] == "20"
    assert lockout_policy["runtime_config_status"] == "valid"


def test_session_and_lockout_readbacks_report_invalid_config_without_raising() -> None:
    service = SupabaseAuthService()
    invalid_config = SimpleNamespace(
        auth_session_ttl_minutes=61,
        auth_max_failed_attempts=False,
        auth_lockout_minutes=14,
    )

    session_policy = service.session_policy(invalid_config)
    assert session_policy["access_token_ttl_minutes"] == "invalid"
    assert session_policy["runtime_config_status"] == "invalid"
    assert "auth_session_ttl_minutes must be at most 60" in session_policy["runtime_config_issues"]
    assert "auth_max_failed_attempts must be an integer" in session_policy["runtime_config_issues"]
    assert "auth_lockout_minutes must be at least 15" in session_policy["runtime_config_issues"]

    lockout_policy = service.lockout_policy(invalid_config)
    assert lockout_policy["max_failed_attempts"] == "invalid"
    assert lockout_policy["lockout_window_minutes"] == "invalid"
    assert lockout_policy["runtime_config_status"] == "invalid"


def test_auth_policy_settings_validator_fails_closed_for_missing_or_malformed_config() -> None:
    service = SupabaseAuthService()

    with pytest.raises(ValueError, match="auth_session_ttl_minutes must be configured"):
        service.validate_auth_policy_settings(SimpleNamespace())

    with pytest.raises(ValueError, match="auth_session_ttl_minutes must be an integer"):
        service.validate_auth_policy_settings(
            SimpleNamespace(
                auth_session_ttl_minutes="invalid",
                auth_max_failed_attempts=5,
                auth_lockout_minutes=15,
            )
        )

    with pytest.raises(ValueError, match="auth_session_ttl_minutes must be an integer"):
        service.validate_auth_policy_settings(
            SimpleNamespace(
                auth_session_ttl_minutes=True,
                auth_max_failed_attempts=5,
                auth_lockout_minutes=15,
            )
        )

    with pytest.raises(ValueError, match="auth_max_failed_attempts must be an integer"):
        service.validate_auth_policy_settings(
            SimpleNamespace(
                auth_session_ttl_minutes=60,
                auth_max_failed_attempts=False,
                auth_lockout_minutes=15,
            )
        )

    with pytest.raises(ValueError, match="auth_session_ttl_minutes must be an integer"):
        service.validate_auth_policy_settings(
            SimpleNamespace(
                auth_session_ttl_minutes=1.0,
                auth_max_failed_attempts=5,
                auth_lockout_minutes=15,
            )
        )

    with pytest.raises(ValueError, match="auth_max_failed_attempts must be an integer"):
        service.validate_auth_policy_settings(
            SimpleNamespace(
                auth_session_ttl_minutes=60,
                auth_max_failed_attempts=5.0,
                auth_lockout_minutes=15,
            )
        )


def test_auth_policy_settings_validator_fails_closed_for_unsafe_config_bounds() -> None:
    service = SupabaseAuthService()

    with pytest.raises(ValueError, match="auth_session_ttl_minutes must be at most 60"):
        service.validate_auth_policy_settings(
            SimpleNamespace(
                auth_session_ttl_minutes=61,
                auth_max_failed_attempts=5,
                auth_lockout_minutes=15,
            )
        )

    with pytest.raises(ValueError, match="auth_max_failed_attempts must be at most 5"):
        service.validate_auth_policy_settings(
            SimpleNamespace(
                auth_session_ttl_minutes=60,
                auth_max_failed_attempts=6,
                auth_lockout_minutes=15,
            )
        )

    with pytest.raises(ValueError, match="auth_lockout_minutes must be at least 15"):
        service.validate_auth_policy_settings(
            SimpleNamespace(
                auth_session_ttl_minutes=60,
                auth_max_failed_attempts=5,
                auth_lockout_minutes=14,
            )
        )


def test_token_revocation_and_auth_audit_event_contracts_are_declared() -> None:
    service = SupabaseAuthService()

    assert service.token_revocation_policy() == {
        "immediate_logout": "required",
        "revoked_token_rejection": "required",
        "propagation_p95_seconds": "5",
        **PREFLIGHT_POLICY_METADATA,
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
