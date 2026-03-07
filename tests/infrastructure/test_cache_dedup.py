"""Maps to: ENG-009, NFR-002"""

from app.services.runtime_ops import build_segment_cache_key, lookup_segment_cache, store_segment_cache


def test_segment_cache_hits_for_same_user_and_namespace() -> None:
    job = {
        "owner_user_id": "cache-user",
        "source_asset_checksum": "checksum-1234",
        "reproducibility_mode": "deterministic",
    }
    segment = {
        "segment_index": 0,
        "segment_start_seconds": 0,
        "segment_end_seconds": 10,
    }
    profile = {"tier": "Restore", "thresholds": {}}
    cache_key = build_segment_cache_key(
        user_id="cache-user",
        source_asset_checksum="checksum-1234",
        segment=segment,
        effective_fidelity_profile=profile,
        reproducibility_mode="deterministic",
        version_namespace="restore:v1",
    )
    store_segment_cache(
        cache_key=cache_key,
        payload={"output_uri": "gs://chronos/jobs/cache-user/segment-0.mp4", "quality_metrics": {}, "reproducibility_proof": {}},
    )

    record, state = lookup_segment_cache(
        job=job,
        segment=segment,
        effective_fidelity_profile=profile,
        version_namespace="restore:v1",
    )

    assert record is not None
    assert state["cache_status"] == "hit"


def test_segment_cache_is_per_user() -> None:
    profile = {"tier": "Restore", "thresholds": {}}
    segment = {
        "segment_index": 0,
        "segment_start_seconds": 0,
        "segment_end_seconds": 10,
    }
    record, state = lookup_segment_cache(
        job={"owner_user_id": "other-user", "source_asset_checksum": "checksum-1234", "reproducibility_mode": "deterministic"},
        segment=segment,
        effective_fidelity_profile=profile,
        version_namespace="restore:v1",
    )

    assert record is None
    assert state["cache_status"] in {"miss", "bypass"}


def test_segment_cache_store_degrades_instead_of_raising_when_backend_is_unavailable(monkeypatch) -> None:
    class BrokenBackend:
        def setex(self, *args, **kwargs) -> None:
            raise ConnectionError("redis unavailable")

    monkeypatch.setattr("app.services.runtime_ops._segment_cache_backend", lambda: BrokenBackend())

    result = store_segment_cache(cache_key="chronos:test", payload={"output_uri": "gs://chronos/jobs/cache-user/segment-0.mp4"})

    assert result["cache_status"] == "bypass"
    assert result["degraded"] is True
