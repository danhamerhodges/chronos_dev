"""Maps to: ENG-011"""

from types import SimpleNamespace

import app.services.job_dispatcher as job_dispatcher
import pytest


def test_pubsub_dispatcher_requires_topic_configuration(monkeypatch) -> None:
    monkeypatch.setattr(
        job_dispatcher,
        "settings",
        SimpleNamespace(job_dispatch_mode="pubsub", job_pubsub_topic=""),
    )

    with pytest.raises(ValueError, match="JOB_PUBSUB_TOPIC is required"):
        job_dispatcher.publish_job("job-1", plan_tier="pro")


def test_pubsub_dispatcher_publishes_message_when_configured(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class StubFuture:
        def result(self, timeout: int) -> None:
            captured["timeout"] = timeout

    class StubPublisherClient:
        def publish(self, topic: str, *, data: bytes, **attributes: str):
            captured["topic"] = topic
            captured["data"] = data.decode("utf-8")
            captured["attributes"] = attributes
            return StubFuture()

    monkeypatch.setattr(
        job_dispatcher,
        "settings",
        SimpleNamespace(job_dispatch_mode="pubsub", job_pubsub_topic="projects/test/topics/chronos-jobs"),
    )
    monkeypatch.setattr(
        job_dispatcher.importlib,
        "import_module",
        lambda name: SimpleNamespace(PublisherClient=StubPublisherClient),
    )

    message = job_dispatcher.publish_job("job-123", plan_tier="museum")

    assert message.job_id == "job-123"
    assert captured["topic"] == "projects/test/topics/chronos-jobs"
    assert '"job_id": "job-123"' in captured["data"]
    assert captured["attributes"]["plan_tier"] == "museum"
    assert captured["timeout"] == 10


def test_dispatch_message_round_trips_through_shared_serializer() -> None:
    message = job_dispatcher.build_dispatch_message(job_id="job-serialize", plan_tier="pro", source="smoke")

    encoded = job_dispatcher.serialize_dispatch_message(message)
    decoded = job_dispatcher.decode_dispatch_message_data(encoded)

    assert decoded["job_id"] == "job-serialize"
    assert decoded["plan_tier"] == "pro"
    assert decoded["source"] == "smoke"


def test_decode_dispatch_message_rejects_non_object_payload() -> None:
    with pytest.raises(ValueError, match="JSON object"):
        job_dispatcher.decode_dispatch_message_data('["not-an-object"]')
