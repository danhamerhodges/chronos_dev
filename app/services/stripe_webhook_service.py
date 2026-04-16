"""Stripe billing webhook handlers for Packet 5D."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.db.phase2_store import (
    BillingAccountRepository,
    BillingAuditRepository,
    ProcessedStripeEventRepository,
)
from app.observability.monitoring import record_billing_event


class BillingWebhookProcessingError(RuntimeError):
    """Raised when a Stripe webhook cannot be processed safely."""


def _field(resource: Any, field_name: str) -> Any:
    if isinstance(resource, dict):
        return resource.get(field_name)
    value = getattr(resource, field_name, None)
    if value is not None:
        return value
    try:
        return resource[field_name]
    except Exception:
        return None


def _metadata(resource: Any) -> dict[str, Any]:
    metadata = _field(resource, "metadata")
    return dict(metadata or {})


def _event_timestamp(event: Any) -> str:
    created = _field(event, "created")
    if isinstance(created, (int, float)):
        return datetime.fromtimestamp(float(created), tz=timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()


def _subscription_price(resource: Any) -> tuple[str, float]:
    items_container = _field(resource, "items") or {}
    items = _field(items_container, "data") or []
    if not items:
        return "", 0.0
    first_item = items[0]
    price = _field(first_item, "price") or {}
    price_id = str(_field(price, "id") or "").strip()
    unit_amount = _field(price, "unit_amount_decimal")
    if unit_amount is None:
        unit_amount = _field(price, "unit_amount")
    if unit_amount in (None, ""):
        return price_id, 0.0
    return price_id, round(float(unit_amount) / 100.0, 4)


def _invoice_summary(invoice: Any) -> dict[str, Any]:
    amount_paid = _field(invoice, "amount_paid")
    amount_due = _field(invoice, "amount_due")
    return {
        "invoice_id": str(_field(invoice, "id") or ""),
        "status": str(_field(invoice, "status") or ""),
        "hosted_invoice_url": str(_field(invoice, "hosted_invoice_url") or ""),
        "amount_paid_usd": round(float(amount_paid or 0) / 100.0, 4),
        "amount_due_usd": round(float(amount_due or 0) / 100.0, 4),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


class StripeWebhookService:
    def __init__(self) -> None:
        self._accounts = BillingAccountRepository()
        self._audit = BillingAuditRepository()
        self._processed = ProcessedStripeEventRepository()

    def process_event(self, event: Any) -> dict[str, Any]:
        event_id = str(_field(event, "id") or "").strip()
        event_type = str(_field(event, "type") or "").strip()
        if not event_id or not event_type:
            raise BillingWebhookProcessingError("Stripe webhook event is missing required identifiers.")
        event_object = _field(_field(event, "data") or {}, "object") or {}
        org_id = self._resolve_org_id(event_object)
        claimed = self._processed.claim_event(
            stripe_event_id=event_id,
            event_type=event_type,
            org_id=org_id,
        )
        if claimed is None:
            return {
                "event_id": event_id,
                "event_type": event_type,
                "status": "duplicate",
                "duplicate": True,
                "org_id": org_id,
            }
        try:
            if event_type.startswith("customer.subscription."):
                org_id = self._process_subscription_event(event_id=event_id, resource=event_object, org_id=org_id)
            elif event_type.startswith("invoice."):
                org_id = self._process_invoice_event(event_id=event_id, resource=event_object, org_id=org_id)
            elif event_type.startswith("quote."):
                org_id = self._process_quote_event(event_id=event_id, resource=event_object, org_id=org_id)
        except Exception as exc:
            self._processed.mark_failed(
                event_id,
                summary_metadata={"event_type": event_type, "org_id": org_id, "error": exc.__class__.__name__},
            )
            record_billing_event("stripe_webhook", outcome="failed")
            raise BillingWebhookProcessingError(
                f"Stripe webhook processing failed for event {event_id}."
            ) from exc
        self._processed.mark_processed(
            event_id,
            summary_metadata={"event_type": event_type, "org_id": org_id},
        )
        record_billing_event("stripe_webhook", outcome="processed")
        return {
            "event_id": event_id,
            "event_type": event_type,
            "status": "processed",
            "duplicate": False,
            "org_id": org_id,
        }

    def _resolve_org_id(self, resource: Any) -> str | None:
        metadata = _metadata(resource)
        metadata_org_id = str(metadata.get("org_id") or "").strip()
        if metadata_org_id:
            return metadata_org_id
        customer_id = str(_field(resource, "customer") or "").strip()
        if not customer_id:
            return None
        account = self._accounts.get_by_customer_id(customer_id)
        return str((account or {}).get("org_id") or "").strip() or None

    def _owner_user_id(self, *, org_id: str | None, resource: Any) -> str:
        metadata = _metadata(resource)
        if org_id:
            account = self._accounts.get_by_org(org_id)
            owner_user_id = str((account or {}).get("owner_user_id") or "").strip()
            if owner_user_id:
                return owner_user_id
        owner_user_id = str(metadata.get("owner_user_id") or metadata.get("user_id") or "").strip()
        if owner_user_id:
            return owner_user_id
        return "system"

    def _required_org_id(self, *, resource: Any, org_id: str | None) -> str:
        resolved_org_id = str(org_id or "").strip()
        if resolved_org_id:
            return resolved_org_id
        customer_id = str(_field(resource, "customer") or "").strip()
        if customer_id:
            raise BillingWebhookProcessingError(
                "Stripe webhook customer is not bound to an org-scoped billing account."
            )
        raise BillingWebhookProcessingError(
            "Stripe webhook metadata must resolve an org_id before billing state can be updated."
        )

    def _process_subscription_event(self, *, event_id: str, resource: Any, org_id: str | None) -> str:
        resolved_org_id = self._required_org_id(resource=resource, org_id=org_id)
        owner_user_id = self._owner_user_id(org_id=resolved_org_id, resource=resource)
        account_before = self._accounts.get_by_org(resolved_org_id) or {}
        subscription_price_id, subscription_price_usd = _subscription_price(resource)
        patch = {
            "stripe_customer_id": str(_field(resource, "customer") or "").strip() or account_before.get("stripe_customer_id"),
            "stripe_subscription_id": str(_field(resource, "id") or "").strip(),
            "subscription_status": str(_field(resource, "status") or "").strip(),
            "subscription_price_id": subscription_price_id or account_before.get("subscription_price_id"),
            "subscription_price_usd": subscription_price_usd or account_before.get("subscription_price_usd"),
            "included_minutes_monthly": _metadata(resource).get("included_minutes_monthly")
            or account_before.get("included_minutes_monthly"),
            "overage_price_id": _metadata(resource).get("overage_price_id") or account_before.get("overage_price_id"),
            "overage_rate_usd_per_minute": _metadata(resource).get("overage_rate_usd_per_minute")
            or account_before.get("overage_rate_usd_per_minute"),
            "last_synced_at": _event_timestamp(resource),
        }
        account_after = self._accounts.upsert_by_org(
            org_id=resolved_org_id,
            owner_user_id=owner_user_id,
            patch=patch,
        )
        self._audit.append_event(
            org_id=resolved_org_id,
            source="stripe_webhook",
            event_type="subscription_updated",
            actor_user_id=owner_user_id,
            stripe_event_id=event_id,
            before_summary={
                "subscription_status": account_before.get("subscription_status"),
                "subscription_price_id": account_before.get("subscription_price_id"),
            },
            after_summary={
                "subscription_status": account_after.get("subscription_status"),
                "subscription_price_id": account_after.get("subscription_price_id"),
            },
        )
        return resolved_org_id

    def _process_invoice_event(self, *, event_id: str, resource: Any, org_id: str | None) -> str:
        resolved_org_id = self._required_org_id(resource=resource, org_id=org_id)
        owner_user_id = self._owner_user_id(org_id=resolved_org_id, resource=resource)
        account_before = self._accounts.get_by_org(resolved_org_id) or {}
        existing_invoices = list(account_before.get("recent_invoices") or [])
        invoice = _invoice_summary(resource)
        deduped = [item for item in existing_invoices if item.get("invoice_id") != invoice["invoice_id"]]
        updated_invoices = [invoice, *deduped][:10]
        account_after = self._accounts.upsert_by_org(
            org_id=resolved_org_id,
            owner_user_id=owner_user_id,
            patch={
                "stripe_customer_id": str(_field(resource, "customer") or "").strip() or account_before.get("stripe_customer_id"),
                "recent_invoices": updated_invoices,
                "last_synced_at": _event_timestamp(resource),
            },
        )
        self._audit.append_event(
            org_id=resolved_org_id,
            source="stripe_webhook",
            event_type="invoice_updated",
            actor_user_id=owner_user_id,
            stripe_event_id=event_id,
            before_summary={"invoice_count": len(existing_invoices)},
            after_summary={"invoice_count": len(account_after.get("recent_invoices") or [])},
        )
        return resolved_org_id

    def _process_quote_event(self, *, event_id: str, resource: Any, org_id: str | None) -> str:
        resolved_org_id = self._required_org_id(resource=resource, org_id=org_id)
        owner_user_id = self._owner_user_id(org_id=resolved_org_id, resource=resource)
        metadata = _metadata(resource)
        account_before = self._accounts.get_by_org(resolved_org_id) or {}
        account_after = self._accounts.upsert_by_org(
            org_id=resolved_org_id,
            owner_user_id=owner_user_id,
            patch={
                "stripe_customer_id": str(_field(resource, "customer") or "").strip() or account_before.get("stripe_customer_id"),
                "museum_quote_id": str(_field(resource, "id") or "").strip(),
                "museum_quote_status": str(_field(resource, "status") or "").strip(),
                "museum_quote_pricing": {
                    "subscription_price_id": metadata.get("subscription_price_id"),
                    "subscription_price_usd": metadata.get("subscription_price_usd"),
                    "included_minutes_monthly": metadata.get("included_minutes_monthly"),
                    "overage_price_id": metadata.get("overage_price_id"),
                    "overage_rate_usd_per_minute": metadata.get("overage_rate_usd_per_minute"),
                },
                "last_synced_at": _event_timestamp(resource),
            },
        )
        self._audit.append_event(
            org_id=resolved_org_id,
            source="stripe_webhook",
            event_type="quote_updated",
            actor_user_id=owner_user_id,
            stripe_event_id=event_id,
            before_summary={"museum_quote_id": account_before.get("museum_quote_id")},
            after_summary={"museum_quote_id": account_after.get("museum_quote_id")},
        )
        return resolved_org_id
