"""
Maps to:
- SEC-001
- SEC-004
"""

from __future__ import annotations

from app.auth.rbac import has_permission, permissions_for_role, role_permission_matrix


def test_rbac_fails_closed_for_unknown_or_empty_roles() -> None:
    assert has_permission("", "jobs:read") is False
    assert has_permission("unknown", "jobs:read") is False
    assert permissions_for_role("unknown") == frozenset()


def test_rbac_normalizes_roles_and_permissions() -> None:
    assert has_permission(" Admin ", " Retention:Write ") is True
    assert has_permission(" PLATFORM_ADMIN ", " OPS:WRITE ") is True


def test_platform_admin_boundary_for_ops_write() -> None:
    assert has_permission("platform_admin", "ops:write") is True
    assert has_permission("admin", "ops:write") is False
    assert has_permission("analyst", "ops:write") is False
    assert has_permission("member", "ops:write") is False


def test_role_permission_matrix_keeps_least_privilege_baseline() -> None:
    matrix = role_permission_matrix()

    assert matrix["member"] == frozenset({"jobs:read", "jobs:write", "billing:read", "users:read"})
    assert "logs:write" not in matrix["analyst"]
    assert "retention:write" in matrix["admin"]
    assert "ops:write" in matrix["platform_admin"]
