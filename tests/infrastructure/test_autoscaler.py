"""Maps to: ENG-008, NFR-002"""

from app.services.runtime_ops import reconcile_gpu_pool


def test_autoscaler_maintains_minimum_warm_pool() -> None:
    snapshot = reconcile_gpu_pool(queue_depth=0, queue_age_seconds=0.0)

    assert snapshot["desired_warm_instances"] >= 1
    assert snapshot["active_warm_instances"] >= snapshot["desired_warm_instances"]


def test_autoscaler_scales_up_with_queue_depth_pressure() -> None:
    snapshot = reconcile_gpu_pool(queue_depth=25, queue_age_seconds=30.0)

    assert snapshot["desired_warm_instances"] >= 2
    assert snapshot["active_warm_instances"] >= snapshot["desired_warm_instances"]

