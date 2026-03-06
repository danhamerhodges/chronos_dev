"""Maps to: ENG-004, FR-002"""

import json

import httpx

from app.services.vertex_gemini import GcsRawResponseStore, VertexGeminiEraClassifier
from tests.helpers.phase2 import valid_detect_request


class StubTokenProvider:
    def access_token(self) -> str:
        return "gcp-access-token"


class StubRawResponseStore:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def store(self, *, job_id, response_id, payload, access_token):
        self.calls.append(
            {
                "job_id": job_id,
                "response_id": response_id,
                "payload": payload,
                "access_token": access_token,
            }
        )
        return f"gs://chronos-dev/era-detection/raw/{job_id}/{response_id}.json"


def test_vertex_gemini_classifier_parses_response_and_uploads_raw_payload(monkeypatch) -> None:
    raw_store = StubRawResponseStore()
    classifier = VertexGeminiEraClassifier(
        token_provider=StubTokenProvider(),
        raw_response_store=raw_store,
    )

    def _post(url, *, headers=None, json=None, timeout=None):
        assert "Authorization" in headers
        assert json["contents"][0]["parts"][1]["fileData"]["fileUri"].startswith("gs://")
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "responseId": "resp-1",
                "modelVersion": "gemini-2.5-pro-live",
                "usageMetadata": {
                    "promptTokenCount": 120,
                    "candidatesTokenCount": 42,
                    "totalTokenCount": 162,
                },
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": json_module.dumps(
                                        {
                                            "era": "1960s Kodachrome Film",
                                            "confidence": 0.88,
                                            "top_candidates": [
                                                {"era": "1960s Kodachrome Film", "confidence": 0.88},
                                                {"era": "1950s Kodachrome Film", "confidence": 0.54},
                                                {"era": "1970s Super 8 Film", "confidence": 0.31},
                                            ],
                                            "forensic_markers": {
                                                "grain_structure": "dense color grain",
                                                "color_saturation": 0.82,
                                                "format_artifacts": ["saturated_reds", "dye_stability"],
                                            },
                                        }
                                    )
                                }
                            ]
                        }
                    }
                ],
            },
        )

    json_module = json
    monkeypatch.setattr(httpx, "post", _post)
    request = valid_detect_request()

    result = classifier.classify(
        job_id=request["job_id"],
        media_uri=request["media_uri"],
        original_filename=request["original_filename"],
        mime_type=request["mime_type"],
        era_profile=request["era_profile"],
    )

    assert result.era == "1960s Kodachrome Film"
    assert result.confidence == 0.88
    assert result.raw_response_gcs_uri == "gs://chronos-dev/era-detection/raw/job-123/resp-1.json"
    assert result.usage.total_token_count == 162
    assert raw_store.calls[0]["job_id"] == "job-123"


def test_vertex_gemini_classifier_supports_inline_media(monkeypatch) -> None:
    classifier = VertexGeminiEraClassifier(
        token_provider=StubTokenProvider(),
        raw_response_store=StubRawResponseStore(),
    )

    def _post(url, *, headers=None, json=None, timeout=None):
        inline_part = json["contents"][0]["parts"][1]["inlineData"]
        assert inline_part["mimeType"] == "image/png"
        assert inline_part["data"]
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "responseId": "resp-inline",
                "modelVersion": "gemini-2.5-pro-live",
                "usageMetadata": {"totalTokenCount": 22},
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": json_module.dumps(
                                        {
                                            "era": "1960s Kodachrome Film",
                                            "confidence": 0.91,
                                            "top_candidates": [
                                                {"era": "1960s Kodachrome Film", "confidence": 0.91},
                                                {"era": "1950s Kodachrome Film", "confidence": 0.5},
                                                {"era": "1970s Super 8 Film", "confidence": 0.3},
                                            ],
                                            "forensic_markers": {
                                                "grain_structure": "dense color grain",
                                                "color_saturation": 0.82,
                                                "format_artifacts": ["saturated_reds"],
                                            },
                                        }
                                    )
                                }
                            ]
                        }
                    }
                ],
            },
        )

    json_module = json
    monkeypatch.setattr(httpx, "post", _post)

    result = classifier.classify(
        job_id="job-inline",
        media_uri="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9VE3dNwAAAAASUVORK5CYII=",
        original_filename="inline.png",
        mime_type="image/png",
        era_profile=valid_detect_request()["era_profile"],
    )

    assert result.era == "1960s Kodachrome Film"
    assert result.usage.total_token_count == 22


def test_vertex_gemini_classifier_marks_unsupported_primary_era_for_manual_confirmation(monkeypatch) -> None:
    classifier = VertexGeminiEraClassifier(
        token_provider=StubTokenProvider(),
        raw_response_store=StubRawResponseStore(),
    )

    def _post(url, *, headers=None, json=None, timeout=None):
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "responseId": "resp-unsupported",
                "modelVersion": "gemini-2.5-pro-live",
                "usageMetadata": {"totalTokenCount": 33},
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": json_module.dumps(
                                        {
                                            "era": "Early Digital Era",
                                            "confidence": 0.95,
                                            "top_candidates": [
                                                {"era": "Early Digital Era", "confidence": 0.95},
                                                {"era": "1960s Kodachrome", "confidence": 0.51},
                                                {"era": "VHS", "confidence": 0.33},
                                            ],
                                            "forensic_markers": {
                                                "grain_structure": "compressed digital noise",
                                                "color_saturation": 0.73,
                                                "format_artifacts": ["macroblocking"],
                                            },
                                        }
                                    )
                                }
                            ]
                        }
                    }
                ],
            },
        )

    json_module = json
    monkeypatch.setattr(httpx, "post", _post)

    result = classifier.classify(
        job_id="job-unsupported",
        media_uri="gs://chronos-dev/uploads/unsupported.mov",
        original_filename="unsupported.mov",
        mime_type="video/quicktime",
        era_profile=valid_detect_request()["era_profile"],
    )

    assert result.era == "Unknown Era"
    assert result.provider_error == "Primary Gemini classifier returned an unsupported era label. Manual confirmation required."
    assert result.top_candidates == [
        {"era": "1960s Kodachrome Film", "confidence": 0.51},
        {"era": "1980s VHS Tape", "confidence": 0.33},
    ]


def test_raw_response_store_returns_gcs_uri(monkeypatch) -> None:
    store = GcsRawResponseStore(bucket_name="chronos-dev", prefix="era-detection/raw")

    def _post(url, *, params=None, headers=None, content=None, timeout=None):
        assert params["uploadType"] == "media"
        assert params["name"].startswith("era-detection/raw/job-123/")
        assert headers["Authorization"] == "Bearer gcp-access-token"
        assert content
        return httpx.Response(200, request=httpx.Request("POST", url), json={"name": params["name"]})

    monkeypatch.setattr(httpx, "post", _post)

    uri = store.store(
        job_id="job-123",
        response_id="resp-2",
        payload={"status": "ok"},
        access_token="gcp-access-token",
    )

    assert uri == "gs://chronos-dev/era-detection/raw/job-123/resp-2.json"
