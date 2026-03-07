"""Maps to: ENG-010"""

from app.services.transformation_manifest import ReferenceEncodingProvider


def test_encoding_contract_exposes_av1_manifest_version_slot() -> None:
    metadata = ReferenceEncodingProvider().version_metadata()

    assert metadata["av1_encoder"] == "reference-av1-fgs-contract-v1"
    assert metadata["encoding_profile"] == "reference-balanced-profile"
