"""Maps to: ENG-003"""

from app.services.job_pipeline import build_segments


def test_pipeline_builds_deterministic_ten_second_segments() -> None:
    segments = build_segments(
        user_id="pipeline-user",
        source_asset_checksum="abc12345def67890",
        estimated_duration_seconds=27,
        fidelity_tier="Restore",
        processing_mode="balanced",
        era_profile={"capture_medium": "film_scan"},
        config={"stabilization": "medium"},
    )

    assert [segment["segment_start_seconds"] for segment in segments] == [0, 10, 20]
    assert [segment["segment_end_seconds"] for segment in segments] == [10, 20, 27]
    assert [segment["segment_duration_seconds"] for segment in segments] == [10, 10, 7]


def test_pipeline_idempotency_key_changes_with_user_boundary() -> None:
    baseline = build_segments(
        user_id="user-a",
        source_asset_checksum="abc12345def67890",
        estimated_duration_seconds=20,
        fidelity_tier="Restore",
        processing_mode="balanced",
        era_profile={"capture_medium": "film_scan"},
        config={"stabilization": "medium"},
    )
    other_user = build_segments(
        user_id="user-b",
        source_asset_checksum="abc12345def67890",
        estimated_duration_seconds=20,
        fidelity_tier="Restore",
        processing_mode="balanced",
        era_profile={"capture_medium": "film_scan"},
        config={"stabilization": "medium"},
    )

    assert baseline[0]["idempotency_key"] != other_user[0]["idempotency_key"]
