"""Maps to: ENG-016"""

import os

import pytest

from app.db.client import SupabaseClient


def test_supabase_client_requires_config() -> None:
    client = SupabaseClient(base_url="", anon_key="")
    assert client.is_configured() is False


def test_pooling_and_backup_profiles_declared() -> None:
    client = SupabaseClient(base_url="https://example.supabase.co", anon_key="anon")
    assert client.pooling_profile()["pooler"] == "supabase-supavisor"
    assert client.backup_restore_profile()["backups"] == "managed-daily-snapshots"


@pytest.mark.skipif(
    os.getenv("CHRONOS_RUN_SUPABASE_INTEGRATION") != "1",
    reason="Supabase integration tests disabled",
)
def test_supabase_sdk_query_smoke() -> None:
    client = SupabaseClient()
    data = client.query_table("user_profiles", columns="id", limit=1)
    assert isinstance(data, list)
