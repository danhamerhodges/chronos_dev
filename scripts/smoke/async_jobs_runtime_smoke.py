#!/usr/bin/env python3
"""Opt-in live smoke for Packet 3A runtime bindings."""

from __future__ import annotations

import asyncio
import base64
import os
import time
from typing import Any

import httpx
from google.cloud import pubsub_v1
from supabase import create_async_client

from app.services.job_dispatcher import decode_dispatch_message_data

TERMINAL_STATUSES = {"completed", "partial", "failed", "cancelled"}


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


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name, "").strip()
    return float(value) if value else default


def _build_auth_headers() -> dict[str, str]:
    headers = {"Authorization": f"Bearer {_require_env('CHRONOS_ASYNC_SMOKE_BEARER_TOKEN')}"}
    for env_name, header_name in (
        ("CHRONOS_ASYNC_SMOKE_ROLE", "X-Chronos-Role"),
        ("CHRONOS_ASYNC_SMOKE_TIER", "X-Chronos-Tier"),
        ("CHRONOS_ASYNC_SMOKE_ORG", "X-Chronos-Org"),
    ):
        value = os.getenv(env_name, "").strip()
        if value:
            headers[header_name] = value
    return headers


def _valid_job_request() -> dict[str, Any]:
    return {
        "media_uri": "gs://chronos-dev/input/runtime-smoke.mov",
        "original_filename": "runtime-smoke.mov",
        "mime_type": "video/quicktime",
        "estimated_duration_seconds": 22,
        "source_asset_checksum": f"runtime-smoke-{int(time.time())}",
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


def _pull_matching_message(job_id: str) -> tuple[pubsub_v1.SubscriberClient, Any, dict[str, Any]]:
    subscription = _require_env("CHRONOS_ASYNC_SMOKE_PUBSUB_SUBSCRIPTION")
    timeout_seconds = _env_float("CHRONOS_ASYNC_SMOKE_PUBSUB_TIMEOUT_SECONDS", 20.0)
    deadline = time.monotonic() + timeout_seconds
    subscriber = pubsub_v1.SubscriberClient()

    while time.monotonic() < deadline:
        response = subscriber.pull(
            request={"subscription": subscription, "max_messages": 5},
            timeout=min(5.0, max(deadline - time.monotonic(), 0.1)),
        )
        for received in response.received_messages:
            try:
                payload = decode_dispatch_message_data(received.message.data)
            except ValueError:
                subscriber.modify_ack_deadline(
                    request={"subscription": subscription, "ack_ids": [received.ack_id], "ack_deadline_seconds": 0}
                )
                continue

            if payload.get("job_id") == job_id:
                return subscriber, received, payload

            subscriber.modify_ack_deadline(
                request={"subscription": subscription, "ack_ids": [received.ack_id], "ack_deadline_seconds": 0}
            )

    raise SystemExit("Timed out waiting for the dispatched Pub/Sub message for the created job.")


async def _wait_for_progress_event(job_id: str, *, ready: asyncio.Event) -> dict[str, Any]:
    timeout_seconds = _env_float("CHRONOS_ASYNC_SMOKE_REALTIME_TIMEOUT_SECONDS", 20.0)
    client = await create_async_client(
        _require_env("SUPABASE_URL"),
        _require_env_with_fallback("SUPABASE_ANON_KEY", "SUPABASE_ANON_KEY_DEV"),
    )
    await client.realtime.set_auth(_require_env("CHRONOS_ASYNC_SMOKE_BEARER_TOKEN"))
    channel = client.channel(
        f"job_progress:{job_id}",
        {"config": {"broadcast": {"ack": True, "self": False}, "presence": {"enabled": False}, "private": True}},
    )
    event = asyncio.Event()
    received: dict[str, Any] = {}

    def _capture(payload: dict[str, Any]) -> None:
        received.update(payload)
        event.set()

    channel.on_broadcast("progress_update", _capture)
    await channel.subscribe()
    ready.set()
    try:
        await asyncio.wait_for(event.wait(), timeout=timeout_seconds)
        return dict(received)
    finally:
        await client.remove_channel(channel)


async def _poll_job_status(http: httpx.AsyncClient, *, base_url: str, headers: dict[str, str], job_id: str) -> dict[str, Any]:
    timeout_seconds = _env_float("CHRONOS_ASYNC_SMOKE_STATUS_TIMEOUT_SECONDS", 30.0)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        response = await http.get(f"{base_url}/v1/jobs/{job_id}", headers=headers)
        response.raise_for_status()
        payload = response.json()
        if payload["status"] in TERMINAL_STATUSES:
            return payload
        await asyncio.sleep(1)
    raise SystemExit("Timed out waiting for the async job to reach a terminal status.")


async def _run() -> None:
    if os.getenv("CHRONOS_RUN_ASYNC_RUNTIME_SMOKE") != "1":
        raise SystemExit("Set CHRONOS_RUN_ASYNC_RUNTIME_SMOKE=1 to run the async jobs runtime smoke.")

    base_url = _require_env("CHRONOS_ASYNC_SMOKE_BASE_URL").rstrip("/")
    auth_headers = _build_auth_headers()
    trusted_token = _require_env("JOB_WORKER_TRUSTED_TOKEN")
    expect_realtime = os.getenv("CHRONOS_ASYNC_SMOKE_EXPECT_REALTIME", "1").strip().lower() not in {"0", "false", "no"}

    async with httpx.AsyncClient(timeout=20.0) as http:
        created_response = await http.post(f"{base_url}/v1/jobs", headers=auth_headers, json=_valid_job_request())
        created_response.raise_for_status()
        created = created_response.json()
        job_id = created["job_id"]

        progress_ready = asyncio.Event()
        progress_task = (
            asyncio.create_task(_wait_for_progress_event(job_id, ready=progress_ready))
            if expect_realtime
            else None
        )
        if progress_task is not None:
            await asyncio.wait_for(progress_ready.wait(), timeout=10)
        subscriber, received, dispatch_payload = _pull_matching_message(job_id)
        worker_payload = {
            "message": {
                "data": base64.b64encode(received.message.data).decode("utf-8"),
                "attributes": dict(received.message.attributes),
            }
        }

        try:
            worker_response = await http.post(
                f"{base_url}/internal/workers/jobs/run",
                headers={"X-Chronos-Worker-Token": trusted_token},
                json=worker_payload,
            )
            worker_response.raise_for_status()
        except Exception:
            subscriber.modify_ack_deadline(
                request={
                    "subscription": _require_env("CHRONOS_ASYNC_SMOKE_PUBSUB_SUBSCRIPTION"),
                    "ack_ids": [received.ack_id],
                    "ack_deadline_seconds": 0,
                }
            )
            if progress_task is not None:
                progress_task.cancel()
            raise

        subscriber.acknowledge(
            request={"subscription": _require_env("CHRONOS_ASYNC_SMOKE_PUBSUB_SUBSCRIPTION"), "ack_ids": [received.ack_id]}
        )

        progress_payload = await progress_task if progress_task is not None else None
        job_status = await _poll_job_status(http, base_url=base_url, headers=auth_headers, job_id=job_id)

    print(
        {
            "job_id": job_id,
            "dispatch_job_id": dispatch_payload.get("job_id"),
            "worker_status": worker_response.json().get("status"),
            "final_status": job_status["status"],
            "progress_topic": created["progress_topic"],
            "progress_event_received": bool(progress_payload),
            "progress_status": progress_payload.get("payload", {}).get("status") if progress_payload else None,
        }
    )


if __name__ == "__main__":
    asyncio.run(_run())
