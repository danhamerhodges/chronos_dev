"""Maps to: ENG-011, ENG-012"""

from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.services.job_runtime as job_runtime
from app.main import app
from tests.helpers.auth import fake_auth_header
from tests.helpers.jobs import run_all_jobs, valid_job_request

client = TestClient(app)


def test_job_lifecycle_transitions_from_queued_to_completed() -> None:
    created = client.post("/v1/jobs", headers=fake_auth_header("lifecycle-user"), json=valid_job_request()).json()

    assert created["status"] == "queued"

    run_all_jobs()
    response = client.get(f"/v1/jobs/{created['job_id']}", headers=fake_auth_header("lifecycle-user"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["manifest_available"] is True
    assert payload["performance_summary"]["total_ms"] is not None
    assert payload["quality_summary"]["thresholds_met"] is True
    assert payload["cache_summary"]["hits"] >= 0
    assert payload["gpu_summary"]["gpu_type"] == "L4"
    assert payload["cost_summary"]["gpu_seconds"] >= 0
    assert payload["slo_summary"]["compliant"] in {True, False}
    assert payload["progress"]["percent_complete"] == 100.0
    assert payload["result_uri"].endswith("/result.mp4")


def test_job_cancellation_is_cooperatively_applied() -> None:
    created = client.post("/v1/jobs", headers=fake_auth_header("cancel-user"), json=valid_job_request()).json()

    cancel = client.delete(f"/v1/jobs/{created['job_id']}", headers=fake_auth_header("cancel-user"))
    run_all_jobs()
    response = client.get(f"/v1/jobs/{created['job_id']}", headers=fake_auth_header("cancel-user"))

    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancel_requested"
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_process_job_releases_gpu_on_cancellation_after_allocation(monkeypatch) -> None:
    class StubRepo:
        def __init__(self) -> None:
            self.calls = 0
            self.job = {
                "job_id": "job-cancel-after-allocate",
                "status": "queued",
                "started_at": None,
                "updated_at": "2026-03-07T00:00:00+00:00",
                "segment_count": 1,
                "progress_percent": 0.0,
                "eta_seconds": 0,
                "owner_user_id": "cancel-user",
                "plan_tier": "pro",
                "fidelity_tier": "Restore",
                "current_operation": "Queued",
                "stage_timings": {},
            }

        def get_job_for_worker(self, job_id: str) -> dict[str, object]:
            del job_id
            self.calls += 1
            if self.calls >= 2:
                return {**self.job, "status": "cancel_requested"}
            return dict(self.job)

        def update_job_for_worker(self, job_id: str, *, patch: dict[str, object]) -> dict[str, object]:
            del job_id
            self.job.update(patch)
            self.job["updated_at"] = "2026-03-07T00:00:01+00:00"
            return dict(self.job)

        def list_segments(self, job_id: str) -> list[dict[str, object]]:
            del job_id
            return [{"segment_index": 0, "segment_duration_seconds": 10, "status": "queued", "cache_status": "miss"}]

    repo = StubRepo()
    released: list[tuple[str, int]] = []

    monkeypatch.setattr(job_runtime, "JobRepository", lambda: repo)
    monkeypatch.setattr(job_runtime, "authorize_trusted_worker", lambda token: "trusted")
    monkeypatch.setattr(
        job_runtime,
        "allocate_gpu",
        lambda job: {
            "gpu_type": "L4",
            "warm_start": False,
            "allocation_latency_ms": 1,
            "queue_wait_ms": 0,
            "gpu_runtime_seconds": 0,
            "desired_warm_instances": 1,
            "active_warm_instances": 1,
            "busy_instances": 1,
            "utilization_percent": 100.0,
            "worker_id": "worker-1",
        },
    )
    monkeypatch.setattr(job_runtime, "release_gpu", lambda job_id, gpu_runtime_seconds: released.append((job_id, gpu_runtime_seconds)) or {})
    monkeypatch.setattr(job_runtime, "_publish_progress", lambda *args, **kwargs: None)
    monkeypatch.setattr(job_runtime, "_deliver_webhooks", lambda *args, **kwargs: None)
    monkeypatch.setattr(job_runtime, "BillingService", lambda: SimpleNamespace(consume_minutes=lambda **kwargs: None))

    result = job_runtime.process_job("job-cancel-after-allocate", trusted_token="trusted")

    assert result is not None
    assert result["status"] == "cancelled"
    assert released == [("job-cancel-after-allocate", 0)]


def test_process_job_releases_gpu_on_exception_before_finalize(monkeypatch) -> None:
    class StubRepo:
        def __init__(self) -> None:
            self.job = {
                "job_id": "job-fail-after-allocate",
                "status": "queued",
                "started_at": None,
                "updated_at": "2026-03-07T00:00:00+00:00",
                "segment_count": 1,
                "progress_percent": 0.0,
                "eta_seconds": 0,
                "owner_user_id": "failure-user",
                "plan_tier": "pro",
                "fidelity_tier": "Restore",
                "current_operation": "Queued",
                "stage_timings": {},
            }

        def get_job_for_worker(self, job_id: str) -> dict[str, object]:
            del job_id
            return dict(self.job)

        def update_job_for_worker(self, job_id: str, *, patch: dict[str, object]) -> dict[str, object]:
            del job_id
            self.job.update(patch)
            self.job["updated_at"] = "2026-03-07T00:00:01+00:00"
            return dict(self.job)

        def list_segments(self, job_id: str) -> list[dict[str, object]]:
            del job_id
            return [{"segment_index": 0, "segment_duration_seconds": 10, "status": "queued", "cache_status": "miss"}]

    repo = StubRepo()
    released: list[tuple[str, int]] = []

    monkeypatch.setattr(job_runtime, "JobRepository", lambda: repo)
    monkeypatch.setattr(job_runtime, "authorize_trusted_worker", lambda token: "trusted")
    monkeypatch.setattr(
        job_runtime,
        "allocate_gpu",
        lambda job: {
            "gpu_type": "L4",
            "warm_start": False,
            "allocation_latency_ms": 1,
            "queue_wait_ms": 0,
            "gpu_runtime_seconds": 0,
            "desired_warm_instances": 1,
            "active_warm_instances": 1,
            "busy_instances": 1,
            "utilization_percent": 100.0,
            "worker_id": "worker-1",
        },
    )
    monkeypatch.setattr(job_runtime, "release_gpu", lambda job_id, gpu_runtime_seconds: released.append((job_id, gpu_runtime_seconds)) or {})
    monkeypatch.setattr(job_runtime, "_process_segment", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(job_runtime, "_publish_progress", lambda *args, **kwargs: None)
    monkeypatch.setattr(job_runtime, "_deliver_webhooks", lambda *args, **kwargs: None)
    monkeypatch.setattr(job_runtime, "BillingService", lambda: SimpleNamespace(consume_minutes=lambda **kwargs: None))

    result = job_runtime.process_job("job-fail-after-allocate", trusted_token="trusted")

    assert result is not None
    assert result["status"] == "failed"
    assert released == [("job-fail-after-allocate", 0)]
