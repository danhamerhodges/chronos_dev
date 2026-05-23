"""Maps to: ENG-011, ENG-012"""

import base64
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.problem_details import ProblemException
from app.main import app
import app.services.job_runtime as job_runtime
import app.services.job_worker as job_worker
from app.services.job_dispatcher import queued_dispatch_messages
from app.services.job_worker import default_trusted_worker_token, run_worker_message
from tests.helpers.auth import fake_auth_header
from tests.helpers.jobs import create_seed_job

client = TestClient(app)


def test_dispatch_queue_and_worker_entrypoint_contract_round_trip() -> None:
    created = create_seed_job(user_id="worker-user")

    queued = queued_dispatch_messages()
    assert len(queued) == 1
    assert queued[0].job_id == created["job_id"]

    run_response = client.post("/v1/testing/jobs/run-dispatcher", headers=fake_auth_header("worker-user"))
    job_response = client.get(f"/v1/jobs/{created['job_id']}", headers=fake_auth_header("worker-user"))

    assert run_response.status_code == 200
    assert run_response.json()["processed_jobs"] == [created["job_id"]]
    assert job_response.status_code == 200
    assert job_response.json()["status"] == "completed"


def test_internal_worker_route_accepts_pubsub_push_envelope() -> None:
    created = create_seed_job(user_id="push-user")
    queued = queued_dispatch_messages()
    envelope = {
        "message": {
            "data": base64.b64encode(
                json.dumps(
                    {
                        "job_id": queued[0].job_id,
                        "plan_tier": queued[0].plan_tier,
                        "source": queued[0].source,
                        "submitted_at": queued[0].submitted_at,
                    }
                ).encode("utf-8")
            ).decode("utf-8"),
            "attributes": {"source": queued[0].source, "plan_tier": queued[0].plan_tier},
        }
    }

    response = client.post(
        "/internal/workers/jobs/run",
        headers={"X-Chronos-Worker-Token": default_trusted_worker_token()},
        json=envelope,
    )
    job_response = client.get(f"/v1/jobs/{created['job_id']}", headers=fake_auth_header("push-user"))

    assert response.status_code == 200
    assert response.json() == {"job_id": created["job_id"], "status": "completed"}
    assert job_response.status_code == 200
    assert job_response.json()["status"] == "completed"


def test_internal_worker_route_rejects_missing_trusted_token() -> None:
    response = client.post("/internal/workers/jobs/run", json={"job_id": "job-1"})

    assert response.status_code == 403
    assert response.json()["title"] == "Forbidden"


def test_internal_runtime_reconcile_endpoint_requires_trusted_token() -> None:
    response = client.post("/internal/ops/runtime/reconcile", json={"queue_depth": 12})

    assert response.status_code == 403
    assert response.json()["title"] == "Forbidden"


def test_worker_entrypoint_requires_trusted_token() -> None:
    with pytest.raises(ProblemException) as exc_info:
        run_worker_message({"job_id": "job-1"}, trusted_token="invalid-token")
    assert exc_info.value.detail == "Trusted worker token is required for background job execution."


def test_process_job_requires_trusted_token_at_runtime_boundary() -> None:
    with pytest.raises(ProblemException) as exc_info:
        job_runtime.process_job("job-1")
    assert exc_info.value.detail == "Trusted worker token is required for background job execution."


def test_dispatcher_requeues_message_when_worker_execution_fails(monkeypatch) -> None:
    created = create_seed_job(user_id="requeue-user")

    def broken_worker(message: dict[str, object], *, trusted_token: str | None = None):
        del message, trusted_token
        raise RuntimeError("worker down")

    monkeypatch.setattr(job_runtime, "run_worker_message", broken_worker)

    with pytest.raises(RuntimeError, match="worker down"):
        job_runtime.drain_job_queue()

    queued = queued_dispatch_messages()
    assert len(queued) == 1
    assert queued[0].job_id == created["job_id"]


def test_supabase_progress_mode_fails_fast_until_trusted_publisher_exists(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class StubSupabaseClient:
        def broadcast_realtime_service_role(self, *, topic: str, event: str, payload: dict[str, object]) -> None:
            captured["topic"] = topic
            captured["event"] = event
            captured["payload"] = payload

    monkeypatch.setattr(
        job_worker,
        "settings",
        SimpleNamespace(job_progress_mode="supabase", job_worker_trusted_token="", environment="test"),
    )
    monkeypatch.setattr(job_worker, "SupabaseClient", StubSupabaseClient)

    job_worker.publish_progress_event(
        trusted_token=default_trusted_worker_token(),
        payload={"job_id": "job-1", "channel": "job_progress:job-1", "event": "progress_update"},
    )

    assert captured["topic"] == "job_progress:job-1"
    assert captured["event"] == "progress_update"


def test_supabase_progress_mode_propagates_missing_service_role_config(monkeypatch) -> None:
    class StubSupabaseClient:
        def broadcast_realtime_service_role(self, *, topic: str, event: str, payload: dict[str, object]) -> None:
            del topic, event, payload
            raise ValueError("Supabase service role configuration is required")

    monkeypatch.setattr(
        job_worker,
        "settings",
        SimpleNamespace(job_progress_mode="supabase", job_worker_trusted_token="", environment="test"),
    )
    monkeypatch.setattr(job_worker, "SupabaseClient", StubSupabaseClient)

    with pytest.raises(ValueError, match="Supabase service role configuration is required"):
        job_worker.publish_progress_event(
            trusted_token=default_trusted_worker_token(),
            payload={"job_id": "job-1", "channel": "job_progress:job-1", "event": "progress_update"},
        )
