"""Maps to: ENG-008, NFR-002, NFR-003"""

from datetime import datetime, timedelta, timezone

from app.config import settings
from app.db.phase2_store import RuntimeOpsRepository
from app.services.runtime_ops import (
    AUTOSCALER_IDLE_CLEANUP_GRACE_SECONDS,
    autoscaler_idle_scale_down_healthy,
    reconcile_gpu_pool,
)


def test_autoscaler_maintains_minimum_warm_pool() -> None:
    snapshot = reconcile_gpu_pool(queue_depth=0, queue_age_seconds=0.0)

    assert snapshot["desired_warm_instances"] >= 1
    assert snapshot["active_warm_instances"] >= snapshot["desired_warm_instances"]


def test_autoscaler_scales_up_with_queue_depth_pressure() -> None:
    snapshot = reconcile_gpu_pool(queue_depth=25, queue_age_seconds=30.0)

    assert snapshot["desired_warm_instances"] >= 2
    assert snapshot["active_warm_instances"] >= snapshot["desired_warm_instances"]


def test_idle_scale_down_health_tolerates_just_expired_extra_idle_leases() -> None:
    repo = RuntimeOpsRepository()
    now = datetime.now(timezone.utc)
    repo.upsert_gpu_lease(
        worker_id="warm-keep",
        payload={
            "gpu_type": "L4",
            "lease_state": "idle",
            "is_warm": True,
            "current_job_id": None,
            "queue_depth_snapshot": 0,
            "metadata": {"desired_warm_instances": settings.gpu_pool_min_warm_instances},
            "allocated_at": None,
            "released_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=settings.gpu_pool_idle_timeout_seconds)).isoformat(),
        },
    )
    repo.upsert_gpu_lease(
        worker_id="warm-extra-expired",
        payload={
            "gpu_type": "L4",
            "lease_state": "idle",
            "is_warm": True,
            "current_job_id": None,
            "queue_depth_snapshot": 0,
            "metadata": {"desired_warm_instances": settings.gpu_pool_min_warm_instances},
            "allocated_at": None,
            "released_at": (now - timedelta(seconds=settings.gpu_pool_idle_timeout_seconds + 5)).isoformat(),
            "expires_at": (now - timedelta(seconds=5)).isoformat(),
        },
    )

    assert autoscaler_idle_scale_down_healthy(
        {
            "queue_depth": 0,
            "desired_warm_instances": settings.gpu_pool_min_warm_instances,
            "active_warm_instances": 2,
        }
    ) is True


def test_idle_scale_down_health_is_false_after_cleanup_grace_for_expired_extra_idle_leases() -> None:
    repo = RuntimeOpsRepository()
    now = datetime.now(timezone.utc)
    repo.upsert_gpu_lease(
        worker_id="warm-keep",
        payload={
            "gpu_type": "L4",
            "lease_state": "idle",
            "is_warm": True,
            "current_job_id": None,
            "queue_depth_snapshot": 0,
            "metadata": {"desired_warm_instances": settings.gpu_pool_min_warm_instances},
            "allocated_at": None,
            "released_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=settings.gpu_pool_idle_timeout_seconds)).isoformat(),
        },
    )
    repo.upsert_gpu_lease(
        worker_id="warm-extra-expired",
        payload={
            "gpu_type": "L4",
            "lease_state": "idle",
            "is_warm": True,
            "current_job_id": None,
            "queue_depth_snapshot": 0,
            "metadata": {"desired_warm_instances": settings.gpu_pool_min_warm_instances},
            "allocated_at": None,
            "released_at": (
                now - timedelta(seconds=settings.gpu_pool_idle_timeout_seconds + AUTOSCALER_IDLE_CLEANUP_GRACE_SECONDS)
            ).isoformat(),
            "expires_at": (now - timedelta(seconds=AUTOSCALER_IDLE_CLEANUP_GRACE_SECONDS + 15)).isoformat(),
        },
    )

    assert autoscaler_idle_scale_down_healthy(
        {
            "queue_depth": 0,
            "desired_warm_instances": settings.gpu_pool_min_warm_instances,
            "active_warm_instances": 2,
        }
    ) is False


def test_idle_scale_down_health_is_true_when_queue_pressure_requires_capacity() -> None:
    assert autoscaler_idle_scale_down_healthy(
        {
            "queue_depth": 5,
            "desired_warm_instances": 2,
            "active_warm_instances": 2,
        }
    ) is True
