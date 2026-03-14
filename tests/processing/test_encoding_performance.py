"""Maps to: ENG-015"""

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
