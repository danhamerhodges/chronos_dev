"""Shared configuration fingerprint and preview-launch identity helpers."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import NAMESPACE_URL, uuid5


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def core_job_payload(job_payload: dict[str, Any]) -> dict[str, Any]:
    payload = dict(job_payload)
    payload.pop("launch_context", None)
    return payload


def configuration_fingerprint(*, configured_at: str, job_payload_preview: dict[str, Any]) -> str:
    return sha256_hex(
        canonical_json(
            {
                "configured_at": configured_at,
                "job_payload_preview": core_job_payload(job_payload_preview),
            }
        )
    )


def preview_launch_external_job_id(*, preview_id: str, configuration_fingerprint_value: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"preview-launch:{preview_id}:{configuration_fingerprint_value}"))
