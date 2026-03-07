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


def build_segments(
    *,
    user_id: str,
    source_asset_checksum: str,
    estimated_duration_seconds: int,
    fidelity_tier: str,
    reproducibility_mode: str,
    processing_mode: str,
    era_profile: dict[str, Any],
    effective_fidelity_profile: dict[str, Any],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    duration_seconds = max(int(estimated_duration_seconds), 1)
    segment_count = max(ceil(duration_seconds / SEGMENT_DURATION_SECONDS), 1)
    config_hash = _sha256(json.dumps(config, sort_keys=True, separators=(",", ":")))
    era_profile_digest = _sha256(json.dumps(era_profile, sort_keys=True, separators=(",", ":")))
    fidelity_profile_digest = _sha256(json.dumps(effective_fidelity_profile, sort_keys=True, separators=(",", ":")))

    segments: list[dict[str, Any]] = []
    for segment_index in range(segment_count):
        start_seconds = segment_index * SEGMENT_DURATION_SECONDS
        end_seconds = min(start_seconds + SEGMENT_DURATION_SECONDS, duration_seconds)
        segment_duration_seconds = max(end_seconds - start_seconds, 1)
        idempotency_source = "|".join(
            [
                user_id,
                source_asset_checksum,
                str(segment_index),
                str(start_seconds * 1000),
                str(end_seconds * 1000),
                str(segment_duration_seconds * 1000),
                fidelity_tier,
                reproducibility_mode,
                processing_mode,
                config_hash,
                MODEL_DIGEST,
                era_profile_digest,
                fidelity_profile_digest,
                ENCODER_DIGEST,
            ]
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
