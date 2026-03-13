"""
Maps to:
- FR-003
- DS-001
"""

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.models.status import UploadStatus
from app.db.phase2_store import UploadRepository, UserProfileRepository, reset_phase2_store
from tests.helpers.auth import fake_auth_header

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state() -> None:
    reset_phase2_store()


def _seed_upload(
    *,
    upload_id: str,
    owner_user_id: str,
    original_filename: str = "sample.mov",
    mime_type: str = "video/quicktime",
    status: UploadStatus = UploadStatus.COMPLETED,
) -> dict[str, object]:
    repo = UploadRepository()
    created = repo.create_session(
        upload_id=upload_id,
        owner_user_id=owner_user_id,
        org_id="org-default",
        original_filename=original_filename,
        mime_type=mime_type,
        size_bytes=1024 * 1024,
        checksum_sha256="abc12345def67890",
        bucket_name="chronos-test-bucket",
        object_path=f"uploads/{owner_user_id}/{upload_id}/{original_filename}",
        resumable_session_url=f"https://example.invalid/{upload_id}",
        access_token=f"test-token-for-{owner_user_id}",
    )
    if status == UploadStatus.COMPLETED:
        updated = repo.update_session(
            upload_id,
            owner_user_id=owner_user_id,
            patch={"status": status.value, "completed_at": "2026-03-10T00:00:00+00:00"},
            access_token=f"test-token-for-{owner_user_id}",
        )
        return updated or created
    return created


def test_fidelity_tiers_catalog_returns_persona_defaults_and_current_preferences() -> None:
    repo = UserProfileRepository()
    repo.get_or_create(
        user_id="catalog-user",
        role="member",
        plan_tier="pro",
        org_id="org-default",
        access_token="test-token-for-catalog-user",
    )
    repo.update(
        "catalog-user",
        {
            "preferences": {
                "fidelity_configuration": {
                    "persona": "filmmaker",
                    "preferred_fidelity_tier": "Enhance",
                    "preferred_grain_preset": "Heavy",
                }
            }
        },
        access_token="test-token-for-catalog-user",
    )

    response = client.get("/v1/fidelity-tiers", headers=fake_auth_header("catalog-user", tier="pro"))

    assert response.status_code == 200
    payload = response.json()
    persona_defaults = {item["persona"]: item["default_fidelity_tier"] for item in payload["personas"]}
    assert persona_defaults == {
        "archivist": "Conserve",
        "filmmaker": "Restore",
        "prosumer": "Enhance",
    }
    assert payload["current_persona"] == "filmmaker"
    assert payload["preferred_fidelity_tier"] == "Enhance"
    assert payload["preferred_grain_preset"] == "Heavy"


def test_fidelity_tiers_catalog_limits_hobbyist_to_enhance_and_resolves_saved_defaults() -> None:
    repo = UserProfileRepository()
    repo.get_or_create(
        user_id="hobbyist-catalog-user",
        role="member",
        plan_tier="hobbyist",
        org_id="org-default",
        access_token="test-token-for-hobbyist-catalog-user",
    )
    repo.update(
        "hobbyist-catalog-user",
        {
            "preferences": {
                "fidelity_configuration": {
                    "persona": "archivist",
                    "preferred_fidelity_tier": "Conserve",
                    "preferred_grain_preset": "Heavy",
                }
            }
        },
        access_token="test-token-for-hobbyist-catalog-user",
    )

    response = client.get("/v1/fidelity-tiers", headers=fake_auth_header("hobbyist-catalog-user", tier="hobbyist"))

    assert response.status_code == 200
    payload = response.json()
    assert [item["tier"] for item in payload["tiers"]] == ["Enhance"]
    assert {item["persona"]: item["default_fidelity_tier"] for item in payload["personas"]} == {
        "archivist": "Enhance",
        "filmmaker": "Enhance",
        "prosumer": "Enhance",
    }
    assert payload["current_persona"] == "archivist"
    assert payload["preferred_fidelity_tier"] == "Enhance"
    assert payload["preferred_grain_preset"] == "Heavy"


def test_fidelity_routes_ignore_invalid_saved_preferences() -> None:
    _seed_upload(upload_id="upload-invalid-prefs", owner_user_id="invalid-pref-user")
    repo = UserProfileRepository()
    repo.get_or_create(
        user_id="invalid-pref-user",
        role="member",
        plan_tier="pro",
        org_id="org-default",
        access_token="test-token-for-invalid-pref-user",
    )
    stored_profile = repo.update(
        "invalid-pref-user",
        {
            "preferences": {
                "fidelity_configuration": {
                    "persona": "legacy-operator",
                    "preferred_fidelity_tier": "Ultra",
                    "preferred_grain_preset": "Impossible",
                }
            }
        },
        access_token="test-token-for-invalid-pref-user",
    )
    assert stored_profile is not None
    assert stored_profile["preferences"]["fidelity_configuration"] == {
        "persona": "legacy-operator",
        "preferred_fidelity_tier": "Ultra",
        "preferred_grain_preset": "Impossible",
    }

    catalog = client.get("/v1/fidelity-tiers", headers=fake_auth_header("invalid-pref-user", tier="pro"))
    assert catalog.status_code == 200
    assert catalog.json()["current_persona"] is None
    assert catalog.json()["preferred_fidelity_tier"] is None
    assert catalog.json()["preferred_grain_preset"] is None

    save = client.patch(
        "/v1/upload/upload-invalid-prefs/configuration",
        headers=fake_auth_header("invalid-pref-user", tier="pro"),
        json={
            "persona": "prosumer",
            "fidelity_tier": "Enhance",
            "grain_preset": "Subtle",
            "estimated_duration_seconds": 120,
        },
    )

    assert save.status_code == 200
    assert save.json()["persona"] == "prosumer"


def test_detect_upload_era_requires_completed_upload() -> None:
    _seed_upload(upload_id="upload-pending", owner_user_id="pending-user", status=UploadStatus.PENDING)

    response = client.post(
        "/v1/upload/upload-pending/detect-era",
        headers=fake_auth_header("pending-user", tier="pro"),
        json={"estimated_duration_seconds": 180},
    )

    assert response.status_code == 409
    assert response.json()["title"] == "Upload Not Ready"


def test_detect_upload_era_enforces_owner_scope() -> None:
    _seed_upload(upload_id="upload-owner-scope", owner_user_id="owner-user")

    response = client.post(
        "/v1/upload/upload-owner-scope/detect-era",
        headers=fake_auth_header("other-user", tier="pro"),
        json={"estimated_duration_seconds": 180},
    )

    assert response.status_code == 404


def test_detect_upload_era_uses_validated_plan_tier_instead_of_stale_profile_data() -> None:
    _seed_upload(upload_id="upload-stale-plan-tier", owner_user_id="stale-plan-user")
    repo = UserProfileRepository()
    repo.get_or_create(
        user_id="stale-plan-user",
        role="member",
        plan_tier="pro",
        org_id="org-default",
        access_token="test-token-for-stale-plan-user",
    )
    repo.update(
        "stale-plan-user",
        {
            "plan_tier": "pro",
            "preferences": {
                "fidelity_configuration": {
                    "persona": "archivist",
                    "preferred_fidelity_tier": "Conserve",
                    "preferred_grain_preset": "Matched",
                }
            },
        },
        access_token="test-token-for-stale-plan-user",
    )

    response = client.post(
        "/v1/upload/upload-stale-plan-tier/detect-era",
        headers=fake_auth_header("stale-plan-user", tier="hobbyist"),
        json={"estimated_duration_seconds": 180},
    )

    assert response.status_code == 200
    assert response.json()["estimated_usage_minutes"] == 3


def test_detect_upload_era_rejects_override_reason_when_missing() -> None:
    _seed_upload(upload_id="upload-override-reason", owner_user_id="override-user", original_filename="mystery.mov")

    response = client.post(
        "/v1/upload/upload-override-reason/detect-era",
        headers=fake_auth_header("override-user", tier="pro"),
        json={
            "estimated_duration_seconds": 180,
            "manual_override_era": "1970s Super 8 Film",
        },
    )

    assert response.status_code == 400
    assert response.json()["title"] == "Override Reason Required"


def test_detect_upload_era_rejects_manual_override_when_confidence_is_high() -> None:
    _seed_upload(upload_id="upload-high-confidence", owner_user_id="override-user")

    response = client.post(
        "/v1/upload/upload-high-confidence/detect-era",
        headers=fake_auth_header("override-user", tier="pro"),
        json={
            "estimated_duration_seconds": 180,
            "manual_override_era": "1970s Super 8 Film",
            "override_reason": "Force alternate era",
        },
    )

    assert response.status_code == 400
    assert response.json()["title"] == "Manual Override Not Allowed"


def test_detect_upload_era_allows_low_confidence_override_and_persists_snapshot() -> None:
    upload = _seed_upload(upload_id="upload-low-confidence", owner_user_id="low-user", original_filename="mystery.mov")

    response = client.post(
        "/v1/upload/upload-low-confidence/detect-era",
        headers=fake_auth_header("low-user", tier="pro"),
        json={
            "estimated_duration_seconds": 180,
            "manual_override_era": "1970s Super 8 Film",
            "override_reason": "Visible sprocket pattern matches super 8",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["upload_id"] == upload["upload_id"]
    assert payload["era"] == "1970s Super 8 Film"
    assert payload["source"] == "user_override"
    repo = UploadRepository()
    stored = repo.get_session(
        "upload-low-confidence",
        owner_user_id="low-user",
        access_token="test-token-for-low-user",
    )
    assert stored is not None
    assert stored["detection_snapshot"]["upload_id"] == "upload-low-confidence"
    assert stored["detection_snapshot"]["override_reason"] == "Visible sprocket pattern matches super 8"


def test_save_configuration_requires_persona_when_preferences_are_empty() -> None:
    _seed_upload(upload_id="upload-missing-persona", owner_user_id="persona-user")

    response = client.patch(
        "/v1/upload/upload-missing-persona/configuration",
        headers=fake_auth_header("persona-user", tier="pro"),
        json={
            "fidelity_tier": "Restore",
            "grain_preset": "Matched",
            "estimated_duration_seconds": 180,
        },
    )

    assert response.status_code == 400
    assert response.json()["title"] == "Persona Required"


def test_save_configuration_updates_preferences_and_returns_job_payload_preview() -> None:
    _seed_upload(upload_id="upload-config", owner_user_id="config-user")

    response = client.patch(
        "/v1/upload/upload-config/configuration",
        headers=fake_auth_header("config-user", tier="pro"),
        json={
            "persona": "filmmaker",
            "fidelity_tier": "Enhance",
            "grain_preset": "Heavy",
            "estimated_duration_seconds": 180,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["persona"] == "filmmaker"
    assert payload["fidelity_tier"] == "Enhance"
    assert payload["grain_preset"] == "Heavy"
    assert payload["relative_cost_multiplier"] == 1.0
    assert payload["relative_processing_time_band"] == "<2 min/min"
    preview = payload["job_payload_preview"]
    assert {key: value for key, value in preview.items() if key != "era_profile"} == {
        "media_uri": "gs://chronos-test-bucket/uploads/config-user/upload-config/sample.mov",
        "original_filename": "sample.mov",
        "mime_type": "video/quicktime",
        "estimated_duration_seconds": 180,
        "source_asset_checksum": "abc12345def67890",
        "fidelity_tier": "Enhance",
        "reproducibility_mode": "perceptual_equivalence",
        "processing_mode": "balanced",
        "config": {
            "persona": "filmmaker",
            "grain_preset": "Heavy",
            "relative_cost_multiplier": 1.0,
            "relative_processing_time_band": "<2 min/min",
            "detection_snapshot": {
                "detection_id": payload["detection_snapshot"]["detection_id"],
                "era": payload["detection_snapshot"]["era"],
                "confidence": payload["detection_snapshot"]["confidence"],
                "source": payload["detection_snapshot"]["source"],
            },
            "fidelity_overrides": {
                "grain_intensity": "Heavy",
            },
        },
    }
    era_profile = preview["era_profile"]
    assert isinstance(era_profile, dict)
    assert era_profile["mode"] == "Enhance"
    assert era_profile["tier"] == "Pro"
    assert era_profile["resolution_cap"] == "4k"
    assert era_profile["hallucination_limit"] == 0.30
    assert era_profile["manual_confirmation_required"] is False
    assert era_profile["capture_medium"] in {"super_8", "kodachrome", "16mm", "vhs", "albumen", "daguerreotype"}
    assert era_profile["artifact_policy"]["grain_intensity"] == "Heavy"
    assert set(era_profile["era_range"]) == {"start_year", "end_year"}
    assert era_profile["era_range"]["start_year"] <= era_profile["era_range"]["end_year"]
    profile = client.get("/v1/users/me", headers=fake_auth_header("config-user", tier="pro"))
    assert profile.status_code == 200
    assert profile.json()["preferences"]["fidelity_configuration"] == {
        "persona": "filmmaker",
        "preferred_fidelity_tier": "Enhance",
        "preferred_grain_preset": "Heavy",
    }


def test_save_configuration_reuses_stored_persona_preference() -> None:
    _seed_upload(upload_id="upload-persona-default", owner_user_id="persona-default-user")
    client.patch(
        "/v1/users/me",
        headers=fake_auth_header("persona-default-user", tier="pro"),
        json={
            "preferences": {
                "fidelity_configuration": {
                    "persona": "archivist",
                    "preferred_fidelity_tier": "Conserve",
                    "preferred_grain_preset": "Matched",
                }
            }
        },
    )

    response = client.patch(
        "/v1/upload/upload-persona-default/configuration",
        headers=fake_auth_header("persona-default-user", tier="pro"),
        json={
            "fidelity_tier": "Conserve",
            "grain_preset": "Matched",
            "estimated_duration_seconds": 240,
        },
    )

    assert response.status_code == 200
    assert response.json()["persona"] == "archivist"


def test_save_configuration_allows_grain_override_for_conserve() -> None:
    _seed_upload(upload_id="upload-grain", owner_user_id="grain-user")

    response = client.patch(
        "/v1/upload/upload-grain/configuration",
        headers=fake_auth_header("grain-user", tier="pro"),
        json={
            "persona": "archivist",
            "fidelity_tier": "Conserve",
            "grain_preset": "Heavy",
            "estimated_duration_seconds": 180,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["grain_preset"] == "Heavy"
    assert payload["job_payload_preview"]["era_profile"]["artifact_policy"]["grain_intensity"] == "Heavy"
    assert payload["job_payload_preview"]["config"]["fidelity_overrides"]["grain_intensity"] == "Heavy"


def test_save_configuration_rejects_hobbyist_non_enhance_tiers_before_validation() -> None:
    _seed_upload(upload_id="upload-hobbyist-tier", owner_user_id="hobbyist-user")

    response = client.patch(
        "/v1/upload/upload-hobbyist-tier/configuration",
        headers=fake_auth_header("hobbyist-user", tier="hobbyist"),
        json={
            "persona": "filmmaker",
            "fidelity_tier": "Restore",
            "grain_preset": "Matched",
            "estimated_duration_seconds": 180,
        },
    )

    assert response.status_code == 403
    payload = response.json()
    assert payload["title"] == "Plan Upgrade Required"
    assert "Hobbyist includes Enhance only" in payload["detail"]

    repo = UploadRepository()
    session = repo.get_session(
        "upload-hobbyist-tier",
        owner_user_id="hobbyist-user",
        access_token="test-token-for-hobbyist-user",
    )
    assert session is not None
    assert session.get("launch_config") in ({}, None)
    assert session.get("configured_at") is None

    profile = client.get("/v1/users/me", headers=fake_auth_header("hobbyist-user", tier="hobbyist"))
    assert profile.status_code == 200
    assert profile.json()["preferences"] == {}


def test_save_configuration_blocks_hobbyist_early_photo_assets_before_persisting_launch_config() -> None:
    _seed_upload(
        upload_id="upload-early-photo",
        owner_user_id="photo-user",
        original_filename="albumen-portrait.tif",
        mime_type="image/tiff",
    )

    response = client.patch(
        "/v1/upload/upload-early-photo/configuration",
        headers=fake_auth_header("photo-user", tier="hobbyist"),
        json={
            "persona": "prosumer",
            "fidelity_tier": "Enhance",
            "grain_preset": "Matched",
            "estimated_duration_seconds": 180,
        },
    )

    assert response.status_code == 403
    payload = response.json()
    assert payload["title"] == "Plan Upgrade Required"
    assert "minimum 2k processing" in payload["detail"]

    repo = UploadRepository()
    session = repo.get_session(
        "upload-early-photo",
        owner_user_id="photo-user",
        access_token="test-token-for-photo-user",
    )
    assert session is not None
    assert session.get("launch_config") in ({}, None)
    assert session.get("configured_at") is None

    profile = client.get("/v1/users/me", headers=fake_auth_header("photo-user", tier="hobbyist"))
    assert profile.status_code == 200
    assert profile.json()["preferences"] == {}


def test_save_configuration_keeps_launch_config_when_preference_update_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    _seed_upload(upload_id="upload-partial-success", owner_user_id="partial-user")

    original_update = UserProfileRepository.update

    def failing_update(self: UserProfileRepository, user_id: str, patch: dict[str, object], *, access_token: str | None = None):
        if user_id == "partial-user":
            raise RuntimeError("profile persistence unavailable")
        return original_update(self, user_id, patch, access_token=access_token)

    monkeypatch.setattr(UserProfileRepository, "update", failing_update)

    response = client.patch(
        "/v1/upload/upload-partial-success/configuration",
        headers=fake_auth_header("partial-user", tier="pro"),
        json={
            "persona": "prosumer",
            "fidelity_tier": "Enhance",
            "grain_preset": "Subtle",
            "estimated_duration_seconds": 180,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["persona"] == "prosumer"

    repo = UploadRepository()
    session = repo.get_session(
        "upload-partial-success",
        owner_user_id="partial-user",
        access_token="test-token-for-partial-user",
    )
    assert session is not None
    assert session.get("launch_config")
    assert session.get("configured_at")

    profile = client.get("/v1/users/me", headers=fake_auth_header("partial-user", tier="pro"))
    assert profile.status_code == 200
    assert profile.json()["preferences"] == {}
