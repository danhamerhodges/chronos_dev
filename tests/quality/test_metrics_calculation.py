"""Maps to: ENG-006"""

import json
from pathlib import Path

from app.api.contracts import FidelityTier
from app.services.fidelity_profiles import resolve_fidelity_profile
from app.services.quality_metrics import ReferenceQualityMetricsProvider


def test_reference_metrics_match_checked_in_fixture() -> None:
    root = Path(__file__).resolve().parents[2]
    fixture = json.loads((root / "tests" / "fixtures" / "quality_metrics_reference.json").read_text(encoding="utf-8"))
    profile = resolve_fidelity_profile(
        requested_tier=FidelityTier(fixture["fidelity_tier"]),
        era_profile={
            "mode": fixture["fidelity_tier"],
            "hallucination_limit": 0.15,
            "artifact_policy": {"grain_intensity": "Matched"},
        },
        config={},
    )
    metrics = ReferenceQualityMetricsProvider().calculate(
        job={
            "job_id": fixture["job_id"],
            "source_asset_checksum": fixture["source_asset_checksum"],
            "config": {},
        },
        segment={
            "segment_index": fixture["segment_index"],
            "segment_duration_seconds": fixture["segment_duration_seconds"],
        },
        fidelity_profile=profile,
    )

    assert metrics["e_hf"] == fixture["expected"]["e_hf"]
    assert metrics["s_ls_db"] == fixture["expected"]["s_ls_db"]
    assert metrics["t_tc"] == fixture["expected"]["t_tc"]
    assert metrics["noise_floor_correction"] == fixture["expected"]["noise_floor_correction"]
    assert metrics["metric_latency_ms"] == fixture["expected"]["metric_latency_ms"]
