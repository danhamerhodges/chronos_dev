#!/usr/bin/env python3
"""Opt-in live diagnostic for job progress Realtime channels."""

from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any

import httpx
import psycopg
from supabase import create_async_client


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"{name} is required")
    return value


def _require_env_with_fallback(primary: str, fallback: str) -> str:
    value = os.getenv(primary, "").strip() or os.getenv(fallback, "").strip()
    if not value:
        raise SystemExit(f"{primary} or {fallback} is required")
    return value


def _valid_job_request() -> dict[str, Any]:
    return {
        "media_uri": "gs://chronos-dev/input/realtime-diagnostic.mov",
        "original_filename": "realtime-diagnostic.mov",
        "mime_type": "video/quicktime",
        "estimated_duration_seconds": 12,
        "source_asset_checksum": f"realtime-diagnostic-{int(time.time())}",
        "fidelity_tier": "Restore",
        "processing_mode": "balanced",
        "era_profile": {
            "capture_medium": "16mm",
            "mode": "Restore",
            "tier": "Pro",
            "resolution_cap": "4k",
            "hallucination_limit": 0.15,
            "artifact_policy": {
                "deinterlace": False,
                "grain_intensity": "Matched",
                "preserve_edge_fog": True,
                "preserve_chromatic_aberration": True,
            },
            "era_range": {"start_year": 1970, "end_year": 1995},
            "gemini_confidence": 0.92,
            "manual_confirmation_required": False,
        },
        "config": {"stabilization": "medium", "color_balance": "neutral"},
    }


def _build_auth_headers() -> dict[str, str]:
    headers = {"Authorization": f"Bearer {_require_env('CHRONOS_REALTIME_DIAG_BEARER_TOKEN')}"}
    for env_name, header_name in (
        ("CHRONOS_REALTIME_DIAG_ROLE", "X-Chronos-Role"),
        ("CHRONOS_REALTIME_DIAG_TIER", "X-Chronos-Tier"),
        ("CHRONOS_REALTIME_DIAG_ORG", "X-Chronos-Org"),
    ):
        value = os.getenv(env_name, "").strip()
        if value:
            headers[header_name] = value
    return headers


async def _broadcast_progress_event(topic: str, payload: dict[str, Any]) -> None:
    conn = psycopg.connect(
        host=_require_env("SUPABASE_DB_HOST"),
        port=_require_env("SUPABASE_DB_PORT"),
        dbname=_require_env("SUPABASE_DB_NAME"),
        user=_require_env("SUPABASE_DB_USER"),
        password=_require_env("SUPABASE_DB_PASSWORD"),
        sslmode="require",
    )
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                "select realtime.send(%s::jsonb, %s, %s, %s)",
                (json.dumps(payload), "progress_update", topic, True),
            )
    finally:
        conn.close()


async def _run() -> None:
    if os.getenv("CHRONOS_RUN_REALTIME_DIAGNOSTIC") != "1":
        raise SystemExit("Set CHRONOS_RUN_REALTIME_DIAGNOSTIC=1 to run the realtime progress diagnostic.")

    base_url = _require_env("CHRONOS_REALTIME_DIAG_BASE_URL").rstrip("/")
    timeout_seconds = float(os.getenv("CHRONOS_REALTIME_DIAG_TIMEOUT_SECONDS", "15"))

    async with httpx.AsyncClient(timeout=20.0) as http:
        created = await http.post(f"{base_url}/v1/jobs", headers=_build_auth_headers(), json=_valid_job_request())
        created.raise_for_status()
        created_payload = created.json()
        topic = str(created_payload["progress_topic"])
        job_id = str(created_payload["job_id"])

    subscriber = await create_async_client(
        _require_env("SUPABASE_URL"),
        _require_env_with_fallback("SUPABASE_ANON_KEY", "SUPABASE_ANON_KEY_DEV"),
    )
    await subscriber.realtime.set_auth(_require_env("CHRONOS_REALTIME_DIAG_BEARER_TOKEN"))
    channel = subscriber.channel(
        topic,
        {"config": {"broadcast": {"ack": True, "self": False}, "presence": {"enabled": False}, "private": True}},
    )

    subscribe_states: list[str] = []
    subscribe_errors: list[str] = []
    received: dict[str, Any] = {}
    subscribed = asyncio.Event()
    delivered = asyncio.Event()

    def _subscribe_callback(state: Any, error: Exception | None) -> None:
        subscribe_states.append(getattr(state, "name", str(state)))
        if error is not None:
            subscribe_errors.append(str(error))
        if getattr(state, "name", str(state)) in {"SUBSCRIBED", "CHANNEL_ERROR", "TIMED_OUT"}:
            subscribed.set()

    def _capture(payload: dict[str, Any]) -> None:
        received.update(payload)
        delivered.set()

    channel.on_broadcast("progress_update", _capture)
    channel.on_system(lambda payload: subscribe_states.append(f"SYSTEM:{payload.get('status', 'unknown')}"))
    await channel.subscribe(_subscribe_callback)
    await asyncio.wait_for(subscribed.wait(), timeout=10)

    if "SUBSCRIBED" not in subscribe_states:
        raise SystemExit(
            f"Realtime subscription did not reach SUBSCRIBED. states={subscribe_states!r} errors={subscribe_errors!r}"
        )

    payload = {
        "job_id": job_id,
        "segment_index": 0,
        "segment_count": 1,
        "percent_complete": 12.5,
        "eta_seconds": 9,
        "status": "processing",
        "current_operation": "Realtime diagnostic",
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    try:
        await _broadcast_progress_event(topic, payload)
        await asyncio.wait_for(delivered.wait(), timeout=timeout_seconds)
        print(
            {
                "job_id": job_id,
                "progress_topic": topic,
                "subscribe_states": subscribe_states,
                "subscribe_errors": subscribe_errors,
                "event_received": True,
                "event_payload": received,
            }
        )
    finally:
        await subscriber.remove_channel(channel)


if __name__ == "__main__":
    asyncio.run(_run())
