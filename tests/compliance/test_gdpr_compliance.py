"""
Maps to:
- SEC-003
"""

from __future__ import annotations

from app.services.data_classification import ARTIFACT_DELETION_PROOF, ARTIFACT_SOURCE_UPLOAD, DataClassificationService


def test_classification_gdpr_scope_is_policy_decision_only() -> None:
    record = DataClassificationService().classify(
        artifact_type=ARTIFACT_SOURCE_UPLOAD,
        object_uri="gs://chronos/uploads/user/upload/source.mov",
        plan_tier="pro",
        anchor_time="2026-05-11T00:00:00+00:00",
    )

    assert record.classification_label == "Confidential"
    assert record.retention_days == 90
    assert record.retention_expires_at == "2026-08-09T00:00:00+00:00"


def test_compliance_artifacts_preserve_deletion_proof_for_legal_minimum() -> None:
    record = DataClassificationService().classify(
        artifact_type=ARTIFACT_DELETION_PROOF,
        object_uri="gs://chronos/deletion-proofs/job/proof.pdf",
        plan_tier="hobbyist",
        anchor_time="2026-05-11T00:00:00+00:00",
    )

    assert record.classification_label == "Compliance"
    assert record.retention_days == 2555
    assert record.retention_expires_at is not None


def test_sec006_erasure_orchestration_is_out_of_scope_for_packet_5g() -> None:
    # Packet 5G covers classification-driven retention decisions only; SEC-006
    # request orchestration and right-to-access workflows are separate work.
    record = DataClassificationService().classify(
        artifact_type=ARTIFACT_SOURCE_UPLOAD,
        object_uri="gs://chronos/uploads/museum/upload/source.mov",
        plan_tier="museum",
        anchor_time="2026-05-11T00:00:00+00:00",
    )

    assert record.retention_days is None
    assert record.retention_expires_at is None
