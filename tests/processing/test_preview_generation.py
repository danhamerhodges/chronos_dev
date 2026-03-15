"""Maps to: ENG-014"""

from __future__ import annotations

import pytest

from app.services.preview_generation import PreviewGenerationService


def test_preview_generation_emits_exactly_ten_keyframes_covering_beginning_middle_end() -> None:
    selection = PreviewGenerationService()._scene_aware_selection(
        source_asset_checksum="previewabc123456789",
        duration_seconds=180,
        preview_id="preview-test",
    )

    timestamps = [frame["timestamp_seconds"] for frame in selection.keyframes]
    assert selection.selection_mode == "scene_aware"
    assert len(selection.keyframes) == 10
    assert timestamps[0] < 40
    assert any(70 <= stamp <= 110 for stamp in timestamps)
    assert timestamps[-1] > 140


def test_preview_generation_includes_full_keyframe_metadata_and_thumbnail_markers() -> None:
    selection = PreviewGenerationService()._scene_aware_selection(
        source_asset_checksum="previewabc123456789",
        duration_seconds=180,
        preview_id="preview-test",
    )

    for expected_index, frame in enumerate(selection.keyframes):
        assert frame["index"] == expected_index
        assert frame["scene_number"] >= 1
        assert 0.0 <= frame["confidence_score"] <= 1.0
        assert frame["thumbnail_uri"].endswith(".jpg")
        assert "320x180" in frame["thumbnail_uri"]
        assert frame["frame_uri"].endswith(".jpg")


def test_preview_generation_falls_back_to_uniform_sampling_when_scene_detection_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = PreviewGenerationService()
    monkeypatch.setattr(service, "_detect_scene_centers", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))

    selection = service._select_keyframes(
        source_asset_checksum="previewabc123456789",
        duration_seconds=180,
        preview_id="preview-test",
    )

    timestamps = [frame["timestamp_seconds"] for frame in selection.keyframes]
    gaps = [round(timestamps[idx + 1] - timestamps[idx], 3) for idx in range(len(timestamps) - 1)]

    assert selection.selection_mode == "uniform_fallback"
    assert len(selection.keyframes) == 10
    assert max(gaps) - min(gaps) < 1.0
