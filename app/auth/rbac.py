"""Role-based access control model for SEC-001 and SEC-013."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class Role:
    name: str


ADMIN = Role(name="admin")
ANALYST = Role(name="analyst")
MEMBER = Role(name="member")
PLATFORM_ADMIN = Role(name="platform_admin")


ROLE_PERMISSIONS: Mapping[str, frozenset[str]] = MappingProxyType({
    PLATFORM_ADMIN.name: frozenset({
        "jobs:read",
        "jobs:write",
        "billing:read",
        "billing:write",
        "users:read",
        "users:write",
        "logs:read",
        "logs:write",
        "retention:write",
        "compliance:write",
        "ops:read",
        "ops:write",
    }),
    ADMIN.name: frozenset({
        "jobs:read",
        "jobs:write",
        "billing:read",
        "billing:write",
        "users:read",
        "users:write",
        "logs:read",
        "logs:write",
        "retention:write",
        "compliance:write",
        "ops:read",
    }),
    ANALYST.name: frozenset({
        "jobs:read",
        "jobs:write",
        "billing:read",
        "users:read",
        "logs:read",
    }),
    MEMBER.name: frozenset({
        "jobs:read",
        "jobs:write",
        "billing:read",
        "users:read",
    }),
})


def normalize_role(role: object | None) -> str:
    if not isinstance(role, str):
        return ""
    return role.strip().lower()


def normalize_permission(permission: object | None) -> str:
    if not isinstance(permission, str):
        return ""
    return permission.strip().lower()


def permissions_for_role(role: object | None) -> frozenset[str]:
    return ROLE_PERMISSIONS.get(normalize_role(role), frozenset())


def role_permission_matrix() -> Mapping[str, frozenset[str]]:
    return ROLE_PERMISSIONS


def has_permission(role: object, permission: object) -> bool:
    return normalize_permission(permission) in permissions_for_role(role)
