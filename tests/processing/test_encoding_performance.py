"""Maps to: ENG-015"""

from datetime import datetime, timezone

from app.services.output_delivery import OutputDeliveryService, resolve_output_encoding


def test_package_size_estimate_stays_positive_for_export_variants() -> None:
    service = OutputDeliveryService()
    av1_size = service._estimate_package_size(  # noqa: SLF001 - deterministic Packet 4D sizing helper
        duration_seconds=180,
        encoding=resolve_output_encoding(plan_tier="pro", variant="av1"),
        package_contents=[
            "job-av1.mp4",
            "transformation_manifest.json",
            "uncertainty_callouts.json",
            "quality_report.pdf",
            "deletion_proof.pdf",
        ],
    )
    h264_size = service._estimate_package_size(  # noqa: SLF001 - deterministic Packet 4D sizing helper
        duration_seconds=180,
        encoding=resolve_output_encoding(plan_tier="pro", variant="h264"),
        package_contents=[
            "job-h264.mp4",
            "transformation_manifest.json",
            "uncertainty_callouts.json",
            "quality_report.pdf",
            "deletion_proof.pdf",
        ],
    )

    assert av1_size > 0
    assert h264_size > 0
    assert av1_size < h264_size


def test_deletion_proof_id_stays_stable_for_repeat_materialization_inputs() -> None:
    service = OutputDeliveryService()
    job = {
        "job_id": "job-stable-proof",
        "owner_user_id": "proof-owner",
        "source_asset_checksum": "abc12345def67890",
        "result_uri": "gs://chronos/jobs/job-stable-proof/result.mp4",
        "fidelity_tier": "Restore",
        "effective_fidelity_tier": "Restore",
    }
    manifest_payload = {
        "manifest_sha256": "manifest-sha",
    }
    generated_at = datetime(2026, 3, 14, tzinfo=timezone.utc)

    first = service._build_deletion_proof(  # noqa: SLF001 - deterministic Packet 4D proof helper
        job=job,
        manifest_payload=manifest_payload,
        callouts=[],
        generated_at=generated_at,
    )
    second = service._build_deletion_proof(  # noqa: SLF001 - deterministic Packet 4D proof helper
        job=job,
        manifest_payload=manifest_payload,
        callouts=[],
        generated_at=generated_at,
    )

    assert first["deletion_proof_id"] == second["deletion_proof_id"]
