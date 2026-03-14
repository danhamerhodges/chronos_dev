"""Maps to: ENG-015"""

from app.services.output_delivery import resolve_output_encoding


def test_output_encoding_resolver_matches_plan_tier_targets() -> None:
    hobbyist = resolve_output_encoding(plan_tier="hobbyist", variant="av1")
    pro = resolve_output_encoding(plan_tier="pro", variant="av1")
    museum = resolve_output_encoding(plan_tier="museum", variant="av1")

    assert hobbyist["bitrate_mbps"] == 8
    assert hobbyist["resolution_target"] == "1080p"
    assert pro["bitrate_mbps"] == 16
    assert pro["resolution_target"] == "4K"
    assert museum["bitrate_mbps"] == 32
    assert museum["resolution_target"] == "native_scan"


def test_output_encoding_resolver_keeps_compatibility_variant_available_for_all_tiers() -> None:
    for tier in ("hobbyist", "pro", "museum"):
        assert resolve_output_encoding(plan_tier=tier, variant="h264")["codec"] == "h264"
