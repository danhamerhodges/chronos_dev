"""
Maps to:
- FR-003
- DS-001
- FR-006
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.phase2_store import reset_phase2_store
from tests.helpers.auth import fake_auth_header
from tests.helpers.previews import (
    approve_preview,
    create_preview,
    save_configuration,
    seed_completed_upload,
    seed_detection,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state() -> None:
    reset_phase2_store()


def _approved_configuration(*, upload_id: str, owner_user_id: str) -> dict[str, object]:
    configuration = save_configuration(client, upload_id=upload_id, owner_user_id=owner_user_id)
    preview = create_preview(client, upload_id=upload_id, owner_user_id=owner_user_id)
    approve_preview(client, preview_id=str(preview["preview_id"]), owner_user_id=owner_user_id)
    return configuration


def test_pre_5b_saved_payload_without_launch_context_is_blocked() -> None:
    seed_completed_upload(upload_id="upload-handoff-legacy", owner_user_id="handoff-user")
    seed_detection(upload_id="upload-handoff-legacy", owner_user_id="handoff-user")
    configuration = save_configuration(client, upload_id="upload-handoff-legacy", owner_user_id="handoff-user")
    legacy_payload = dict(configuration["job_payload_preview"])
    legacy_payload.pop("launch_context", None)

    job_create = client.post(
        "/v1/jobs",
        headers=fake_auth_header("handoff-user", tier="pro"),
        json=legacy_payload,
    )

    assert job_create.status_code == 409
    payload = job_create.json()
    assert payload["type"] == "/problems/preview_approval_required"
    assert "approved-preview launch provenance" in payload["detail"]


def test_refreshed_saved_payload_with_approved_preview_is_accepted_by_jobs_api() -> None:
    seed_completed_upload(upload_id="upload-handoff", owner_user_id="handoff-user")
    seed_detection(upload_id="upload-handoff", owner_user_id="handoff-user")
    configuration = _approved_configuration(upload_id="upload-handoff", owner_user_id="handoff-user")

    job_create = client.post(
        "/v1/jobs",
        headers=fake_auth_header("handoff-user", tier="pro"),
        json=configuration["job_payload_preview"],
    )

    assert job_create.status_code == 202
    payload = job_create.json()
    assert payload["status"] == "queued"
    assert payload["fidelity_tier"] == "Restore"


def test_configuration_resave_makes_old_launch_payload_stale() -> None:
    seed_completed_upload(upload_id="upload-handoff-stale", owner_user_id="handoff-stale-user")
    seed_detection(upload_id="upload-handoff-stale", owner_user_id="handoff-stale-user")
    first = _approved_configuration(upload_id="upload-handoff-stale", owner_user_id="handoff-stale-user")
    second = save_configuration(client, upload_id="upload-handoff-stale", owner_user_id="handoff-stale-user")

    stale_launch = client.post(
        "/v1/jobs",
        headers=fake_auth_header("handoff-stale-user", tier="pro"),
        json=first["job_payload_preview"],
    )

    assert stale_launch.status_code == 409
    assert stale_launch.json()["type"] == "/problems/preview_stale"

    preview = create_preview(client, upload_id="upload-handoff-stale", owner_user_id="handoff-stale-user")
    approve_preview(client, preview_id=str(preview["preview_id"]), owner_user_id="handoff-stale-user")
    fresh_launch = client.post(
        "/v1/jobs",
        headers=fake_auth_header("handoff-stale-user", tier="pro"),
        json=second["job_payload_preview"],
    )

    assert fresh_launch.status_code == 202


def test_cross_user_generic_launch_is_denied_even_with_owner_payload() -> None:
    seed_completed_upload(upload_id="upload-cross-user", owner_user_id="handoff-owner")
    seed_detection(upload_id="upload-cross-user", owner_user_id="handoff-owner")
    configuration = _approved_configuration(upload_id="upload-cross-user", owner_user_id="handoff-owner")

    response = client.post(
        "/v1/jobs",
        headers=fake_auth_header("handoff-other", tier="pro"),
        json=configuration["job_payload_preview"],
    )

    assert response.status_code == 404
