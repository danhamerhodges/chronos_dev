"""SEC-005 transformation manifest retention policy helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

RETENTION_POLICY_VERSION = "sec-005-v1"
BACKFILL_RETENTION_POLICY_VERSION = "v0-backfill"

RETENTION_CLASS_ZERO = "0d"
RETENTION_CLASS_7D = "7d"
RETENTION_CLASS_90D = "90d"
RETENTION_CLASS_365D = "365d"
RETENTION_CLASS_1825D = "1825d"
RETENTION_CLASS_INDEFINITE = "indefinite"

MUSEUM_ALLOWED_RETENTION_DAYS: tuple[int | None, ...] = (0, 90, 365, 1825, None)

_TIER_DEFAULT_RETENTION_DAYS: dict[str, int | None] = {
    "hobbyist": 7,
    "pro": 90,
    "museum": None,
}


@dataclass(frozen=True)
class ManifestRetentionPolicy:
    retention_days: int | None
    retention_expires_at: str | None
    retention_class: str
    retention_policy_source: str
    manifest_redaction_enabled: bool

    @property
    def persistence_fields(self) -> dict[str, Any]:
        return {
            "retention_days": self.retention_days,
            "retention_expires_at": self.retention_expires_at,
            "retention_class": self.retention_class,
            "retention_policy_source": self.retention_policy_source,
            "manifest_redaction_enabled": self.manifest_redaction_enabled,
        }


class ManifestRetentionService:
    def __init__(self, *, settings_repository: Any | None = None) -> None:
        if settings_repository is None:
            from app.db.phase2_store import ManifestRetentionSettingsRepository

            settings_repository = ManifestRetentionSettingsRepository()
        self._settings = settings_repository

    def resolve_policy(
        self,
        *,
        org_id: str | None,
        plan_tier: str,
        generated_at: str | datetime,
    ) -> ManifestRetentionPolicy:
        normalized_tier = plan_tier.lower()
        retention_days = _TIER_DEFAULT_RETENTION_DAYS.get(normalized_tier, _TIER_DEFAULT_RETENTION_DAYS["hobbyist"])
        redaction_enabled = False
        policy_source = "tier_default"

        if normalized_tier == "museum":
            setting = self._settings.get(org_id) if org_id else None
            if setting is not None:
                retention_days = setting.get("manifest_retention_days")
                redaction_enabled = bool(setting.get("manifest_redaction_enabled"))
                policy_source = "org_data_retention_settings"

        return ManifestRetentionPolicy(
            retention_days=retention_days,
            retention_expires_at=_retention_expires_at(anchor_time=generated_at, retention_days=retention_days),
            retention_class=retention_class_for_days(retention_days),
            retention_policy_source=policy_source,
            manifest_redaction_enabled=redaction_enabled if normalized_tier == "museum" else False,
        )

    def validate_settings(self, *, plan_tier: str, manifest_retention_days: int | None) -> None:
        if plan_tier.lower() != "museum":
            raise ValueError("SEC-005 manifest retention settings are Museum-tier only.")
        if manifest_retention_days not in MUSEUM_ALLOWED_RETENTION_DAYS:
            raise ValueError("Museum manifest retention must be one of 0, 90, 365, 1825, or indefinite.")

    def update_settings(
        self,
        *,
        org_id: str,
        user_id: str,
        plan_tier: str,
        manifest_retention_days: int | None,
        manifest_redaction_enabled: bool,
        access_token: str | None = None,
    ) -> dict[str, Any]:
        self.validate_settings(plan_tier=plan_tier, manifest_retention_days=manifest_retention_days)
        record = self._settings.upsert(
            org_id=org_id,
            plan_tier=plan_tier,
            manifest_retention_days=manifest_retention_days,
            manifest_redaction_enabled=manifest_redaction_enabled,
            updated_by=user_id,
            access_token=access_token,
        )
        return {
            "org_id": record["org_id"],
            "plan_tier": record["plan_tier"],
            "manifest_retention_days": record["manifest_retention_days"],
            "manifest_redaction_enabled": bool(record["manifest_redaction_enabled"]),
            "retention_class": retention_class_for_days(record["manifest_retention_days"]),
            "updated_by": record.get("updated_by"),
            "updated_at": record["updated_at"],
        }


def retention_class_for_days(retention_days: int | None) -> str:
    if retention_days is None:
        return RETENTION_CLASS_INDEFINITE
    if retention_days == 0:
        return RETENTION_CLASS_ZERO
    if retention_days == 7:
        return RETENTION_CLASS_7D
    if retention_days == 90:
        return RETENTION_CLASS_90D
    if retention_days == 365:
        return RETENTION_CLASS_365D
    if retention_days == 1825:
        return RETENTION_CLASS_1825D
    raise ValueError(f"Unsupported SEC-005 manifest retention days: {retention_days}")


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
