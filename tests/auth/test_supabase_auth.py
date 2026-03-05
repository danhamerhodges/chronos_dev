"""Maps to: SEC-013"""

import os

import pytest

from app.auth.supabase_auth import SupabaseAuthService


def test_supported_flows_include_required_phase1_methods() -> None:
    service = SupabaseAuthService()
    flows = service.supported_flows()
    assert flows["email_password"]
    assert flows["oauth_google"]
    assert flows["oauth_github"]
    assert flows["magic_link"]


def test_oauth_provider_validation() -> None:
    service = SupabaseAuthService()
    with pytest.raises(ValueError):
        service.oauth_authorize_url("unknown-provider", "https://example.com/callback")


@pytest.mark.skipif(
    os.getenv("CHRONOS_RUN_SUPABASE_INTEGRATION") != "1",
    reason="Supabase integration tests disabled",
)
def test_supabase_auth_password_flow_smoke() -> None:
    email = os.getenv("CHRONOS_TEST_EMAIL", "")
    password = os.getenv("CHRONOS_TEST_PASSWORD", "")
    if not email or not password:
        pytest.skip("Missing CHRONOS_TEST_EMAIL/CHRONOS_TEST_PASSWORD for auth integration")
    response = SupabaseAuthService().sign_in_with_password(email=email, password=password)
    assert response is not None
