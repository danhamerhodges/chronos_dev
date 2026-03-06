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
    environment: str = os.getenv("ENVIRONMENT", app_env)
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8000"))
    build_version: str = os.getenv("BUILD_VERSION", "0.2.0")
    build_sha: str = os.getenv("BUILD_SHA", "local")
    build_time: str = os.getenv("BUILD_TIME", "unknown")
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    test_auth_override: bool = _as_bool(os.getenv("TEST_AUTH_OVERRIDE", "false"), default=False)

    supabase_url: str = _env_with_fallback("SUPABASE_URL", "SUPABASE_URL_DEV")
    supabase_anon_key: str = _env_with_fallback("SUPABASE_ANON_KEY", "SUPABASE_ANON_KEY_DEV")
    supabase_service_role_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    supabase_db_url: str = os.getenv("SUPABASE_DB_URL", "")
    supabase_db_host: str = os.getenv("SUPABASE_DB_HOST", "")
    supabase_db_port: int = int(os.getenv("SUPABASE_DB_PORT", "5432"))
    supabase_db_name: str = os.getenv("SUPABASE_DB_NAME", "postgres")
    supabase_db_user: str = os.getenv("SUPABASE_DB_USER", "postgres")
    supabase_db_password: str = os.getenv("SUPABASE_DB_PASSWORD", "")

    stripe_secret_key: str = os.getenv("STRIPE_SECRET_KEY", "")
    stripe_webhook_secret: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    stripe_product_id: str = _env_with_fallback("STRIPE_PRODUCT_ID", "STRIPE_SUBSCRIPTION_PRODUCT_ID")
    stripe_price_id: str = _env_with_fallback("STRIPE_PRICE_ID", "STRIPE_SUBSCRIPTION_PRICE_ID")
    stripe_overage_product_id: str = _env_with_fallback(
        "STRIPE_OVERAGE_PRODUCT_ID",
        default=_env_with_fallback("STRIPE_PRODUCT_ID", "STRIPE_SUBSCRIPTION_PRODUCT_ID"),
    )
    stripe_overage_price_id: str = _env_with_fallback(
        "STRIPE_OVERAGE_PRICE_ID",
        default=_env_with_fallback("STRIPE_PRICE_ID", "STRIPE_SUBSCRIPTION_PRICE_ID"),
    )
    stripe_billing_portal_return_url: str = os.getenv("STRIPE_BILLING_PORTAL_RETURN_URL", "")
    hobbyist_monthly_limit_minutes: int = int(os.getenv("HOBBYIST_MONTHLY_LIMIT_MINUTES", "60"))
    pro_monthly_limit_minutes: int = int(os.getenv("PRO_MONTHLY_LIMIT_MINUTES", "600"))
    museum_monthly_limit_minutes: int = int(os.getenv("MUSEUM_MONTHLY_LIMIT_MINUTES", "2000"))

    metrics_enabled: bool = _as_bool(os.getenv("METRICS_ENABLED", "true"), default=True)
    metrics_namespace: str = os.getenv("METRICS_NAMESPACE", "chronos")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_redaction_mode: str = os.getenv("LOG_REDACTION_MODE", "standard")

    auth_session_ttl_minutes: int = int(os.getenv("AUTH_SESSION_TTL_MINUTES", "60"))
    auth_max_failed_attempts: int = int(os.getenv("AUTH_MAX_FAILED_ATTEMPTS", "5"))
    auth_lockout_minutes: int = int(os.getenv("AUTH_LOCKOUT_MINUTES", "15"))
    hobbyist_rate_limit_per_minute: int = int(os.getenv("HOBBYIST_RATE_LIMIT_PER_MINUTE", "100"))
    pro_rate_limit_per_minute: int = int(os.getenv("PRO_RATE_LIMIT_PER_MINUTE", "1000"))
    museum_rate_limit_per_minute: int = int(os.getenv("MUSEUM_RATE_LIMIT_PER_MINUTE", "1000"))
    gcs_bucket_name: str = os.getenv("GCS_BUCKET_NAME", "")
    gcp_project_id: str = _env_with_fallback("GCP_PROJECT_ID", "GOOGLE_CLOUD_PROJECT")
    gcp_region: str = _env_with_fallback("GCP_REGION", "VERTEX_AI_LOCATION", default="us-central1")
    gcp_access_token: str = os.getenv("GCP_ACCESS_TOKEN", "")
    enable_real_gemini: bool = _as_bool(os.getenv("ENABLE_REAL_GEMINI", "false"), default=False)
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
    gemini_prompt_version: str = os.getenv("GEMINI_PROMPT_VERSION", "phase2-era-detection-v2")
    gemini_raw_response_prefix: str = os.getenv("GEMINI_RAW_RESPONSE_PREFIX", "era-detection/raw")
    redis_url: str = os.getenv("REDIS_URL", "")


settings = Settings()
