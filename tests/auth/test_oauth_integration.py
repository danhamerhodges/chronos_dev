"""Maps to: SEC-013"""

import os

import pytest
from supabase_auth.errors import AuthApiError

from app.auth.supabase_auth import AuthProviderConfig, SupabaseAuthService


def test_oauth_flags_configurable() -> None:
    service = SupabaseAuthService(AuthProviderConfig(oauth_google_enabled=True, oauth_github_enabled=False))
    flows = service.supported_flows()
    assert flows["oauth_google"] is True
    assert flows["oauth_github"] is False


def test_profile_management_capabilities_exist() -> None:
    service = SupabaseAuthService()
    capabilities = service.profile_management_capabilities()
    assert "change_password" in capabilities


@pytest.mark.skipif(
    os.getenv("CHRONOS_RUN_SUPABASE_INTEGRATION") != "1",
    reason="Supabase integration tests disabled",
)
def test_magic_link_smoke() -> None:
    email = os.getenv("CHRONOS_TEST_EMAIL", "")
    if not email:
        pytest.skip("Missing CHRONOS_TEST_EMAIL for magic-link integration")
    try:
        response = SupabaseAuthService().send_magic_link(email=email)
    except AuthApiError as exc:
        if "security purposes" in str(exc).lower() or "too many requests" in str(exc).lower():
            pytest.skip(f"Supabase magic-link rate limit hit: {exc}")
        raise
    assert response is not None
