"""
Maps to:
- FR-001
- AC-FR-001-01
- AC-FR-001-03
- AC-FR-001-04
- AC-FR-001-05
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.db.phase2_store import _STORE
from app.main import app
from app.models.status import UploadStatus
from app.services.upload_service import ResumableUploadProbe, UploadService
from app.services.vertex_gemini import GoogleAccessTokenProvider
from scripts.ops.run_packet4a_live_smoke import (
    LiveSmokeExecutionError,
    LiveSmokePrerequisiteError,
    resolve_primary_actor_headers,
    resolve_secondary_actor_headers,
    run_packet4a_live_smoke,
)
from tests.helpers.auth import fake_auth_header

client = TestClient(app)


@pytest.fixture
def override_upload_service() -> object:
    from app.api import uploads

    def apply(session_client: object) -> UploadService:
        service = UploadService(session_client=session_client)
        app.dependency_overrides[uploads.get_upload_service] = lambda: service
        return service

    yield apply

    app.dependency_overrides.pop(uploads.get_upload_service, None)


def valid_upload_request(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "original_filename": "archive.mov",
        "mime_type": "video/quicktime",
        "size_bytes": 4 * 1024 * 1024,
        "checksum_sha256": "ff00112233445566",
    }
    payload.update(overrides)
    return payload


class ReplayableSessionClient:
    def __init__(
        self,
        *,
        session_urls: list[str] | None = None,
        object_size: int | None = None,
        probes: list[ResumableUploadProbe] | None = None,
    ) -> None:
        self._session_urls = list(session_urls or ["https://example.invalid/resumable"])
        self.object_size = object_size
        self._probes = list(probes or [ResumableUploadProbe(next_byte_offset=0, upload_complete=False)])

    def create_resumable_session(self, *, bucket_name: str, object_path: str, mime_type: str, size_bytes: int) -> str:
        del bucket_name, object_path, mime_type, size_bytes
        if len(self._session_urls) == 1:
            return self._session_urls[0]
        return self._session_urls.pop(0)

    def probe_resumable_session(self, *, session_url: str, size_bytes: int) -> ResumableUploadProbe:
        del session_url, size_bytes
        if len(self._probes) == 1:
            return self._probes[0]
        return self._probes.pop(0)

    def fetch_object_metadata(self, *, bucket_name: str, object_path: str) -> dict[str, object] | None:
        del bucket_name, object_path
        if self.object_size is None:
            return None
        return {"size_bytes": self.object_size, "mime_type": "video/quicktime"}


@pytest.mark.parametrize(
    ("percent_complete", "next_byte_offset"),
    [
        (0, 0),
        (10, 419_430),
        (25, 1_048_576),
        (50, 2_097_152),
        (75, 3_145_728),
        (99, 4_152_360),
    ],
)
def test_resume_endpoint_reports_confirmed_offsets(
    override_upload_service,
    percent_complete: int,
    next_byte_offset: int,
) -> None:
    override_upload_service(ReplayableSessionClient(probes=[ResumableUploadProbe(next_byte_offset=next_byte_offset, upload_complete=False)]))

    created = client.post("/v1/upload", headers=fake_auth_header("resume-user"), json=valid_upload_request()).json()
    resumed = client.post(
        f"/v1/upload/{created['upload_id']}/resume",
        headers=fake_auth_header("resume-user"),
    )

    assert resumed.status_code == 200
    payload = resumed.json()
    expected_offset = int(4 * 1024 * 1024 * percent_complete / 100)
    assert next_byte_offset == expected_offset
    assert payload["next_byte_offset"] == next_byte_offset
    assert payload["status"] == UploadStatus.UPLOADING.value
    assert _STORE.upload_sessions[created["upload_id"]]["status"] == UploadStatus.UPLOADING.value


def test_expired_upload_session_can_be_regenerated_without_changing_upload_identity(override_upload_service) -> None:
    override_upload_service(
        ReplayableSessionClient(
            session_urls=[
                "https://example.invalid/resumable/first",
                "https://example.invalid/resumable/regenerated",
            ],
            probes=[ResumableUploadProbe(next_byte_offset=0, upload_complete=False, session_expired=True)],
        )
    )

    created = client.post("/v1/upload", headers=fake_auth_header("regen-user"), json=valid_upload_request()).json()
    resumed = client.post(
        f"/v1/upload/{created['upload_id']}/resume",
        headers=fake_auth_header("regen-user"),
    )

    assert resumed.status_code == 200
    payload = resumed.json()
    assert payload["upload_id"] == created["upload_id"]
    assert payload["object_path"] == created["object_path"]
    assert payload["resumable_session_url"] != created["resumable_session_url"]
    assert payload["session_regenerated"] is True
    assert _STORE.upload_sessions[created["upload_id"]]["resumable_session_url"] == payload["resumable_session_url"]


def test_resume_then_finalize_persists_pointer_metadata(override_upload_service) -> None:
    override_upload_service(
        ReplayableSessionClient(
            probes=[
                ResumableUploadProbe(next_byte_offset=2 * 1024 * 1024, upload_complete=False),
                ResumableUploadProbe(next_byte_offset=4 * 1024 * 1024, upload_complete=True),
            ],
            object_size=4 * 1024 * 1024,
        )
    )
    created = client.post("/v1/upload", headers=fake_auth_header("pointer-user"), json=valid_upload_request()).json()
    resume_response = client.post(
        f"/v1/upload/{created['upload_id']}/resume",
        headers=fake_auth_header("pointer-user"),
    )
    assert resume_response.status_code == 200

    finalized = client.patch(
        f"/v1/upload/{created['upload_id']}",
        headers=fake_auth_header("pointer-user"),
        json={"size_bytes": 4 * 1024 * 1024, "checksum_sha256": "ff00112233445566"},
    )

    assert finalized.status_code == 200
    pointer = _STORE.gcs_object_pointers[created["upload_id"]]
    assert pointer["checksum_sha256"] == "ff00112233445566"
    assert pointer["object_path"] == created["object_path"]


def _skip_if_gcs_prerequisites_missing() -> None:
    if not settings.gcs_bucket_name:
        pytest.skip("GCS_BUCKET_NAME is required for live resumable upload validation.")
    if GoogleAccessTokenProvider().access_token() is None:
        pytest.skip("A Google access token is required for live resumable upload validation.")


def _live_evidence_path(name: str) -> Path:
    return Path(".tmp/packet4a") / name


@pytest.mark.skipif(
    os.getenv("CHRONOS_RUN_GCS_UPLOAD_INTEGRATION") != "1",
    reason="Set CHRONOS_RUN_GCS_UPLOAD_INTEGRATION=1 to exercise real GCS upload sessions.",
)
def test_real_gcs_upload_session_supports_probe_resume_and_finalize() -> None:
    _skip_if_gcs_prerequisites_missing()
    evidence_path = _live_evidence_path("memory-live-smoke.json")

    result = run_packet4a_live_smoke(
        client=client,
        primary_headers=resolve_primary_actor_headers(require_real_auth=False),
        secondary_headers=resolve_secondary_actor_headers(require_real_auth=False),
        output_path=evidence_path,
    )

    assert result["backend"] == "memory"
    assert result["same_upload_id"] is True
    assert result["same_object_path"] is True
    assert result["resume_offset"] == 256 * 1024
    assert result["resume_upload_complete"] is False
    assert result["after_create_status"] == UploadStatus.PENDING.value
    assert result["after_resume_status"] == UploadStatus.UPLOADING.value
    assert result["after_finalize_status"] == UploadStatus.COMPLETED.value
    assert result["pointer_persisted"] is True
    assert result["resume_session_url_persisted"] is True
    assert result["secondary_resume_status"] == 404
    assert result["secondary_finalize_status"] == 404
    assert result["session_snapshots"]["after_resume"]["status"] == UploadStatus.UPLOADING.value
    assert result["pointer_snapshots"]["after_finalize"]["object_path"] == result["object_path"]
    assert evidence_path.exists()


@pytest.mark.skipif(
    os.getenv("CHRONOS_RUN_GCS_UPLOAD_INTEGRATION") != "1" or os.getenv("CHRONOS_RUN_SUPABASE_INTEGRATION") != "1",
    reason="Set CHRONOS_RUN_GCS_UPLOAD_INTEGRATION=1 and CHRONOS_RUN_SUPABASE_INTEGRATION=1 to validate live Supabase-backed uploads.",
)
def test_supabase_real_gcs_upload_session_persists_rls_artifacts() -> None:
    _skip_if_gcs_prerequisites_missing()
    evidence_path = _live_evidence_path("supabase-live-smoke.json")

    try:
        primary_headers = resolve_primary_actor_headers(require_real_auth=True)
    except LiveSmokePrerequisiteError as exc:
        pytest.skip(str(exc))

    try:
        secondary_headers = resolve_secondary_actor_headers(require_real_auth=True)
    except LiveSmokePrerequisiteError as exc:
        message = str(exc)
        assert "CHRONOS_TEST_SECONDARY_ACCESS_TOKEN" in message
        assert "CHRONOS_TEST_SECONDARY_EMAIL" in message
        pytest.skip(message)

    try:
        result = run_packet4a_live_smoke(
            client=client,
            primary_headers=primary_headers,
            secondary_headers=secondary_headers,
            output_path=evidence_path,
        )
    except LiveSmokePrerequisiteError as exc:
        pytest.skip(str(exc))

    assert result["backend"] == "supabase"
    assert result["same_upload_id"] is True
    assert result["same_object_path"] is True
    assert result["resume_offset"] == 256 * 1024
    assert result["after_create_status"] == UploadStatus.PENDING.value
    assert result["after_resume_status"] == UploadStatus.UPLOADING.value
    assert result["after_finalize_status"] == UploadStatus.COMPLETED.value
    assert result["pointer_persisted"] is True
    assert result["resume_session_url_persisted"] is True
    assert result["pointer_owner_matches_creator"] is True
    assert result["secondary_resume_status"] == 404
    assert result["secondary_finalize_status"] == 404
    assert result["session_snapshots"]["after_create"]["status"] == UploadStatus.PENDING.value
    assert result["session_snapshots"]["after_resume"]["status"] == UploadStatus.UPLOADING.value
    assert result["session_snapshots"]["after_finalize"]["status"] == UploadStatus.COMPLETED.value
    assert result["pointer_snapshots"]["after_finalize"]["external_upload_id"] == result["upload_id"]
    assert result["pointer_snapshots"]["after_finalize"]["object_path"] == result["object_path"]
    assert evidence_path.exists()


def test_live_smoke_enables_test_auth_override_for_fake_headers(monkeypatch) -> None:
    from scripts.ops import run_packet4a_live_smoke as live_smoke

    base_settings = replace(live_smoke.api_dependencies.settings, test_auth_override=False)
    monkeypatch.setattr(live_smoke.app_config, "settings", base_settings)
    monkeypatch.setattr(live_smoke.api_dependencies, "settings", base_settings)
    monkeypatch.delenv("TEST_AUTH_OVERRIDE", raising=False)

    live_smoke._enable_test_auth_override()

    assert os.getenv("TEST_AUTH_OVERRIDE") == "1"
    assert live_smoke.api_dependencies.settings.test_auth_override is True


def test_resolve_real_auth_headers_rejects_ineffective_override_envs(monkeypatch) -> None:
    from scripts.ops import run_packet4a_live_smoke as live_smoke

    base_settings = replace(live_smoke.api_dependencies.settings, test_auth_override=False)
    monkeypatch.setattr(live_smoke.app_config, "settings", base_settings)
    monkeypatch.setattr(live_smoke.api_dependencies, "settings", base_settings)
    monkeypatch.setenv("CHRONOS_TEST_ACCESS_TOKEN", "access-token")
    monkeypatch.setenv("CHRONOS_TEST_ROLE", "admin")
    monkeypatch.delenv("TEST_AUTH_OVERRIDE", raising=False)

    with pytest.raises(LiveSmokePrerequisiteError) as excinfo:
        live_smoke._resolve_real_auth_headers("CHRONOS_TEST")

    assert "CHRONOS_TEST_ROLE" in str(excinfo.value)
    assert "TEST_AUTH_OVERRIDE=1" in str(excinfo.value)


def test_ephemeral_secondary_user_is_cleaned_up_when_sign_in_fails(monkeypatch) -> None:
    from scripts.ops import run_packet4a_live_smoke as live_smoke

    deleted_user_ids: list[str] = []

    class FakeAdmin:
        def create_user(self, payload: dict[str, object]) -> SimpleNamespace:
            del payload
            return SimpleNamespace(user=SimpleNamespace(id="secondary-user"))

        def delete_user(self, user_id: str) -> None:
            deleted_user_ids.append(user_id)

    class FakeSupabaseClient:
        def service_role_sdk_client(self) -> SimpleNamespace:
            return SimpleNamespace(auth=SimpleNamespace(admin=FakeAdmin()))

    class FakeAuthService:
        def sign_in_with_password(self, *, email: str, password: str) -> None:
            del email, password
            raise RuntimeError("sign-in failed")

    monkeypatch.setattr(live_smoke, "SupabaseClient", FakeSupabaseClient)
    monkeypatch.setattr(live_smoke, "SupabaseAuthService", FakeAuthService)

    with pytest.raises(LiveSmokePrerequisiteError):
        live_smoke._provision_ephemeral_secondary_headers()

    assert deleted_user_ids == ["secondary-user"]


def test_live_smoke_percentile_uses_ceil_for_high_percentiles() -> None:
    from scripts.ops import run_packet4a_live_smoke as live_smoke

    samples = [float(index) for index in range(20)]

    assert live_smoke._percentile(samples, 0.50) == 9.0
    assert live_smoke._percentile(samples, 0.95) == 18.0
    assert live_smoke._percentile(samples, 0.99) == 19.0


def test_live_smoke_fails_when_secondary_actor_is_not_denied(monkeypatch) -> None:
    from scripts.ops import run_packet4a_live_smoke as live_smoke

    class FakeResponse:
        def __init__(self, status_code: int, payload: dict[str, object]) -> None:
            self.status_code = status_code
            self._payload = payload
            self.text = str(payload)

        def json(self) -> dict[str, object]:
            return self._payload

    class FakeClient:
        def get(self, path: str, headers: dict[str, str]) -> FakeResponse:
            del headers
            assert path == "/v1/users/me"
            return FakeResponse(200, {"user_id": "owner-user", "org_id": "org-default"})

        def post(self, path: str, headers: dict[str, str], json: dict[str, object] | None = None) -> FakeResponse:
            del json
            if path == "/v1/upload":
                return FakeResponse(
                    200,
                    {
                        "upload_id": "upload-1",
                        "object_path": "uploads/owner-user/upload-1/archive.mov",
                        "resumable_session_url": "https://example.invalid/resumable/upload-1",
                    },
                )
            assert path == "/v1/upload/upload-1/resume"
            if headers["Authorization"] == "Bearer secondary-token":
                return FakeResponse(200, {"detail": "unexpected access"})
            return FakeResponse(200, {"detail": "unused"})

        def patch(self, path: str, headers: dict[str, str], json: dict[str, object]) -> FakeResponse:
            del json
            assert path == "/v1/upload/upload-1"
            if headers["Authorization"] == "Bearer secondary-token":
                return FakeResponse(404, {"detail": "not found"})
            return FakeResponse(200, {"detail": "unused"})

    monkeypatch.setattr(live_smoke, "phase2_backend_name", lambda: "memory")
    monkeypatch.setattr(
        live_smoke,
        "snapshot_upload_artifacts",
        lambda upload_id: {"backend": "memory", "session": {"status": "pending"}, "pointer": None},
    )

    with pytest.raises(LiveSmokeExecutionError) as excinfo:
        live_smoke.run_packet4a_live_smoke(
            client=FakeClient(),
            primary_headers={"Authorization": "Bearer primary-token"},
            secondary_headers={"Authorization": "Bearer secondary-token"},
            output_path=None,
        )

    assert "secondary resume should return 404" in str(excinfo.value)


@pytest.mark.parametrize(
    ("total_requests", "concurrency", "expected_message"),
    [
        (0, 5, "total_requests must be greater than 0."),
        (1, 0, "concurrency must be greater than 0."),
    ],
)
def test_measure_packet4a_staging_latency_rejects_non_positive_settings(
    total_requests: int,
    concurrency: int,
    expected_message: str,
) -> None:
    from scripts.ops import run_packet4a_live_smoke as live_smoke

    with pytest.raises(LiveSmokePrerequisiteError) as excinfo:
        asyncio.run(
            live_smoke.measure_packet4a_staging_latency(
                base_url="https://example.invalid",
                headers={"Authorization": "Bearer access-token"},
                total_requests=total_requests,
                concurrency=concurrency,
            )
        )

    assert str(excinfo.value) == expected_message
