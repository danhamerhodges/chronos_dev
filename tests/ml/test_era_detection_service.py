"""Maps to: ENG-004, FR-002"""

from app.db.phase2_store import EraDetectionRepository
from app.services.era_classifier import ClassifierError, EraClassification, EraClassifierUsage
from app.services.era_detection_service import EraDetectionService
from tests.helpers.phase2 import valid_detect_request


class StubClassifier:
    def classify(self, *, job_id, media_uri, original_filename, mime_type, era_profile):
        return EraClassification(
            era="1960s Kodachrome Film",
            confidence=0.88,
            forensic_markers={
                "grain_structure": "dense color grain",
                "color_saturation": 0.82,
                "format_artifacts": ["saturated_reds", "dye_stability"],
            },
            top_candidates=[
                {"era": "1960s Kodachrome Film", "confidence": 0.88},
                {"era": "1950s Kodachrome Film", "confidence": 0.54},
                {"era": "1970s Super 8 Film", "confidence": 0.31},
            ],
            model_version="gemini-2.5-pro-live",
            prompt_version="phase2-era-detection-v2",
            raw_response_gcs_uri="gs://chronos-dev/era-detection/raw/job-123/resp-1.json",
            usage=EraClassifierUsage(
                prompt_token_count=111,
                candidates_token_count=27,
                total_token_count=138,
                api_call_count=1,
            ),
        )


class RaisingClassifier:
    def classify(self, *, job_id, media_uri, original_filename, mime_type, era_profile):
        raise ClassifierError("vertex unavailable")


class UnexpectedRuntimeErrorClassifier:
    def classify(self, *, job_id, media_uri, original_filename, mime_type, era_profile):
        raise RuntimeError("unexpected classifier bug")


class UnsupportedEraClassifier:
    def classify(self, *, job_id, media_uri, original_filename, mime_type, era_profile):
        return EraClassification(
            era="Early Digital Era",
            confidence=0.95,
            forensic_markers={
                "grain_structure": "compressed digital noise",
                "color_saturation": 0.77,
                "format_artifacts": ["macroblocking"],
            },
            top_candidates=[
                {"era": "Early Digital Era", "confidence": 0.95},
                {"era": "1960s Kodachrome", "confidence": 0.52},
            ],
            model_version="gemini-2.5-pro-live",
            prompt_version="phase2-era-detection-v2",
            usage=EraClassifierUsage(
                prompt_token_count=91,
                candidates_token_count=14,
                total_token_count=105,
                api_call_count=1,
            ),
        )


def test_service_persists_detection_metadata_for_auditability() -> None:
    service = EraDetectionService()
    service._classifier = StubClassifier()
    request = valid_detect_request()

    response = service.detect(
        job_id=request["job_id"],
        user_id="user-1",
        org_id="org-default",
        media_uri=request["media_uri"],
        original_filename=request["original_filename"],
        mime_type=request["mime_type"],
        payload=request,
    )
    latest = EraDetectionRepository().latest_detection(request["job_id"])

    assert response["detection_id"]
    assert latest is not None
    assert latest["model_version"] == "gemini-2.5-pro-live"
    assert latest["prompt_version"] == "phase2-era-detection-v2"
    assert latest["source"] == "system"
    assert latest["raw_response_gcs_uri"] == "gs://chronos-dev/era-detection/raw/job-123/resp-1.json"
    assert latest["prompt_token_count"] == 111
    assert latest["candidates_token_count"] == 27
    assert latest["total_token_count"] == 138
    assert latest["api_call_count"] == 1


def test_provider_failure_returns_unknown_and_requires_manual_confirmation() -> None:
    service = EraDetectionService()
    service._classifier = RaisingClassifier()
    request = valid_detect_request()

    response = service.detect(
        job_id=request["job_id"],
        user_id="user-1",
        org_id="org-default",
        media_uri=request["media_uri"],
        original_filename=request["original_filename"],
        mime_type=request["mime_type"],
        payload=request,
    )

    assert response["era"] == "Unknown Era"
    assert response["manual_confirmation_required"] is True
    assert response["source"] == "system"
    assert len(response["top_candidates"]) == 3
    assert any("Manual confirmation required" in warning for warning in response["warnings"])


def test_unexpected_runtime_error_is_not_swallowed_by_fallback() -> None:
    service = EraDetectionService()
    service._classifier = UnexpectedRuntimeErrorClassifier()
    request = valid_detect_request()

    try:
        service.detect(
            job_id=request["job_id"],
            user_id="user-1",
            org_id="org-default",
            media_uri=request["media_uri"],
            original_filename=request["original_filename"],
            mime_type=request["mime_type"],
            payload=request,
        )
    except RuntimeError as exc:
        assert str(exc) == "unexpected classifier bug"
    else:
        raise AssertionError("Expected unexpected RuntimeError to propagate without fallback.")


def test_unsupported_provider_era_returns_unknown_with_canonical_candidates() -> None:
    service = EraDetectionService()
    service._classifier = UnsupportedEraClassifier()
    request = valid_detect_request()

    response = service.detect(
        job_id=request["job_id"],
        user_id="user-1",
        org_id="org-default",
        media_uri=request["media_uri"],
        original_filename=request["original_filename"],
        mime_type=request["mime_type"],
        payload=request,
    )

    assert response["era"] == "Unknown Era"
    assert response["manual_confirmation_required"] is True
    assert response["top_candidates"] == [
        {"era": "1960s Kodachrome Film", "confidence": 0.52},
        {"era": "1970s Super 8 Film", "confidence": 0.52},
        {"era": "1980s VHS Tape", "confidence": 0.41},
    ]
    assert any("unsupported era label" in warning for warning in response["warnings"])


def test_manual_override_persists_system_and_override_records() -> None:
    service = EraDetectionService()
    service._classifier = StubClassifier()
    captured_calls: list[dict[str, object]] = []

    class FakeRepo:
        def save_job(self, **kwargs):
            return {"job_id": kwargs["job_id"]}

        def save_detection(self, *, job_id, detection, access_token=None):
            captured_calls.append(detection)
            return {"id": f"detection-{len(captured_calls)}", **detection}

    service._repo = FakeRepo()
    request = valid_detect_request(
        manual_override_era="1950s Kodachrome Film",
        override_reason="Archivist confirmed sleeve metadata",
    )

    response = service.detect(
        job_id=request["job_id"],
        user_id="user-override",
        org_id="org-default",
        media_uri=request["media_uri"],
        original_filename=request["original_filename"],
        mime_type=request["mime_type"],
        payload=request,
    )

    assert len(captured_calls) == 2
    assert captured_calls[0]["source"] == "system"
    assert captured_calls[0]["created_by"] is None
    assert captured_calls[0]["api_call_count"] == 1
    assert captured_calls[1]["source"] == "user_override"
    assert captured_calls[1]["created_by"] == "user-override"
    assert captured_calls[1]["override_reason"] == "Archivist confirmed sleeve metadata"
    assert captured_calls[1]["api_call_count"] == 0
    assert response["source"] == "user_override"
    assert response["era"] == "1950s Kodachrome Film"
    assert response["confidence"] == 0.88


def test_unsupported_manual_override_is_rejected() -> None:
    service = EraDetectionService()
    service._classifier = StubClassifier()
    request = valid_detect_request(
        manual_override_era="Early Digital Era",
        override_reason="Not in supported catalog",
    )

    try:
        service.detect(
            job_id=request["job_id"],
            user_id="user-override",
            org_id="org-default",
            media_uri=request["media_uri"],
            original_filename=request["original_filename"],
            mime_type=request["mime_type"],
            payload=request,
        )
    except ValueError as exc:
        assert str(exc) == "Manual override era must use a supported catalog value."
    else:
        raise AssertionError("Expected manual override validation to reject unsupported era label.")
