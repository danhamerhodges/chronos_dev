"""Dispatcher abstraction for async job execution."""

from __future__ import annotations

import importlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from app.config import settings
from app.observability.monitoring import record_job_runtime_event


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class DispatchMessage:
    job_id: str
    plan_tier: str
    source: str
    submitted_at: str


class JobDispatcher(Protocol):
    def publish(self, message: DispatchMessage) -> None: ...


_PLAN_PRIORITY = {"museum": 0, "pro": 1, "hobbyist": 2}
_MEMORY_QUEUE: list[tuple[int, int, DispatchMessage]] = []
_QUEUE_SEQUENCE = 0


class InMemoryJobDispatcher:
    def publish(self, message: DispatchMessage) -> None:
        global _QUEUE_SEQUENCE
        _MEMORY_QUEUE.append((_PLAN_PRIORITY.get(message.plan_tier.lower(), 99), _QUEUE_SEQUENCE, message))
        _QUEUE_SEQUENCE += 1
        _MEMORY_QUEUE.sort()
        record_job_runtime_event("dispatch_enqueued")


class PubSubJobDispatcher:
    def publish(self, message: DispatchMessage) -> None:
        if not settings.job_pubsub_topic:
            raise ValueError("JOB_PUBSUB_TOPIC is required when JOB_DISPATCH_MODE=pubsub.")
        try:
            pubsub_v1 = importlib.import_module("google.cloud.pubsub_v1")
        except ImportError as exc:  # pragma: no cover - dependency gated
            raise RuntimeError("google-cloud-pubsub must be installed for Pub/Sub dispatch mode.") from exc

        publisher = pubsub_v1.PublisherClient()
        future = publisher.publish(
            settings.job_pubsub_topic,
            data=serialize_dispatch_message(message),
            source=message.source,
            plan_tier=message.plan_tier,
            job_id=message.job_id,
        )
        future.result(timeout=10)
        record_job_runtime_event("dispatch_published")


def serialize_dispatch_message(message: DispatchMessage) -> bytes:
    return json.dumps(asdict(message)).encode("utf-8")


def decode_dispatch_message_data(data: bytes | str) -> dict[str, Any]:
    raw_data = data.encode("utf-8") if isinstance(data, str) else data
    try:
        decoded = json.loads(raw_data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Dispatch message payload could not be decoded as JSON.") from exc
    if not isinstance(decoded, dict):
        raise ValueError("Dispatch message payload must decode to a JSON object.")
    return decoded


def build_dispatch_message(*, job_id: str, plan_tier: str, source: str = "api") -> DispatchMessage:
    return DispatchMessage(
        job_id=job_id,
        plan_tier=plan_tier,
        source=source,
        submitted_at=_utc_now(),
    )


def get_job_dispatcher() -> JobDispatcher:
    if settings.job_dispatch_mode.lower() == "pubsub":
        return PubSubJobDispatcher()
    return InMemoryJobDispatcher()


def publish_job(job_id: str, *, plan_tier: str, source: str = "api") -> DispatchMessage:
    message = build_dispatch_message(job_id=job_id, plan_tier=plan_tier, source=source)
    get_job_dispatcher().publish(message)
    return message


def reset_job_dispatcher_state() -> None:
    global _QUEUE_SEQUENCE
    _MEMORY_QUEUE.clear()
    _QUEUE_SEQUENCE = 0


def queued_dispatch_messages() -> list[DispatchMessage]:
    return [item[2] for item in _MEMORY_QUEUE]


def pop_next_dispatch_message() -> DispatchMessage | None:
    if not _MEMORY_QUEUE:
        return None
    _, _, message = _MEMORY_QUEUE.pop(0)
    return message


def requeue_dispatch_message(message: DispatchMessage) -> None:
    global _QUEUE_SEQUENCE
    _MEMORY_QUEUE.append((_PLAN_PRIORITY.get(message.plan_tier.lower(), 99), _QUEUE_SEQUENCE, message))
    _QUEUE_SEQUENCE += 1
    _MEMORY_QUEUE.sort()
    record_job_runtime_event("dispatch_requeued")
