"""Commercial pricebook revision services for Packet 5D."""

from __future__ import annotations

import json

from app.billing.pricebook import CommercialPricebook, validate_commercial_pricebook_configuration
from app.config import settings
from app.db.phase2_store import CommercialPricebookRevisionRepository


def _recurring_price_ids_by_tier() -> dict[str, str]:
    return {
        "hobbyist": settings.stripe_hobbyist_price_id.strip(),
        "pro": settings.stripe_pro_price_id.strip(),
        "museum": settings.stripe_museum_price_id.strip(),
    }


def _validated_pricebook_from_payload(payload: dict[str, object]) -> CommercialPricebook:
    return validate_commercial_pricebook_configuration(
        raw_json=json.dumps(payload, sort_keys=True),
        recurring_price_ids_by_tier=_recurring_price_ids_by_tier(),
    )


def active_pricebook() -> tuple[CommercialPricebook, str]:
    revision = CommercialPricebookRevisionRepository().get_active()
    if revision is not None:
        return _validated_pricebook_from_payload(dict(revision["payload"])), "db"
    return (
        validate_commercial_pricebook_configuration(
            raw_json=settings.commercial_pricebook_json,
            recurring_price_ids_by_tier=_recurring_price_ids_by_tier(),
        ),
        "env",
    )


def activate_pricebook_revision(
    *,
    payload: dict[str, object],
    applied_by_user_id: str,
    applied_by_org_id: str,
    change_summary: str,
    source: str = "api",
) -> dict[str, object]:
    pricebook = _validated_pricebook_from_payload(payload)
    return CommercialPricebookRevisionRepository().activate(
        version=pricebook.version,
        payload=json.loads(json.dumps(payload)),
        applied_by_user_id=applied_by_user_id,
        applied_by_org_id=applied_by_org_id,
        source=source,
        change_summary=change_summary,
    )


def bootstrap_pricebook_revision_from_environment(
    *,
    applied_by_user_id: str,
    applied_by_org_id: str,
    change_summary: str,
) -> dict[str, object]:
    repository = CommercialPricebookRevisionRepository()
    if repository.get_active() is not None:
        raise ValueError("A hosted commercial pricebook revision is already active.")
    payload = json.loads(settings.commercial_pricebook_json)
    pricebook = _validated_pricebook_from_payload(payload)
    return repository.activate(
        version=pricebook.version,
        payload=payload,
        applied_by_user_id=applied_by_user_id,
        applied_by_org_id=applied_by_org_id,
        source="environment_bootstrap",
        change_summary=change_summary,
    )
