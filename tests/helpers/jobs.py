"""Maps to: ENG-003, ENG-011, ENG-012

Job request and runtime helpers for Packet 3A tests.
"""

from __future__ import annotations

from typing import Any

from app.api.contracts import FidelityTier
from app.services.job_runtime import drain_job_queue


def valid_job_request(**overrides: Any) -> dict[str, Any]:
    payload = {
        "media_uri": "gs://chronos-dev/input/sample.mov",
        "original_filename": "sample.mov",
        "mime_type": "video/quicktime",
        "estimated_duration_seconds": 27,
        "source_asset_checksum": "abc12345def67890",
        "fidelity_tier": FidelityTier.RESTORE.value,
        "reproducibility_mode": "perceptual_equivalence",
        "processing_mode": "balanced",
        "era_profile": {
            "capture_medium": "16mm",
            "mode": "Restore",
            "tier": "Pro",
            "resolution_cap": "4k",
            "hallucination_limit": 0.15,
            "artifact_policy": {
                "deinterlace": False,
                "grain_intensity": "Matched",
                "preserve_edge_fog": True,
                "preserve_chromatic_aberration": True,
            },
            "era_range": {"start_year": 1970, "end_year": 1995},
            "gemini_confidence": 0.92,
            "manual_confirmation_required": False,
        },
        "config": {"stabilization": "medium", "color_balance": "neutral"},
    }
    payload.update(overrides)
    return payload


def run_all_jobs() -> list[str]:
    return drain_job_queue()
