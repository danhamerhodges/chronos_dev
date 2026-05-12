"""
Maps to:
- SEC-003
"""

from __future__ import annotations

from app.db.phase2_store import DataClassificationAuditRepository, reset_phase2_store
from app.services.data_classification import ARTIFACT_DELETION_PROOF, ARTIFACT_SOURCE_UPLOAD, DataClassificationService


def test_deletion_policy_uses_retention_expiry_for_non_indefinite_data() -> None:
    record = DataClassificationService().classify(
        artifact_type=ARTIFACT_SOURCE_UPLOAD,
        object_uri="gs://chronos/uploads/user/upload/source.mov",
        plan_tier="hobbyist",
        anchor_time="2026-05-11T00:00:00+00:00",
    )

    assert record.retention_days == 7
    assert record.retention_expires_at == "2026-05-18T00:00:00+00:00"


def test_indefinite_museum_policy_has_no_deletion_deadline() -> None:
    record = DataClassificationService().classify(
        artifact_type=ARTIFACT_SOURCE_UPLOAD,
        object_uri="gs://chronos/uploads/museum/upload/source.mov",
        plan_tier="museum",
        anchor_time="2026-05-11T00:00:00+00:00",
    )

    assert record.retention_days is None
    assert record.retention_expires_at is None


def test_deletion_proof_audit_event_carries_compliance_retention() -> None:
    reset_phase2_store()
    service = DataClassificationService()
    record = service.classify(
        artifact_type=ARTIFACT_DELETION_PROOF,
        object_uri="gs://chronos/deletion-proofs/job/proof.pdf",
        plan_tier="pro",
        anchor_time="2026-05-11T00:00:00+00:00",
    )

    service.record_event(record, event_type="classification_assigned")

    [event] = DataClassificationAuditRepository().list_events()
    assert event["classification_label"] == "Compliance"
    assert event["retention_days"] == 2555
    assert event["retention_expires_at"] == record.retention_expires_at
