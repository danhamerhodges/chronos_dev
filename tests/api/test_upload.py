"""
Maps to:
- FR-001
- AC-FR-001-01
- AC-FR-001-02
- AC-FR-001-03
- AC-FR-001-04
- AC-FR-001-05
"""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.problem_details import ProblemException
from app.main import app
from app.models.status import UploadStatus
from app.services.upload_service import GcsUploadSessionClient, ResumableUploadProbe, UploadService
from tests.helpers.auth import fake_auth_header

client = TestClient(app)


def valid_upload_request(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "original_filename": "sample.mov",
        "mime_type": "video/quicktime",
        "size_bytes": 1024 * 1024,
        "checksum_sha256": "abc12345def67890",
    }
    payload.update(overrides)
    return payload


class StubSessionClient:
    def __init__(
        self,
        *,
        session_urls: list[str] | None = None,
        object_size: int | None = None,
        probes: list[ResumableUploadProbe] | None = None,
    ) -> None:
        self._session_urls = list(session_urls or ["https://storage.googleapis.com/upload/resumable/fake/session"])
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


class CaptureBucketSessionClient(StubSessionClient):
    def __init__(self) -> None:
        super().__init__()
        self.bucket_name: str | None = None

    def create_resumable_session(self, *, bucket_name: str, object_path: str, mime_type: str, size_bytes: int) -> str:
        self.bucket_name = bucket_name
        return super().create_resumable_session(
            bucket_name=bucket_name,
            object_path=object_path,
            mime_type=mime_type,
            size_bytes=size_bytes,
        )


@pytest.fixture
def override_upload_service() -> object:
    from app.api import uploads

    def apply(session_client: object) -> UploadService:
        service = UploadService(session_client=session_client)
        app.dependency_overrides[uploads.get_upload_service] = lambda: service
        return service

    yield apply

    app.dependency_overrides.pop(uploads.get_upload_service, None)


def test_upload_route_requires_bearer_token() -> None:
    response = client.post("/v1/upload", json=valid_upload_request())
    assert response.status_code == 401
    assert response.json()["title"] == "Unauthorized"


def test_create_upload_returns_pending_session(override_upload_service) -> None:
    override_upload_service(StubSessionClient())

    response = client.post("/v1/upload", headers=fake_auth_header("upload-user"), json=valid_upload_request())

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == UploadStatus.PENDING.value
    assert payload["upload_id"]
    assert payload["resumable_session_url"].startswith("https://storage.googleapis.com/upload/resumable/fake/")
    assert payload["object_path"].endswith("/sample.mov")
    assert payload["media_uri"].startswith("gs://")


def test_create_upload_rejects_unsupported_format(override_upload_service) -> None:
    override_upload_service(StubSessionClient())

    response = client.post(
        "/v1/upload",
        headers=fake_auth_header("upload-user"),
        json=valid_upload_request(original_filename="sample.exe", mime_type="application/octet-stream"),
    )

    assert response.status_code == 415
    assert response.json()["title"] == "Unsupported Media Format"


def test_create_upload_rejects_zero_byte_files(override_upload_service) -> None:
    override_upload_service(StubSessionClient())

    response = client.post(
        "/v1/upload",
        headers=fake_auth_header("upload-user"),
        json=valid_upload_request(size_bytes=0),
    )

    assert response.status_code == 400
    assert response.json()["title"] == "Invalid Upload Size"


def test_create_upload_accepts_declared_100gb_payload(override_upload_service) -> None:
    override_upload_service(StubSessionClient())

    response = client.post(
        "/v1/upload",
        headers=fake_auth_header("upload-user"),
        json=valid_upload_request(size_bytes=100 * 1024 * 1024 * 1024),
    )

    assert response.status_code == 200
    assert response.json()["size_bytes"] == 100 * 1024 * 1024 * 1024


def test_create_upload_uses_explicit_test_bucket_when_gcs_bucket_is_unset(monkeypatch) -> None:
    from app.services import upload_service

    session_client = CaptureBucketSessionClient()
    monkeypatch.setattr(
        upload_service,
        "settings",
        replace(upload_service.settings, environment="test", gcs_bucket_name=""),
    )

    created = UploadService(session_client=session_client).create_upload(
        user_id="bucket-user",
        org_id="org-default",
        payload=valid_upload_request(),
        access_token="test-access-token",
    )

    assert session_client.bucket_name == "chronos-test-bucket"
    assert created["bucket_name"] == "chronos-test-bucket"
    assert created["media_uri"].startswith("gs://chronos-test-bucket/")


def test_resume_upload_returns_zero_offset_for_fresh_session(override_upload_service) -> None:
    override_upload_service(StubSessionClient(probes=[ResumableUploadProbe(next_byte_offset=0, upload_complete=False)]))
    created = client.post("/v1/upload", headers=fake_auth_header("resume-user"), json=valid_upload_request()).json()

    resumed = client.post(
        f"/v1/upload/{created['upload_id']}/resume",
        headers=fake_auth_header("resume-user"),
    )

    assert resumed.status_code == 200
    payload = resumed.json()
    assert payload["upload_id"] == created["upload_id"]
    assert payload["next_byte_offset"] == 0
    assert payload["status"] == UploadStatus.UPLOADING.value
    assert payload["session_regenerated"] is False
    assert payload["upload_complete"] is False


def test_resume_upload_regenerates_expired_session_for_same_upload(override_upload_service) -> None:
    override_upload_service(
        StubSessionClient(
            session_urls=[
                "https://storage.googleapis.com/upload/resumable/fake/original",
                "https://storage.googleapis.com/upload/resumable/fake/regenerated",
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
    assert payload["resumable_session_url"].endswith("/regenerated")
    assert payload["session_regenerated"] is True


def test_resume_upload_succeeds_only_for_owner(override_upload_service) -> None:
    override_upload_service(StubSessionClient(probes=[ResumableUploadProbe(next_byte_offset=256, upload_complete=False)]))
    created = client.post("/v1/upload", headers=fake_auth_header("owner-user"), json=valid_upload_request()).json()

    unauthorized = client.post(
        f"/v1/upload/{created['upload_id']}/resume",
        headers=fake_auth_header("other-user"),
    )
    authorized = client.post(
        f"/v1/upload/{created['upload_id']}/resume",
        headers=fake_auth_header("owner-user"),
    )

    assert unauthorized.status_code == 404
    assert authorized.status_code == 200
    assert authorized.json()["next_byte_offset"] == 256


def test_finalize_upload_succeeds_only_for_owner(override_upload_service) -> None:
    override_upload_service(
        StubSessionClient(
            object_size=1024 * 1024,
            probes=[ResumableUploadProbe(next_byte_offset=1024 * 1024, upload_complete=True)],
        )
    )
    created = client.post("/v1/upload", headers=fake_auth_header("owner-user"), json=valid_upload_request()).json()

    unauthorized = client.patch(
        f"/v1/upload/{created['upload_id']}",
        headers=fake_auth_header("other-user"),
        json={"size_bytes": 1024 * 1024, "checksum_sha256": "abc12345def67890"},
    )
    authorized = client.patch(
        f"/v1/upload/{created['upload_id']}",
        headers=fake_auth_header("owner-user"),
        json={"size_bytes": 1024 * 1024, "checksum_sha256": "abc12345def67890"},
    )

    assert unauthorized.status_code == 404
    assert authorized.status_code == 200
    assert authorized.json()["status"] == UploadStatus.COMPLETED.value


def test_finalize_upload_rejects_false_positive_completion_when_session_is_incomplete(override_upload_service) -> None:
    from app.db.phase2_store import _STORE

    override_upload_service(
        StubSessionClient(
            session_urls=["https://example.invalid/resumable/session"],
            object_size=1024 * 1024,
            probes=[ResumableUploadProbe(next_byte_offset=512 * 1024, upload_complete=False)],
        )
    )
    created = client.post("/v1/upload", headers=fake_auth_header("owner-user"), json=valid_upload_request()).json()

    response = client.patch(
        f"/v1/upload/{created['upload_id']}",
        headers=fake_auth_header("owner-user"),
        json={"size_bytes": 1024 * 1024, "checksum_sha256": "abc12345def67890"},
    )

    assert response.status_code == 409
    assert response.json()["title"] == "Upload Finalization Failed"
    assert _STORE.upload_sessions[created["upload_id"]]["status"] == UploadStatus.UPLOADING.value


def test_finalize_upload_rejects_missing_object_state_without_marking_session_failed(override_upload_service) -> None:
    from app.db.phase2_store import _STORE

    override_upload_service(
        StubSessionClient(
            session_urls=["https://example.invalid/resumable/session"],
            object_size=None,
            probes=[
                ResumableUploadProbe(next_byte_offset=256, upload_complete=False),
                ResumableUploadProbe(next_byte_offset=1024 * 1024, upload_complete=True),
            ],
        )
    )
    created = client.post("/v1/upload", headers=fake_auth_header("owner-user"), json=valid_upload_request()).json()
    resume_response = client.post(
        f"/v1/upload/{created['upload_id']}/resume",
        headers=fake_auth_header("owner-user"),
    )
    assert resume_response.status_code == 200

    response = client.patch(
        f"/v1/upload/{created['upload_id']}",
        headers=fake_auth_header("owner-user"),
        json={"size_bytes": 1024 * 1024, "checksum_sha256": "abc12345def67890"},
    )

    assert response.status_code == 409
    assert response.json()["title"] == "Upload Finalization Failed"
    assert _STORE.upload_sessions[created["upload_id"]]["status"] == UploadStatus.UPLOADING.value


def test_finalize_upload_rejects_mime_mismatch(override_upload_service) -> None:
    from app.db.phase2_store import _STORE

    class MismatchedMimeSessionClient(StubSessionClient):
        def fetch_object_metadata(self, *, bucket_name: str, object_path: str) -> dict[str, object] | None:
            del bucket_name, object_path
            return {"size_bytes": 1024 * 1024, "mime_type": "image/png"}

    override_upload_service(
        MismatchedMimeSessionClient(
            object_size=1024 * 1024,
            probes=[ResumableUploadProbe(next_byte_offset=1024 * 1024, upload_complete=True)],
        )
    )
    created = client.post("/v1/upload", headers=fake_auth_header("owner-user"), json=valid_upload_request()).json()

    response = client.patch(
        f"/v1/upload/{created['upload_id']}",
        headers=fake_auth_header("owner-user"),
        json={"size_bytes": 1024 * 1024, "checksum_sha256": "abc12345def67890"},
    )

    assert response.status_code == 400
    assert response.json()["title"] == "Upload Metadata Mismatch"
    assert _STORE.upload_sessions[created["upload_id"]]["status"] != UploadStatus.COMPLETED.value


def test_upload_rate_limit_is_enforced_per_user(monkeypatch, override_upload_service) -> None:
    import app.services.rate_limits as rate_limits

    override_upload_service(StubSessionClient())
    monkeypatch.setattr(rate_limits, "_limit_for_tier", lambda plan_tier: 1)

    first = client.post("/v1/upload", headers=fake_auth_header("rate-user"), json=valid_upload_request())
    second = client.post("/v1/upload", headers=fake_auth_header("rate-user"), json=valid_upload_request())

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["title"] == "Rate Limit Exceeded"


def test_create_resumable_session_requires_location_header_outside_test(monkeypatch) -> None:
    from app.services import upload_service

    request = httpx.Request("POST", "https://storage.googleapis.com/upload/storage/v1/b/test-bucket/o")
    response = httpx.Response(200, request=request, headers={})

    monkeypatch.setattr(upload_service, "settings", replace(upload_service.settings, environment="production"))
    monkeypatch.setattr(upload_service.httpx, "post", lambda *args, **kwargs: response)

    session_client = GcsUploadSessionClient(token_provider=SimpleNamespace(access_token=lambda: "test-access-token"))

    with pytest.raises(ProblemException) as excinfo:
        session_client.create_resumable_session(
            bucket_name="test-bucket",
            object_path="uploads/user/upload/archive.mov",
            mime_type="video/quicktime",
            size_bytes=1024,
        )
    assert excinfo.value.detail == "Resumable upload sessions must return a session URL."


def test_fetch_object_metadata_normalizes_transport_errors(monkeypatch) -> None:
    from app.services import upload_service

    monkeypatch.setattr(upload_service, "settings", replace(upload_service.settings, environment="production"))

    def raise_connect_error(*args, **kwargs):
        raise httpx.ConnectError("boom", request=httpx.Request("GET", "https://storage.googleapis.com"))

    monkeypatch.setattr(upload_service.httpx, "get", raise_connect_error)

    session_client = GcsUploadSessionClient(token_provider=SimpleNamespace(access_token=lambda: "test-access-token"))

    with pytest.raises(ProblemException) as excinfo:
        session_client.fetch_object_metadata(
            bucket_name="test-bucket",
            object_path="uploads/user/upload/archive.mov",
        )
    assert excinfo.value.detail == "Uploaded object metadata could not be verified."
