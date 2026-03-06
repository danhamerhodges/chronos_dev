"""Maps to: ENG-001, ENG-002, ENG-004, FR-002, NFR-007"""

from fastapi.testclient import TestClient

import app.api.era_detection as era_detection_module
from app.main import app
from tests.helpers.auth import fake_auth_header
from tests.helpers.phase2 import valid_detect_request, valid_era_profile

client = TestClient(app)


def test_detect_era_returns_detection_response_and_usage_estimate() -> None:
    response = client.post(
        "/v1/detect-era",
        headers=fake_auth_header("user-42", tier="pro"),
        json=valid_detect_request(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["era"] == "1960s Kodachrome Film"
    assert payload["manual_confirmation_required"] is False
    assert payload["estimated_usage_minutes"] == 3
    assert payload["top_candidates"] == []
    assert payload["source"] == "system"


def test_detect_era_schema_validation_failure_returns_problem_detail() -> None:
    request = valid_detect_request(era_profile=valid_era_profile(mode="Conserve", hallucination_limit=0.2))
    response = client.post(
        "/v1/detect-era",
        headers=fake_auth_header("user-77", tier="museum"),
        json=request,
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["title"] == "Schema Validation Failed"
    assert any(error["rule_id"] == "VR-002" for error in payload["errors"])


def test_detect_era_low_confidence_returns_unknown_with_top_candidates() -> None:
    request = valid_detect_request(
        media_uri="gs://chronos-dev/uploads/mystery-reel.mov",
        era_profile=valid_era_profile(gemini_confidence=0.61, manual_confirmation_required=True),
    )
    response = client.post(
        "/v1/detect-era",
        headers=fake_auth_header("user-88", tier="pro"),
        json=request,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["era"] == "Unknown Era"
    assert payload["manual_confirmation_required"] is True
    assert len(payload["top_candidates"]) == 3
    assert payload["warnings"]


def test_detect_era_rejects_unsupported_manual_override() -> None:
    response = client.post(
        "/v1/detect-era",
        headers=fake_auth_header("user-91", tier="pro"),
        json=valid_detect_request(
            manual_override_era="Early Digital Era",
            override_reason="Outside canonical catalog",
        ),
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["title"] == "Unsupported Era Override"
    assert payload["errors"] == [
        {
            "field": "manual_override_era",
            "message": "Manual override era must match the supported era catalog.",
            "rule_id": "FR-002",
        }
    ]


def test_detect_era_blocks_before_detection_when_budget_requires_overage(monkeypatch) -> None:
    calls = {"detect": 0}

    class StubDetectionService:
        def detect(self, **kwargs):
            calls["detect"] += 1
            raise AssertionError("Detection should not run when hard-stop is active.")

    monkeypatch.setattr(era_detection_module, "_era_detection_service", StubDetectionService())

    response = client.post(
        "/v1/detect-era",
        headers=fake_auth_header("user-budget-stop", tier="hobbyist"),
        json=valid_detect_request(estimated_duration_seconds=60 * 300),
    )

    assert response.status_code == 403
    payload = response.json()
    assert payload["title"] == "Overage Approval Required"
    assert payload["errors"] == [
        {
            "field": "estimated_duration_seconds",
            "message": "The projected usage exceeds the available monthly processing budget.",
            "rule_id": "NFR-007",
        }
    ]
    assert calls["detect"] == 0
