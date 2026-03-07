"""Maps to: ENG-016"""

from datetime import datetime, timezone
import os
from types import SimpleNamespace

import pytest

from app.db.client import SupabaseClient


def test_supabase_client_requires_config(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("SUPABASE_URL", "SUPABASE_URL_DEV", "SUPABASE_ANON_KEY", "SUPABASE_ANON_KEY_DEV"):
        monkeypatch.delenv(key, raising=False)
    client = SupabaseClient(base_url="", anon_key="")
    assert client.is_configured() is False


def test_pooling_and_backup_profiles_declared() -> None:
    client = SupabaseClient(base_url="https://example.supabase.co", anon_key="anon")
    assert client.pooling_profile()["pooler"] == "supabase-supavisor"
    assert client.backup_restore_profile()["backups"] == "managed-daily-snapshots"


def test_rest_helpers_require_explicit_headers() -> None:
    client = SupabaseClient(base_url="https://example.supabase.co", anon_key="anon")

    with pytest.raises(ValueError, match="Explicit REST headers are required"):
        client.rest_select("user_profiles", params={"select": "*"})

    with pytest.raises(ValueError, match="Explicit REST headers are required"):
        client.rest_insert("user_profiles", payload={"id": "user-1"})

    with pytest.raises(ValueError, match="Explicit REST headers are required"):
        client.rest_upsert("user_profiles", payload={"id": "user-1"}, on_conflict="id")

    with pytest.raises(ValueError, match="Explicit REST headers are required"):
        client.rest_update("user_profiles", payload={"role": "admin"}, params={"id": "eq.user-1"})

    with pytest.raises(ValueError, match="Explicit REST headers are required"):
        client.rest_delete("user_profiles", params={"id": "eq.user-1"})


def test_explicit_service_role_wrapper_remains_available(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class StubResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> list[dict[str, object]]:
            return [{"id": "user-1"}]

    class StubHttpClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def get(self, url: str, *, headers: dict[str, str], params: dict[str, str]):
            captured["url"] = url
            captured["headers"] = headers
            captured["params"] = params
            return StubResponse()

    monkeypatch.setattr("app.db.client.httpx.Client", lambda timeout: StubHttpClient())
    monkeypatch.setattr(
        "app.db.client.settings",
        SimpleNamespace(supabase_service_role_key="service-role-key"),
    )
    client = SupabaseClient(base_url="https://example.supabase.co", anon_key="anon")

    rows = client.rest_select_service_role("user_profiles", params={"select": "*", "limit": "1"})

    assert rows == [{"id": "user-1"}]
    assert captured["url"] == "https://example.supabase.co/rest/v1/user_profiles"
    assert captured["headers"]["Authorization"] == "Bearer service-role-key"
    assert captured["headers"]["apikey"] == "service-role-key"


def test_realtime_broadcast_service_role_uses_realtime_send_function(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class StubCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def execute(self, query: str, params: tuple[object, ...]) -> None:
            captured["query"] = query
            captured["params"] = params

    class StubConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def cursor(self) -> StubCursor:
            return StubCursor()

    monkeypatch.setattr("app.db.client.psycopg.connect", lambda dsn: StubConnection())
    client = SupabaseClient(base_url="https://example.supabase.co", anon_key="anon")
    monkeypatch.setattr(client, "direct_db_dsn", lambda: "postgresql://example")

    client.broadcast_realtime_service_role(
        topic="job_progress:job-1",
        event="progress_update",
        payload={"job_id": "job-1"},
    )

    assert captured["query"] == "select realtime.send(%s::jsonb, %s, %s, %s)"
    assert captured["params"][1:] == ("progress_update", "job_progress:job-1", True)
    assert '"job_id": "job-1"' in captured["params"][0]


def test_realtime_broadcast_service_role_serializes_datetime_payloads(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class StubCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def execute(self, query: str, params: tuple[object, ...]) -> None:
            captured["params"] = params

    class StubConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def cursor(self) -> StubCursor:
            return StubCursor()

    monkeypatch.setattr("app.db.client.psycopg.connect", lambda dsn: StubConnection())
    client = SupabaseClient(base_url="https://example.supabase.co", anon_key="anon")
    monkeypatch.setattr(client, "direct_db_dsn", lambda: "postgresql://example")

    client.broadcast_realtime_service_role(
        topic="job_progress:job-1",
        event="progress_update",
        payload={"updated_at": datetime(2026, 3, 7, tzinfo=timezone.utc)},
    )

    assert "2026-03-07" in captured["params"][0]


@pytest.mark.skipif(
    os.getenv("CHRONOS_RUN_SUPABASE_INTEGRATION") != "1",
    reason="Supabase integration tests disabled",
)
def test_supabase_sdk_query_smoke() -> None:
    client = SupabaseClient()
    ok, detail = client.healthcheck()
    assert ok is True
    assert detail.startswith("status=")
