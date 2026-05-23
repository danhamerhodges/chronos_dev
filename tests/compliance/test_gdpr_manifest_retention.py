"""
Maps to:
- SEC-005
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.db.phase2_store import JobRepository, ManifestRepository, reset_phase2_store
from app.main import app
from tests.helpers.auth import fake_auth_header

client = TestClient(app)


def _manifest_payload(job_id: str, owner_user_id: str) -> dict[str, object]:
    return {
        "manifest_id": job_id,
        "job_id": job_id,
        "generated_at": "2026-05-11T00:00:00+00:00",
        "user_id": owner_user_id,
        "era_profile": {},
        "fidelity_tier": "Restore",
        "effective_fidelity_profile": {},
        "reproducibility_mode": "perceptual_equivalence",
        "job_status": "completed",
        "quality_summary": {"e_hf": 0.9, "s_ls_db": 0.1, "t_tc": 0.95, "thresholds_met": True},
        "reproducibility_summary": {
            "mode": "perceptual_equivalence",
            "verification_status": "pass",
            "failed_segment_count": 0,
            "rerun_count": 0,
            "rollup": "pass",
            "metric_epsilon_percent": 0.5,
            "environment_fingerprint": "abc",
        },
        "stage_timings": {},
        "processing_time_ms": 0,
        "gpu_usage": {},
        "slo_summary": {"target_total_ms": 120000},
        "model_versions": {},
        "environment": {},
        "segments": [],
        "uncertainty_callouts": [],
        "warnings": [],
        "result_uri": None,
        "manifest_uri": f"gs://chronos/manifests/90d/{job_id}/manifest.json",
        "manifest_sha256": "hash",
        "size_bytes": 512,
    }


def _seed_job(job_id: str, owner_user_id: str) -> None:
    JobRepository().create_job(
        job_id=job_id,
        owner_user_id=owner_user_id,
        plan_tier="pro",
        org_id="org-gdpr",
        media_uri="gs://chronos/input.mov",
        original_filename="input.mov",
        mime_type="video/mp4",
        source_asset_checksum="abc12345def67890",
        fidelity_tier="Restore",
        processing_mode="balanced",
        era_profile={"capture_medium": "film_scan"},
        config={},
        estimated_duration_seconds=25,
        segments=[],
    )


def test_expired_manifest_returns_existing_not_found_response() -> None:
    reset_phase2_store()
    _seed_job("gdpr-expired-manifest", "gdpr-owner")
    ManifestRepository().upsert_manifest_for_worker(
        job_id="gdpr-expired-manifest",
        manifest=_manifest_payload("gdpr-expired-manifest", "gdpr-owner"),
        retention={"retention_expires_at": "2026-01-01T00:00:00+00:00"},
    )

    response = client.get(
        "/v1/manifests/gdpr-expired-manifest",
        headers=fake_auth_header("gdpr-owner", tier="pro"),
    )

    assert response.status_code == 404
    assert response.json()["title"] == "Not Found"


def test_zero_day_deleted_manifest_returns_existing_not_found_response() -> None:
    reset_phase2_store()
    _seed_job("gdpr-deleted-manifest", "gdpr-owner")
    ManifestRepository().upsert_manifest_for_worker(
        job_id="gdpr-deleted-manifest",
        manifest=_manifest_payload("gdpr-deleted-manifest", "gdpr-owner"),
        retention={"retention_delete_status": "deleted", "retention_deleted_at": "2026-05-11T00:00:00+00:00"},
    )

    response = client.get(
        "/v1/manifests/gdpr-deleted-manifest",
        headers=fake_auth_header("gdpr-owner", tier="pro"),
    )

    assert response.status_code == 404
    assert response.json()["title"] == "Not Found"


def test_sec006_erasure_workflows_are_out_of_scope_for_packet_5h() -> None:
    reset_phase2_store()
    _seed_job("gdpr-retained-manifest", "gdpr-owner")
    ManifestRepository().upsert_manifest_for_worker(
        job_id="gdpr-retained-manifest",
        manifest=_manifest_payload("gdpr-retained-manifest", "gdpr-owner"),
        retention={"retention_expires_at": "2030-01-01T00:00:00+00:00"},
    )

    response = client.get(
        "/v1/manifests/gdpr-retained-manifest",
        headers=fake_auth_header("gdpr-owner", tier="pro"),
    )

    assert response.status_code == 200
    assert response.json()["manifest_id"] == "gdpr-retained-manifest"
