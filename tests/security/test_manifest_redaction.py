"""
Maps to:
- SEC-005
"""

from __future__ import annotations

from typing import Any

import pytest

from app.db.phase2_store import ManifestRetentionSettingsRepository, reset_phase2_store
from app.services.transformation_manifest import finalize_manifest_payload


@pytest.fixture(autouse=True)
def reset_state() -> None:
    reset_phase2_store()


class RecordingStore:
    def __init__(self) -> None:
        self.stored: list[dict[str, Any]] = []

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
        del object_uri, metadata
        return False


def _job_payload() -> dict[str, Any]:
    return {
        "job_id": "museum-redaction-job",
        "owner_user_id": "museum-owner",
        "org_id": "museum-redaction-org",
        "era_profile": {"capture_medium": "35mm", "detected_era": "1970s"},
        "plan_tier": "museum",
        "effective_fidelity_tier": "Restore",
        "effective_fidelity_profile": {"tier": "Restore", "identity_lock": True},
        "reproducibility_mode": "deterministic",
        "status": "completed",
        "quality_summary": {"e_hf": 0.9, "s_ls_db": -1.0, "t_tc": 0.95, "thresholds_met": True},
        "reproducibility_summary": {
            "mode": "deterministic",
            "verification_status": "pass",
            "failed_segment_count": 0,
            "rerun_count": 0,
            "rollup": "pass",
            "metric_epsilon_percent": 0.5,
            "environment_fingerprint": "fingerprint",
        },
        "stage_timings": {"processing_ms": 1000},
        "gpu_summary": {"gpu_type": "l4", "gpu_seconds": 10},
        "cost_summary": {},
        "cache_summary": {},
        "slo_summary": {"target_total_ms": 120000},
        "warnings": ["minor grain uncertainty"],
        "result_uri": "gs://chronos-outputs/jobs/museum-redaction-job/result.mp4",
    }


def _segments() -> list[dict[str, Any]]:
    return [
        {
            "segment_index": 0,
            "segment_start_seconds": 0,
            "segment_end_seconds": 5,
            "quality_metrics": {
                "e_hf": 0.9,
                "s_ls_db": -1.0,
                "t_tc": 0.95,
                "thresholds_met": True,
                "sampling_protocol": {
                    "frames_per_second": 1.0,
                    "frames_sampled": 5,
                    "sampled_timestamps_seconds": [0.0, 1.0],
                    "downscale_rule": "720p",
                    "roi_256": {"x": 0, "y": 0, "width": 256, "height": 256},
                    "roi_512": {"x": 0, "y": 0, "width": 512, "height": 512},
                    "roi_full_frame": {"x": 0, "y": 0, "width": 1280, "height": 720},
                    "roi_source": "center_crop",
                },
            },
            "uncertainty_callouts": ["low-light"],
            "reproducibility_proof": {"seed": "stable"},
            "output_uri": "gs://chronos-outputs/jobs/museum-redaction-job/segment-0.mp4",
        }
    ]


def test_museum_redaction_enabled_generates_full_and_redacted_manifests_with_shared_basename() -> None:
    ManifestRetentionSettingsRepository().upsert(
        org_id="museum-redaction-org",
        plan_tier="museum",
        manifest_retention_days=90,
        manifest_redaction_enabled=True,
        updated_by="platform-admin",
    )
    store = RecordingStore()

    result = finalize_manifest_payload(
        manifest_id="museum-redaction-job",
        generated_at="2026-05-11T00:00:00+00:00",
        job=_job_payload(),
        segments=_segments(),
        store=store,
    )

    assert [record["variant"] for record in store.stored] == ["full", "redacted"]
    assert store.stored[0]["object_basename"] == store.stored[1]["object_basename"]
    assert result["payload"]["manifest_uri"].endswith(".json")
    assert result["redaction"]["redacted_manifest_uri"].endswith(".redacted.json")
    assert result["redaction"]["redacted_payload"]["source_manifest_sha256"] == result["payload"]["manifest_sha256"]


def test_redacted_manifest_excludes_pii_paths_and_operational_environment() -> None:
    ManifestRetentionSettingsRepository().upsert(
        org_id="museum-redaction-org",
        plan_tier="museum",
        manifest_retention_days=None,
        manifest_redaction_enabled=True,
        updated_by="platform-admin",
    )

    result = finalize_manifest_payload(
        manifest_id="museum-redaction-job",
        generated_at="2026-05-11T00:00:00+00:00",
        job=_job_payload(),
        segments=_segments(),
        store=RecordingStore(),
    )

    redacted_payload = result["redaction"]["redacted_payload"]
    redacted_text = str(redacted_payload)
    assert "user_id" not in redacted_payload
    assert "generated_at" not in redacted_payload
    assert "manifest_uri" not in redacted_payload
    assert "result_uri" not in redacted_payload
    assert "environment" not in redacted_payload
    assert "gpu_usage" not in redacted_payload
    assert "warnings" not in redacted_payload
    assert "uncertainty_callouts" not in redacted_payload
    assert "output_uri" not in redacted_payload["segments"][0]
    assert "uncertainty_callouts" not in redacted_payload["segments"][0]
    assert "museum-owner" not in redacted_text
    assert "gs://" not in redacted_text
    assert redacted_payload["era_profile"]["capture_medium"] == "35mm"
    assert redacted_payload["model_versions"]
    assert redacted_payload["segments"][0]["reproducibility_proof"] == {"seed": "stable"}


def test_non_museum_or_disabled_setting_does_not_generate_redacted_manifest() -> None:
    store = RecordingStore()

    result = finalize_manifest_payload(
        manifest_id="pro-job",
        generated_at="2026-05-11T00:00:00+00:00",
        job={**_job_payload(), "job_id": "pro-job", "plan_tier": "pro", "org_id": "pro-org"},
        segments=[],
        store=store,
    )

    assert [record["variant"] for record in store.stored] == ["full"]
    assert result["redaction"] == {}
    assert "redacted_manifest_uri" not in result["payload"]
    assert "retention_class" not in result["payload"]
