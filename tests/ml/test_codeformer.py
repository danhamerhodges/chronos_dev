"""Maps to: ENG-005"""

from app.api.contracts import FidelityTier
from app.services.fidelity_profiles import resolve_fidelity_profile


def test_codeformer_contract_weights_follow_canonical_ranges() -> None:
    scenarios = [
        (FidelityTier.ENHANCE, 0.30, "Subtle", 0.15, 0.30),
        (FidelityTier.RESTORE, 0.15, "Matched", 0.05, 0.15),
        (FidelityTier.CONSERVE, 0.05, "Matched", 0.0, 0.049),
    ]

    for tier, hallucination_limit, grain, lower, upper in scenarios:
        profile = resolve_fidelity_profile(
            requested_tier=tier,
            era_profile={
                "mode": tier.value,
                "hallucination_limit": hallucination_limit,
                "artifact_policy": {"grain_intensity": grain},
            },
            config={},
        )

        assert lower <= profile["codeformer_weight"] <= upper
        assert profile["grain_preset"] == grain
