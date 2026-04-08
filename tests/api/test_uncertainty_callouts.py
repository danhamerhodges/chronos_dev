"""
Maps to:
- FR-004
- DS-006
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db.phase2_store import JobRepository, reset_phase2_store
from app.main import app
from tests.helpers.auth import fake_auth_header
from tests.helpers.jobs import create_seed_job, valid_job_request

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state() -> None:
    reset_phase2_store()


def _request_with_low_confidence_detection() -> dict[str, object]:
    payload = valid_job_request(
        estimated_duration_seconds=120,
        era_profile={
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
            "gemini_confidence": 0.61,
            "manual_confirmation_required": True,
        },
        config={
            "persona": "filmmaker",
            "grain_preset": "Matched",
            "detection_snapshot": {
                "detection_id": "detect-callout",
                "era": "1970s Super 8 Film",
                "confidence": 0.61,
                "source": "system",
            },
        },
    )
    return payload


def _request_with_manual_confirmation_only() -> dict[str, object]:
    payload = valid_job_request(
        estimated_duration_seconds=120,
        era_profile={
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
            "gemini_confidence": 0.91,
            "manual_confirmation_required": True,
        },
        config={
            "persona": "filmmaker",
            "grain_preset": "Matched",
            "detection_snapshot": {
                "detection_id": "detect-manual-callout",
                "era": "1970s Super 8 Film",
                "confidence": 0.91,
                "source": "system",
            },
        },
    )
    return payload


def _request_with_invalid_confidence() -> dict[str, object]:
    payload = valid_job_request(
        estimated_duration_seconds=120,
        era_profile={
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
            "gemini_confidence": 1.7,
            "manual_confirmation_required": False,
        },
        config={
            "persona": "filmmaker",
            "grain_preset": "Matched",
            "detection_snapshot": {
                "detection_id": "detect-invalid-confidence",
                "era": "1970s Super 8 Film",
                "confidence": 1.7,
                "source": "system",
            },
        },
    )
    return payload


def test_uncertainty_callouts_enforce_owner_scope() -> None:
    created = create_seed_job(
        user_id="callout-owner",
        tier="pro",
        payload=_request_with_low_confidence_detection(),
    )

    response = client.get(
        f"/v1/jobs/{created['job_id']}/uncertainty-callouts",
        headers=fake_auth_header("other-user", tier="pro"),
    )

    assert response.status_code == 404
    assert response.json()["title"] == "Not Found"


def test_uncertainty_callouts_return_low_confidence_and_segment_mapping() -> None:
    created = create_seed_job(
        user_id="callout-user",
        tier="pro",
        payload=_request_with_low_confidence_detection(),
    )
    repo = JobRepository()
    repo.update_job_for_worker(
        created["job_id"],
        patch={
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
                "gemini_confidence": 0.61,
                "manual_confirmation_required": False,
            }
        },
    )
    repo.update_segment_for_worker(
        created["job_id"],
        0,
        patch={
            "uncertainty_callouts": [
                "texture_energy_margin_low",
                "texture_energy_margin_low",
                "spectral_slope_margin_low",
            ]
        },
    )

    response = client.get(
        f"/v1/jobs/{created['job_id']}/uncertainty-callouts",
        headers=fake_auth_header("callout-user", tier="pro"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == created["job_id"]
    assert payload["status"] == "queued"
    assert len(payload["callouts"]) == 3

    callouts = {item["code"]: item for item in payload["callouts"]}
    assert set(callouts) == {
        "low_confidence_era_classification",
        "texture_loss_risk",
        "spectral_boundary_risk",
    }

    global_callout = callouts["low_confidence_era_classification"]
    assert global_callout["scope"] == "global"
    assert global_callout["time_range_seconds"] == {"start": 0.0, "end": 120.0}
    assert global_callout["source"]["metric_key"] == "gemini_confidence"
    assert "below 0.70" in global_callout["message"]

    texture_callout = callouts["texture_loss_risk"]
    assert texture_callout["scope"] == "segment"
    assert texture_callout["source"]["segment_index"] == 0
    assert texture_callout["source"]["metric_key"] == "e_hf"
    assert texture_callout["time_range_seconds"] == {"start": 0.0, "end": 10.0}

    spectral_callout = callouts["spectral_boundary_risk"]
    assert spectral_callout["source"]["metric_key"] == "s_ls_db"


def test_uncertainty_callouts_prefer_manual_confirmation_message_when_confidence_is_high() -> None:
    created = create_seed_job(
        user_id="manual-callout-user",
        tier="pro",
        payload=_request_with_manual_confirmation_only(),
    )

    response = client.get(
        f"/v1/jobs/{created['job_id']}/uncertainty-callouts",
        headers=fake_auth_header("manual-callout-user", tier="pro"),
    )

    assert response.status_code == 200
    payload = response.json()
    global_callout = next(item for item in payload["callouts"] if item["code"] == "low_confidence_era_classification")
    assert "manual confirmation" in global_callout["message"]
    assert "below 0.70" not in global_callout["message"]


def test_uncertainty_callouts_treat_invalid_confidence_as_uncertain() -> None:
    created = create_seed_job(
        user_id="invalid-confidence-user",
        tier="pro",
        payload=_request_with_invalid_confidence(),
    )

    response = client.get(
        f"/v1/jobs/{created['job_id']}/uncertainty-callouts",
        headers=fake_auth_header("invalid-confidence-user", tier="pro"),
    )

    assert response.status_code == 200
    payload = response.json()
    global_callout = next(item for item in payload["callouts"] if item["code"] == "low_confidence_era_classification")
    assert "could not be validated" in global_callout["message"]
