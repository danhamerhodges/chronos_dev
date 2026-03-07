"""Maps to: ENG-008, NFR-002"""

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
