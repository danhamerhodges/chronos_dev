"""Maps to: ENG-015"""

from app.services.output_delivery import resolve_output_encoding


def test_av1_variant_is_the_default_primary_export_codec() -> None:
    metadata = resolve_output_encoding(plan_tier="pro", variant="av1")

    assert metadata["variant"] == "av1"
    assert metadata["codec"] == "av1"
    assert metadata["container"] == "mp4"
