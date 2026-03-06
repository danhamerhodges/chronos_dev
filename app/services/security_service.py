"""Log-retention and compliance helpers for SEC-009."""

from __future__ import annotations

from datetime import date

from app.api.problem_details import ProblemException
from app.db.phase2_store import ComplianceRepository, LogSettingsRepository


LOG_CATEGORIES = [
    "application_logs",
    "audit_logs",
    "processing_logs",
    "error_traces",
    "billing_logs",
]
EXPORT_TARGETS = ["cloud_logging", "cloudwatch", "splunk", "syslog"]
REDACTION_MODES = {"none", "standard", "strict"}


def supported_export_targets() -> list[str]:
    return list(EXPORT_TARGETS)


def validate_log_settings(*, plan_tier: str, retention_days: int, redaction_mode: str, categories: list[str]) -> None:
    if redaction_mode not in REDACTION_MODES:
        raise ProblemException(
            title="Invalid Log Settings",
            detail="redaction_mode must be one of none, standard, or strict.",
            status_code=400,
        )
    unknown_categories = [category for category in categories if category not in LOG_CATEGORIES]
    if unknown_categories:
        raise ProblemException(
            title="Invalid Log Settings",
            detail=f"Unknown log categories: {', '.join(unknown_categories)}.",
            status_code=400,
        )
    if plan_tier.lower() == "hobbyist" and not (7 <= retention_days <= 365):
        raise ProblemException(
            title="Invalid Log Settings",
            detail="Hobbyist retention must stay between 7 and 365 days.",
            status_code=400,
        )
    if plan_tier.lower() == "pro" and not (30 <= retention_days <= 730):
        raise ProblemException(
            title="Invalid Log Settings",
            detail="Pro retention must stay between 30 and 730 days.",
            status_code=400,
        )
    if plan_tier.lower() == "museum" and not (7 <= retention_days <= 2555):
        raise ProblemException(
            title="Invalid Log Settings",
            detail="Museum retention must stay between 7 and 2555 days.",
            status_code=400,
        )
    if plan_tier.lower() == "hobbyist" and redaction_mode != "none":
        raise ProblemException(
            title="Invalid Log Settings",
            detail="Hobbyist tier only supports redaction_mode='none'.",
            status_code=400,
        )
    if plan_tier.lower() == "pro" and redaction_mode == "strict":
        raise ProblemException(
            title="Invalid Log Settings",
            detail="Strict redaction is only available for Museum tier.",
            status_code=400,
        )


class SecurityService:
    def __init__(self) -> None:
        self._log_repo = LogSettingsRepository()
        self._compliance_repo = ComplianceRepository()

    def update_log_settings(
        self,
        *,
        org_id: str,
        user_id: str,
        plan_tier: str,
        retention_days: int,
        redaction_mode: str,
        categories: list[str],
        export_targets: list[str],
        access_token: str | None = None,
    ) -> dict[str, object]:
        categories = categories or list(LOG_CATEGORIES)
        validate_log_settings(
            plan_tier=plan_tier,
            retention_days=retention_days,
            redaction_mode=redaction_mode,
            categories=categories,
        )
        invalid_targets = [target for target in export_targets if target not in EXPORT_TARGETS]
        if invalid_targets:
            raise ProblemException(
                title="Invalid Log Settings",
                detail=f"Unsupported export targets: {', '.join(invalid_targets)}.",
                status_code=400,
            )
        return self._log_repo.upsert(
            org_id=org_id,
            payload={
                "retention_days": retention_days,
                "redaction_mode": redaction_mode,
                "categories": categories,
                "export_targets": export_targets,
            },
            updated_by=user_id,
            access_token=access_token,
        )

    def delete_logs(
        self,
        *,
        user_id: str,
        categories: list[str],
        date_from: str,
        date_to: str,
        reason: str | None,
        access_token: str | None = None,
    ) -> dict[str, object]:
        requested_categories = categories or list(LOG_CATEGORIES)
        unknown_categories = [category for category in requested_categories if category not in LOG_CATEGORIES]
        if unknown_categories:
            raise ProblemException(
                title="Invalid Log Deletion Request",
                detail=f"Unknown log categories: {', '.join(unknown_categories)}.",
                status_code=400,
            )
        try:
            start = date.fromisoformat(date_from)
            end = date.fromisoformat(date_to)
        except ValueError as exc:
            raise ProblemException(
                title="Invalid Log Deletion Request",
                detail="date_from and date_to must be ISO-8601 calendar dates.",
                status_code=400,
            ) from exc
        if start > end:
            raise ProblemException(
                title="Invalid Log Deletion Request",
                detail="date_from cannot be later than date_to.",
                status_code=400,
            )
        payload = {
            "categories": requested_categories,
            "date_from": date_from,
            "date_to": date_to,
            "reason": reason,
        }
        return self._compliance_repo.create_deletion_request(user_id=user_id, payload=payload, access_token=access_token)
