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

from fastapi.testclient import TestClient

from app.main import app
from app.models.status import UploadStatus
from app.services.upload_service import ResumableUploadProbe
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
        probe: ResumableUploadProbe | None = None,
    ) -> None:
        self._session_urls = list(session_urls or ["https://storage.googleapis.com/upload/resumable/fake/session"])
        self.object_size = object_size
        self.probe = probe or ResumableUploadProbe(next_byte_offset=0, upload_complete=False)

    def create_resumable_session(self, *, bucket_name: str, object_path: str, mime_type: str, size_bytes: int) -> str:
        del bucket_name, object_path, mime_type, size_bytes
        if len(self._session_urls) == 1:
            return self._session_urls[0]
        return self._session_urls.pop(0)

    def probe_resumable_session(self, *, session_url: str, size_bytes: int) -> ResumableUploadProbe:
        del session_url, size_bytes
        return self.probe

    def fetch_object_metadata(self, *, bucket_name: str, object_path: str) -> dict[str, object] | None:
        del bucket_name, object_path
        if self.object_size is None:
            return None
        return {"size_bytes": self.object_size, "mime_type": "video/quicktime"}


def test_upload_route_requires_bearer_token() -> None:
    response = client.post("/v1/upload", json=valid_upload_request())
    assert response.status_code == 401
    assert response.json()["title"] == "Unauthorized"


def test_create_upload_returns_pending_session(monkeypatch) -> None:
    from app.api import uploads

    monkeypatch.setattr(uploads._upload_service, "_session_client", StubSessionClient())

    response = client.post("/v1/upload", headers=fake_auth_header("upload-user"), json=valid_upload_request())

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == UploadStatus.PENDING.value
    assert payload["upload_id"]
    assert payload["resumable_session_url"].startswith("https://storage.googleapis.com/upload/resumable/fake/")
    assert payload["object_path"].endswith("/sample.mov")
    assert payload["media_uri"].startswith("gs://")


def test_create_upload_rejects_unsupported_format(monkeypatch) -> None:
    from app.api import uploads

    monkeypatch.setattr(uploads._upload_service, "_session_client", StubSessionClient())

    response = client.post(
        "/v1/upload",
        headers=fake_auth_header("upload-user"),
        json=valid_upload_request(original_filename="sample.exe", mime_type="application/octet-stream"),
    )

    assert response.status_code == 415
    assert response.json()["title"] == "Unsupported Media Format"


def test_create_upload_rejects_zero_byte_files(monkeypatch) -> None:
    from app.api import uploads

    monkeypatch.setattr(uploads._upload_service, "_session_client", StubSessionClient())

    response = client.post(
        "/v1/upload",
        headers=fake_auth_header("upload-user"),
        json=valid_upload_request(size_bytes=0),
    )

    assert response.status_code == 400
    assert response.json()["title"] == "Invalid Upload Size"


def test_create_upload_accepts_declared_100gb_payload(monkeypatch) -> None:
    from app.api import uploads

    monkeypatch.setattr(uploads._upload_service, "_session_client", StubSessionClient())

    response = client.post(
        "/v1/upload",
        headers=fake_auth_header("upload-user"),
        json=valid_upload_request(size_bytes=100 * 1024 * 1024 * 1024),
    )

    assert response.status_code == 200
    assert response.json()["size_bytes"] == 100 * 1024 * 1024 * 1024


def test_resume_upload_returns_zero_offset_for_fresh_session(monkeypatch) -> None:
    from app.api import uploads

    monkeypatch.setattr(
        uploads._upload_service,
        "_session_client",
        StubSessionClient(probe=ResumableUploadProbe(next_byte_offset=0, upload_complete=False)),
    )
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


def test_resume_upload_regenerates_expired_session_for_same_upload(monkeypatch) -> None:
    from app.api import uploads

    monkeypatch.setattr(
        uploads._upload_service,
        "_session_client",
        StubSessionClient(
            session_urls=[
                "https://storage.googleapis.com/upload/resumable/fake/original",
                "https://storage.googleapis.com/upload/resumable/fake/regenerated",
            ],
            probe=ResumableUploadProbe(next_byte_offset=0, upload_complete=False, session_expired=True),
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
    assert payload["resumable_session_url"].endswith("/regenerated")
    assert payload["session_regenerated"] is True


def test_resume_upload_succeeds_only_for_owner(monkeypatch) -> None:
    from app.api import uploads

    monkeypatch.setattr(
        uploads._upload_service,
        "_session_client",
        StubSessionClient(probe=ResumableUploadProbe(next_byte_offset=256, upload_complete=False)),
    )
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


def test_finalize_upload_succeeds_only_for_owner(monkeypatch) -> None:
    from app.api import uploads

    monkeypatch.setattr(uploads._upload_service, "_session_client", StubSessionClient(object_size=1024 * 1024))
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


def test_finalize_upload_rejects_missing_object_state_without_marking_session_failed(monkeypatch) -> None:
    from app.api import uploads
    from app.db.phase2_store import _STORE

    monkeypatch.setattr(
        uploads._upload_service,
        "_session_client",
        StubSessionClient(session_urls=["https://example.invalid/resumable/session"], object_size=None),
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


def test_upload_rate_limit_is_enforced_per_user(monkeypatch) -> None:
    import app.services.rate_limits as rate_limits
    from app.api import uploads

    monkeypatch.setattr(uploads._upload_service, "_session_client", StubSessionClient())
    monkeypatch.setattr(rate_limits, "_limit_for_tier", lambda plan_tier: 1)

    first = client.post("/v1/upload", headers=fake_auth_header("rate-user"), json=valid_upload_request())
    second = client.post("/v1/upload", headers=fake_auth_header("rate-user"), json=valid_upload_request())

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["title"] == "Rate Limit Exceeded"
