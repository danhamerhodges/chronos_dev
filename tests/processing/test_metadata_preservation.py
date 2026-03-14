"""Maps to: ENG-015"""

from app.services.output_delivery import resolve_output_encoding


def test_output_encoding_metadata_preserves_frame_rate_color_space_and_source_metadata() -> None:
    metadata = resolve_output_encoding(plan_tier="museum", variant="av1")

    assert metadata["frame_rate"] == "source_preserved"
    assert metadata["color_space"] == "bt709_preserved"
    assert metadata["metadata_preservation"] == {
        "timecode": True,
        "aspect_ratio": True,
        "color_primaries": True,
        "source_filename": True,
    }
