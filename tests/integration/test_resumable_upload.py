"""
Maps to:
- FR-001
- AC-FR-001-01
- AC-FR-001-03
- AC-FR-001-04
- AC-FR-001-05
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.db.phase2_store import _STORE
from app.main import app
from app.models.status import UploadStatus
from app.services.upload_service import ResumableUploadProbe
from app.services.vertex_gemini import GoogleAccessTokenProvider
from scripts.ops.run_packet4a_live_smoke import (
    LiveSmokePrerequisiteError,
    _SECONDARY_PREREQ_MESSAGE,
    resolve_primary_actor_headers,
    resolve_secondary_actor_headers,
    run_packet4a_live_smoke,
)
from tests.helpers.auth import fake_auth_header

client = TestClient(app)


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
        (10, 400_000),
        (25, 1_000_000),
        (50, 2_000_000),
        (75, 3_000_000),
        (99, 3_960_000),
    ],
)
def test_resume_endpoint_reports_confirmed_offsets(monkeypatch, percent_complete: int, next_byte_offset: int) -> None:
    from app.api import uploads

    monkeypatch.setattr(
        uploads._upload_service,
        "_session_client",
        ReplayableSessionClient(probes=[ResumableUploadProbe(next_byte_offset=next_byte_offset, upload_complete=False)]),
    )

    created = client.post("/v1/upload", headers=fake_auth_header("resume-user"), json=valid_upload_request()).json()
    resumed = client.post(
        f"/v1/upload/{created['upload_id']}/resume",
        headers=fake_auth_header("resume-user"),
    )

    assert resumed.status_code == 200
    assert percent_complete in {0, 10, 25, 50, 75, 99}
    payload = resumed.json()
    assert payload["next_byte_offset"] == next_byte_offset
    assert payload["status"] == UploadStatus.UPLOADING.value
    assert _STORE.upload_sessions[created["upload_id"]]["status"] == UploadStatus.UPLOADING.value


def test_expired_upload_session_can_be_regenerated_without_changing_upload_identity(monkeypatch) -> None:
    from app.api import uploads

    monkeypatch.setattr(
        uploads._upload_service,
        "_session_client",
        ReplayableSessionClient(
            session_urls=[
                "https://example.invalid/resumable/first",
                "https://example.invalid/resumable/regenerated",
            ],
            probes=[ResumableUploadProbe(next_byte_offset=0, upload_complete=False, session_expired=True)],
        ),
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


def test_resume_then_finalize_persists_pointer_metadata(monkeypatch) -> None:
    from app.api import uploads

    monkeypatch.setattr(
        uploads._upload_service,
        "_session_client",
        ReplayableSessionClient(
            probes=[ResumableUploadProbe(next_byte_offset=2 * 1024 * 1024, upload_complete=False)],
            object_size=4 * 1024 * 1024,
        ),
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
def test_real_gcs_upload_session_supports_probe_resume_and_finalize(tmp_path: Path) -> None:
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
        if str(exc) == _SECONDARY_PREREQ_MESSAGE:
            pytest.skip(str(exc))
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
