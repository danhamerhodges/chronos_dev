"""Application configuration and typed access to environment settings."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_with_fallback(primary: str, *fallbacks: str, default: str = "") -> str:
    value = os.getenv(primary)
    if value:
        return value
    for key in fallbacks:
        fallback_value = os.getenv(key)
        if fallback_value:
            return fallback_value
    return default


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8000"))

    supabase_url: str = _env_with_fallback("SUPABASE_URL", "SUPABASE_URL_DEV")
    supabase_anon_key: str = _env_with_fallback("SUPABASE_ANON_KEY", "SUPABASE_ANON_KEY_DEV")
    supabase_service_role_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    stripe_secret_key: str = os.getenv("STRIPE_SECRET_KEY", "")
    stripe_webhook_secret: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    stripe_product_id: str = _env_with_fallback("STRIPE_PRODUCT_ID", "STRIPE_SUBSCRIPTION_PRODUCT_ID")
    stripe_price_id: str = _env_with_fallback("STRIPE_PRICE_ID", "STRIPE_SUBSCRIPTION_PRICE_ID")
    stripe_billing_portal_return_url: str = os.getenv("STRIPE_BILLING_PORTAL_RETURN_URL", "")

    metrics_enabled: bool = _as_bool(os.getenv("METRICS_ENABLED", "true"), default=True)
    metrics_namespace: str = os.getenv("METRICS_NAMESPACE", "chronos")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    auth_session_ttl_minutes: int = int(os.getenv("AUTH_SESSION_TTL_MINUTES", "60"))
    auth_max_failed_attempts: int = int(os.getenv("AUTH_MAX_FAILED_ATTEMPTS", "5"))
    auth_lockout_minutes: int = int(os.getenv("AUTH_LOCKOUT_MINUTES", "15"))


settings = Settings()
