"""Maps to: ENG-001, ENG-002, ENG-004, FR-002, NFR-007, SEC-009"""


def valid_era_profile(**overrides):
    payload = {
        "capture_medium": "kodachrome",
        "mode": "Enhance",
        "tier": "Pro",
        "resolution_cap": "4k",
        "hallucination_limit": 0.2,
        "artifact_policy": {
            "deinterlace": False,
            "grain_intensity": "Subtle",
            "preserve_edge_fog": False,
            "preserve_chromatic_aberration": False,
        },
        "era_range": {
            "start_year": 1955,
            "end_year": 1969,
        },
        "gemini_confidence": 0.93,
        "manual_confirmation_required": False,
    }
    payload.update(overrides)
    return payload


def valid_detect_request(**overrides):
    payload = {
        "job_id": "job-123",
        "media_uri": "gs://chronos-dev/uploads/reel.mov",
        "original_filename": "reel.mov",
        "mime_type": "video/quicktime",
        "estimated_duration_seconds": 180,
        "era_profile": valid_era_profile(),
    }
    payload.update(overrides)
    return payload
