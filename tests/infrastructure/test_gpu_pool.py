"""Maps to: ENG-008, NFR-002"""

import pytest

import app.services.runtime_ops as runtime_ops
from app.services.runtime_ops import allocate_gpu, current_runtime_snapshot, release_gpu


def test_gpu_pool_allocates_l4_for_default_tiers() -> None:
    summary = allocate_gpu(
        {
            "job_id": "job-gpu-l4",
            "plan_tier": "pro",
            "estimated_duration_seconds": 27,
            "queued_at": "2026-03-07T00:00:00+00:00",
        }
    )

    assert summary["gpu_type"] == "L4"
    assert summary["allocation_latency_ms"] is not None


def test_gpu_pool_maps_museum_tier_to_rtx_6000_and_releases_back_to_pool() -> None:
    summary = allocate_gpu(
        {
            "job_id": "job-gpu-museum",
            "plan_tier": "museum",
            "estimated_duration_seconds": 27,
            "queued_at": "2026-03-07T00:00:00+00:00",
        }
    )
    snapshot = release_gpu("job-gpu-museum", gpu_runtime_seconds=20)
    runtime = current_runtime_snapshot()

    assert summary["gpu_type"] == "RTX 6000"
    assert snapshot["active_warm_instances"] >= 1
    assert runtime["active_warm_instances"] >= 1


def test_runtime_snapshot_exposes_alert_evaluator_fields() -> None:
    allocate_gpu(
        {
            "job_id": "job-gpu-snapshot",
            "plan_tier": "pro",
            "estimated_duration_seconds": 27,
            "queued_at": "2026-03-07T00:00:00+00:00",
        }
    )

    runtime = current_runtime_snapshot()

    assert "queue_depth" in runtime
    assert "queue_age_seconds" in runtime
    assert "utilization_percent" in runtime


def test_runtime_snapshot_and_reconcile_exclude_cold_leases_from_warm_pool_accounting(monkeypatch) -> None:
    leases = [
        {
            "worker_id": "warm-1",
            "lease_state": "idle",
            "is_warm": True,
            "queue_depth_snapshot": 3,
        },
        {
            "worker_id": "cold-1",
            "lease_state": "busy",
            "is_warm": False,
            "queue_depth_snapshot": 9,
        },
    ]

    class StubRepo:
        def list_gpu_leases(self) -> list[dict[str, object]]:
            return list(leases)

        def queued_job_backlog_count(self) -> int:
            return 1

        def list_incidents(self) -> list[dict[str, object]]:
            return []

        def upsert_gpu_lease(self, worker_id: str, payload: dict[str, object]) -> dict[str, object]:
            record = {"worker_id": worker_id, **payload}
            for index, lease in enumerate(leases):
                if lease["worker_id"] == worker_id:
                    leases[index] = record
                    break
            else:
                leases.append(record)
            return dict(record)

        def delete_gpu_lease(self, worker_id: str) -> None:
            raise AssertionError(f"unexpected delete for {worker_id}")

    monkeypatch.setattr(runtime_ops, "RuntimeOpsRepository", lambda: StubRepo())

    reconcile = runtime_ops.reconcile_gpu_pool(queue_depth=0, queue_age_seconds=0.0)
    snapshot = runtime_ops.current_runtime_snapshot()

    assert reconcile["active_warm_instances"] == 1
    assert reconcile["busy_instances"] == 0
    assert snapshot["active_warm_instances"] == 1
    assert snapshot["busy_instances"] == 0
    assert snapshot["queue_depth"] == 0


def test_allocate_gpu_uses_runnable_backlog_depth_instead_of_single_job_segment_count(monkeypatch) -> None:
    queue_depths: list[int] = []

    class StubRepo:
        def queued_job_backlog_count(self) -> int:
            return 2

        def list_gpu_leases(self) -> list[dict[str, object]]:
            return []

        def upsert_gpu_lease(self, worker_id: str, payload: dict[str, object]) -> dict[str, object]:
            return {"worker_id": worker_id, **payload}

        def delete_gpu_lease(self, worker_id: str) -> None:
            raise AssertionError(f"unexpected delete for {worker_id}")

    def fake_reconcile_gpu_pool(*, queue_depth: int, queue_age_seconds: float = 0.0) -> dict[str, object]:
        queue_depths.append(queue_depth)
        return {
            "queue_depth": queue_depth,
            "queue_age_seconds": queue_age_seconds,
            "desired_warm_instances": 1,
            "active_warm_instances": 1,
            "busy_instances": 0,
            "idle_instances": 1,
            "utilization_percent": 0.0,
        }

    monkeypatch.setattr(runtime_ops, "RuntimeOpsRepository", lambda: StubRepo())
    monkeypatch.setattr(runtime_ops, "reconcile_gpu_pool", fake_reconcile_gpu_pool)
    monkeypatch.setattr(runtime_ops, "record_gpu_allocation", lambda **kwargs: None)

    summary = allocate_gpu(
        {
            "job_id": "job-backlog-depth",
            "plan_tier": "pro",
            "segment_count": 99,
            "estimated_duration_seconds": 27,
            "queued_at": "2026-03-07T00:00:00+00:00",
        }
    )

    assert summary["worker_id"].startswith("cold-")
    assert queue_depths == [2, 2]


def test_allocate_gpu_rolls_back_busy_lease_when_post_allocation_bookkeeping_fails(monkeypatch) -> None:
    leases = {
        "warm-1": {
            "worker_id": "warm-1",
            "gpu_type": "L4",
            "lease_state": "idle",
            "is_warm": True,
            "current_job_id": None,
            "queue_depth_snapshot": 1,
            "metadata": {"queue_age_seconds": 0.0, "desired_warm_instances": 1},
            "allocated_at": None,
            "released_at": None,
            "expires_at": None,
        }
    }

    class StubRepo:
        def queued_job_backlog_count(self) -> int:
            return 1

        def list_gpu_leases(self) -> list[dict[str, object]]:
            return [dict(item) for item in leases.values()]

        def upsert_gpu_lease(self, worker_id: str, payload: dict[str, object]) -> dict[str, object]:
            record = {"worker_id": worker_id, **payload}
            leases[worker_id] = record
            return dict(record)

        def delete_gpu_lease(self, worker_id: str) -> None:
            leases.pop(worker_id, None)

    monkeypatch.setattr(runtime_ops, "RuntimeOpsRepository", lambda: StubRepo())
    monkeypatch.setattr(runtime_ops, "record_gpu_allocation", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))

    with pytest.raises(RuntimeError, match="boom"):
        allocate_gpu(
            {
                "job_id": "job-allocation-rollback",
                "plan_tier": "pro",
                "estimated_duration_seconds": 27,
                "queued_at": "2026-03-07T00:00:00+00:00",
            }
        )

    assert leases["warm-1"]["lease_state"] == "idle"
    assert leases["warm-1"]["current_job_id"] is None


def test_current_runtime_snapshot_uses_live_lease_metadata_for_desired_warm_and_queue_age(monkeypatch) -> None:
    leases = [
        {
            "worker_id": "warm-1",
            "lease_state": "busy",
            "is_warm": True,
            "queue_depth_snapshot": 6,
            "metadata": {"desired_warm_instances": 4, "queue_age_seconds": 12.5},
        }
    ]

    class StubRepo:
        def list_gpu_leases(self) -> list[dict[str, object]]:
            return list(leases)

        def list_incidents(self) -> list[dict[str, object]]:
            return []

    monkeypatch.setattr(runtime_ops, "RuntimeOpsRepository", lambda: StubRepo())

    snapshot = current_runtime_snapshot()

    assert snapshot["desired_warm_instances"] == 4
    assert snapshot["queue_age_seconds"] == 12.5
    assert snapshot["queue_depth"] == 6
