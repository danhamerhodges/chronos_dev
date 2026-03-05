"""Maps to: SEC-013"""


def fake_auth_header(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer test-token-for-{user_id}"}
