"""Canonical fidelity tier resolution for Packet 3B."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.api.problem_details import ProblemException
from app.api.contracts import FidelityTier


@dataclass(frozen=True)
class FidelityProfile:
    tier: FidelityTier
    e_hf_min: float
    s_ls_band_db: float
    t_tc_min: float
    hallucination_limit_max: float
    grain_preset: str
    codeformer_weight_min: float
    codeformer_weight_max: float
    identity_lock: bool
    error_policy: str
    uncertainty_callout_threshold: float


_FidelityProfileMap = {
    FidelityTier.ENHANCE: FidelityProfile(
        tier=FidelityTier.ENHANCE,
        e_hf_min=0.55,
        s_ls_band_db=6.0,
        t_tc_min=0.90,
        hallucination_limit_max=0.30,
        grain_preset="Subtle",
        codeformer_weight_min=0.15,
        codeformer_weight_max=0.30,
        identity_lock=False,
        error_policy="permissive",
        uncertainty_callout_threshold=0.06,
    ),
    FidelityTier.RESTORE: FidelityProfile(
        tier=FidelityTier.RESTORE,
        e_hf_min=0.70,
        s_ls_band_db=4.0,
        t_tc_min=0.90,
        hallucination_limit_max=0.15,
        grain_preset="Matched",
        codeformer_weight_min=0.05,
        codeformer_weight_max=0.15,
        identity_lock=False,
        error_policy="balanced",
        uncertainty_callout_threshold=0.04,
    ),
    FidelityTier.CONSERVE: FidelityProfile(
        tier=FidelityTier.CONSERVE,
        e_hf_min=0.85,
        s_ls_band_db=2.0,
        t_tc_min=0.90,
        hallucination_limit_max=0.05,
        grain_preset="Matched",
        codeformer_weight_min=0.0,
        codeformer_weight_max=0.049,
        identity_lock=True,
        error_policy="strict",
        uncertainty_callout_threshold=0.02,
    ),
}


def _config_override(config: dict[str, Any], key: str) -> Any:
    if key in config:
        return config[key]
    fidelity_overrides = config.get("fidelity_overrides")
    if isinstance(fidelity_overrides, dict):
        return fidelity_overrides.get(key)
    return None


def fidelity_profile_for(tier: FidelityTier) -> FidelityProfile:
    return _FidelityProfileMap[tier]


def resolve_fidelity_profile(
    *,
    requested_tier: FidelityTier,
    era_profile: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    profile = fidelity_profile_for(requested_tier)
    if str(era_profile.get("mode")) != requested_tier.value:
        raise ProblemException(
            title="Invalid Fidelity Tier",
            detail="fidelity_tier must align with era_profile.mode for Packet 3B processing.",
            status_code=400,
        )

    hallucination_limit = float(era_profile.get("hallucination_limit", 0.0))
    if hallucination_limit > profile.hallucination_limit_max:
        raise ProblemException(
            title="Invalid Fidelity Override",
            detail=f"{requested_tier.value} limits hallucination_limit to {profile.hallucination_limit_max:.2f}.",
            status_code=400,
        )

    grain_intensity = str((era_profile.get("artifact_policy") or {}).get("grain_intensity", ""))
    if grain_intensity != profile.grain_preset:
        raise ProblemException(
            title="Invalid Fidelity Override",
            detail=f"{requested_tier.value} requires artifact_policy.grain_intensity='{profile.grain_preset}'.",
            status_code=400,
        )

    requested_hallucination = _config_override(config, "hallucination_limit")
    if requested_hallucination is not None and float(requested_hallucination) > profile.hallucination_limit_max:
        raise ProblemException(
            title="Invalid Fidelity Override",
            detail=f"{requested_tier.value} cannot raise hallucination_limit beyond {profile.hallucination_limit_max:.2f}.",
            status_code=400,
        )

    requested_grain = _config_override(config, "grain_intensity")
    if requested_grain is not None and str(requested_grain) != profile.grain_preset:
        raise ProblemException(
            title="Invalid Fidelity Override",
            detail=f"{requested_tier.value} locks grain_intensity to '{profile.grain_preset}'.",
            status_code=400,
        )

    requested_codeformer = _config_override(config, "codeformer_weight")
    if requested_codeformer is not None:
        codeformer_weight = float(requested_codeformer)
        if not profile.codeformer_weight_min <= codeformer_weight <= profile.codeformer_weight_max:
            raise ProblemException(
                title="Invalid Fidelity Override",
                detail=(
                    f"{requested_tier.value} requires codeformer_weight between "
                    f"{profile.codeformer_weight_min:.3f} and {profile.codeformer_weight_max:.3f}."
                ),
                status_code=400,
            )
    else:
        codeformer_weight = round((profile.codeformer_weight_min + profile.codeformer_weight_max) / 2, 3)

    requested_identity_lock = _config_override(config, "identity_lock")
    if requested_identity_lock is not None and bool(requested_identity_lock) is not profile.identity_lock:
        raise ProblemException(
            title="Invalid Fidelity Override",
            detail=f"{requested_tier.value} requires identity_lock={str(profile.identity_lock).lower()}.",
            status_code=400,
        )

    resolved = asdict(profile)
    resolved["tier"] = profile.tier.value
    resolved["hallucination_limit"] = min(hallucination_limit, profile.hallucination_limit_max)
    resolved["codeformer_weight"] = codeformer_weight
    resolved["thresholds"] = {
        "e_hf_min": profile.e_hf_min,
        "s_ls_band_db": profile.s_ls_band_db,
        "t_tc_min": profile.t_tc_min,
    }
    return resolved
