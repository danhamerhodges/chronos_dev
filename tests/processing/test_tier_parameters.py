"""
Maps to:
- FR-003
- DS-001
"""

from app.api.contracts import FidelityTier, GrainPreset, UserPersona
from app.services.fidelity_profiles import (
    allowed_grain_presets_for_tier,
    default_tier_for_persona,
    fidelity_profile_for,
    relative_cost_multiplier_for_tier,
    relative_processing_time_band_for_tier,
    resolve_fidelity_profile,
)


def test_canonical_thresholds_match_packet_4b_catalog() -> None:
    expected = {
        FidelityTier.ENHANCE: (0.55, 6.0, 0.90, 0.30, GrainPreset.SUBTLE.value),
        FidelityTier.RESTORE: (0.70, 4.0, 0.90, 0.15, GrainPreset.MATCHED.value),
        FidelityTier.CONSERVE: (0.85, 2.0, 0.90, 0.05, GrainPreset.MATCHED.value),
    }

    for tier, thresholds in expected.items():
        profile = fidelity_profile_for(tier)
        assert (
            profile.e_hf_min,
            profile.s_ls_band_db,
            profile.t_tc_min,
            profile.hallucination_limit_max,
            profile.grain_preset,
        ) == thresholds


def test_grain_preset_constraints_follow_packet_4b_policy() -> None:
    expected = [GrainPreset.MATCHED, GrainPreset.SUBTLE, GrainPreset.HEAVY]
    assert allowed_grain_presets_for_tier(FidelityTier.ENHANCE) == expected
    assert allowed_grain_presets_for_tier(FidelityTier.RESTORE) == expected
    assert allowed_grain_presets_for_tier(FidelityTier.CONSERVE) == expected


def test_shared_resolver_accepts_all_canonical_grain_presets_per_tier() -> None:
    for tier in FidelityTier:
        profile = fidelity_profile_for(tier)
        for grain in allowed_grain_presets_for_tier(tier):
            resolved = resolve_fidelity_profile(
                requested_tier=tier,
                era_profile={
                    "mode": tier.value,
                    "hallucination_limit": profile.hallucination_limit_max,
                    "artifact_policy": {"grain_intensity": grain.value},
                },
                config={
                    "grain_preset": grain.value,
                    "fidelity_overrides": {"grain_intensity": grain.value},
                },
            )

            assert resolved["grain_preset"] == grain.value
            assert resolved["thresholds"] == {
                "e_hf_min": profile.e_hf_min,
                "s_ls_band_db": profile.s_ls_band_db,
                "t_tc_min": profile.t_tc_min,
            }


def test_persona_defaults_match_canon() -> None:
    assert default_tier_for_persona(UserPersona.ARCHIVIST) == FidelityTier.CONSERVE
    assert default_tier_for_persona(UserPersona.FILMMAKER) == FidelityTier.RESTORE
    assert default_tier_for_persona(UserPersona.PROSUMER) == FidelityTier.ENHANCE


def test_relative_multiplier_and_processing_bands_match_functional_requirements() -> None:
    assert relative_cost_multiplier_for_tier(FidelityTier.ENHANCE) == 1.0
    assert relative_cost_multiplier_for_tier(FidelityTier.RESTORE) == 1.5
    assert relative_cost_multiplier_for_tier(FidelityTier.CONSERVE) == 2.0

    assert relative_processing_time_band_for_tier(FidelityTier.ENHANCE) == "<2 min/min"
    assert relative_processing_time_band_for_tier(FidelityTier.RESTORE) == "<4 min/min"
    assert relative_processing_time_band_for_tier(FidelityTier.CONSERVE) == "<8 min/min"
