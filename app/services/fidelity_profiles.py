"""Canonical fidelity tier resolution for Packet 3B."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.api.problem_details import ProblemException
from app.api.contracts import FidelityTier, FidelityTierCatalogItem, FidelityPersonaOption, GrainPreset, UserPersona


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

_PERSONA_DEFAULT_TIER = {
    UserPersona.ARCHIVIST: FidelityTier.CONSERVE,
    UserPersona.FILMMAKER: FidelityTier.RESTORE,
    UserPersona.PROSUMER: FidelityTier.ENHANCE,
}

_PERSONA_LABELS = {
    UserPersona.ARCHIVIST: "Archivist",
    UserPersona.FILMMAKER: "Filmmaker",
    UserPersona.PROSUMER: "Prosumer",
}

_PERSONA_DESCRIPTIONS = {
    UserPersona.ARCHIVIST: "Preserve authenticity and retain a defensible audit trail for archival work.",
    UserPersona.FILMMAKER: "Balance cleanup with era-accurate texture for editorial and documentary use.",
    UserPersona.PROSUMER: "Prioritize a cleaner family-video presentation while keeping the footage recognizable.",
}

_TIER_DESCRIPTIONS = {
    FidelityTier.ENHANCE: "Best for family videos. Reduces grain for a cleaner look.",
    FidelityTier.RESTORE: "Best for documentaries. Preserves era-accurate texture.",
    FidelityTier.CONSERVE: "Best for archival work. Maximum authenticity with full audit trail.",
}

_TIER_COST_MULTIPLIERS = {
    FidelityTier.ENHANCE: 1.0,
    FidelityTier.RESTORE: 1.5,
    FidelityTier.CONSERVE: 2.0,
}

_TIER_PROCESSING_TIME_BANDS = {
    FidelityTier.ENHANCE: "<2 min/min",
    FidelityTier.RESTORE: "<4 min/min",
    FidelityTier.CONSERVE: "<8 min/min",
}

_ALL_GRAIN_PRESETS = [GrainPreset.MATCHED, GrainPreset.SUBTLE, GrainPreset.HEAVY]
_TIER_ALLOWED_GRAIN_PRESETS = {
    FidelityTier.ENHANCE: list(_ALL_GRAIN_PRESETS),
    FidelityTier.RESTORE: list(_ALL_GRAIN_PRESETS),
    FidelityTier.CONSERVE: list(_ALL_GRAIN_PRESETS),
}


def _config_override(config: dict[str, Any], key: str) -> Any:
    if key in config:
        return config[key]
    fidelity_overrides = config.get("fidelity_overrides")
    if isinstance(fidelity_overrides, dict):
        return fidelity_overrides.get(key)
    return None


def _grain_preset_from(value: Any) -> GrainPreset | None:
    if value in (None, ""):
        return None
    try:
        return GrainPreset(str(value))
    except ValueError as exc:
        raise ProblemException(
            title="Invalid Fidelity Override",
            detail="grain_intensity must use one of the canonical grain preset values.",
            status_code=400,
        ) from exc


def resolve_grain_preset(
    *,
    requested_tier: FidelityTier,
    era_profile: dict[str, Any],
    config: dict[str, Any],
) -> GrainPreset:
    era_grain = _grain_preset_from((era_profile.get("artifact_policy") or {}).get("grain_intensity"))
    if era_grain is None:
        raise ProblemException(
            title="Invalid Fidelity Override",
            detail="artifact_policy.grain_intensity is required for fidelity resolution.",
            status_code=400,
        )

    requested_grain = _grain_preset_from(_config_override(config, "grain_intensity"))
    if requested_grain is None:
        requested_grain = _grain_preset_from(config.get("grain_preset"))

    if requested_grain is not None and requested_grain != era_grain:
        raise ProblemException(
            title="Invalid Fidelity Override",
            detail="grain_intensity must match the saved era profile and job configuration.",
            status_code=400,
        )

    resolved_grain = requested_grain or era_grain
    allowed = allowed_grain_presets_for_tier(requested_tier)
    if resolved_grain not in allowed:
        allowed_labels = ", ".join(preset.value for preset in allowed)
        raise ProblemException(
            title="Invalid Fidelity Override",
            detail=f"{requested_tier.value} allows these grain presets: {allowed_labels}.",
            status_code=400,
        )
    return resolved_grain


def fidelity_profile_for(tier: FidelityTier) -> FidelityProfile:
    return _FidelityProfileMap[tier]


def default_tier_for_persona(persona: UserPersona) -> FidelityTier:
    return _PERSONA_DEFAULT_TIER[persona]


def allowed_grain_presets_for_tier(tier: FidelityTier) -> list[GrainPreset]:
    return list(_TIER_ALLOWED_GRAIN_PRESETS[tier])


def relative_cost_multiplier_for_tier(tier: FidelityTier) -> float:
    return _TIER_COST_MULTIPLIERS[tier]


def relative_processing_time_band_for_tier(tier: FidelityTier) -> str:
    return _TIER_PROCESSING_TIME_BANDS[tier]


def tier_catalog() -> list[FidelityTierCatalogItem]:
    items: list[FidelityTierCatalogItem] = []
    for tier in FidelityTier:
        profile = fidelity_profile_for(tier)
        items.append(
            FidelityTierCatalogItem(
                tier=tier,
                label=tier.value,
                description=_TIER_DESCRIPTIONS[tier],
                default_grain_preset=GrainPreset(profile.grain_preset),
                allowed_grain_presets=allowed_grain_presets_for_tier(tier),
                relative_cost_multiplier=relative_cost_multiplier_for_tier(tier),
                relative_processing_time_band=relative_processing_time_band_for_tier(tier),
                thresholds={
                    "e_hf_min": profile.e_hf_min,
                    "s_ls_band_db": profile.s_ls_band_db,
                    "t_tc_min": profile.t_tc_min,
                    "hallucination_limit_max": profile.hallucination_limit_max,
                },
                identity_lock=profile.identity_lock,
            )
        )
    return items


def persona_catalog() -> list[FidelityPersonaOption]:
    return [
        FidelityPersonaOption(
            persona=persona,
            label=_PERSONA_LABELS[persona],
            default_fidelity_tier=default_tier_for_persona(persona),
            description=_PERSONA_DESCRIPTIONS[persona],
        )
        for persona in UserPersona
    ]


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

    resolved_grain_preset = resolve_grain_preset(
        requested_tier=requested_tier,
        era_profile=era_profile,
        config=config,
    )

    requested_hallucination = _config_override(config, "hallucination_limit")
    if requested_hallucination is not None and float(requested_hallucination) > profile.hallucination_limit_max:
        raise ProblemException(
            title="Invalid Fidelity Override",
            detail=f"{requested_tier.value} cannot raise hallucination_limit beyond {profile.hallucination_limit_max:.2f}.",
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
    resolved["grain_preset"] = resolved_grain_preset.value
    resolved["hallucination_limit"] = min(hallucination_limit, profile.hallucination_limit_max)
    resolved["codeformer_weight"] = codeformer_weight
    resolved["thresholds"] = {
        "e_hf_min": profile.e_hf_min,
        "s_ls_band_db": profile.s_ls_band_db,
        "t_tc_min": profile.t_tc_min,
    }
    return resolved
