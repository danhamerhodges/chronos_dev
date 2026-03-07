"""Deterministic segment planning for Packet 3A and Packet 3B."""

from __future__ import annotations

import hashlib
import json
from math import ceil
from typing import Any

SEGMENT_DURATION_SECONDS = 10
MODEL_DIGEST = "packet-3b-pipeline-v1"
ENCODER_DIGEST = "packet-3b-encoder-v1"


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_pipeline_variant_fingerprint(
    *,
    processing_mode: str,
    config: dict[str, Any],
    era_profile: dict[str, Any],
    effective_fidelity_profile: dict[str, Any],
) -> dict[str, str]:
    return {
        "processing_mode": processing_mode,
        "config_hash": _sha256(json.dumps(config, sort_keys=True, separators=(",", ":"))),
        "model_digest": MODEL_DIGEST,
        "era_profile_digest": _sha256(json.dumps(era_profile, sort_keys=True, separators=(",", ":"))),
        "fidelity_profile_digest": _sha256(
            json.dumps(effective_fidelity_profile, sort_keys=True, separators=(",", ":"))
        ),
        "encoder_digest": ENCODER_DIGEST,
    }


def build_segments(
    *,
    user_id: str,
    source_asset_checksum: str,
    estimated_duration_seconds: int,
    fidelity_tier: str,
    reproducibility_mode: str = "perceptual_equivalence",
    processing_mode: str,
    era_profile: dict[str, Any],
    effective_fidelity_profile: dict[str, Any] | None = None,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    duration_seconds = ceil(float(estimated_duration_seconds))
    if duration_seconds < 1:
        raise ValueError("estimated_duration_seconds must be >= 1")
    segment_count = max(ceil(duration_seconds / SEGMENT_DURATION_SECONDS), 1)
    effective_fidelity_profile = effective_fidelity_profile or {"tier": fidelity_tier}
    pipeline_variant = build_pipeline_variant_fingerprint(
        processing_mode=processing_mode,
        config=config,
        era_profile=era_profile,
        effective_fidelity_profile=effective_fidelity_profile,
    )

    segments: list[dict[str, Any]] = []
    for segment_index in range(segment_count):
        start_seconds = segment_index * SEGMENT_DURATION_SECONDS
        end_seconds = min(start_seconds + SEGMENT_DURATION_SECONDS, duration_seconds)
        segment_duration_seconds = max(end_seconds - start_seconds, 1)
        idempotency_source = json.dumps(
            [
                user_id,
                source_asset_checksum,
                segment_index,
                start_seconds * 1000,
                end_seconds * 1000,
                segment_duration_seconds * 1000,
                fidelity_tier,
                reproducibility_mode,
                pipeline_variant["processing_mode"],
                pipeline_variant["config_hash"],
                pipeline_variant["model_digest"],
                pipeline_variant["era_profile_digest"],
                pipeline_variant["fidelity_profile_digest"],
                pipeline_variant["encoder_digest"],
            ],
            separators=(",", ":"),
            ensure_ascii=False,
        )
        segments.append(
            {
                "segment_index": segment_index,
                "segment_start_seconds": start_seconds,
                "segment_end_seconds": end_seconds,
                "segment_duration_seconds": segment_duration_seconds,
                "idempotency_key": _sha256(idempotency_source),
            }
        )
    return segments
