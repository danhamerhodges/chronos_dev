"""Build/version endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.contracts import VersionResponse
from app.config import settings

router = APIRouter()


@router.get("/v1/version", response_model=VersionResponse)
def version() -> VersionResponse:
    return VersionResponse(version=settings.build_version, build_sha=settings.build_sha, build_time=settings.build_time)

