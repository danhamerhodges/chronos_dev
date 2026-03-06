"""Health endpoints."""

from fastapi import APIRouter
from datetime import datetime, timezone

from app.api.contracts import HealthResponse
from app.config import settings
from app.db.client import SupabaseClient

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/v1/health", response_model=HealthResponse)
def health_v1() -> HealthResponse:
    database_status = "not_configured"
    if settings.supabase_url and settings.supabase_anon_key:
        ok, _detail = SupabaseClient().healthcheck()
        database_status = "healthy" if ok else "degraded"
    components = {
        "database": database_status,
        "redis": "healthy" if settings.redis_url else "not_configured",
        "gcs": "healthy" if settings.gcs_bucket_name else "not_configured",
    }
    status = "healthy" if all(value in {"healthy", "not_configured"} for value in components.values()) else "degraded"
    return HealthResponse(
        status=status,
        components=components,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
