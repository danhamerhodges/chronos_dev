"""Common dependencies for Phase 2 routes."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header
import httpx

from app.api.problem_details import ProblemException
from app.auth.rbac import has_permission
from app.config import settings
from app.db.client import SupabaseClient
from app.db.phase2_store import UserProfileRepository
from app.services.rate_limits import enforce_rate_limit


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    email: str | None
    role: str
    plan_tier: str
    org_id: str
    access_token: str


_user_profiles = UserProfileRepository()


def get_current_user(
    authorization: str | None = Header(default=None),
    x_chronos_role: str = Header(default="member"),
    x_chronos_tier: str = Header(default="hobbyist"),
    x_chronos_org: str = Header(default="org-default"),
) -> AuthenticatedUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise ProblemException(
            title="Unauthorized",
            detail="Bearer token is required for this endpoint.",
            status_code=401,
        )
    access_token = authorization.split(" ", 1)[1].strip()
    if settings.test_auth_override and access_token.startswith("test-token-for-"):
        user_id = access_token.removeprefix("test-token-for-")
        return AuthenticatedUser(
            user_id=user_id,
            email=f"{user_id}@example.com",
            role=x_chronos_role.lower(),
            plan_tier=x_chronos_tier.lower(),
            org_id=x_chronos_org,
            access_token=access_token,
        )
    try:
        auth_user = SupabaseClient().auth_user(access_token)
    except (ValueError, httpx.HTTPError) as exc:
        raise ProblemException(
            title="Unauthorized",
            detail="Bearer token is invalid or expired.",
            status_code=401,
        ) from exc

    user_id = auth_user["id"]
    profile = _user_profiles.get_or_create(
        user_id=user_id,
        email=auth_user.get("email"),
        role="member",
        plan_tier="hobbyist",
        org_id="org-default",
        access_token=access_token,
    )
    return AuthenticatedUser(
        user_id=profile["user_id"],
        email=profile.get("email"),
        role=profile["role"],
        plan_tier=profile["plan_tier"],
        org_id=profile["org_id"],
        access_token=access_token,
    )


def require_permission(permission: str):
    def dependency(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if not has_permission(user.role, permission):
            raise ProblemException(
                title="Forbidden",
                detail=f"Role '{user.role}' lacks required permission '{permission}'.",
                status_code=403,
            )
        return user

    return dependency


def apply_rate_limit(user: AuthenticatedUser, route: str) -> None:
    enforce_rate_limit(user_id=user.user_id, plan_tier=user.plan_tier, route=route)
