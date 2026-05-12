"""
Maps to:
- SEC-005
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.db.phase2_store import (
    JobRepository,
    ManifestRepository,
    ManifestRetentionSettingsRepository,
    _SupabaseManifestRepository,
    reset_phase2_store,
)
from app.services.manifest_retention import ManifestRetentionService
from app.services.transformation_manifest import GcsManifestStore, finalize_manifest_payload


@pytest.fixture(autouse=True)
def reset_state() -> None:
    reset_phase2_store()


def _job_payload(*, tier: str = "pro", org_id: str = "org-5h") -> dict[str, Any]:
    return {
        "job_id": f"manifest-{tier}",
        "owner_user_id": "manifest-owner",
        "org_id": org_id,
        "era_profile": {"capture_medium": "16mm"},
        "plan_tier": tier,
        "effective_fidelity_tier": "Restore",
        "effective_fidelity_profile": {"tier": "Restore", "identity_lock": False},
        "reproducibility_mode": "deterministic",
        "status": "completed",
        "quality_summary": {"e_hf": 0.9, "s_ls_db": -1.0, "t_tc": 0.95, "thresholds_met": True},
        "reproducibility_summary": {"mode": "deterministic", "verification_status": "verified"},
        "stage_timings": {"processing_ms": 1000},
        "gpu_summary": {},
        "cost_summary": {},
        "cache_summary": {},
        "slo_summary": {"target_total_ms": 120000},
        "warnings": [],
        "result_uri": "gs://chronos-outputs/jobs/manifest/result.mp4",
    }


class RecordingStore:
    def __init__(self) -> None:
        self.stored: list[dict[str, Any]] = []
        self.patched: list[str] = []
        self.deleted: list[str] = []

    def store(
        self,
        *,
        job_id: str,
        payload: dict[str, Any],
        retention_class: str,
        object_basename: str,
        variant: str = "full",
    ) -> tuple[str, int]:
        suffix = ".redacted.json" if variant == "redacted" else ".json"
        uri = f"gs://chronos/manifests/{retention_class}/{job_id}/{object_basename}{suffix}"
        self.stored.append(
            {
                "job_id": job_id,
                "payload": dict(payload),
                "retention_class": retention_class,
                "object_basename": object_basename,
                "variant": variant,
                "uri": uri,
            }
        )
        return uri, 512

    def patch_object_metadata(self, *, object_uri: str, metadata: dict[str, str]) -> bool:
        del metadata
        self.patched.append(object_uri)
        return False

    def delete_object(self, *, object_uri: str) -> bool:
        self.deleted.append(object_uri)
        return False


def test_tier_defaults_resolve_manifest_retention_classes() -> None:
    service = ManifestRetentionService()

    hobbyist = service.resolve_policy(org_id="org-hobbyist", plan_tier="hobbyist", generated_at="2026-05-11T00:00:00+00:00")
    pro = service.resolve_policy(org_id="org-pro", plan_tier="pro", generated_at="2026-05-11T00:00:00+00:00")
    museum = service.resolve_policy(org_id="org-museum", plan_tier="museum", generated_at="2026-05-11T00:00:00+00:00")

    assert (hobbyist.retention_days, hobbyist.retention_class) == (7, "7d")
    assert hobbyist.retention_expires_at == "2026-05-18T00:00:00+00:00"
    assert (pro.retention_days, pro.retention_class) == (90, "90d")
    assert pro.retention_expires_at == "2026-08-09T00:00:00+00:00"
    assert (museum.retention_days, museum.retention_class, museum.retention_expires_at) == (None, "indefinite", None)


@pytest.mark.parametrize(
    ("retention_days", "expected_class"),
    [(0, "0d"), (90, "90d"), (365, "365d"), (1825, "1825d"), (None, "indefinite")],
)
def test_museum_org_settings_cover_all_sec005_options(retention_days: int | None, expected_class: str) -> None:
    ManifestRetentionSettingsRepository().upsert(
        org_id="museum-org",
        plan_tier="museum",
        manifest_retention_days=retention_days,
        manifest_redaction_enabled=False,
        updated_by="platform-admin",
    )

    policy = ManifestRetentionService().resolve_policy(
        org_id="museum-org",
        plan_tier="museum",
        generated_at="2026-05-11T00:00:00+00:00",
    )

    assert policy.retention_days == retention_days
    assert policy.retention_class == expected_class


def test_non_museum_settings_fail_closed() -> None:
    with pytest.raises(ValueError):
        ManifestRetentionSettingsRepository().upsert(
            org_id="pro-org",
            plan_tier="pro",
            manifest_retention_days=90,
            manifest_redaction_enabled=True,
            updated_by="platform-admin",
        )


def test_manifest_store_uses_retention_aware_prefix_and_shared_basename() -> None:
    store = RecordingStore()

    result = finalize_manifest_payload(
        manifest_id="manifest-pro",
        generated_at="2026-05-11T00:00:00+00:00",
        job=_job_payload(tier="pro"),
        segments=[],
        store=store,
    )

    assert result["payload"]["manifest_uri"].startswith("gs://chronos/manifests/90d/manifest-pro/")
    assert store.stored[0]["object_basename"]
    assert result["classification"]["retention_class"] == "90d"
    assert result["classification"]["retention_policy_source"] == "tier_default"


def test_zero_day_writes_patches_and_returns_post_persist_delete_intent() -> None:
    ManifestRetentionSettingsRepository().upsert(
        org_id="museum-zero",
        plan_tier="museum",
        manifest_retention_days=0,
        manifest_redaction_enabled=False,
        updated_by="platform-admin",
    )
    store = RecordingStore()

    result = finalize_manifest_payload(
        manifest_id="manifest-museum",
        generated_at="2026-05-11T00:00:00+00:00",
        job=_job_payload(tier="museum", org_id="museum-zero"),
        segments=[],
        store=store,
    )

    assert result["payload"]["manifest_uri"].startswith("gs://chronos/manifests/0d/manifest-museum/")
    assert result["classification"]["retention_delete_status"] == "pending"
    assert result["classification"]["retention_delete_attempted_at"]
    assert "retention_deleted_at" not in result["classification"]
    assert store.patched == [result["payload"]["manifest_uri"]]
    assert result["deletion"]["object_uris"] == [result["payload"]["manifest_uri"]]
    assert store.deleted == []


def test_memory_manifest_repository_hides_expired_and_deleted_records() -> None:
    job_repo = JobRepository()
    manifest_repo = ManifestRepository()
    job_repo.create_job(
        job_id="expired-manifest",
        owner_user_id="manifest-owner",
        plan_tier="pro",
        org_id="org-expired",
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
    payload = {
        "manifest_id": "expired-manifest",
        "job_id": "expired-manifest",
        "generated_at": "2026-05-11T00:00:00+00:00",
        "user_id": "manifest-owner",
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
        "model_versions": {},
        "environment": {},
        "segments": [],
        "uncertainty_callouts": [],
        "warnings": [],
        "result_uri": None,
        "manifest_uri": "gs://chronos/manifests/90d/expired-manifest/a.json",
        "manifest_sha256": "hash",
        "size_bytes": 512,
    }
    manifest_repo.upsert_manifest_for_worker(
        job_id="expired-manifest",
        manifest=payload,
        retention={"retention_expires_at": "2026-01-01T00:00:00+00:00"},
    )
    assert manifest_repo.get_manifest("expired-manifest", owner_user_id="manifest-owner") is None

    manifest_repo.upsert_manifest_for_worker(
        job_id="expired-manifest",
        manifest=payload,
        retention={"retention_expires_at": None, "retention_delete_status": "pending"},
    )
    assert manifest_repo.get_manifest("expired-manifest", owner_user_id="manifest-owner") is None


def test_supabase_rest_manifest_filter_includes_retention_guards() -> None:
    captured: dict[str, Any] = {}

    class FakeClient:
        def user_scoped_headers(self, access_token: str) -> dict[str, str]:
            return {"Authorization": f"Bearer {access_token}"}

        def rest_select(self, table_name: str, *, params: dict[str, str], headers: dict[str, str]) -> list[dict[str, Any]]:
            captured.update({"table_name": table_name, "params": params, "headers": headers})
            return []

    repo = _SupabaseManifestRepository()
    repo._client = FakeClient()  # type: ignore[assignment]

    assert repo.get_manifest("job-rest", access_token="token-rest") is None
    assert captured["table_name"] == "job_manifests"
    assert captured["params"]["retention_deleted_at"] == "is.null"
    assert captured["params"]["retention_delete_status"] == "is.null"
    assert captured["params"]["or"].startswith("(retention_expires_at.is.null,retention_expires_at.gt.")


def test_gcs_lifecycle_rules_target_only_finite_manifest_prefixes() -> None:
    root = Path(__file__).resolve().parents[2]
    lifecycle_tf = (root / "infra" / "terraform" / "storage_lifecycle.tf").read_text(encoding="utf-8")

    for prefix in ("manifests/7d/", "manifests/90d/", "manifests/365d/", "manifests/1825d/"):
        assert prefix in lifecycle_tf
    assert "manifests/0d/" not in lifecycle_tf
    assert "manifests/indefinite/" not in lifecycle_tf
    assert "authoritative" in lifecycle_tf
