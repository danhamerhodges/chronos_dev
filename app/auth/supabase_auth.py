"""Supabase Auth integration scaffolding for SEC-013."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.db.client import SupabaseClient

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

    def session_policy(self) -> dict[str, str]:
        return {
            "rotation": "enabled",
            "short_lived_access_tokens": "enabled",
            "refresh_token_required": "enabled",
        }

    def lockout_policy(self) -> dict[str, str]:
        return {
            "failed_attempts_threshold": "configurable",
            "lockout_window": "configurable",
            "reset_on_success": "enabled",
        }

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
