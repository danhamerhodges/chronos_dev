"""Maps to: ENG-002, ENG-004, ENG-010, ENG-011, NFR-007, SEC-009"""

from types import SimpleNamespace

import pytest

from app.db.phase2_store import (
    JobRepository,
    ManifestRepository,
    UserProfileRepository,
    WebhookSubscriptionRepository,
    _SupabaseJobRepository,
    phase2_backend_name,
)


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


def test_memory_backed_job_repository_round_trips() -> None:
    repo = JobRepository()
    created = repo.create_job(
        job_id="job-memory-1",
        owner_user_id="user-phase3",
        plan_tier="pro",
        org_id="org-7",
        media_uri="gs://chronos-dev/input.mov",
        original_filename="input.mov",
        mime_type="video/mp4",
        source_asset_checksum="abc12345def67890",
        fidelity_tier="Restore",
        processing_mode="balanced",
        era_profile={"capture_medium": "film_scan"},
        config={"stabilization": "medium"},
        estimated_duration_seconds=25,
        segments=[
            {
                "segment_index": 0,
                "segment_start_seconds": 0,
                "segment_end_seconds": 10,
                "segment_duration_seconds": 10,
                "idempotency_key": "seg-0",
            }
        ],
    )

    fetched = repo.get_job("job-memory-1", owner_user_id="user-phase3")
    segments = repo.list_segments("job-memory-1", owner_user_id="user-phase3")

    assert created["status"] == "queued"
    assert created["reproducibility_mode"] == "perceptual_equivalence"
    assert fetched is not None
    assert fetched["progress_topic"] == "job_progress:job-memory-1"
    assert fetched["quality_summary"]["thresholds_met"] is False
    assert fetched["cache_summary"]["hits"] == 0
    assert fetched["gpu_summary"]["gpu_runtime_seconds"] == 0
    assert fetched["slo_summary"]["target_total_ms"] == 50000
    assert segments[0]["idempotency_key"] == "seg-0"
    assert segments[0]["cache_status"] == "miss"


def test_memory_backed_manifest_repository_round_trips() -> None:
    job_repo = JobRepository()
    manifest_repo = ManifestRepository()
    job_repo.create_job(
        job_id="job-memory-manifest",
        owner_user_id="user-phase3",
        plan_tier="pro",
        org_id="org-7",
        media_uri="gs://chronos-dev/input.mov",
        original_filename="input.mov",
        mime_type="video/mp4",
        source_asset_checksum="abc12345def67890",
        fidelity_tier="Restore",
        processing_mode="balanced",
        era_profile={"capture_medium": "film_scan"},
        config={"stabilization": "medium"},
        estimated_duration_seconds=25,
        segments=[],
    )

    manifest_repo.upsert_manifest_for_worker(
        job_id="job-memory-manifest",
        manifest={
            "manifest_id": "job-memory-manifest",
            "job_id": "job-memory-manifest",
            "generated_at": "2026-03-07T00:00:00+00:00",
            "user_id": "user-phase3",
            "era_profile": {},
            "fidelity_tier": "Restore",
            "effective_fidelity_profile": {},
            "reproducibility_mode": "perceptual_equivalence",
            "job_status": "completed",
            "quality_summary": {"e_hf": 0.9, "s_ls_db": 0.1, "t_tc": 0.95, "thresholds_met": True},
            "reproducibility_summary": {
                "mode": "perceptual_equivalence",
                "verification_status": "pass",
                "failed_segment_count": 0,
                "rerun_count": 0,
                "rollup": "pass",
                "metric_epsilon_percent": 0.5,
                "environment_fingerprint": "abc",
            },
            "stage_timings": {"upload_ms": None, "era_detection_ms": None, "processing_ms": 1200, "encoding_ms": 90, "download_ms": None, "total_ms": 1290},
            "processing_time_ms": 1200,
            "gpu_usage": {},
            "model_versions": {},
            "environment": {},
            "segments": [],
            "uncertainty_callouts": [],
            "warnings": [],
            "result_uri": "gs://chronos/jobs/job-memory-manifest/result.mp4",
            "manifest_uri": "gs://chronos/manifests/job-memory-manifest.json",
            "manifest_sha256": "hash",
            "size_bytes": 512,
        },
    )

    manifest = manifest_repo.get_manifest("job-memory-manifest", owner_user_id="user-phase3")
    assert manifest is not None
    assert manifest["manifest_sha256"] == "hash"


def test_memory_webhook_subscription_repository_filters_enabled_events() -> None:
    repo = WebhookSubscriptionRepository()
    repo.upsert(
        owner_user_id="user-phase3",
        webhook_url="https://hooks.example.test/jobs",
        event_types=["started", "completed"],
        enabled=True,
    )

    subscriptions = repo.list_enabled(owner_user_id="user-phase3", event_type="completed")

    assert len(subscriptions) == 1
    assert subscriptions[0]["webhook_url"] == "https://hooks.example.test/jobs"


def test_supabase_webhook_subscription_repository_uses_direct_db_for_enabled_list(monkeypatch) -> None:
    import app.db.phase2_store as phase2_store

    captured: dict[str, object] = {}

    class StubCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def execute(self, query: str, params: tuple[object, ...]) -> None:
            captured["query"] = query
            captured["params"] = params

        def fetchall(self) -> list[dict[str, object]]:
            return [
                {
                    "id": "subscription-1",
                    "external_user_id": "user-phase3",
                    "webhook_url": "https://hooks.example.test/jobs",
                    "event_types": ["completed"],
                    "enabled": True,
                    "created_at": "2026-03-07T00:00:00Z",
                    "updated_at": "2026-03-07T00:00:00Z",
                }
            ]

    class StubConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def cursor(self) -> StubCursor:
            return StubCursor()

    repo = phase2_store._SupabaseWebhookSubscriptionRepository()
    monkeypatch.setattr(repo, "_connect", lambda: StubConnection())

    subscriptions = repo.list_enabled(owner_user_id="user-phase3", event_type="completed")

    assert "from public.webhook_subscriptions" in captured["query"]
    assert "any(event_types)" in captured["query"]
    assert captured["params"] == ("user-phase3", "completed")
    assert subscriptions[0]["webhook_url"] == "https://hooks.example.test/jobs"


def test_supabase_job_repository_rest_retry_does_not_delete_existing_job_on_segment_failure(monkeypatch) -> None:
    repo = _SupabaseJobRepository()
    calls: list[tuple[str, object]] = []

    class StubClient:
        def user_scoped_headers(self, access_token: str) -> dict[str, str]:
            return {"Authorization": f"Bearer {access_token}"}

        def rest_select(self, table_name: str, *, params: dict[str, str], headers: dict[str, str]) -> list[dict[str, object]]:
            calls.append(("select", table_name, params, headers))
            return [{"id": "existing-job"}]

        def rest_upsert(
            self,
            table_name: str,
            *,
            payload: dict[str, object],
            on_conflict: str,
            headers: dict[str, str],
        ) -> list[dict[str, object]]:
            calls.append(("upsert", table_name, on_conflict, payload))
            if table_name == "media_jobs":
                return [
                    {
                        "external_job_id": "job-existing",
                        "external_user_id": "user-phase3",
                        "org_id": "org-7",
                        "media_uri": "gs://chronos-dev/input.mov",
                        "original_filename": "input.mov",
                        "mime_type": "video/mp4",
                        "status": "queued",
                        "created_at": "2026-03-07T00:00:00+00:00",
                        "updated_at": "2026-03-07T00:00:00+00:00",
                    }
                ]
            if payload["segment_index"] == 1:
                raise RuntimeError("segment write failed")
            return [payload]

        def rest_delete(self, table_name: str, *, params: dict[str, str], headers: dict[str, str]) -> None:
            calls.append(("delete", table_name, params, headers))

    monkeypatch.setattr(repo, "_client", StubClient())

    with pytest.raises(RuntimeError, match="segment write failed"):
        repo.create_job(
            job_id="job-existing",
            owner_user_id="user-phase3",
            plan_tier="pro",
            org_id="org-7",
            media_uri="gs://chronos-dev/input.mov",
            original_filename="input.mov",
            mime_type="video/mp4",
            source_asset_checksum="abc12345def67890",
            fidelity_tier="Restore",
            processing_mode="balanced",
            era_profile={"capture_medium": "film_scan"},
            config={"stabilization": "medium"},
            estimated_duration_seconds=25,
            segments=[
                {
                    "segment_index": 0,
                    "segment_start_seconds": 0,
                    "segment_end_seconds": 10,
                    "segment_duration_seconds": 10,
                    "idempotency_key": "seg-0",
                },
                {
                    "segment_index": 1,
                    "segment_start_seconds": 10,
                    "segment_end_seconds": 20,
                    "segment_duration_seconds": 10,
                    "idempotency_key": "seg-1",
                },
            ],
            access_token="token-1",
        )

    segment_upserts = [entry for entry in calls if entry[0] == "upsert" and entry[1] == "job_segments"]
    assert len(segment_upserts) == 2
    assert all(entry[2] == "job_id,segment_index" for entry in segment_upserts)
    assert not any(entry[0] == "delete" and entry[1] == "media_jobs" for entry in calls)


def test_supabase_job_repository_rest_cancellation_keeps_terminal_job_immutable(monkeypatch) -> None:
    repo = _SupabaseJobRepository()
    updates: list[tuple[str, dict[str, str]]] = []

    class StubClient:
        def user_scoped_headers(self, access_token: str) -> dict[str, str]:
            return {"Authorization": f"Bearer {access_token}"}

        def rest_select(self, table_name: str, *, params: dict[str, str], headers: dict[str, str]) -> list[dict[str, object]]:
            assert table_name == "media_jobs"
            return [
                {
                    "external_job_id": "job-complete",
                    "external_user_id": "user-phase3",
                    "org_id": "org-7",
                    "media_uri": "gs://chronos-dev/input.mov",
                    "original_filename": "input.mov",
                    "mime_type": "video/mp4",
                    "status": "completed",
                    "created_at": "2026-03-07T00:00:00+00:00",
                    "updated_at": "2026-03-07T00:00:00+00:00",
                }
            ]

        def rest_update(
            self,
            table_name: str,
            *,
            payload: dict[str, object],
            params: dict[str, str],
            headers: dict[str, str],
        ) -> list[dict[str, object]]:
            updates.append((table_name, params))
            return []

    monkeypatch.setattr(repo, "_client", StubClient())

    result = repo.request_cancellation(
        "job-complete",
        owner_user_id="user-phase3",
        access_token="token-1",
    )

    assert result is not None
    assert result["status"] == "completed"
    assert updates == []


def test_supabase_job_repository_rejects_unknown_worker_job_patch_field() -> None:
    repo = _SupabaseJobRepository()

    with pytest.raises(ValueError, match="Unsupported worker patch field 'drop_table'"):
        repo.update_job_for_worker("job-1", patch={"drop_table": "jobs"})


def test_supabase_job_repository_rejects_unknown_worker_segment_patch_field() -> None:
    repo = _SupabaseJobRepository()

    with pytest.raises(ValueError, match="Unsupported worker patch field 'drop_table'"):
        repo.update_segment_for_worker("job-1", 0, patch={"drop_table": "segments"})


def test_supabase_job_repository_checks_ownership_before_direct_db_cancellation(monkeypatch) -> None:
    import app.db.phase2_store as phase2_store

    repo = phase2_store._SupabaseJobRepository()
    update_called = {"value": False}

    monkeypatch.setattr(
        repo,
        "get_job",
        lambda job_id, owner_user_id=None, access_token=None: {
            "job_id": job_id,
            "owner_user_id": "owner-a",
            "status": "queued",
        },
    )
    monkeypatch.setattr(
        repo,
        "update_job_for_worker",
        lambda job_id, patch: update_called.__setitem__("value", True),
    )

    cancelled = repo.request_cancellation("job-direct-db", owner_user_id="owner-b")

    assert cancelled is None
    assert update_called["value"] is False


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


def test_supabase_log_settings_upsert_uses_user_scoped_rest_when_access_token_present(monkeypatch) -> None:
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
                    "org_id": "org-1",
                    "retention_days": 365,
                    "redaction_mode": "strict",
                    "categories": ["application_logs", "audit_logs"],
                    "export_targets": ["cloud_logging"],
                    "external_updated_by": "admin-1",
                    "updated_at": "2026-03-06T00:00:00+00:00",
                }
            ]

    repo = phase2_store._SupabaseLogSettingsRepository()
    monkeypatch.setattr(repo, "_client", StubClient())
    monkeypatch.setattr(repo, "_connect", lambda: (_ for _ in ()).throw(AssertionError("direct DB should not be used")))

    saved = repo.upsert(
        org_id="org-1",
        payload={
            "retention_days": 365,
            "redaction_mode": "strict",
            "categories": ["application_logs", "audit_logs"],
            "export_targets": ["cloud_logging"],
        },
        updated_by="admin-1",
        access_token="jwt-token",
    )

    assert captured["table_name"] == "org_log_settings"
    assert captured["on_conflict"] == "org_id"
    assert captured["headers"] == {"Authorization": "Bearer jwt-token"}
    assert saved["updated_by"] == "admin-1"


def test_supabase_log_settings_get_uses_user_scoped_rest_when_access_token_present(monkeypatch) -> None:
    import app.db.phase2_store as phase2_store

    captured: dict[str, object] = {}

    class StubClient:
        def user_scoped_headers(self, access_token: str) -> dict[str, str]:
            return {"Authorization": f"Bearer {access_token}"}

        def rest_select(self, table_name: str, *, params: dict[str, str], headers: dict[str, str]):
            captured["table_name"] = table_name
            captured["params"] = params
            captured["headers"] = headers
            return [
                {
                    "org_id": "org-1",
                    "retention_days": 365,
                    "redaction_mode": "strict",
                    "categories": ["application_logs"],
                    "export_targets": ["splunk"],
                    "external_updated_by": "admin-1",
                    "updated_at": "2026-03-06T00:00:00+00:00",
                }
            ]

    repo = phase2_store._SupabaseLogSettingsRepository()
    monkeypatch.setattr(repo, "_client", StubClient())
    monkeypatch.setattr(repo, "_connect", lambda: (_ for _ in ()).throw(AssertionError("direct DB should not be used")))

    record = repo.get("org-1", access_token="jwt-token")

    assert captured["table_name"] == "org_log_settings"
    assert captured["params"] == {"select": "*", "org_id": "eq.org-1", "limit": "1"}
    assert captured["headers"] == {"Authorization": "Bearer jwt-token"}
    assert record is not None
    assert record["export_targets"] == ["splunk"]


def test_supabase_log_settings_require_access_token_for_user_scoped_paths() -> None:
    import app.db.phase2_store as phase2_store

    repo = phase2_store._SupabaseLogSettingsRepository()

    with pytest.raises(ValueError, match="access token is required"):
        repo.upsert(
            org_id="org-1",
            payload={
                "retention_days": 365,
                "redaction_mode": "strict",
                "categories": ["application_logs"],
                "export_targets": [],
            },
            updated_by="admin-1",
            access_token=None,
        )

    with pytest.raises(ValueError, match="access token is required"):
        repo.get("org-1", access_token=None)
