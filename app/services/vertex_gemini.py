"""Vertex AI Gemini era-classifier integration and raw-response storage."""

from __future__ import annotations

import json
import subprocess
import uuid
from base64 import b64decode
from typing import Any

import httpx

from app.config import settings
from app.services.era_classifier import (
    ClassifierError,
    UNKNOWN_ERA,
    EraClassification,
    EraClassifierUsage,
    build_default_era_profile,
    canonicalize_era_label,
    normalize_top_candidates,
)

_METADATA_TOKEN_URL = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
_GCS_UPLOAD_URL = "https://storage.googleapis.com/upload/storage/v1/b/{bucket}/o"
_PROMPT_TEMPLATE = """Classify the historical era of this media.

Return strict JSON with this shape:
{
  "era": "string",
  "confidence": 0.0,
  "top_candidates": [{"era": "string", "confidence": 0.0}],
  "forensic_markers": {
    "grain_structure": "string",
    "color_saturation": 0.0,
    "format_artifacts": ["string"]
  }
}

Rules:
- Confidence must be between 0.0 and 1.0.
- top_candidates must contain exactly 3 unique eras sorted by confidence descending.
- forensic_markers must reflect the visible media evidence.
- Use the era profile as a prior, but prefer visible evidence from the media."""


class GoogleAccessTokenProvider:
    def access_token(self) -> str | None:
        if settings.gcp_access_token:
            return settings.gcp_access_token
        metadata_token = self._metadata_token()
        if metadata_token:
            return metadata_token
        return self._gcloud_token()

    def _metadata_token(self) -> str | None:
        try:
            response = httpx.get(
                _METADATA_TOKEN_URL,
                headers={"Metadata-Flavor": "Google"},
                timeout=2.0,
            )
            response.raise_for_status()
            return response.json().get("access_token")
        except httpx.HTTPError:
            return None

    def _gcloud_token(self) -> str | None:
        try:
            completed = subprocess.run(
                ["gcloud", "auth", "print-access-token"],
                check=True,
                capture_output=True,
                text=True,
                timeout=10.0,
            )
        except (subprocess.SubprocessError, FileNotFoundError):
            return None
        token = completed.stdout.strip()
        return token or None


class GcsRawResponseStore:
    def __init__(self, bucket_name: str | None = None, prefix: str | None = None) -> None:
        self.bucket_name = bucket_name or settings.gcs_bucket_name
        self.prefix = (prefix or settings.gemini_raw_response_prefix).strip("/")

    def store(self, *, job_id: str, response_id: str | None, payload: dict[str, Any], access_token: str) -> str | None:
        if not self.bucket_name:
            return None
        object_name = f"{self.prefix}/{job_id}/{response_id or uuid.uuid4().hex}.json"
        response = httpx.post(
            _GCS_UPLOAD_URL.format(bucket=self.bucket_name),
            params={"uploadType": "media", "name": object_name},
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            content=json.dumps(payload).encode("utf-8"),
            timeout=10.0,
        )
        response.raise_for_status()
        return f"gs://{self.bucket_name}/{object_name}"


class VertexGeminiEraClassifier:
    def __init__(
        self,
        *,
        token_provider: GoogleAccessTokenProvider | None = None,
        raw_response_store: GcsRawResponseStore | None = None,
    ) -> None:
        self._token_provider = token_provider or GoogleAccessTokenProvider()
        self._raw_response_store = raw_response_store or GcsRawResponseStore()

    def classify(
        self,
        *,
        job_id: str,
        media_uri: str,
        original_filename: str,
        mime_type: str,
        era_profile: dict[str, Any] | None = None,
    ) -> EraClassification:
        access_token = self._token_provider.access_token()
        if not access_token:
            raise ClassifierError("Google access token is not available for Vertex Gemini requests.")
        resolved_era_profile = (
            era_profile
            if era_profile is not None
            else build_default_era_profile(
                media_uri=media_uri,
                original_filename=original_filename,
                mime_type=mime_type,
            )
        )
        response_payload = self._generate_content(
            access_token=access_token,
            media_uri=media_uri,
            original_filename=original_filename,
            mime_type=mime_type,
            era_profile=resolved_era_profile,
        )
        parsed = self._parse_candidate_payload(response_payload)
        try:
            raw_response_gcs_uri = self._raw_response_store.store(
                job_id=job_id,
                response_id=response_payload.get("responseId"),
                payload=response_payload,
                access_token=access_token,
            )
        except httpx.HTTPError:
            raw_response_gcs_uri = None
        usage_metadata = response_payload.get("usageMetadata") or {}
        canonical_era = canonicalize_era_label(parsed["era"])
        provider_error = None
        if canonical_era is None:
            canonical_era = UNKNOWN_ERA
            provider_error = "Primary Gemini classifier returned an unsupported era label. Manual confirmation required."
        return EraClassification(
            era=canonical_era,
            confidence=_clamp_confidence(parsed["confidence"]),
            forensic_markers=_normalize_forensic_markers(parsed.get("forensic_markers") or {}),
            top_candidates=normalize_top_candidates(parsed.get("top_candidates") or []),
            model_version=response_payload.get("modelVersion") or settings.gemini_model,
            prompt_version=settings.gemini_prompt_version,
            raw_response=response_payload,
            raw_response_gcs_uri=raw_response_gcs_uri,
            usage=EraClassifierUsage(
                prompt_token_count=int(usage_metadata.get("promptTokenCount", 0) or 0),
                candidates_token_count=int(
                    usage_metadata.get("candidatesTokenCount", usage_metadata.get("candidateTokenCount", 0)) or 0
                ),
                total_token_count=int(usage_metadata.get("totalTokenCount", 0) or 0),
                api_call_count=1,
            ),
            provider_error=provider_error,
        )

    def _generate_content(
        self,
        *,
        access_token: str,
        media_uri: str,
        original_filename: str,
        mime_type: str,
        era_profile: dict[str, Any],
    ) -> dict[str, Any]:
        endpoint = (
            f"https://{settings.gcp_region}-aiplatform.googleapis.com/v1/projects/{settings.gcp_project_id}"
            f"/locations/{settings.gcp_region}/publishers/google/models/{settings.gemini_model}:generateContent"
        )
        payload = {
            "systemInstruction": {
                "parts": [{"text": _PROMPT_TEMPLATE}],
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": json.dumps(
                                {
                                    "original_filename": original_filename,
                                    "mime_type": mime_type or "application/octet-stream",
                                    "era_profile": era_profile,
                                }
                            )
                        },
                        _media_part(media_uri=media_uri, mime_type=mime_type),
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "topP": 0.8,
                "candidateCount": 1,
                "responseMimeType": "application/json",
            },
        }
        response = httpx.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=20.0,
        )
        response.raise_for_status()
        return response.json()

    def _parse_candidate_payload(self, response_payload: dict[str, Any]) -> dict[str, Any]:
        candidates = response_payload.get("candidates") or []
        if not candidates:
            raise ClassifierError("Vertex Gemini response did not contain candidates.")
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text_part = next((part.get("text") for part in parts if part.get("text")), "")
        if not text_part:
            raise ClassifierError("Vertex Gemini response did not contain JSON text output.")
        try:
            parsed = json.loads(text_part)
        except json.JSONDecodeError as exc:
            raise ClassifierError("Vertex Gemini response did not contain valid JSON output.") from exc
        if not isinstance(parsed, dict):
            raise ClassifierError("Vertex Gemini JSON output must be an object.")
        return parsed


def _clamp_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError) as exc:
        raise ClassifierError("Vertex Gemini response omitted a valid confidence value.") from exc
    return max(0.0, min(confidence, 1.0))


def _normalize_forensic_markers(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "grain_structure": str(payload.get("grain_structure") or "unknown grain signature"),
        "color_saturation": float(payload.get("color_saturation", 0.0) or 0.0),
        "format_artifacts": [str(item) for item in payload.get("format_artifacts") or []],
    }
def _media_part(*, media_uri: str, mime_type: str) -> dict[str, Any]:
    if media_uri.startswith("data:"):
        header, encoded = media_uri.split(",", 1)
        inferred_mime_type = header.removeprefix("data:").split(";", 1)[0] or mime_type or "application/octet-stream"
        # Validate the payload before forwarding it to Vertex.
        b64decode(encoded, validate=True)
        return {
            "inlineData": {
                "mimeType": inferred_mime_type,
                "data": encoded,
            }
        }
    return {
        "fileData": {
            "mimeType": mime_type or "application/octet-stream",
            "fileUri": media_uri,
        }
    }
