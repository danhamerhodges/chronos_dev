"""SEC-003 data classification policy and audit helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
from typing import Any, Literal

from app.db.phase2_store import DataClassificationAuditRepository

CLASSIFICATION_POLICY_VERSION = "sec-003-v1"
BACKFILL_POLICY_VERSION = "v0-backfill"

ClassificationLabel = Literal["Confidential", "Internal", "Compliance", "Public"]
ClassificationEventType = Literal[
    "classification_assigned",
    "gcs_metadata_patched",
    "gcs_metadata_patch_skipped",
    "gcs_metadata_patch_failed",
]

ARTIFACT_SOURCE_UPLOAD = "source_upload"
ARTIFACT_PROCESSED_OUTPUT = "processed_output"
ARTIFACT_TRANSFORMATION_MANIFEST = "transformation_manifest"
ARTIFACT_EXPORT_PACKAGE = "export_package"
ARTIFACT_DELETION_PROOF = "deletion_proof"
ClassificationArtifactType = Literal[
    "source_upload",
    "processed_output",
    "transformation_manifest",
    "export_package",
    "deletion_proof",
]

CLASSIFICATION_LABELS: tuple[ClassificationLabel, ...] = ("Confidential", "Internal", "Compliance", "Public")
CLASSIFICATION_ARTIFACT_TYPES: tuple[ClassificationArtifactType, ...] = (
    ARTIFACT_SOURCE_UPLOAD,
    ARTIFACT_PROCESSED_OUTPUT,
    ARTIFACT_TRANSFORMATION_MANIFEST,
    ARTIFACT_EXPORT_PACKAGE,
    ARTIFACT_DELETION_PROOF,
)
CLASSIFICATION_EVENT_TYPES: tuple[ClassificationEventType, ...] = (
    "classification_assigned",
    "gcs_metadata_patched",
    "gcs_metadata_patch_skipped",
    "gcs_metadata_patch_failed",
)

_LOCAL_ENVIRONMENTS = {"test", "dev", "development", "local"}
_TIER_RETENTION_DAYS: dict[str, int | None] = {
    "hobbyist": 7,
    "pro": 90,
    "museum": None,
}
_COMPLIANCE_RETENTION_DAYS = 2555


@dataclass(frozen=True)
class ClassificationRecord:
    artifact_type: str
    classification_label: ClassificationLabel
    object_uri: str
    object_hash: str
    retention_days: int | None
    retention_expires_at: str | None
    policy_version: str

    @property
    def metadata(self) -> dict[str, str]:
        payload = {
            "classification_label": self.classification_label,
            "artifact_type": self.artifact_type,
            "classification_policy_version": self.policy_version,
        }
        if self.retention_days is not None:
            payload["retention_days"] = str(self.retention_days)
        if self.retention_expires_at is not None:
            payload["retention_expires_at"] = self.retention_expires_at
        return payload

    @property
    def persistence_fields(self) -> dict[str, Any]:
        return {
            "classification_label": self.classification_label,
            "retention_days": self.retention_days,
            "retention_expires_at": self.retention_expires_at,
            "classification_policy_version": self.policy_version,
        }


class DataClassificationService:
    def __init__(self, *, audit_repository: DataClassificationAuditRepository | None = None) -> None:
        self._audit = audit_repository or DataClassificationAuditRepository()

    def classify(
        self,
        *,
        artifact_type: str,
        object_uri: str,
        plan_tier: str,
        anchor_time: str | datetime,
        retention_days_override: int | None = None,
        use_retention_override: bool = False,
    ) -> ClassificationRecord:
        label = classification_label_for_artifact(artifact_type)
        retention_days = (
            retention_days_override
            if use_retention_override
            else retention_days_for_artifact(artifact_type=artifact_type, plan_tier=plan_tier)
        )
        retention_expires_at = _retention_expires_at(anchor_time=anchor_time, retention_days=retention_days)
        return ClassificationRecord(
            artifact_type=artifact_type,
            classification_label=label,
            object_uri=object_uri,
            object_hash=object_hash(object_uri),
            retention_days=retention_days,
            retention_expires_at=retention_expires_at,
            policy_version=CLASSIFICATION_POLICY_VERSION,
        )

    def record_event(
        self,
        record: ClassificationRecord,
        *,
        event_type: ClassificationEventType,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._audit.record_event(
            artifact_type=record.artifact_type,
            classification_label=record.classification_label,
            object_uri=record.object_uri,
            object_hash=record.object_hash,
            retention_days=record.retention_days,
            retention_expires_at=record.retention_expires_at,
            policy_version=record.policy_version,
            event_type=event_type,
            metadata=metadata or {},
        )


def classification_label_for_artifact(artifact_type: str) -> ClassificationLabel:
    if artifact_type in {ARTIFACT_SOURCE_UPLOAD, ARTIFACT_PROCESSED_OUTPUT, ARTIFACT_EXPORT_PACKAGE}:
        return "Confidential"
    if artifact_type == ARTIFACT_TRANSFORMATION_MANIFEST:
        return "Internal"
    if artifact_type == ARTIFACT_DELETION_PROOF:
        return "Compliance"
    raise ValueError(f"Unsupported SEC-003 artifact type: {artifact_type}")


def retention_days_for_artifact(*, artifact_type: str, plan_tier: str) -> int | None:
    if artifact_type == ARTIFACT_DELETION_PROOF:
        return _COMPLIANCE_RETENTION_DAYS
    return _TIER_RETENTION_DAYS.get(plan_tier.lower(), _TIER_RETENTION_DAYS["hobbyist"])


def object_hash(object_uri: str) -> str:
    return hashlib.sha256(object_uri.encode("utf-8")).hexdigest()


def is_local_environment(environment: str) -> bool:
    return environment in _LOCAL_ENVIRONMENTS


def _retention_expires_at(*, anchor_time: str | datetime, retention_days: int | None) -> str | None:
    if retention_days is None:
        return None
    anchor = _coerce_datetime(anchor_time)
    return (anchor + timedelta(days=retention_days)).isoformat()


def _coerce_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
