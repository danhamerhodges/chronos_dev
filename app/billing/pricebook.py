"""Commercial pricebook parsing and validation for Packet 5C."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Mapping

_SUPPORTED_PLAN_TIERS = ("hobbyist", "pro", "museum")
_SUPPORTED_FIDELITY_TIERS = {"Enhance", "Restore", "Conserve"}
_SUPPORTED_RESOLUTION_CAPS = {"1080p", "4k", "native_scan"}


class CommercialPricebookConfigurationError(ValueError):
    """Raised when commercial pricebook configuration is missing or invalid."""


@dataclass(frozen=True)
class CommercialPricebookOverage:
    enabled: bool
    price_id: str
    rate_usd_per_minute: float


@dataclass(frozen=True)
class CommercialEntitlements:
    preview_review: bool
    fidelity_tiers: tuple[str, ...]
    resolution_cap: str
    parallel_jobs: int
    export_retention_days: int


@dataclass(frozen=True)
class CommercialPricebookEntry:
    subscription_price_id: str
    plan_tier: str
    included_minutes_monthly: int
    overage: CommercialPricebookOverage
    entitlements: CommercialEntitlements


@dataclass(frozen=True)
class CommercialPricebook:
    version: str
    entries: dict[str, CommercialPricebookEntry]


def _require_dict(value: object, *, field_name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise CommercialPricebookConfigurationError(f"{field_name} must be an object.")
    return dict(value)


def _require_string(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CommercialPricebookConfigurationError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _require_bool(value: object, *, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise CommercialPricebookConfigurationError(f"{field_name} must be a boolean.")
    return value


def _require_int(value: object, *, field_name: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CommercialPricebookConfigurationError(f"{field_name} must be an integer.")
    if value < minimum:
        raise CommercialPricebookConfigurationError(f"{field_name} must be >= {minimum}.")
    return value


def _require_float(value: object, *, field_name: str, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CommercialPricebookConfigurationError(f"{field_name} must be a number.")
    normalized = float(value)
    if normalized < minimum:
        raise CommercialPricebookConfigurationError(f"{field_name} must be >= {minimum}.")
    return normalized


def _parse_entitlements(payload: object, *, entry_name: str) -> CommercialEntitlements:
    entitlements = _require_dict(payload, field_name=f"entries[{entry_name}].entitlements")
    fidelity_tiers_raw = entitlements.get("fidelity_tiers")
    if not isinstance(fidelity_tiers_raw, list) or not fidelity_tiers_raw:
        raise CommercialPricebookConfigurationError(
            f"entries[{entry_name}].entitlements.fidelity_tiers must be a non-empty array."
        )
    fidelity_tiers = tuple(str(item) for item in fidelity_tiers_raw)
    if any(tier not in _SUPPORTED_FIDELITY_TIERS for tier in fidelity_tiers):
        raise CommercialPricebookConfigurationError(
            f"entries[{entry_name}].entitlements.fidelity_tiers must use canonical fidelity tiers only."
        )
    resolution_cap = _require_string(
        entitlements.get("resolution_cap"),
        field_name=f"entries[{entry_name}].entitlements.resolution_cap",
    )
    if resolution_cap not in _SUPPORTED_RESOLUTION_CAPS:
        raise CommercialPricebookConfigurationError(
            f"entries[{entry_name}].entitlements.resolution_cap must use a supported canonical value."
        )
    return CommercialEntitlements(
        preview_review=_require_bool(
            entitlements.get("preview_review"),
            field_name=f"entries[{entry_name}].entitlements.preview_review",
        ),
        fidelity_tiers=fidelity_tiers,
        resolution_cap=resolution_cap,
        parallel_jobs=_require_int(
            entitlements.get("parallel_jobs"),
            field_name=f"entries[{entry_name}].entitlements.parallel_jobs",
            minimum=1,
        ),
        export_retention_days=_require_int(
            entitlements.get("export_retention_days"),
            field_name=f"entries[{entry_name}].entitlements.export_retention_days",
            minimum=1,
        ),
    )


def _parse_overage(payload: object, *, entry_name: str) -> CommercialPricebookOverage:
    overage = _require_dict(payload, field_name=f"entries[{entry_name}].overage")
    enabled = _require_bool(overage.get("enabled"), field_name=f"entries[{entry_name}].overage.enabled")
    price_id = str(overage.get("price_id") or "").strip()
    rate = _require_float(
        overage.get("rate_usd_per_minute"),
        field_name=f"entries[{entry_name}].overage.rate_usd_per_minute",
        minimum=0.0,
    )
    if enabled and not price_id:
        raise CommercialPricebookConfigurationError(
            f"entries[{entry_name}].overage.price_id is required when overage.enabled is true."
        )
    if enabled and rate <= 0:
        raise CommercialPricebookConfigurationError(
            f"entries[{entry_name}].overage.rate_usd_per_minute must be > 0 when overage.enabled is true."
        )
    if not enabled and rate != 0.0:
        raise CommercialPricebookConfigurationError(
            f"entries[{entry_name}].overage.rate_usd_per_minute must be 0 when overage.enabled is false."
        )
    return CommercialPricebookOverage(
        enabled=enabled,
        price_id=price_id,
        rate_usd_per_minute=rate,
    )


def parse_commercial_pricebook(raw_json: str) -> CommercialPricebook:
    if not raw_json or not raw_json.strip():
        raise CommercialPricebookConfigurationError("COMMERCIAL_PRICEBOOK_JSON is required.")
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise CommercialPricebookConfigurationError("COMMERCIAL_PRICEBOOK_JSON must be valid JSON.") from exc
    root = _require_dict(payload, field_name="COMMERCIAL_PRICEBOOK_JSON")
    version = _require_string(root.get("version"), field_name="COMMERCIAL_PRICEBOOK_JSON.version")
    entries_raw = _require_dict(root.get("entries"), field_name="COMMERCIAL_PRICEBOOK_JSON.entries")
    if not entries_raw:
        raise CommercialPricebookConfigurationError("COMMERCIAL_PRICEBOOK_JSON.entries must not be empty.")
    entries: dict[str, CommercialPricebookEntry] = {}
    for subscription_price_id, entry_payload in entries_raw.items():
        entry_name = _require_string(subscription_price_id, field_name="COMMERCIAL_PRICEBOOK_JSON.entries key")
        entry = _require_dict(entry_payload, field_name=f"entries[{entry_name}]")
        plan_tier = _require_string(entry.get("plan_tier"), field_name=f"entries[{entry_name}].plan_tier").lower()
        if plan_tier not in _SUPPORTED_PLAN_TIERS:
            raise CommercialPricebookConfigurationError(
                f"entries[{entry_name}].plan_tier must be one of: {', '.join(_SUPPORTED_PLAN_TIERS)}."
            )
        entries[entry_name] = CommercialPricebookEntry(
            subscription_price_id=entry_name,
            plan_tier=plan_tier,
            included_minutes_monthly=_require_int(
                entry.get("included_minutes_monthly"),
                field_name=f"entries[{entry_name}].included_minutes_monthly",
                minimum=0,
            ),
            overage=_parse_overage(entry.get("overage"), entry_name=entry_name),
            entitlements=_parse_entitlements(entry.get("entitlements"), entry_name=entry_name),
        )
    return CommercialPricebook(version=version, entries=entries)


def validate_commercial_pricebook_configuration(
    *,
    raw_json: str,
    recurring_price_ids_by_tier: Mapping[str, str],
) -> CommercialPricebook:
    pricebook = parse_commercial_pricebook(raw_json)
    for plan_tier in _SUPPORTED_PLAN_TIERS:
        recurring_price_id = str(recurring_price_ids_by_tier.get(plan_tier) or "").strip()
        if not recurring_price_id:
            raise CommercialPricebookConfigurationError(
                f"{plan_tier} recurring Stripe price id is required for COMMERCIAL_PRICEBOOK_JSON resolution."
            )
        entry = pricebook.entries.get(recurring_price_id)
        if entry is None:
            raise CommercialPricebookConfigurationError(
                f"COMMERCIAL_PRICEBOOK_JSON is missing an entry for recurring price id {recurring_price_id}."
            )
        if entry.plan_tier != plan_tier:
            raise CommercialPricebookConfigurationError(
                f"COMMERCIAL_PRICEBOOK_JSON entry {recurring_price_id} must declare plan_tier={plan_tier}."
            )
    return pricebook


@lru_cache(maxsize=8)
def cached_commercial_pricebook(
    raw_json: str,
    hobbyist_price_id: str,
    pro_price_id: str,
    museum_price_id: str,
) -> CommercialPricebook:
    return validate_commercial_pricebook_configuration(
        raw_json=raw_json,
        recurring_price_ids_by_tier={
            "hobbyist": hobbyist_price_id,
            "pro": pro_price_id,
            "museum": museum_price_id,
        },
    )


def resolve_pricebook_entry(
    *,
    pricebook: CommercialPricebook,
    recurring_price_ids_by_tier: Mapping[str, str],
    plan_tier: str,
) -> CommercialPricebookEntry:
    normalized_tier = str(plan_tier).strip().lower()
    if normalized_tier not in _SUPPORTED_PLAN_TIERS:
        raise CommercialPricebookConfigurationError(
            f"Unsupported plan tier for COMMERCIAL_PRICEBOOK_JSON resolution: {plan_tier}"
        )
    recurring_price_id = str(recurring_price_ids_by_tier.get(normalized_tier) or "").strip()
    if not recurring_price_id:
        raise CommercialPricebookConfigurationError(
            f"Recurring Stripe price id is missing for plan tier {normalized_tier}."
        )
    entry = pricebook.entries.get(recurring_price_id)
    if entry is None:
        raise CommercialPricebookConfigurationError(
            f"COMMERCIAL_PRICEBOOK_JSON has no entry for recurring price id {recurring_price_id}."
        )
    if entry.plan_tier != normalized_tier:
        raise CommercialPricebookConfigurationError(
            f"COMMERCIAL_PRICEBOOK_JSON entry {recurring_price_id} does not match plan tier {normalized_tier}."
        )
    return entry
