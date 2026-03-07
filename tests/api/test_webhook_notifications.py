"""Maps to: ENG-011"""

from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

import app.services.job_runtime as job_runtime
from app.db.phase2_store import WebhookSubscriptionRepository
from app.main import app
from tests.helpers.auth import fake_auth_header
from tests.helpers.jobs import run_all_jobs, valid_job_request

client = TestClient(app)


def test_webhook_notifications_fire_for_started_and_completed_events() -> None:
    WebhookSubscriptionRepository().upsert(
        owner_user_id="webhook-user",
        webhook_url="https://hooks.example.test/jobs",
        event_types=["started", "completed"],
    )
    created = client.post("/v1/jobs", headers=fake_auth_header("webhook-user"), json=valid_job_request()).json()

    run_all_jobs()
    deliveries = job_runtime.webhook_deliveries_for_job(created["job_id"])

    assert [item["event_type"] for item in deliveries] == ["started", "completed"]
    assert all(item["status"] == "delivered" for item in deliveries)


def test_webhook_delivery_retries_up_to_three_attempts(monkeypatch) -> None:
    attempts = {"count": 0}

    def flaky_sender(url: str, payload: dict[str, object]) -> None:
        del url, payload
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("temporary webhook failure")

    monkeypatch.setattr(job_runtime, "_send_webhook_request", flaky_sender)
    WebhookSubscriptionRepository().upsert(
        owner_user_id="retry-webhook-user",
        webhook_url="https://hooks.example.test/retry",
        event_types=["started"],
    )
    created = client.post(
        "/v1/jobs",
        headers=fake_auth_header("retry-webhook-user"),
        json=valid_job_request(),
    ).json()

    run_all_jobs()
    deliveries = [item for item in job_runtime.webhook_deliveries_for_job(created["job_id"]) if item["event_type"] == "started"]

    assert [item["status"] for item in deliveries] == ["retrying", "retrying", "delivered"]
    assert [item["attempt"] for item in deliveries] == [1, 2, 3]


def test_completion_webhook_payload_includes_packet_3b_fields(monkeypatch) -> None:
    captured: list[dict[str, object]] = []

    def capture_sender(url: str, payload: dict[str, object]) -> None:
        del url
        captured.append(payload)

    monkeypatch.setattr(job_runtime, "_send_webhook_request", capture_sender)
    WebhookSubscriptionRepository().upsert(
        owner_user_id="packet-3b-webhook-user",
        webhook_url="https://hooks.example.test/packet3b",
        event_types=["completed"],
    )
    created = client.post(
        "/v1/jobs",
        headers=fake_auth_header("packet-3b-webhook-user", tier="pro"),
        json=valid_job_request(),
    ).json()

    run_all_jobs()

    completed_payload = next(item for item in captured if item["job_id"] == created["job_id"])
    assert completed_payload["effective_fidelity_tier"] == "Restore"
    assert completed_payload["performance_summary"]["total_ms"] is not None
    assert completed_payload["quality_summary"]["thresholds_met"] is True
    assert completed_payload["cache_summary"]["hit_rate"] >= 0.0
    assert completed_payload["gpu_summary"]["gpu_type"] == "L4"
    assert completed_payload["cost_summary"]["gpu_seconds"] >= 0
    assert completed_payload["slo_summary"]["target_total_ms"] == 54000
    assert completed_payload["reproducibility_mode"] == "perceptual_equivalence"
    assert completed_payload["manifest_available"] is True


def test_webhook_sender_rejects_private_targets(monkeypatch) -> None:
    monkeypatch.setattr(job_runtime, "settings", SimpleNamespace(environment="staging"))
    monkeypatch.setattr(
        job_runtime.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(job_runtime.socket.AF_INET, job_runtime.socket.SOCK_STREAM, 0, "", ("127.0.0.1", 443))],
    )

    with pytest.raises(RuntimeError, match="non-public address"):
        job_runtime._send_webhook_request("https://hooks.example.test/jobs", {"job_id": "job-1"})


def test_webhook_sender_rejects_redirect_targets(monkeypatch) -> None:
    monkeypatch.setattr(job_runtime, "settings", SimpleNamespace(environment="staging"))
    monkeypatch.setattr(
        job_runtime.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(job_runtime.socket.AF_INET, job_runtime.socket.SOCK_STREAM, 0, "", ("93.184.216.34", 443))],
    )

    class RedirectClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def post(self, url: str, json: dict[str, object]) -> httpx.Response:
            request = httpx.Request("POST", url, json=json)
            return httpx.Response(302, headers={"Location": "https://example.net/redirect"}, request=request)

    monkeypatch.setattr(job_runtime.httpx, "Client", RedirectClient)

    with pytest.raises(RuntimeError, match="redirects are not allowed"):
        job_runtime._send_webhook_request("https://hooks.example.test/jobs", {"job_id": "job-1"})
