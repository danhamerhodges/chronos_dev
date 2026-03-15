"""Maps to: ENG-014"""

from __future__ import annotations

from app.services.preview_generation import PreviewGenerationService


def test_scene_aware_distribution_spreads_keyframes_without_clustering() -> None:
    selection = PreviewGenerationService()._scene_aware_selection(
        source_asset_checksum="previewabc123456789",
        duration_seconds=180,
        preview_id="preview-scene-test",
    )

    timestamps = [frame["timestamp_seconds"] for frame in selection.keyframes]
    gaps = [timestamps[idx + 1] - timestamps[idx] for idx in range(len(timestamps) - 1)]

    assert selection.selection_mode == "scene_aware"
    assert selection.scene_diversity > 0.7
    assert min(gaps) > 8.0
    assert max(gaps) < 30.0


def test_scene_numbers_increase_monotonically_across_selected_keyframes() -> None:
    selection = PreviewGenerationService()._scene_aware_selection(
        source_asset_checksum="previewabc123456789",
        duration_seconds=180,
        preview_id="preview-scene-test",
    )

    scene_numbers = [frame["scene_number"] for frame in selection.keyframes]
    assert scene_numbers == sorted(scene_numbers)
    assert len(set(scene_numbers)) == len(scene_numbers)
