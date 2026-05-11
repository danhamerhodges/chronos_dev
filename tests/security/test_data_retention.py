"""
Maps to:
- SEC-003
"""

from __future__ import annotations

from app.services.data_classification import (
    ARTIFACT_DELETION_PROOF,
    ARTIFACT_EXPORT_PACKAGE,
    ARTIFACT_SOURCE_UPLOAD,
    ARTIFACT_TRANSFORMATION_MANIFEST,
    DataClassificationService,
    retention_days_for_artifact,
)


def test_tier_retention_defaults_for_classified_data() -> None:
    assert retention_days_for_artifact(artifact_type=ARTIFACT_SOURCE_UPLOAD, plan_tier="hobbyist") == 7
    assert retention_days_for_artifact(artifact_type=ARTIFACT_SOURCE_UPLOAD, plan_tier="pro") == 90
    assert retention_days_for_artifact(artifact_type=ARTIFACT_SOURCE_UPLOAD, plan_tier="museum") is None


def test_retention_expiry_uses_artifact_anchor_timestamp() -> None:
    service = DataClassificationService()

    upload = service.classify(
        artifact_type=ARTIFACT_SOURCE_UPLOAD,
        object_uri="gs://chronos/uploads/user/upload/sample.mov",
        plan_tier="hobbyist",
        anchor_time="2026-05-11T12:00:00+00:00",
    )
    manifest = service.classify(
        artifact_type=ARTIFACT_TRANSFORMATION_MANIFEST,
        object_uri="gs://chronos/manifests/job/manifest.json",
        plan_tier="pro",
        anchor_time="2026-05-11T12:00:00+00:00",
    )
    package = service.classify(
        artifact_type=ARTIFACT_EXPORT_PACKAGE,
        object_uri="gs://chronos/downloads/job/av1.zip",
        plan_tier="museum",
        anchor_time="2026-05-11T12:00:00+00:00",
    )

    assert upload.retention_days == 7
    assert upload.retention_expires_at == "2026-05-18T12:00:00+00:00"
    assert manifest.retention_days == 90
    assert manifest.retention_expires_at == "2026-08-09T12:00:00+00:00"
    assert package.retention_days is None
    assert package.retention_expires_at is None


def test_compliance_retention_uses_2555_day_minimum() -> None:
    proof = DataClassificationService().classify(
        artifact_type=ARTIFACT_DELETION_PROOF,
        object_uri="gs://chronos/deletion-proofs/job/proof.pdf",
        plan_tier="hobbyist",
        anchor_time="2026-05-11T12:00:00+00:00",
    )

    assert proof.classification_label == "Compliance"
    assert proof.retention_days == 2555
    assert proof.retention_expires_at == "2033-05-09T12:00:00+00:00"
