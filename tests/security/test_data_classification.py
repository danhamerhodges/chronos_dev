"""
Maps to:
- SEC-003
"""

from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
from typing import Any

import pytest
import httpx
from fastapi.testclient import TestClient

from app.api.problem_details import ProblemException
from app.db.phase2_store import DataClassificationAuditRepository, UploadRepository, reset_phase2_store
from app.main import app
from app.services.data_classification import (
    ARTIFACT_SOURCE_UPLOAD,
    ARTIFACT_DELETION_PROOF,
    ARTIFACT_EXPORT_PACKAGE,
    ARTIFACT_PROCESSED_OUTPUT,
    ARTIFACT_TRANSFORMATION_MANIFEST,
    CLASSIFICATION_LABELS,
    CLASSIFICATION_POLICY_VERSION,
    DataClassificationService,
    classification_label_for_artifact,
    object_hash,
    retention_days_for_artifact,
)
from app.services.output_delivery import max_retention_days_for_plan
from app.services.transformation_manifest import GcsManifestStore, finalize_manifest_payload
from app.services.upload_service import ResumableUploadProbe, UploadService
from tests.helpers.auth import fake_auth_header
from tests.helpers.jobs import create_seed_job, run_all_jobs

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state() -> None:
    reset_phase2_store()


class UploadClassificationClient:
    def __init__(self, *, fail_patch: bool = False) -> None:
        self.fail_patch = fail_patch
        self.patched_metadata: dict[str, str] | None = None

    def create_resumable_session(self, *, bucket_name: str, object_path: str, mime_type: str, size_bytes: int) -> str:
        del bucket_name, object_path, mime_type, size_bytes
        return "https://storage.googleapis.com/upload/resumable/fake/classification"

    def probe_resumable_session(self, *, session_url: str, size_bytes: int) -> ResumableUploadProbe:
        del session_url
        return ResumableUploadProbe(next_byte_offset=size_bytes, upload_complete=True)

    def fetch_object_metadata(self, *, bucket_name: str, object_path: str) -> dict[str, object]:
        del bucket_name, object_path
        return {"size_bytes": 1024, "mime_type": "video/quicktime"}

    def patch_object_metadata(self, *, bucket_name: str, object_path: str, metadata: dict[str, str]) -> bool:
        del bucket_name, object_path
        self.patched_metadata = dict(metadata)
        if self.fail_patch:
            raise ProblemException(title="Upload Storage Unavailable", detail="patch failed", status_code=500)
        return False


class _PatchResponse:
    def __init__(self, *, should_fail: bool = False) -> None:
        self.should_fail = should_fail

    def raise_for_status(self) -> None:
        if self.should_fail:
            raise httpx.RequestError("patch failed")


def _upload_payload() -> dict[str, object]:
    return {
        "original_filename": "classified.mov",
        "mime_type": "video/quicktime",
        "size_bytes": 1024,
        "checksum_sha256": "abc12345def67890",
    }


def _manifest_job_payload() -> dict[str, object]:
    return {
        "job_id": "manifest-job",
        "owner_user_id": "manifest-owner",
        "era_profile": {"detected_era": "1990s"},
        "plan_tier": "pro",
        "effective_fidelity_tier": "Restore",
        "effective_fidelity_profile": {"tier": "Restore", "identity_lock": False},
        "reproducibility_mode": "deterministic",
        "status": "completed",
        "quality_summary": {},
        "reproducibility_summary": {"mode": "deterministic", "verification_status": "verified"},
        "stage_timings": {},
        "gpu_summary": {},
        "cost_summary": {},
        "cache_summary": {},
        "slo_summary": {"target_total_ms": 120000},
        "warnings": [],
        "result_uri": "gs://chronos-outputs/jobs/manifest-job/result.mp4",
    }


def test_classification_labels_cover_sec003_artifact_types() -> None:
    assert CLASSIFICATION_LABELS == ("Confidential", "Internal", "Compliance", "Public")
    assert classification_label_for_artifact(ARTIFACT_SOURCE_UPLOAD) == "Confidential"
    assert classification_label_for_artifact(ARTIFACT_PROCESSED_OUTPUT) == "Confidential"
    assert classification_label_for_artifact(ARTIFACT_EXPORT_PACKAGE) == "Confidential"
    assert classification_label_for_artifact(ARTIFACT_TRANSFORMATION_MANIFEST) == "Internal"
    assert classification_label_for_artifact(ARTIFACT_DELETION_PROOF) == "Compliance"


def test_unknown_artifact_type_fails_closed() -> None:
    with pytest.raises(ValueError):
        classification_label_for_artifact("thumbnail")


def test_object_hash_is_stable_sha256_of_object_uri() -> None:
    object_uri = "gs://chronos-test-bucket/uploads/user/upload/file.mov"

    assert object_hash(object_uri) == hashlib.sha256(object_uri.encode("utf-8")).hexdigest()


def test_museum_classification_retention_is_independent_of_download_link_expiry() -> None:
    assert max_retention_days_for_plan("museum") == 90
    assert retention_days_for_artifact(artifact_type=ARTIFACT_SOURCE_UPLOAD, plan_tier="museum") is None

    record = DataClassificationService().classify(
        artifact_type=ARTIFACT_SOURCE_UPLOAD,
        object_uri="gs://chronos-test-bucket/uploads/museum/object.mov",
        plan_tier="museum",
        anchor_time="2026-05-11T12:00:00+00:00",
    )

    assert record.policy_version == CLASSIFICATION_POLICY_VERSION
    assert record.retention_days is None
    assert record.retention_expires_at is None
    assert "retention_days" not in record.metadata
    assert "retention_expires_at" not in record.metadata


def test_upload_finalization_applies_metadata_before_marking_complete() -> None:
    session_client = UploadClassificationClient(fail_patch=True)
    service = UploadService(session_client=session_client)
    created = service.create_upload(
        user_id="classification-upload-user",
        org_id="org-default",
        payload=_upload_payload(),
        access_token="test-token-for-classification-upload-user",
    )

    with pytest.raises(ProblemException):
        service.finalize_upload(
            created["upload_id"],
            owner_user_id="classification-upload-user",
            payload={"size_bytes": 1024, "checksum_sha256": "abc12345def67890"},
            plan_tier="pro",
            access_token="test-token-for-classification-upload-user",
        )

    session = UploadRepository().get_session(created["upload_id"], owner_user_id="classification-upload-user")
    assert session is not None
    assert session["status"] != "completed"


def test_upload_finalization_records_classification_metadata_and_audit_events() -> None:
    session_client = UploadClassificationClient()
    service = UploadService(session_client=session_client)
    created = service.create_upload(
        user_id="classified-owner",
        org_id="org-default",
        payload=_upload_payload(),
        access_token="test-token-for-classified-owner",
    )

    completed = service.finalize_upload(
        created["upload_id"],
        owner_user_id="classified-owner",
        payload={"size_bytes": 1024, "checksum_sha256": "abc12345def67890"},
        plan_tier="pro",
        access_token="test-token-for-classified-owner",
    )

    assert completed["status"] == "completed"
    assert session_client.patched_metadata == {
        "classification_label": "Confidential",
        "artifact_type": "source_upload",
        "classification_policy_version": CLASSIFICATION_POLICY_VERSION,
        "retention_days": "90",
        "retention_expires_at": session_client.patched_metadata["retention_expires_at"],
    }
    events = DataClassificationAuditRepository().list_events()
    assert [event["event_type"] for event in events] == ["classification_assigned", "gcs_metadata_patch_skipped"]
    assert events[0]["classification_label"] == "Confidential"


def test_manifest_patch_skips_in_local_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import transformation_manifest

    monkeypatch.setattr(
        transformation_manifest,
        "settings",
        replace(transformation_manifest.settings, environment="test", gcs_bucket_name=""),
    )

    patched = GcsManifestStore().patch_object_metadata(
        object_uri="gs://chronos-test-bucket/manifests/job-1/manifest.json",
        metadata={"classification_label": "Internal"},
    )

    assert patched is False


def test_manifest_local_store_uses_configured_bucket_for_classification_uri(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import transformation_manifest

    monkeypatch.setattr(
        transformation_manifest,
        "settings",
        replace(transformation_manifest.settings, environment="test", gcs_bucket_name="chronos-manifest-test"),
    )

    uri, size_bytes = GcsManifestStore().store(job_id="manifest-job", payload={"manifest_id": "manifest-1"})

    assert uri.startswith("gs://chronos-manifest-test/manifests/manifest-job/")
    assert uri.endswith(".json")
    assert size_bytes > 0


def test_manifest_patch_requires_hosted_bucket(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import transformation_manifest

    monkeypatch.setattr(
        transformation_manifest,
        "settings",
        replace(transformation_manifest.settings, environment="staging", gcs_bucket_name=""),
    )

    with pytest.raises(ProblemException):
        GcsManifestStore().patch_object_metadata(
            object_uri="gs://chronos-staging/manifests/job-1/manifest.json",
            metadata={"classification_label": "Internal"},
        )


def test_manifest_patch_uses_hosted_object_metadata_api(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import transformation_manifest

    captured: dict[str, Any] = {}

    def fake_patch(
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, Any],
        timeout: float,
    ) -> _PatchResponse:
        captured.update({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return _PatchResponse()

    monkeypatch.setattr(
        transformation_manifest,
        "settings",
        replace(transformation_manifest.settings, environment="staging", gcs_bucket_name="chronos-staging"),
    )
    monkeypatch.setattr(transformation_manifest.GoogleAccessTokenProvider, "access_token", lambda self: "token-123")
    monkeypatch.setattr(transformation_manifest.httpx, "patch", fake_patch)

    patched = GcsManifestStore().patch_object_metadata(
        object_uri="gs://chronos-staging/manifests/job-1/manifest.json",
        metadata={"classification_label": "Internal"},
    )

    assert patched is True
    assert captured["url"].endswith("/b/chronos-staging/o/manifests%2Fjob-1%2Fmanifest.json")
    assert captured["headers"]["Authorization"] == "Bearer token-123"
    assert captured["json"] == {"metadata": {"classification_label": "Internal"}}


def test_manifest_patch_failure_raises_problem(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import transformation_manifest

    monkeypatch.setattr(
        transformation_manifest,
        "settings",
        replace(transformation_manifest.settings, environment="staging", gcs_bucket_name="chronos-staging"),
    )
    monkeypatch.setattr(transformation_manifest.GoogleAccessTokenProvider, "access_token", lambda self: "token-123")
    monkeypatch.setattr(
        transformation_manifest.httpx,
        "patch",
        lambda *args, **kwargs: _PatchResponse(should_fail=True),
    )

    with pytest.raises(ProblemException):
        GcsManifestStore().patch_object_metadata(
            object_uri="gs://chronos-staging/manifests/job-1/manifest.json",
            metadata={"classification_label": "Internal"},
        )


def test_manifest_finalize_uses_configured_bucket_for_store_and_patch(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import transformation_manifest

    patched: dict[str, Any] = {}

    class Store:
        def store(self, *, job_id: str, payload: dict[str, Any]) -> tuple[str, int]:
            del payload
            return f"gs://chronos-manifest-test/manifests/{job_id}/manifest.json", 128

        def patch_object_metadata(self, *, object_uri: str, metadata: dict[str, str]) -> bool:
            patched.update({"object_uri": object_uri, "metadata": metadata})
            return True

    monkeypatch.setattr(
        transformation_manifest,
        "settings",
        replace(transformation_manifest.settings, environment="staging", gcs_bucket_name="chronos-manifest-test"),
    )

    result = finalize_manifest_payload(
        manifest_id="manifest-id",
        generated_at="2026-05-11T12:00:00+00:00",
        job=_manifest_job_payload(),
        segments=[],
        store=Store(),
    )

    assert result["payload"]["manifest_uri"] == "gs://chronos-manifest-test/manifests/manifest-job/manifest.json"
    assert patched["object_uri"] == result["payload"]["manifest_uri"]
    assert patched["metadata"]["classification_label"] == "Internal"


def test_uri_only_artifacts_emit_skipped_metadata_events() -> None:
    created = create_seed_job(user_id="uri-only-owner", tier="museum")
    run_all_jobs()

    response = client.get(
        f"/v1/jobs/{created['job_id']}/export",
        headers=fake_auth_header("uri-only-owner", tier="museum"),
    )

    assert response.status_code == 200
    events = DataClassificationAuditRepository().list_events()
    skipped = [event for event in events if event["event_type"] == "gcs_metadata_patch_skipped"]
    artifact_types = {event["artifact_type"] for event in skipped}
    assert ARTIFACT_PROCESSED_OUTPUT in artifact_types
    assert ARTIFACT_EXPORT_PACKAGE in artifact_types
    assert ARTIFACT_DELETION_PROOF in artifact_types


def test_storage_data_access_audit_config_is_declared_with_authoritative_warning() -> None:
    root = Path(__file__).resolve().parents[2]
    iam_tf = (root / "infra" / "terraform" / "iam.tf").read_text(encoding="utf-8")

    assert 'resource "google_project_iam_audit_config" "storage_data_access"' in iam_tf
    assert 'service = "storage.googleapis.com"' in iam_tf
    assert 'log_type = "DATA_READ"' in iam_tf
    assert 'log_type = "DATA_WRITE"' in iam_tf
    assert "authoritative" in iam_tf
    assert "gcloud projects get-iam-policy" in iam_tf
