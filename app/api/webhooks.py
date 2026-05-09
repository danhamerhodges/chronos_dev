"""Stripe webhook routes for Packet 5D."""

from __future__ import annotations

from fastapi import APIRouter, Header, Request

from app.api.contracts import StripeWebhookResponse
from app.api.problem_details import ProblemException
from app.billing.webhooks import construct_event
from app.config import settings
from app.services.stripe_webhook_service import BillingWebhookProcessingError, StripeWebhookService

router = APIRouter()
_stripe_webhooks = StripeWebhookService()


@router.post("/v1/webhooks/stripe", response_model=StripeWebhookResponse)
async def receive_stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> StripeWebhookResponse:
    if not stripe_signature:
        raise ProblemException(
            title="Invalid Stripe Webhook",
            detail="Stripe-Signature header is required.",
            status_code=400,
        )
    secret = settings.stripe_webhook_secret.strip()
    if not secret:
        raise ProblemException(
            title="Stripe Webhook Unavailable",
            detail="Stripe webhook handling is temporarily unavailable.",
            status_code=503,
        )
    payload = await request.body()
    try:
        event = construct_event(
            payload=payload,
            stripe_signature_header=stripe_signature,
            secret=secret,
        )
    except Exception as exc:
        raise ProblemException(
            title="Invalid Stripe Webhook",
            detail="Stripe webhook signature verification failed.",
            status_code=400,
        ) from exc
    try:
        result = _stripe_webhooks.process_event(event)
    except BillingWebhookProcessingError as exc:
        raise ProblemException(
            title="Stripe Webhook Unavailable",
            detail=str(exc),
            status_code=503,
        ) from exc
    return StripeWebhookResponse.model_validate(result)
