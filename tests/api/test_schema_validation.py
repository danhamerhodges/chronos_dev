"""Maps to: ENG-001"""

from tests.helpers.phase2 import valid_era_profile

from app.validation.schema_validation import SCHEMA_DRAFT, load_schema, validate_era_profile


def test_schema_file_declares_canonical_draft_and_enums() -> None:
    schema = load_schema()
    assert schema["$schema"] == SCHEMA_DRAFT
    assert "daguerreotype" in schema["properties"]["capture_medium"]["enum"]
    assert "Museum" in schema["properties"]["tier"]["enum"]


def test_validate_era_profile_accepts_valid_payload() -> None:
    result = validate_era_profile(valid_era_profile())
    assert result.is_valid is True
    assert result.errors == []
    assert result.latency_ms >= 0


def test_validate_era_profile_enforces_vhs_deinterlace_rule() -> None:
    result = validate_era_profile(
        valid_era_profile(
            capture_medium="vhs",
            artifact_policy={
                "deinterlace": False,
                "grain_intensity": "Subtle",
                "preserve_edge_fog": False,
                "preserve_chromatic_aberration": False,
            },
        )
    )
    assert result.is_valid is False
    assert any(issue.rule_id == "VR-001" for issue in result.errors)


def test_validate_era_profile_enforces_low_confidence_confirmation() -> None:
    result = validate_era_profile(
        valid_era_profile(
            gemini_confidence=0.61,
            manual_confirmation_required=False,
        )
    )
    assert result.is_valid is False
    assert any(issue.rule_id == "VR-003" for issue in result.errors)
