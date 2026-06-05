"""Supabase Auth integration scaffolding for SEC-001 and SEC-013."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.auth.rbac import normalize_role
from app.config import settings
from app.db.client import SupabaseClient


MUSEUM_MFA_REQUIRED_ROLES = frozenset({"admin", "platform_admin"})
GLOBAL_MFA_REQUIRED_ROLES = frozenset({"platform_admin"})
SEC001_ACCESS_TOKEN_TTL_MINUTES = 60
SEC001_MAX_FAILED_ATTEMPTS = 5
SEC001_LOCKOUT_MINUTES = 15
PREFLIGHT_POLICY_METADATA = {
    "policy_stage": "local_preflight_metadata",
    "runtime_enforcement": "deferred_to_hosted_auth_integration",
}


def normalize_plan_tier(plan_tier: object) -> str:
    if not isinstance(plan_tier, str):
        return ""
    return plan_tier.strip().lower()


def preflight_policy(policy: dict[str, str]) -> dict[str, str]:
    return {**policy, **PREFLIGHT_POLICY_METADATA}


def validated_security_int(
    config: object,
    name: str,
    *,
    min_value: int = 1,
    max_value: int | None = None,
) -> str:
    if not hasattr(config, name):
        raise ValueError(f"{name} must be configured")
    value = getattr(config, name)
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be an integer") from None
    if parsed < min_value:
        raise ValueError(f"{name} must be at least {min_value}")
    if max_value is not None and parsed > max_value:
        raise ValueError(f"{name} must be at most {max_value}")
    return str(parsed)


@dataclass(frozen=True)
class AuthProviderConfig:
    email_password_enabled: bool = True
    oauth_google_enabled: bool = True
    oauth_github_enabled: bool = True
    magic_link_enabled: bool = True


class SupabaseAuthService:
    """Lightweight service abstraction for auth flows.

    Concrete SDK calls are intentionally deferred to integration wiring.
    """

    def __init__(self, config: AuthProviderConfig | None = None) -> None:
        self.config = config or AuthProviderConfig()
        self._db_client = SupabaseClient()

    def supported_flows(self) -> dict[str, bool]:
        return {
            "email_password": self.config.email_password_enabled,
            "oauth_google": self.config.oauth_google_enabled,
            "oauth_github": self.config.oauth_github_enabled,
            "magic_link": self.config.magic_link_enabled,
        }

    def validate_auth_policy_settings(self, config: object | None = None) -> dict[str, str]:
        source = settings if config is None else config
        return {
            "access_token_ttl_minutes": validated_security_int(
                source,
                "auth_session_ttl_minutes",
                max_value=SEC001_ACCESS_TOKEN_TTL_MINUTES,
            ),
            "max_failed_attempts": validated_security_int(
                source,
                "auth_max_failed_attempts",
                max_value=SEC001_MAX_FAILED_ATTEMPTS,
            ),
            "lockout_window_minutes": validated_security_int(
                source,
                "auth_lockout_minutes",
                min_value=SEC001_LOCKOUT_MINUTES,
            ),
        }

    def session_policy(self, config: object | None = None) -> dict[str, str]:
        validated = self.validate_auth_policy_settings(config)
        return preflight_policy(
            {
                "rotation": "enabled",
                "short_lived_access_tokens": "enabled",
                "refresh_token_required": "enabled",
                "access_token_ttl_minutes": validated["access_token_ttl_minutes"],
                "refresh_token_rolling_days": "7",
            }
        )

    def lockout_policy(self, config: object | None = None) -> dict[str, str]:
        validated = self.validate_auth_policy_settings(config)
        return preflight_policy(
            {
                "failed_attempts_threshold": "configurable",
                "lockout_window": "configurable",
                "max_failed_attempts": validated["max_failed_attempts"],
                "lockout_window_minutes": validated["lockout_window_minutes"],
                "reset_on_success": "enabled",
            }
        )

    def session_cookie_policy(self) -> dict[str, str]:
        return preflight_policy(
            {
                "domain": "host_only",
                "httponly": "required",
                "secure": "required",
                "samesite": "Strict",
            }
        )

    def password_policy(self) -> dict[str, str]:
        return preflight_policy(
            {
                "minimum_length": "12",
                "complexity_rules": "required",
                "weak_password_screening": "offline_or_k_anonymity",
            }
        )

    def api_key_policy(self) -> dict[str, str]:
        return preflight_policy(
            {
                "museum_tier_only": "required",
                "revocation": "required",
                "expiration": "required",
                "rate_limiting": "required",
            }
        )

    def api_key_allowed_for_plan(self, plan_tier: object) -> bool:
        return normalize_plan_tier(plan_tier) == "museum"

    def mfa_policy(self) -> dict[str, str]:
        return preflight_policy(
            {
                "optional_for_all_tiers": "enabled",
                "museum_admin_required": "enabled",
                "platform_admin_required": "enabled",
                "supported_methods": "deferred_to_hosted_mfa_integration",
            }
        )

    def is_mfa_required(self, *, plan_tier: object, role: str) -> bool:
        normalized_role = normalize_role(role)
        if normalized_role in GLOBAL_MFA_REQUIRED_ROLES:
            return True
        return normalize_plan_tier(plan_tier) == "museum" and normalized_role in MUSEUM_MFA_REQUIRED_ROLES

    def token_revocation_policy(self) -> dict[str, str]:
        return preflight_policy(
            {
                "immediate_logout": "required",
                "revoked_token_rejection": "required",
                "propagation_p95_seconds": "5",
            }
        )

    def auth_audit_events(self) -> tuple[str, ...]:
        return (
            "login",
            "logout",
            "failed_attempt",
            "mfa_enrollment",
            "password_reset",
            "token_refresh",
            "account_lockout",
            "admin_action",
        )

    def profile_management_capabilities(self) -> list[str]:
        return [
            "update_display_name",
            "update_avatar_url",
            "change_password",
            "manage_connected_oauth_providers",
        ]

    def sign_in_with_password(self, email: str, password: str) -> Any:
        """Execute email/password sign-in using Supabase Auth SDK."""
        client = self._db_client.sdk_client()
        return client.auth.sign_in_with_password({"email": email, "password": password})

    def send_magic_link(self, email: str) -> Any:
        """Execute magic-link auth using Supabase Auth SDK."""
        client = self._db_client.sdk_client()
        return client.auth.sign_in_with_otp({"email": email})

    def oauth_authorize_url(self, provider: str, redirect_to: str) -> Any:
        """Create OAuth authorization URL using Supabase Auth SDK."""
        if provider not in {"google", "github"}:
            raise ValueError("Unsupported provider")
        client = self._db_client.sdk_client()
        return client.auth.sign_in_with_oauth({"provider": provider, "options": {"redirect_to": redirect_to}})
