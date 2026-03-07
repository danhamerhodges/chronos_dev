"""Maps to: ENG-003"""

import pytest

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


def test_pipeline_rejects_non_positive_durations() -> None:
    with pytest.raises(ValueError, match="estimated_duration_seconds must be >= 1"):
        build_segments(
            user_id="pipeline-user",
            source_asset_checksum="abc12345def67890",
            estimated_duration_seconds=0,
            fidelity_tier="Restore",
            processing_mode="balanced",
            era_profile={"capture_medium": "film_scan"},
            config={"stabilization": "medium"},
        )


def test_pipeline_rounds_fractional_durations_up_to_cover_trailing_media() -> None:
    segments = build_segments(
        user_id="pipeline-user",
        source_asset_checksum="abc12345def67890",
        estimated_duration_seconds=10.2,
        fidelity_tier="Restore",
        processing_mode="balanced",
        era_profile={"capture_medium": "film_scan"},
        config={"stabilization": "medium"},
    )

    assert len(segments) == 2
    assert segments[-1]["segment_end_seconds"] == 11


def test_pipeline_idempotency_seed_is_unambiguous_when_fields_contain_delimiters() -> None:
    baseline = build_segments(
        user_id="user|a",
        source_asset_checksum="checksum-b",
        estimated_duration_seconds=10,
        fidelity_tier="Restore",
        reproducibility_mode="deterministic",
        processing_mode="balanced",
        era_profile={"capture_medium": "film_scan"},
        effective_fidelity_profile={"tier": "Restore", "thresholds": {}},
        config={"stabilization": "medium"},
    )
    shifted = build_segments(
        user_id="user",
        source_asset_checksum="a|checksum-b",
        estimated_duration_seconds=10,
        fidelity_tier="Restore",
        reproducibility_mode="deterministic",
        processing_mode="balanced",
        era_profile={"capture_medium": "film_scan"},
        effective_fidelity_profile={"tier": "Restore", "thresholds": {}},
        config={"stabilization": "medium"},
    )

    assert baseline[0]["idempotency_key"] != shifted[0]["idempotency_key"]
