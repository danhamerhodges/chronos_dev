"""Maps to: ENG-006"""

from app.api.contracts import FidelityTier
from app.services.fidelity_profiles import resolve_fidelity_profile
from app.services.quality_metrics import ReferenceQualityMetricsProvider


def test_metrics_enforce_thresholds_and_sampling_protocol_shape() -> None:
    profile = resolve_fidelity_profile(
        requested_tier=FidelityTier.RESTORE,
        era_profile={
            "mode": "Restore",
            "hallucination_limit": 0.15,
            "artifact_policy": {"grain_intensity": "Matched"},
        },
        config={},
    )
    metrics = ReferenceQualityMetricsProvider().calculate(
        job={"job_id": "job-metrics-1", "source_asset_checksum": "abc12345def67890", "config": {}},
        segment={"segment_index": 1, "segment_duration_seconds": 10},
        fidelity_profile=profile,
    )

    assert metrics["e_hf"] >= profile["thresholds"]["e_hf_min"]
    assert abs(metrics["s_ls_db"]) <= profile["thresholds"]["s_ls_band_db"]
    assert metrics["t_tc"] >= profile["thresholds"]["t_tc_min"]
    assert metrics["sampling_protocol"]["roi_256"]["width"] == 256
    assert metrics["sampling_protocol"]["roi_512"]["width"] == 512
    assert metrics["sampling_protocol"]["roi_full_frame"]["height"] == 720
    assert metrics["thresholds_met"] is True
