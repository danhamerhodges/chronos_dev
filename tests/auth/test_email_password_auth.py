"""Maps to: SEC-013"""

from app.auth.supabase_auth import SupabaseAuthService


def test_session_policy_baseline() -> None:
    policy = SupabaseAuthService().session_policy()
    assert policy["rotation"] == "enabled"
    assert policy["refresh_token_required"] == "enabled"


def test_lockout_policy_present() -> None:
    policy = SupabaseAuthService().lockout_policy()
    assert policy["failed_attempts_threshold"] == "configurable"
