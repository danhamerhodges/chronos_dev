"""Role-based access control model for SEC-013."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Role:
    name: str


ADMIN = Role(name="admin")
ANALYST = Role(name="analyst")
MEMBER = Role(name="member")


ROLE_PERMISSIONS: dict[str, set[str]] = {
    ADMIN.name: {"jobs:read", "jobs:write", "billing:read", "billing:write"},
    ANALYST.name: {"jobs:read", "jobs:write", "billing:read"},
    MEMBER.name: {"jobs:read"},
}


def has_permission(role: str, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())
