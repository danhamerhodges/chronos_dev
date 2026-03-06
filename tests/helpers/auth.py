"""Maps to: SEC-013"""


def fake_auth_header(
    user_id: str,
    *,
    role: str = "member",
    tier: str = "hobbyist",
    org_id: str = "org-default",
) -> dict[str, str]:
    return {
        "Authorization": f"Bearer test-token-for-{user_id}",
        "X-Chronos-Role": role,
        "X-Chronos-Tier": tier,
        "X-Chronos-Org": org_id,
    }
