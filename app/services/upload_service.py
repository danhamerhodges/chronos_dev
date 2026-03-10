"""Upload session orchestration for Packet 4A."""

from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

import httpx

from app.api.problem_details import ProblemException
from app.config import settings
from app.db.phase2_store import UploadRepository
from app.models.status import UploadStatus
from app.services.vertex_gemini import GoogleAccessTokenProvider

_GCS_RESUMABLE_UPLOAD_URL = "https://storage.googleapis.com/upload/storage/v1/b/{bucket}/o"
_GCS_OBJECT_METADATA_URL = "https://storage.googleapis.com/storage/v1/b/{bucket}/o/{object_path}"
_MAX_UPLOAD_SIZE_BYTES = 100 * 1024 * 1024 * 1024
_FAKE_SESSION_PREFIX = "https://storage.googleapis.com/upload/resumable/fake"
_TEST_BUCKET_NAME = "chronos-test-bucket"
_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")
_COMMITTED_RANGE = re.compile(r"bytes=0-(\d+)$")

_SUPPORTED_FORMATS: dict[str, set[str]] = {
    ".mp4": {"video/mp4"},
    ".avi": {"video/x-msvideo", "video/avi"},
    ".mov": {"video/quicktime"},
    ".mkv": {"video/x-matroska"},
    ".tif": {"image/tiff"},
    ".tiff": {"image/tiff"},
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
}


@dataclass(frozen=True)
class ResumableUploadProbe:
    next_byte_offset: int
    upload_complete: bool
    session_expired: bool = False


class GcsUploadSessionClient:
    def __init__(self, token_provider: GoogleAccessTokenProvider | None = None) -> None:
        self._token_provider = token_provider or GoogleAccessTokenProvider()

    def create_resumable_session(self, *, bucket_name: str, object_path: str, mime_type: str, size_bytes: int) -> str:
        if not bucket_name:
            if settings.environment != "test":
                raise ProblemException(
                    title="Upload Storage Unavailable",
                    detail="GCS bucket configuration is required for resumable uploads.",
                    status_code=500,
                )
            return f"{_FAKE_SESSION_PREFIX}/{object_path}"
        access_token = self._token_provider.access_token()
        if not access_token:
            if settings.environment != "test":
                raise ProblemException(
                    title="Upload Storage Unavailable",
                    detail="GCP access token is required to create resumable upload sessions.",
                    status_code=500,
                )
            return f"{_FAKE_SESSION_PREFIX}/{object_path}"
        try:
            response = httpx.post(
                _GCS_RESUMABLE_UPLOAD_URL.format(bucket=bucket_name),
                params={"uploadType": "resumable", "name": object_path},
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "X-Upload-Content-Type": mime_type,
                    "X-Upload-Content-Length": str(size_bytes),
                    "Content-Type": "application/json; charset=UTF-8",
                },
                content=b"{}",
                timeout=10.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProblemException(
                title="Upload Storage Unavailable",
                detail="Resumable upload sessions could not be created.",
                status_code=500,
            ) from exc
        location = response.headers.get("Location")
        if location:
            return location
        if settings.environment == "test":
            return f"{_FAKE_SESSION_PREFIX}/{object_path}"
        raise ProblemException(
            title="Upload Storage Unavailable",
            detail="Resumable upload sessions must return a session URL.",
            status_code=500,
        )

    def fetch_object_metadata(self, *, bucket_name: str, object_path: str) -> dict[str, object] | None:
        if not bucket_name:
            if settings.environment != "test":
                raise ProblemException(
                    title="Upload Storage Unavailable",
                    detail="GCS bucket configuration is required to verify uploaded objects.",
                    status_code=500,
                )
            return None
        access_token = self._token_provider.access_token()
        if not access_token:
            if settings.environment != "test":
                raise ProblemException(
                    title="Upload Storage Unavailable",
                    detail="GCP access token is required to verify uploaded objects.",
                    status_code=500,
                )
            return None
        try:
            response = httpx.get(
                _GCS_OBJECT_METADATA_URL.format(bucket=bucket_name, object_path=quote(object_path, safe="")),
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0,
            )
        except httpx.HTTPError as exc:
            raise ProblemException(
                title="Upload Storage Unavailable",
                detail="Uploaded object metadata could not be verified.",
                status_code=500,
            ) from exc
        if response.status_code == 404:
            return None
        try:
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProblemException(
                title="Upload Storage Unavailable",
                detail="Uploaded object metadata could not be verified.",
                status_code=500,
            ) from exc
        payload = response.json()
        return {
            "size_bytes": int(payload.get("size", 0) or 0),
            "mime_type": payload.get("contentType") or "",
        }

    def probe_resumable_session(self, *, session_url: str, size_bytes: int) -> ResumableUploadProbe:
        if not session_url:
            return ResumableUploadProbe(next_byte_offset=0, upload_complete=False, session_expired=True)
        if session_url.startswith(_FAKE_SESSION_PREFIX):
            return ResumableUploadProbe(next_byte_offset=0, upload_complete=False)
        try:
            response = httpx.put(
                session_url,
                headers={
                    "Content-Length": "0",
                    "Content-Range": f"bytes */{size_bytes}",
                },
                content=b"",
                timeout=10.0,
            )
        except httpx.HTTPError as exc:
            raise ProblemException(
                title="Upload Session Probe Failed",
                detail="The current resumable upload session could not be inspected.",
                status_code=500,
            ) from exc
        if response.status_code == 308:
            next_byte_offset = _parse_committed_offset(response.headers.get("Range"), size_bytes=size_bytes)
            return ResumableUploadProbe(
                next_byte_offset=next_byte_offset,
                upload_complete=next_byte_offset >= size_bytes,
            )
        if response.status_code in {200, 201}:
            return ResumableUploadProbe(next_byte_offset=size_bytes, upload_complete=True)
        if response.status_code in {404, 410}:
            return ResumableUploadProbe(next_byte_offset=0, upload_complete=False, session_expired=True)
        raise ProblemException(
            title="Upload Session Probe Failed",
            detail="The resumable upload session returned an unexpected response.",
            status_code=500,
        )


def _normalize_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def _validate_media_type(*, original_filename: str, mime_type: str) -> None:
    extension = _normalize_extension(original_filename)
    if extension not in _SUPPORTED_FORMATS or mime_type not in _SUPPORTED_FORMATS[extension]:
        raise ProblemException(
            title="Unsupported Media Format",
            detail="Supported formats are MP4, AVI, MOV, MKV, TIFF, PNG, and JPEG.",
            status_code=415,
        )


def _sanitize_filename(filename: str) -> str:
    cleaned = _SAFE_FILENAME.sub("_", filename).strip("._")
    return cleaned or "upload.bin"


def _parse_committed_offset(range_header: str | None, *, size_bytes: int) -> int:
    if not range_header:
        return 0
    match = _COMMITTED_RANGE.match(range_header.strip())
    if match is None:
        return 0
    committed_last_byte = int(match.group(1))
    return min(committed_last_byte + 1, size_bytes)


def _resolve_bucket_name() -> str:
    if settings.gcs_bucket_name:
        return settings.gcs_bucket_name
    if settings.environment == "test":
        return _TEST_BUCKET_NAME
    return ""


class UploadService:
    def __init__(
        self,
        *,
        repository: UploadRepository | None = None,
        session_client: GcsUploadSessionClient | None = None,
    ) -> None:
        self._repo = repository or UploadRepository()
        self._session_client = session_client or GcsUploadSessionClient()

    def create_upload(
        self,
        *,
        user_id: str,
        org_id: str,
        payload: dict[str, object],
        access_token: str,
    ) -> dict[str, object]:
        original_filename = str(payload["original_filename"])
        mime_type = str(payload["mime_type"]).lower()
        size_bytes = int(payload["size_bytes"])
        checksum_sha256 = str(payload["checksum_sha256"]).lower() if payload.get("checksum_sha256") else None

        if size_bytes <= 0:
            raise ProblemException(
                title="Invalid Upload Size",
                detail="Upload size must be greater than zero bytes.",
                status_code=400,
            )
        if size_bytes > _MAX_UPLOAD_SIZE_BYTES:
            raise ProblemException(
                title="Upload Too Large",
                detail="Uploads larger than 100GB are not supported in Packet 4A.",
                status_code=413,
            )
        _validate_media_type(original_filename=original_filename, mime_type=mime_type)

        upload_id = str(uuid4())
        object_path = f"uploads/{user_id}/{upload_id}/{_sanitize_filename(original_filename)}"
        bucket_name = _resolve_bucket_name()
        resumable_session_url = self._session_client.create_resumable_session(
            bucket_name=bucket_name,
            object_path=object_path,
            mime_type=mime_type,
            size_bytes=size_bytes,
        )
        created = self._repo.create_session(
            upload_id=upload_id,
            owner_user_id=user_id,
            org_id=org_id,
            original_filename=original_filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
            checksum_sha256=checksum_sha256,
            bucket_name=bucket_name,
            object_path=object_path,
            resumable_session_url=resumable_session_url,
            access_token=access_token,
        )
        return _public_upload_payload(created)

    def resume_upload(
        self,
        upload_id: str,
        *,
        owner_user_id: str,
        access_token: str,
    ) -> dict[str, object]:
        session = self._repo.get_session(upload_id, owner_user_id=owner_user_id, access_token=access_token)
        if session is None:
            raise ProblemException(
                title="Not Found",
                detail="Upload session not found for the current user.",
                status_code=404,
            )
        declared_size = int(session["size_bytes"])
        if session["status"] == UploadStatus.COMPLETED.value:
            return _resume_upload_payload(
                session,
                next_byte_offset=declared_size,
                upload_complete=True,
                session_regenerated=False,
            )

        probe = self._session_client.probe_resumable_session(
            session_url=str(session["resumable_session_url"]),
            size_bytes=declared_size,
        )
        session_regenerated = False
        resumable_session_url = str(session["resumable_session_url"])
        if probe.session_expired:
            resumable_session_url = self._session_client.create_resumable_session(
                bucket_name=str(session["bucket_name"]),
                object_path=str(session["object_path"]),
                mime_type=str(session["mime_type"]),
                size_bytes=declared_size,
            )
            probe = ResumableUploadProbe(next_byte_offset=0, upload_complete=False)
            session_regenerated = True

        patch = {}
        if str(session["status"]) != UploadStatus.UPLOADING.value:
            patch["status"] = UploadStatus.UPLOADING.value
        if resumable_session_url != str(session["resumable_session_url"]):
            patch["resumable_session_url"] = resumable_session_url
        if patch:
            updated = self._repo.update_session(
                upload_id,
                owner_user_id=owner_user_id,
                patch=patch,
                access_token=access_token,
            )
            if updated is None:
                raise ProblemException(
                    title="Upload Session Probe Failed",
                    detail="Upload session could not be updated.",
                    status_code=500,
                )
            session = updated
        return _resume_upload_payload(
            session,
            next_byte_offset=probe.next_byte_offset,
            upload_complete=probe.upload_complete,
            session_regenerated=session_regenerated,
        )

    def finalize_upload(
        self,
        upload_id: str,
        *,
        owner_user_id: str,
        payload: dict[str, object],
        access_token: str,
    ) -> dict[str, object]:
        session = self._repo.get_session(upload_id, owner_user_id=owner_user_id, access_token=access_token)
        if session is None:
            raise ProblemException(
                title="Not Found",
                detail="Upload session not found for the current user.",
                status_code=404,
            )
        if session["status"] == UploadStatus.COMPLETED.value:
            return _public_upload_payload(session)

        finalized_size = int(payload["size_bytes"])
        finalized_checksum = str(payload["checksum_sha256"]).lower() if payload.get("checksum_sha256") else None
        if finalized_size <= 0:
            raise ProblemException(
                title="Invalid Upload Size",
                detail="Upload size must be greater than zero bytes.",
                status_code=400,
            )
        if finalized_size != int(session["size_bytes"]):
            raise ProblemException(
                title="Upload Metadata Mismatch",
                detail="Completed upload size does not match the initiated upload session.",
                status_code=400,
            )
        if session.get("checksum_sha256") and finalized_checksum and finalized_checksum != session["checksum_sha256"]:
            raise ProblemException(
                title="Upload Metadata Mismatch",
                detail="Completed upload checksum does not match the initiated upload session.",
                status_code=400,
            )

        probe = self._session_client.probe_resumable_session(
            session_url=str(session["resumable_session_url"]),
            size_bytes=finalized_size,
        )
        if not probe.upload_complete:
            session = _mark_upload_in_progress(
                self._repo,
                session,
                upload_id=upload_id,
                owner_user_id=owner_user_id,
                access_token=access_token,
            )
            detail = "Uploaded object is not yet available. Retry finalization after the upload completes."
            if probe.session_expired:
                detail = "The resumable upload session expired before completion. Resume the upload and retry finalization."
            raise ProblemException(
                title="Upload Finalization Failed",
                detail=detail,
                status_code=409,
            )

        metadata = self._session_client.fetch_object_metadata(
            bucket_name=str(session["bucket_name"]),
            object_path=str(session["object_path"]),
        )
        if metadata is None:
            if settings.environment == "test" and str(session["resumable_session_url"]).startswith(_FAKE_SESSION_PREFIX):
                metadata = {
                    "size_bytes": finalized_size,
                    "mime_type": session["mime_type"],
                }
            else:
                session = _mark_upload_in_progress(
                    self._repo,
                    session,
                    upload_id=upload_id,
                    owner_user_id=owner_user_id,
                    access_token=access_token,
                )
                raise ProblemException(
                    title="Upload Finalization Failed",
                    detail="Uploaded object is not yet available. Retry finalization after the upload completes.",
                    status_code=409,
                )
        if int(metadata.get("size_bytes", 0) or 0) != finalized_size:
            raise ProblemException(
                title="Upload Metadata Mismatch",
                detail="Stored object size does not match the completed upload metadata.",
                status_code=400,
            )
        metadata_mime_type = str(metadata.get("mime_type") or "").lower()
        try:
            _validate_media_type(
                original_filename=str(session["original_filename"]),
                mime_type=metadata_mime_type,
            )
        except ProblemException as exc:
            raise ProblemException(
                title="Upload Metadata Mismatch",
                detail="Stored object MIME type does not match the initiated upload session.",
                status_code=400,
            ) from exc

        checksum_sha256 = finalized_checksum or session.get("checksum_sha256")
        self._repo.upsert_pointer(
            upload_id=upload_id,
            owner_user_id=owner_user_id,
            org_id=str(session["org_id"]),
            bucket_name=str(session["bucket_name"]),
            object_path=str(session["object_path"]),
            original_filename=str(session["original_filename"]),
            mime_type=str(session["mime_type"]),
            size_bytes=finalized_size,
            checksum_sha256=checksum_sha256,
            access_token=access_token,
        )
        updated = self._repo.update_session(
            upload_id,
            owner_user_id=owner_user_id,
            patch={
                "status": UploadStatus.COMPLETED.value,
                "checksum_sha256": checksum_sha256,
                "size_bytes": finalized_size,
                "completed_at": datetime_now_iso(),
            },
            access_token=access_token,
        )
        if updated is None:
            raise ProblemException(
                title="Upload Finalization Failed",
                detail="Upload session could not be updated.",
                status_code=500,
            )
        return _public_upload_payload(updated)


def datetime_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _mark_upload_in_progress(
    repo: UploadRepository,
    session: dict[str, object],
    *,
    upload_id: str,
    owner_user_id: str,
    access_token: str,
) -> dict[str, object]:
    if session["status"] == UploadStatus.UPLOADING.value and session.get("completed_at") is None:
        return session
    updated = repo.update_session(
        upload_id,
        owner_user_id=owner_user_id,
        patch={"status": UploadStatus.UPLOADING.value, "completed_at": None},
        access_token=access_token,
    )
    return updated or session


def _public_upload_payload(record: dict[str, object]) -> dict[str, object]:
    return {
        "upload_id": record["upload_id"],
        "status": record["status"],
        "original_filename": record["original_filename"],
        "mime_type": record["mime_type"],
        "size_bytes": record["size_bytes"],
        "checksum_sha256": record.get("checksum_sha256"),
        "bucket_name": record["bucket_name"],
        "object_path": record["object_path"],
        "media_uri": record["media_uri"],
        "resumable_session_url": record["resumable_session_url"],
        "created_at": record["created_at"],
        "updated_at": record["updated_at"],
        "completed_at": record.get("completed_at"),
    }


def _resume_upload_payload(
    record: dict[str, object],
    *,
    next_byte_offset: int,
    upload_complete: bool,
    session_regenerated: bool,
) -> dict[str, object]:
    return {
        "upload_id": record["upload_id"],
        "status": record["status"],
        "resumable_session_url": record["resumable_session_url"],
        "next_byte_offset": next_byte_offset,
        "upload_complete": upload_complete,
        "session_regenerated": session_regenerated,
        "object_path": record["object_path"],
        "media_uri": record["media_uri"],
    }
