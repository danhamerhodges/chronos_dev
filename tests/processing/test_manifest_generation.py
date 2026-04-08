"""Maps to: ENG-010"""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.services.transformation_manifest import build_manifest_payload
from tests.helpers.auth import fake_auth_header
from tests.helpers.jobs import create_seed_job, run_all_jobs

client = TestClient(app)


def test_completed_job_generates_manifest_with_required_fields() -> None:
    created = create_seed_job(user_id="manifest-user", tier="pro")

    run_all_jobs()
    response = client.get(f"/v1/manifests/{created['job_id']}", headers=fake_auth_header("manifest-user", tier="pro"))

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == created["job_id"]
    assert payload["manifest_sha256"]
    assert payload["manifest_uri"].startswith("gs://")
    assert payload["segments"]
    assert payload["segments"][0]["sampling_protocol"]["roi_256"]["width"] == 256


def test_manifest_payload_coerces_datetime_generated_at() -> None:
    payload = build_manifest_payload(
        manifest_id="manifest-datetime",
        generated_at=datetime(2026, 3, 7, 0, 0, tzinfo=timezone.utc),
        job={
            "job_id": "manifest-datetime",
            "owner_user_id": "manifest-user",
            "era_profile": {"capture_medium": "16mm"},
            "effective_fidelity_tier": "Restore",
            "effective_fidelity_profile": {"tier": "Restore", "identity_lock": True},
            "reproducibility_mode": "deterministic",
            "status": "completed",
            "quality_summary": {"e_hf": 0.9, "s_ls_db": -1.0, "t_tc": 0.95, "thresholds_met": True},
            "reproducibility_summary": {"mode": "deterministic"},
            "stage_timings": {"processing_ms": 1000},
            "gpu_summary": {},
            "cost_summary": {},
            "slo_summary": {},
            "warnings": [],
            "result_uri": "gs://chronos/jobs/result.mp4",
        },
        segments=[],
    )

    assert payload["generated_at"] == "2026-03-07T00:00:00+00:00"
