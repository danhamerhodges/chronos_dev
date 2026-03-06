"""Maps to: ENG-002, ENG-004, NFR-007, SEC-009"""

from types import SimpleNamespace

import pytest

from app.db.phase2_store import UserProfileRepository, phase2_backend_name


def test_phase2_backend_defaults_to_memory_in_test_mode(monkeypatch) -> None:
    import app.db.phase2_store as phase2_store

    monkeypatch.setattr(
        phase2_store,
        "settings",
        SimpleNamespace(
            supabase_db_url="",
            supabase_db_host="db.example.supabase.co",
            supabase_db_port=5432,
            supabase_db_name="postgres",
            supabase_db_user="postgres",
            supabase_db_password="password",
            environment="test",
        ),
    )
    monkeypatch.delenv("CHRONOS_RUN_SUPABASE_INTEGRATION", raising=False)

    assert phase2_backend_name() == "memory"


def test_phase2_backend_can_enable_supabase_integration(monkeypatch) -> None:
    import app.db.phase2_store as phase2_store

    monkeypatch.setattr(
        phase2_store,
        "settings",
        SimpleNamespace(
            supabase_db_url="",
            supabase_db_host="db.example.supabase.co",
            supabase_db_port=5432,
            supabase_db_name="postgres",
            supabase_db_user="postgres",
            supabase_db_password="password",
            environment="test",
        ),
    )
    monkeypatch.setenv("CHRONOS_RUN_SUPABASE_INTEGRATION", "1")

    assert phase2_backend_name() == "supabase"


def test_phase2_backend_requires_direct_db_configuration_in_production(monkeypatch) -> None:
    import app.db.phase2_store as phase2_store

    monkeypatch.setattr(
        phase2_store,
        "settings",
        SimpleNamespace(
            supabase_db_url="",
            supabase_db_host="",
            supabase_db_port=5432,
            supabase_db_name="postgres",
            supabase_db_user="postgres",
            supabase_db_password="",
            environment="production",
        ),
    )
    monkeypatch.delenv("CHRONOS_RUN_SUPABASE_INTEGRATION", raising=False)

    with pytest.raises(
        RuntimeError,
        match="Production environment requires direct Supabase database configuration.",
    ):
        phase2_backend_name()


def test_memory_backed_user_profile_repository_round_trips() -> None:
    repo = UserProfileRepository()
    profile = repo.get_or_create(user_id="user-phase2", role="member", plan_tier="pro", org_id="org-7")
    updated = repo.update("user-phase2", {"display_name": "Archivist", "preferences": {"theme": "sepia"}})

    assert profile["user_id"] == "user-phase2"
    assert updated["display_name"] == "Archivist"
    assert updated["preferences"] == {"theme": "sepia"}


def test_supabase_usage_update_omits_null_request_fields(monkeypatch) -> None:
    import app.db.phase2_store as phase2_store

    captured: dict[str, object] = {}

    class StubClient:
        def user_scoped_headers(self, access_token: str) -> dict[str, str]:
            return {"Authorization": f"Bearer {access_token}"}

        def rest_update(self, table_name: str, *, payload: dict[str, object], params: dict[str, str], headers: dict[str, str]):
            captured["table_name"] = table_name
            captured["payload"] = payload
            captured["params"] = params
            captured["headers"] = headers
            return [
                {
                    "external_user_id": "user-phase2",
                    "plan_tier": "pro",
                    "used_minutes": 0,
                    "monthly_limit_minutes": 120,
                    "estimated_next_job_minutes": 3,
                    "approved_overage_minutes": 0,
                    "approval_scope": None,
                    "threshold_alerts": [80],
                }
            ]

    repo = phase2_store._SupabaseUsageRepository()
    monkeypatch.setattr(repo, "_client", StubClient())

    updated = repo.update(
        "user-phase2",
        {"estimated_next_job_minutes": 3, "threshold_alerts": [80]},
        access_token="jwt-token",
    )

    assert captured["table_name"] == "user_usage_monthly"
    assert captured["headers"] == {"Authorization": "Bearer jwt-token"}
    assert captured["payload"] == {
        "estimated_next_job_minutes": 3,
        "threshold_alerts": [80],
        "updated_at": captured["payload"]["updated_at"],
    }
    assert updated["estimated_next_job_minutes"] == 3
    assert updated["threshold_alerts"] == [80]


def test_supabase_profile_update_omits_null_request_fields(monkeypatch) -> None:
    import app.db.phase2_store as phase2_store

    captured: dict[str, object] = {}

    class StubClient:
        def user_scoped_headers(self, access_token: str) -> dict[str, str]:
            return {"Authorization": f"Bearer {access_token}"}

        def rest_update(self, table_name: str, *, payload: dict[str, object], params: dict[str, str], headers: dict[str, str]):
            captured["table_name"] = table_name
            captured["payload"] = payload
            captured["params"] = params
            captured["headers"] = headers
            return [
                {
                    "external_user_id": "user-phase2",
                    "email": "archivist@example.com",
                    "role": "member",
                    "plan_tier": "pro",
                    "org_id": "org-default",
                    "display_name": "Archivist",
                    "avatar_url": None,
                    "preferences": {"theme": "sepia"},
                }
            ]

    repo = phase2_store._SupabaseUserProfileRepository()
    monkeypatch.setattr(repo, "_client", StubClient())

    updated = repo.update(
        "user-phase2",
        {"display_name": "Archivist", "preferences": {"theme": "sepia"}},
        access_token="jwt-token",
    )

    assert captured["table_name"] == "user_profiles"
    assert captured["headers"] == {"Authorization": "Bearer jwt-token"}
    assert captured["payload"] == {
        "display_name": "Archivist",
        "preferences": {"theme": "sepia"},
        "updated_at": captured["payload"]["updated_at"],
    }
    assert updated["display_name"] == "Archivist"
    assert updated["preferences"] == {"theme": "sepia"}


def test_supabase_profile_get_or_create_uses_atomic_upsert(monkeypatch) -> None:
    import app.db.phase2_store as phase2_store

    captured: dict[str, object] = {}

    class StubClient:
        def user_scoped_headers(self, access_token: str) -> dict[str, str]:
            return {"Authorization": f"Bearer {access_token}"}

        def rest_upsert(
            self,
            table_name: str,
            *,
            payload: dict[str, object],
            on_conflict: str,
            headers: dict[str, str],
        ):
            captured["table_name"] = table_name
            captured["payload"] = payload
            captured["on_conflict"] = on_conflict
            captured["headers"] = headers
            return [
                {
                    "external_user_id": "user-phase2",
                    "email": "archivist@example.com",
                    "role": "member",
                    "plan_tier": "pro",
                    "org_id": "org-7",
                    "display_name": None,
                    "avatar_url": None,
                    "preferences": {},
                }
            ]

    repo = phase2_store._SupabaseUserProfileRepository()
    monkeypatch.setattr(repo, "_client", StubClient())

    profile = repo.get_or_create(
        user_id="user-phase2",
        role="member",
        plan_tier="pro",
        org_id="org-7",
        email="archivist@example.com",
        access_token="jwt-token",
    )

    assert captured["table_name"] == "user_profiles"
    assert captured["on_conflict"] == "id"
    assert captured["headers"] == {"Authorization": "Bearer jwt-token"}
    assert profile["user_id"] == "user-phase2"


def test_supabase_usage_update_can_clear_single_job_approval_scope(monkeypatch) -> None:
    import app.db.phase2_store as phase2_store

    captured: dict[str, object] = {}

    class StubClient:
        def user_scoped_headers(self, access_token: str) -> dict[str, str]:
            return {"Authorization": f"Bearer {access_token}"}

        def rest_update(self, table_name: str, *, payload: dict[str, object], params: dict[str, str], headers: dict[str, str]):
            captured["table_name"] = table_name
            captured["payload"] = payload
            return [
                {
                    "external_user_id": "user-phase2",
                    "plan_tier": "pro",
                    "used_minutes": 121,
                    "monthly_limit_minutes": 120,
                    "estimated_next_job_minutes": 0,
                    "approved_overage_minutes": 5,
                    "approval_scope": None,
                    "threshold_alerts": [100],
                }
            ]

    repo = phase2_store._SupabaseUsageRepository()
    monkeypatch.setattr(repo, "_client", StubClient())

    updated = repo.update(
        "user-phase2",
        {"overage_approval_scope": None, "estimated_next_job_minutes": 0},
        access_token="jwt-token",
    )

    assert captured["table_name"] == "user_usage_monthly"
    assert "approval_scope" in captured["payload"]
    assert captured["payload"]["approval_scope"] is None
    assert updated["overage_approval_scope"] is None


def test_supabase_compliance_rolls_back_request_when_proof_insert_fails(monkeypatch) -> None:
    import app.db.phase2_store as phase2_store

    calls: list[tuple[str, dict[str, object]]] = []

    class StubClient:
        def user_scoped_headers(self, access_token: str) -> dict[str, str]:
            return {"Authorization": f"Bearer {access_token}"}

        def rest_insert(self, table_name: str, *, payload: dict[str, object], headers: dict[str, str]):
            calls.append((table_name, payload))
            if table_name == "log_deletion_proofs":
                raise RuntimeError("proof insert failed")
            return [payload]

        def rest_delete(self, table_name: str, *, params: dict[str, str], headers: dict[str, str]) -> None:
            calls.append((table_name, params))

    repo = phase2_store._SupabaseComplianceRepository()
    monkeypatch.setattr(repo, "_client", StubClient())

    with pytest.raises(RuntimeError, match="proof insert failed"):
        repo.create_deletion_request(
            user_id="user-phase2",
            payload={
                "categories": ["application_logs"],
                "date_from": "2026-03-01",
                "date_to": "2026-03-06",
                "reason": "GDPR request",
            },
            access_token="jwt-token",
        )

    assert calls[0][0] == "log_deletion_requests"
    assert calls[1][0] == "log_deletion_proofs"
    assert calls[2][0] == "log_deletion_requests"
    assert calls[2][1]["id"].startswith("eq.")


def test_supabase_detection_insert_returns_manual_confirmation_flag(monkeypatch) -> None:
    import app.db.phase2_store as phase2_store

    class StubClient:
        def user_scoped_headers(self, access_token: str) -> dict[str, str]:
            return {"Authorization": f"Bearer {access_token}"}

        def rest_insert(self, table_name: str, *, payload: dict[str, object], headers: dict[str, str]):
            assert payload["manual_confirmation_required"] is True
            return [
                {
                    "id": "detection-1",
                    "external_job_id": "job-123",
                    "era_label": "Unknown Era",
                    "confidence": 0.88,
                    "forensic_markers": {"grain_structure": "dense color grain"},
                    "top_candidates": [{"era": "1960s Kodachrome Film", "confidence": 0.88}],
                    "manual_confirmation_required": True,
                    "overridden_by_user": False,
                    "override_reason": None,
                    "model_version": "deterministic-fallback-v1",
                    "prompt_version": "phase2-era-detection-fallback-v1",
                    "source": "system",
                    "raw_response_gcs_uri": None,
                    "prompt_token_count": 0,
                    "candidates_token_count": 0,
                    "total_token_count": 0,
                    "api_call_count": 0,
                    "external_created_by": None,
                    "created_at": "2026-03-06T00:00:00+00:00",
                }
            ]

    repo = phase2_store._SupabaseEraDetectionRepository()
    monkeypatch.setattr(repo, "_client", StubClient())

    saved = repo.save_detection(
        job_id="job-123",
        detection={
            "era": "Unknown Era",
            "confidence": 0.88,
            "forensic_markers": {"grain_structure": "dense color grain"},
            "top_candidates": [{"era": "1960s Kodachrome Film", "confidence": 0.88}],
            "manual_confirmation_required": True,
            "overridden_by_user": False,
            "override_reason": None,
            "model_version": "deterministic-fallback-v1",
            "prompt_version": "phase2-era-detection-fallback-v1",
            "source": "system",
            "created_by": None,
        },
        access_token="jwt-token",
    )

    assert saved["manual_confirmation_required"] is True
